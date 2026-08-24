import contextlib
import datetime
import os

import octobot_commons.constants as commons_constants
import octobot_commons.databases.relational_databases.sqlite.base_sqlite_database as base_sqlite_database

import octobot_trading.constants as trading_constants
import octobot_trading.exchange_data.exchange_cache_key as exchange_cache_key_module

MARKET_DATA_DB_FILENAME = "market_data.sqlite"
SCHEMA_VERSION = 1


class MarketDataSQLiteDatabase(base_sqlite_database.BaseSQLiteDatabase):
    def __init__(self, file_name, read_only: bool = False):
        super().__init__(file_name, read_only=read_only)
        self._schema_initialized = False

    @classmethod
    def get_db_path(
        cls,
        exchange_name: str,
        exchange_type: str,
        sandboxed: bool,
        data_root: str = None,
    ) -> str:
        exchange_key = exchange_cache_key_module.get_exchange_key(
            exchange_name, exchange_type, sandboxed
        )
        root = data_root or os.path.join(
            commons_constants.USER_FOLDER, commons_constants.DATA_FOLDER
        )
        return os.path.join(
            root,
            trading_constants.EXCHANGE_CACHE_FOLDER,
            exchange_key,
            MARKET_DATA_DB_FILENAME,
        )

    async def _table_exists(self, table_name: str) -> bool:
        row = await self.fetchone(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (table_name,),
        )
        return row is not None

    async def _ensure_schema(self) -> None:
        if self._schema_initialized:
            return
        await self.execute("BEGIN IMMEDIATE")
        await self.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
        )
        # daily_closes: PRIMARY KEY (symbol, day_ts) is the upsert index for merge_daily_closes;
        # WITHOUT ROWID stores rows in the PK btree (no secondary indexes).
        await self.execute(
            "CREATE TABLE IF NOT EXISTS daily_closes ("
            "symbol TEXT NOT NULL, day_ts INTEGER NOT NULL, close REAL NOT NULL, "
            "PRIMARY KEY (symbol, day_ts)) WITHOUT ROWID"
        )
        # latest_tickers: PRIMARY KEY (symbol) is the upsert index for update_latest_tickers.
        await self.execute(
            "CREATE TABLE IF NOT EXISTS latest_tickers ("
            "symbol TEXT PRIMARY KEY, close REAL NOT NULL, updated_at TEXT NOT NULL)"
        )
        # daily_close_sources: maps base asset to the exchange-native symbol used for daily closes.
        await self.execute(
            "CREATE TABLE IF NOT EXISTS daily_close_sources ("
            "reference_asset TEXT PRIMARY KEY, fetch_symbol TEXT NOT NULL) WITHOUT ROWID"
        )
        existing_version = await self.fetchone("SELECT version FROM schema_version LIMIT 1")
        if existing_version is None:
            await self.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
        await self.commit()
        self._schema_initialized = True

    async def merge_daily_closes(self, symbol: str, closes_by_timestamp: dict[str, float]) -> None:
        await self._ensure_schema()
        rows = [
            (symbol, int(day_timestamp), close)
            for day_timestamp, close in closes_by_timestamp.items()
        ]
        if not rows:
            return
        await self.executemany(
            "INSERT INTO daily_closes (symbol, day_ts, close) VALUES (?, ?, ?) "
            "ON CONFLICT(symbol, day_ts) DO UPDATE SET close=excluded.close",
            rows,
        )
        await self.commit()

    async def load_daily_prices_dict(self) -> dict:
        if not await self._table_exists("daily_closes"):
            return {"symbols": {}, "sources": {}}
        rows = await self.fetchall("SELECT symbol, day_ts, close FROM daily_closes")
        symbols: dict[str, dict[str, float]] = {}
        for symbol, day_timestamp, close in rows:
            symbols.setdefault(symbol, {})[str(day_timestamp)] = close
        sources = await self._load_daily_close_sources()
        return {"symbols": symbols, "sources": sources}

    async def _load_daily_close_sources(self) -> dict[str, str]:
        if not await self._table_exists("daily_close_sources"):
            return {}
        rows = await self.fetchall(
            "SELECT reference_asset, fetch_symbol FROM daily_close_sources"
        )
        return {reference_asset: fetch_symbol for reference_asset, fetch_symbol in rows}

    async def set_daily_close_source(self, reference_asset: str, fetch_symbol: str) -> None:
        await self._ensure_schema()
        await self.execute(
            "INSERT INTO daily_close_sources (reference_asset, fetch_symbol) VALUES (?, ?) "
            "ON CONFLICT(reference_asset) DO UPDATE SET fetch_symbol=excluded.fetch_symbol",
            (reference_asset, fetch_symbol),
        )
        await self.commit()

    async def get_daily_close_source(self, reference_asset: str) -> str | None:
        if not await self._table_exists("daily_close_sources"):
            return None
        row = await self.fetchone(
            "SELECT fetch_symbol FROM daily_close_sources WHERE reference_asset = ?",
            (reference_asset,),
        )
        if row is None:
            return None
        return row[0]

    async def rename_daily_closes_symbol(self, old_symbol: str, new_symbol: str) -> None:
        await self._ensure_schema()
        await self.execute("BEGIN IMMEDIATE")
        await self.execute(
            "INSERT INTO daily_closes (symbol, day_ts, close) "
            "SELECT ?, day_ts, close FROM daily_closes WHERE symbol = ? "
            "ON CONFLICT(symbol, day_ts) DO UPDATE SET close=excluded.close",
            (new_symbol, old_symbol),
        )
        await self.execute("DELETE FROM daily_closes WHERE symbol = ?", (old_symbol,))
        await self.commit()

    async def oldest_day_ts(self, symbol: str) -> float | None:
        if not await self._table_exists("daily_closes"):
            return None
        row = await self.fetchone(
            "SELECT MIN(day_ts) FROM daily_closes WHERE symbol = ?",
            (symbol,),
        )
        if row is None or row[0] is None:
            return None
        return float(row[0])

    async def newest_day_ts(self, symbol: str) -> float | None:
        if not await self._table_exists("daily_closes"):
            return None
        row = await self.fetchone(
            "SELECT MAX(day_ts) FROM daily_closes WHERE symbol = ?",
            (symbol,),
        )
        if row is None or row[0] is None:
            return None
        return float(row[0])

    async def update_latest_tickers(self, closes: dict[str, float]) -> None:
        await self._ensure_schema()
        updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        rows = [(symbol, close, updated_at) for symbol, close in closes.items()]
        if not rows:
            return
        await self.executemany(
            "INSERT INTO latest_tickers (symbol, close, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(symbol) DO UPDATE SET close=excluded.close, updated_at=excluded.updated_at",
            rows,
        )
        await self.commit()

    async def load_latest_tickers_dict(self) -> dict:
        if not await self._table_exists("latest_tickers"):
            return {"updated_at": None, "closes": {}}
        rows = await self.fetchall("SELECT symbol, close, updated_at FROM latest_tickers")
        closes = {symbol: close for symbol, close, _updated_at in rows}
        updated_at = max((row[2] for row in rows), default=None) if rows else None
        return {"updated_at": updated_at, "closes": closes}


@contextlib.asynccontextmanager
async def open_market_data_sqlite_database(
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    data_root: str = None,
    read_only: bool = False,
):
    db_path = MarketDataSQLiteDatabase.get_db_path(
        exchange_name, exchange_type, sandboxed, data_root
    )
    if read_only:
        async with base_sqlite_database.open_sqlite_database(
            MarketDataSQLiteDatabase, db_path, read_only=True
        ) as database:
            yield database
    else:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        async with base_sqlite_database.open_sqlite_database(
            MarketDataSQLiteDatabase, db_path, read_only=False
        ) as database:
            yield database
