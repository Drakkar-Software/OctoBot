import octobot_commons.errors as commons_errors
import octobot_trading.exchange_data.databases.market_data_sqlite_database as market_data_sqlite_database_module


async def load(
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    data_root: str = None,
) -> dict:
    """Load latest tickers from market_data.sqlite; return empty structure when missing."""
    try:
        async with market_data_sqlite_database_module.open_market_data_sqlite_database(
            exchange_name, exchange_type, sandboxed, data_root, read_only=True
        ) as database:
            return await database.load_latest_tickers_dict()
    except commons_errors.DatabaseNotFoundError:
        return {"updated_at": None, "closes": {}}


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


def get_close(data: dict, symbol: str, default: float | None = None) -> float | None:
    """Look up the latest close price for a symbol."""
    return data.get("closes", {}).get(symbol, default)
