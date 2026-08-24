import octobot_commons.errors as commons_errors
import octobot_trading.exchange_data.databases.market_data_sqlite_database as market_data_sqlite_database_module


async def load(
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    data_root: str = None,
) -> dict:
    """Load daily closes from market_data.sqlite; return empty structure when missing."""
    try:
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            exchange_name, exchange_type, sandboxed, data_root, read_only=True
        ) as database:
            return await database.load_daily_prices_dict()
    except commons_errors.DatabaseNotFoundError:
        return {"symbols": {}, "sources": {}}


async def merge_closes(
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    symbol: str,
    closes_by_timestamp: dict[str, float],
    data_root: str = None,
) -> None:
    """Merge close prices for a symbol into market_data.sqlite."""
    async with market_data_sqlite_database_module.open_market_data_sqlite_database(
        exchange_name, exchange_type, sandboxed, data_root, read_only=False
    ) as database:
        await database.merge_daily_closes(symbol, closes_by_timestamp)


async def set_daily_close_source(
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    reference_asset: str,
    fetch_symbol: str,
    data_root: str = None,
) -> None:
    """Persist which exchange symbol is used to fetch daily closes for a base asset."""
    async with market_data_sqlite_database_module.open_market_data_sqlite_database(
        exchange_name, exchange_type, sandboxed, data_root, read_only=False
    ) as database:
        await database.set_daily_close_source(reference_asset, fetch_symbol)


async def rename_daily_closes_symbol(
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    old_symbol: str,
    new_symbol: str,
    data_root: str = None,
) -> None:
    """Move all daily close rows from old_symbol to new_symbol."""
    async with market_data_sqlite_database_module.open_market_data_sqlite_database(
        exchange_name, exchange_type, sandboxed, data_root, read_only=False
    ) as database:
        await database.rename_daily_closes_symbol(old_symbol, new_symbol)


def _resolve_symbol(data: dict, symbol: str) -> str:
    if "/" not in symbol:
        return symbol
    base_asset, _quote = symbol.split("/", 1)
    return data.get("sources", {}).get(base_asset, symbol)


def oldest_timestamp(data: dict, symbol: str) -> float | None:
    """Return the oldest cached day timestamp for a symbol, or None."""
    resolved_symbol = _resolve_symbol(data, symbol)
    symbol_data = data.get("symbols", {}).get(resolved_symbol, {})
    if not symbol_data:
        return None
    return min(float(timestamp) for timestamp in symbol_data)


def newest_timestamp(data: dict, symbol: str) -> float | None:
    """Return the newest cached day timestamp for a symbol, or None."""
    resolved_symbol = _resolve_symbol(data, symbol)
    symbol_data = data.get("symbols", {}).get(resolved_symbol, {})
    if not symbol_data:
        return None
    return max(float(timestamp) for timestamp in symbol_data)


def get_close(data: dict, symbol: str, day_timestamp: str, default: float | None = None) -> float | None:
    """Look up a close price for a symbol at a specific day timestamp."""
    resolved_symbol = _resolve_symbol(data, symbol)
    return data.get("symbols", {}).get(resolved_symbol, {}).get(day_timestamp, default)
