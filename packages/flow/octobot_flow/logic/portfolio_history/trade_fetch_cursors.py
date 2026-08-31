import octobot_commons.constants as commons_constants
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_protocol.models as protocol_models
import octobot_trading.api as trading_api
import octobot_trading.enums as trading_enums
import octobot_trading.exchange_data.prices.daily_prices_cache_types as daily_prices_cache_types

import octobot_flow.constants as flow_constants


def symbols_with_persisted_trades(
    account_trading: protocol_models.AccountTrading | None,
) -> set[str]:
    if account_trading is None or not account_trading.trades:
        return set()
    persisted_symbols: set[str] = set()
    for trade in account_trading.trades:
        if trade.symbol:
            persisted_symbols.add(trade.symbol)
    return persisted_symbols


def get_global_latest_daily_price_timestamp(
    daily_prices: daily_prices_cache_types.DailyPricesCache,
) -> float | None:
    symbols_cache = daily_prices[trading_enums.DailyPricesCacheKeys.SYMBOLS]
    newest_timestamps = [
        trading_api.get_latest_daily_price_timestamp(daily_prices, cached_symbol)
        for cached_symbol, closes_by_day in symbols_cache.items()
        if closes_by_day
    ]
    valid_timestamps = [
        newest_timestamp
        for newest_timestamp in newest_timestamps
        if newest_timestamp is not None
    ]
    if not valid_timestamps:
        return None
    return max(valid_timestamps)


def resolve_daily_cache_symbol(
    daily_prices: daily_prices_cache_types.DailyPricesCache,
    trade_symbol: str,
) -> str | None:
    symbols_cache = daily_prices[trading_enums.DailyPricesCacheKeys.SYMBOLS]
    if trade_symbol in symbols_cache and symbols_cache[trade_symbol]:
        return trade_symbol
    if not symbol_util.is_symbol(trade_symbol):
        return None
    base_asset, _quote_asset = symbol_util.parse_symbol(trade_symbol).base_and_quote()
    if not base_asset:
        return None
    sticky_fetch_symbol = trading_api.get_daily_close_source(daily_prices, base_asset)
    if sticky_fetch_symbol is None:
        return None
    if trading_api.get_latest_daily_price_timestamp(daily_prices, sticky_fetch_symbol) is None:
        return None
    return sticky_fetch_symbol


def uses_global_daily_price_cursor(
    daily_prices: daily_prices_cache_types.DailyPricesCache,
    trade_symbol: str,
) -> bool:
    if resolve_daily_cache_symbol(daily_prices, trade_symbol) is not None:
        return False
    if not symbol_util.is_usd_like_to_usd_like_pair(trade_symbol):
        return False
    return get_global_latest_daily_price_timestamp(daily_prices) is not None


def compute_trade_fetch_since_ms(
    daily_prices: daily_prices_cache_types.DailyPricesCache,
    trade_symbol: str,
) -> int | None:
    # USD-like x USD-like pairs never get per-symbol daily candles; borrow exchange cache freshness.
    cache_symbol = resolve_daily_cache_symbol(daily_prices, trade_symbol)
    if cache_symbol is not None:
        newest_timestamp = trading_api.get_latest_daily_price_timestamp(daily_prices, cache_symbol)
    elif symbol_util.is_usd_like_to_usd_like_pair(trade_symbol):
        newest_timestamp = get_global_latest_daily_price_timestamp(daily_prices)
    else:
        newest_timestamp = None
    if newest_timestamp is None:
        return None
    since_seconds = newest_timestamp - (
        flow_constants.PORTFOLIO_HISTORY_TRADE_FETCH_SINCE_LOOKBACK_DAYS
        * commons_constants.DAYS_TO_SECONDS
    )
    return int(since_seconds * 1000)


def build_symbol_since_ms(
    discovered_symbols: list[str],
    account_trading: protocol_models.AccountTrading | None,
    daily_prices: daily_prices_cache_types.DailyPricesCache,
) -> dict[str, int]:
    persisted_symbols = symbols_with_persisted_trades(account_trading)
    symbol_since_ms: dict[str, int] = {}
    for trading_symbol in discovered_symbols:
        if trading_symbol not in persisted_symbols:
            continue
        since_ms = compute_trade_fetch_since_ms(daily_prices, trading_symbol)
        if since_ms is None:
            continue
        symbol_since_ms[trading_symbol] = since_ms
    return symbol_since_ms
