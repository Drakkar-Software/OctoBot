import octobot_commons.errors as commons_errors
import octobot_trading.enums as trading_enums
import octobot_trading.exchange_data.databases.market_data_sqlite_database as market_data_sqlite_database_module
import octobot_trading.exchange_data.prices.daily_prices_cache_types as daily_prices_cache_types


async def load(
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    data_root: str = None,
) -> daily_prices_cache_types.DailyPricesCache:
    """Load daily closes from market_data.sqlite; return empty structure when missing."""
    try:
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            exchange_name, exchange_type, sandboxed, data_root, read_only=True
        ) as database:
            return await database.load_daily_prices_dict()
    except commons_errors.DatabaseNotFoundError:
        return daily_prices_cache_types.empty_daily_prices_cache()


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


def _resolve_symbol(
    data: daily_prices_cache_types.DailyPricesCache,
    symbol: str,
) -> str:
    if "/" not in symbol:
        return symbol
    base_asset, _quote = symbol.split("/", 1)
    return data[trading_enums.DailyPricesCacheKeys.SOURCES].get(base_asset, symbol)


def oldest_timestamp(
    data: daily_prices_cache_types.DailyPricesCache,
    symbol: str,
) -> float | None:
    """Return the oldest cached day timestamp for a symbol, or None."""
    resolved_symbol = _resolve_symbol(data, symbol)
    symbol_data = data[trading_enums.DailyPricesCacheKeys.SYMBOLS].get(resolved_symbol, {})
    if not symbol_data:
        return None
    return min(float(timestamp) for timestamp in symbol_data)


def newest_timestamp(
    data: daily_prices_cache_types.DailyPricesCache,
    symbol: str,
) -> float | None:
    """Return the newest cached day timestamp for a symbol, or None."""
    resolved_symbol = _resolve_symbol(data, symbol)
    symbol_data = data[trading_enums.DailyPricesCacheKeys.SYMBOLS].get(resolved_symbol, {})
    if not symbol_data:
        return None
    return max(float(timestamp) for timestamp in symbol_data)


def get_close(
    data: daily_prices_cache_types.DailyPricesCache,
    symbol: str,
    day_timestamp: str,
    default: float | None = None,
) -> float | None:
    """Look up a close price for a symbol at a specific day timestamp."""
    resolved_symbol = _resolve_symbol(data, symbol)
    return data[trading_enums.DailyPricesCacheKeys.SYMBOLS].get(resolved_symbol, {}).get(
        day_timestamp, default,
    )


def latest_close_on_or_before(
    data: daily_prices_cache_types.DailyPricesCache,
    symbol: str,
    day_timestamp: float,
) -> float | None:
    """Return the latest cached close on or before the given day timestamp."""
    resolved_symbol = _resolve_symbol(data, symbol)
    symbol_data = data[trading_enums.DailyPricesCacheKeys.SYMBOLS].get(resolved_symbol, {})
    if not symbol_data:
        return None
    day_timestamp_int = int(day_timestamp)
    latest_timestamp = None
    latest_close = None
    for timestamp_str, close_price in symbol_data.items():
        timestamp_int = int(timestamp_str)
        if timestamp_int > day_timestamp_int:
            continue
        if latest_timestamp is None or timestamp_int > latest_timestamp:
            latest_timestamp = timestamp_int
            latest_close = close_price
    return latest_close


def get_close_source(
    data: daily_prices_cache_types.DailyPricesCache,
    base_asset: str,
) -> str | None:
    """Return the exchange symbol used to fetch daily closes for a base asset."""
    return data[trading_enums.DailyPricesCacheKeys.SOURCES].get(base_asset)


def set_close_source_in_memory(
    data: daily_prices_cache_types.DailyPricesCache,
    base_asset: str,
    fetch_symbol: str,
) -> None:
    """Record in memory which exchange symbol backs daily closes for a base asset."""
    data[trading_enums.DailyPricesCacheKeys.SOURCES][base_asset] = fetch_symbol


def merge_symbol_closes_in_memory(
    data: daily_prices_cache_types.DailyPricesCache,
    symbol: str,
    closes_by_timestamp: dict[str, float],
) -> None:
    """Merge close prices for a symbol into the in-memory daily prices cache."""
    data[trading_enums.DailyPricesCacheKeys.SYMBOLS].setdefault(symbol, {}).update(
        closes_by_timestamp,
    )


def move_symbol_closes_in_memory(
    data: daily_prices_cache_types.DailyPricesCache,
    old_symbol: str,
    new_symbol: str,
) -> None:
    old_closes = data[trading_enums.DailyPricesCacheKeys.SYMBOLS].pop(old_symbol, {})
    if old_closes:
        data[trading_enums.DailyPricesCacheKeys.SYMBOLS].setdefault(new_symbol, {}).update(old_closes)
