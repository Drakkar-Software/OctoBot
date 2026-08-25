import octobot_commons.errors as commons_errors
import octobot_trading.enums as trading_enums
import octobot_trading.exchange_data.databases.market_data_sqlite_database as market_data_sqlite_database_module
import octobot_trading.exchange_data.prices.daily_prices_cache_types as daily_prices_cache_types


async def load(
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    data_root: str = None,
) -> daily_prices_cache_types.LatestTickersCache:
    """Load latest tickers from market_data.sqlite; return empty structure when missing."""
    try:
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            exchange_name, exchange_type, sandboxed, data_root, read_only=True
        ) as database:
            return await database.load_latest_tickers_dict()
    except commons_errors.DatabaseNotFoundError:
        return daily_prices_cache_types.empty_latest_tickers_cache()


async def update(
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    closes: dict[str, float],
    data_root: str = None,
) -> None:
    """Merge closes into market_data.sqlite latest_tickers table."""
    async with market_data_sqlite_database_module.open_market_data_sqlite_database(
        exchange_name, exchange_type, sandboxed, data_root, read_only=False
    ) as database:
        await database.update_latest_tickers(closes)


def get_close(
    data: daily_prices_cache_types.LatestTickersCache,
    symbol: str,
    default: float | None = None,
) -> float | None:
    """Look up the latest close price for a symbol."""
    return data[trading_enums.LatestTickersCacheKeys.CLOSES].get(symbol, default)
