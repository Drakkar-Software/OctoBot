import octobot_trading.exchange_data.prices.persisted_price_cache as persisted_price_cache
import octobot_trading.exchange_data.ticker.persisted_ticker_cache as persisted_ticker_cache


async def load_daily_prices(
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    data_root: str = None,
) -> dict:
    return await persisted_price_cache.load(exchange_name, exchange_type, sandboxed, data_root)


async def merge_daily_prices(
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    symbol: str,
    closes_by_timestamp: dict[str, float],
    data_root: str = None,
) -> None:
    await persisted_price_cache.merge_closes(
        exchange_name, exchange_type, sandboxed, symbol, closes_by_timestamp, data_root
    )


async def set_daily_close_source(
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    reference_asset: str,
    fetch_symbol: str,
    data_root: str = None,
) -> None:
    await persisted_price_cache.set_daily_close_source(
        exchange_name, exchange_type, sandboxed, reference_asset, fetch_symbol, data_root
    )


async def rename_daily_closes_symbol(
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    old_symbol: str,
    new_symbol: str,
    data_root: str = None,
) -> None:
    await persisted_price_cache.rename_daily_closes_symbol(
        exchange_name, exchange_type, sandboxed, old_symbol, new_symbol, data_root
    )


async def load_latest_tickers(
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    data_root: str = None,
) -> dict:
    return await persisted_ticker_cache.load(exchange_name, exchange_type, sandboxed, data_root)


async def update_latest_tickers(
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    closes: dict[str, float],
    data_root: str = None,
) -> None:
    await persisted_ticker_cache.update(exchange_name, exchange_type, sandboxed, closes, data_root)


def get_daily_price(data: dict, symbol: str, day_timestamp: str, default: float | None = None) -> float | None:
    return persisted_price_cache.get_close(data, symbol, day_timestamp, default)


def get_latest_ticker_close(data: dict, symbol: str, default: float | None = None) -> float | None:
    return persisted_ticker_cache.get_close(data, symbol, default)


def get_oldest_daily_price_timestamp(data: dict, symbol: str) -> float | None:
    return persisted_price_cache.oldest_timestamp(data, symbol)


def get_latest_daily_price_timestamp(data: dict, symbol: str) -> float | None:
    return persisted_price_cache.newest_timestamp(data, symbol)
