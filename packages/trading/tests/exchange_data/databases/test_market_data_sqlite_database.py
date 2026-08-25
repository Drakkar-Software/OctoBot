import asyncio
import os
import time

import pytest

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_commons.databases.relational_databases.sqlite.base_sqlite_database as base_sqlite_database_module
import octobot_trading.exchange_data.prices.persisted_price_cache as persisted_price_cache
import octobot_trading.exchange_data.databases.market_data_sqlite_database as market_data_sqlite_database_module


_CONCURRENT_READ_SLEEP_SECONDS = 0.05
_CONCURRENT_READ_MAX_ELAPSED_SECONDS = 0.15


@pytest.fixture
def data_root(tmp_path):
    return str(tmp_path)


class TestMarketDataSqliteDatabasePath:
    def test_db_path_under_exchange_cache(self, data_root):
        path = market_data_sqlite_database_module.MarketDataSQLiteDatabase.get_db_path(
            "binance", "spot", False, data_root
        )
        assert path.endswith(os.path.join("binance_spot_False", "market_data.sqlite"))
        assert trading_constants.EXCHANGE_CACHE_FOLDER in path


class TestMarketDataSqliteDatabaseSchema:
    @pytest.mark.asyncio
    async def test_tables_exist_after_init(self, data_root):
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            await database.merge_daily_closes("BTC/USDT", {"1000": 1.0})
        db_path = market_data_sqlite_database_module.MarketDataSQLiteDatabase.get_db_path(
            "binance", "spot", False, data_root
        )
        assert os.path.isfile(db_path)

    @pytest.mark.asyncio
    async def test_daily_closes_uses_without_rowid(self, data_root):
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            await database.merge_daily_closes("BTC/USDT", {"1000": 1.0})
            create_sql_row = await database.fetchone(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='daily_closes'"
            )
        assert create_sql_row is not None
        assert "WITHOUT ROWID" in create_sql_row[0].upper()


class TestDailyClosesQueryPlan:
    @pytest.mark.asyncio
    async def test_pk_lookup_uses_primary_key(self, data_root):
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            await database.merge_daily_closes("BTC/USDT", {"1000": 42000.0})
            plan_rows = await database.fetchall(
                "EXPLAIN QUERY PLAN SELECT close FROM daily_closes "
                "WHERE symbol = ? AND day_ts = ?",
                ("BTC/USDT", 1000),
            )
        plan_text = " ".join(str(column) for row in plan_rows for column in row).upper()
        assert "PRIMARY KEY" in plan_text


class TestMergeDailyCloses:
    @pytest.mark.asyncio
    async def test_merge_and_overwrite_same_day(self, data_root):
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            await database.merge_daily_closes("BTC/USDT", {"1000": 42000.0, "2000": 43000.0})
            await database.merge_daily_closes("BTC/USDT", {"1000": 42500.0})
            result = await database.load_daily_prices_dict()
        assert result[trading_enums.DailyPricesCacheKeys.SYMBOLS]["BTC/USDT"] == {"1000": 42500.0, "2000": 43000.0}


class TestLoadDailyPricesDict:
    @pytest.mark.asyncio
    async def test_empty_database(self, data_root):
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            pass
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=True
        ) as database:
            result = await database.load_daily_prices_dict()
        assert result == {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }

    @pytest.mark.asyncio
    async def test_multi_symbol_shape(self, data_root):
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            await database.merge_daily_closes("BTC/USDT", {"1000": 1.0})
            await database.merge_daily_closes("ETH/USDT", {"1000": 2.0})
            result = await database.load_daily_prices_dict()
        assert result == {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"1000": 1.0}, "ETH/USDT": {"1000": 2.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }


class TestDailyCloseSources:
    @pytest.mark.asyncio
    async def test_set_and_load_source(self, data_root):
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            await database.set_daily_close_source("KNC", "KNC/USD")
            result = await database.load_daily_prices_dict()
            assert await database.get_daily_close_source("KNC") == "KNC/USD"
        assert result[trading_enums.DailyPricesCacheKeys.SOURCES] == {"KNC": "KNC/USD"}


class TestRenameDailyClosesSymbol:
    @pytest.mark.asyncio
    async def test_moves_rows_to_new_symbol(self, data_root):
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            await database.merge_daily_closes("KNC/USD", {"1000": 1.0, "2000": 1.1})
            await database.rename_daily_closes_symbol("KNC/USD", "KNC/USDC")
            result = await database.load_daily_prices_dict()
        assert "KNC/USD" not in result[trading_enums.DailyPricesCacheKeys.SYMBOLS]
        assert result[trading_enums.DailyPricesCacheKeys.SYMBOLS]["KNC/USDC"] == {"1000": 1.0, "2000": 1.1}

    @pytest.mark.asyncio
    async def test_conflict_keeps_migrated_value(self, data_root):
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            await database.merge_daily_closes("KNC/USD", {"1000": 1.0})
            await database.merge_daily_closes("KNC/USDC", {"1000": 2.0})
            await database.rename_daily_closes_symbol("KNC/USD", "KNC/USDC")
            result = await database.load_daily_prices_dict()
        assert result[trading_enums.DailyPricesCacheKeys.SYMBOLS]["KNC/USDC"] == {"1000": 1.0}


class TestOldestNewestDayTs:
    @pytest.mark.asyncio
    async def test_oldest_and_newest(self, data_root):
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            await database.merge_daily_closes("BTC/USDT", {"1000": 1.0, "3000": 3.0, "2000": 2.0})
            oldest = await database.oldest_day_ts("BTC/USDT")
            newest = await database.newest_day_ts("BTC/USDT")
        assert oldest == 1000.0
        assert newest == 3000.0


class TestUpdateLatestTickers:
    @pytest.mark.asyncio
    async def test_merge_and_updated_at(self, data_root):
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            await database.update_latest_tickers({"BTC/USDT": 65000.0})
            result = await database.load_latest_tickers_dict()
        assert result[trading_enums.LatestTickersCacheKeys.CLOSES]["BTC/USDT"] == 65000.0
        assert result[trading_enums.LatestTickersCacheKeys.UPDATED_AT] is not None


class TestPerDbPathLock:
    @pytest.mark.asyncio
    async def test_concurrent_merges_serialize(self, data_root):
        async def merge_closes(close_value: float):
            async with market_data_sqlite_database_module.open_market_data_sqlite_database(
                "binance", "spot", False, data_root, read_only=False
            ) as database:
                await database.merge_daily_closes("BTC/USDT", {"1000": close_value})
                await asyncio.sleep(0.01)
                return await database.load_daily_prices_dict()

        first_result, second_result = await asyncio.gather(
            merge_closes(1.0),
            merge_closes(2.0),
        )
        final = first_result if first_result[trading_enums.DailyPricesCacheKeys.SYMBOLS] else second_result
        assert final[trading_enums.DailyPricesCacheKeys.SYMBOLS]["BTC/USDT"]["1000"] in (1.0, 2.0)


class TestConcurrentReadOnlyOpens:
    @pytest.mark.asyncio
    async def test_concurrent_read_only_loads_do_not_block(self, data_root):
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            await database.merge_daily_closes("BTC/USDT", {"1000": 42000.0})

        async def read_prices():
            async with market_data_sqlite_database_module.open_market_data_sqlite_database(
                "binance", "spot", False, data_root, read_only=True
            ) as database:
                await asyncio.sleep(_CONCURRENT_READ_SLEEP_SECONDS)
                return await database.load_daily_prices_dict()

        started_at = time.monotonic()
        first_result, second_result = await asyncio.gather(read_prices(), read_prices())
        elapsed = time.monotonic() - started_at
        assert first_result[trading_enums.DailyPricesCacheKeys.SYMBOLS]["BTC/USDT"]["1000"] == 42000.0
        assert second_result[trading_enums.DailyPricesCacheKeys.SYMBOLS]["BTC/USDT"]["1000"] == 42000.0
        assert elapsed < _CONCURRENT_READ_MAX_ELAPSED_SECONDS


class TestCrashRecovery:
    @pytest.mark.asyncio
    async def test_committed_data_passes_integrity_check_after_reopen(self, data_root):
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            await database.merge_daily_closes("BTC/USDT", {"1000": 42000.0})

        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=True
        ) as database:
            integrity_row = await database.fetchone("PRAGMA integrity_check")
            result = await database.load_daily_prices_dict()

        assert integrity_row == ("ok",)
        assert result[trading_enums.DailyPricesCacheKeys.SYMBOLS]["BTC/USDT"]["1000"] == 42000.0

    @pytest.mark.asyncio
    async def test_uncommitted_write_discarded_after_abrupt_connection_close(self, data_root):
        db_path = market_data_sqlite_database_module.MarketDataSQLiteDatabase.get_db_path(
            "binance", "spot", False, data_root
        )
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            await database.merge_daily_closes("BTC/USDT", {"1000": 1.0})

        async with base_sqlite_database_module.sqlite_database_write_lock(db_path):
            database = market_data_sqlite_database_module.MarketDataSQLiteDatabase(db_path)
            await database.initialize()
            await database.execute("BEGIN IMMEDIATE")
            await database.executemany(
                "INSERT INTO daily_closes (symbol, day_ts, close) VALUES (?, ?, ?) "
                "ON CONFLICT(symbol, day_ts) DO UPDATE SET close=excluded.close",
                [("BTC/USDT", 2000, 2.0)],
            )
            if database._cursor_pool is not None:
                await database._cursor_pool.close()
                database._cursor_pool = None
            await database.connection.close()
            database.connection = None

        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=True
        ) as database:
            integrity_row = await database.fetchone("PRAGMA integrity_check")
            result = await database.load_daily_prices_dict()

        assert integrity_row == ("ok",)
        assert result[trading_enums.DailyPricesCacheKeys.SYMBOLS]["BTC/USDT"] == {"1000": 1.0}

    @pytest.mark.asyncio
    async def test_wal_truncated_after_graceful_close(self, data_root):
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            await database.merge_daily_closes("BTC/USDT", {"1000": 42000.0})

        db_path = market_data_sqlite_database_module.MarketDataSQLiteDatabase.get_db_path(
            "binance", "spot", False, data_root
        )
        wal_path = f"{db_path}-wal"
        assert not os.path.isfile(wal_path) or os.path.getsize(wal_path) == 0

        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=True
        ) as database:
            integrity_row = await database.fetchone("PRAGMA integrity_check")
            result = await database.load_daily_prices_dict()

        assert integrity_row == ("ok",)
        assert result[trading_enums.DailyPricesCacheKeys.SYMBOLS]["BTC/USDT"]["1000"] == 42000.0

    @pytest.mark.asyncio
    async def test_read_only_open_after_graceful_close(self, data_root):
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            "binance", "spot", False, data_root, read_only=False
        ) as database:
            await database.merge_daily_closes("BTC/USDT", {"1000": 42000.0})

        result = await persisted_price_cache.load("binance", "spot", False, data_root)
        assert result[trading_enums.DailyPricesCacheKeys.SYMBOLS]["BTC/USDT"]["1000"] == 42000.0


class TestReadOnlyMissingDatabase:
    @pytest.mark.asyncio
    async def test_missing_database_returns_empty_without_creating_file(self, data_root):
        result = await persisted_price_cache.load("binance", "spot", False, data_root)
        assert result == {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        db_path = market_data_sqlite_database_module.MarketDataSQLiteDatabase.get_db_path(
            "binance", "spot", False, data_root
        )
        assert not os.path.isfile(db_path)
        assert not os.path.isdir(os.path.dirname(db_path))
