import octobot_commons.constants as commons_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchange_data.prices.daily_prices_cache_types as daily_prices_cache_types

import octobot_flow.constants as flow_constants
import octobot_flow.logic.portfolio_history.trade_fetch_cursors as trade_fetch_cursors


TICKER_WISE_TRADE_SYMBOL = "BTC@BTC/USDT@ETH"


def _daily_prices_with_sticky_base() -> daily_prices_cache_types.DailyPricesCache:
    daily_prices: daily_prices_cache_types.DailyPricesCache = {
        trading_enums.DailyPricesCacheKeys.SYMBOLS: {
            "BTC/USDT": {1_700_000_000: 50000.0},
        },
        trading_enums.DailyPricesCacheKeys.SOURCES: {
            "BTC@BTC": "BTC/USDT",
        },
    }
    return daily_prices


class TestResolveDailyCacheSymbolTickerWise:
    def test_uses_qualified_base_for_sticky_lookup(self):
        daily_prices = _daily_prices_with_sticky_base()
        resolved = trade_fetch_cursors.resolve_daily_cache_symbol(daily_prices, TICKER_WISE_TRADE_SYMBOL)
        assert resolved == "BTC/USDT"


class TestComputeTradeFetchSinceMsTickerWise:
    def test_returns_since_ms_when_sticky_resolves(self):
        daily_prices = _daily_prices_with_sticky_base()
        since_ms = trade_fetch_cursors.compute_trade_fetch_since_ms(daily_prices, TICKER_WISE_TRADE_SYMBOL)
        assert since_ms is not None
        lookback_ms = int(
            flow_constants.PORTFOLIO_HISTORY_TRADE_FETCH_SINCE_LOOKBACK_DAYS
            * commons_constants.DAYS_TO_SECONDS
            * 1000
        )
        assert since_ms <= 1_700_000_000_000 - lookback_ms + 1000
