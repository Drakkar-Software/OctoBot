import typing

import octobot_trading.enums as trading_enums


class DailyPricesCache(typing.TypedDict):
    symbols: dict[str, dict[str, float]]
    sources: dict[str, str]


class LatestTickersCache(typing.TypedDict):
    updated_at: typing.Optional[float]
    closes: dict[str, float]


def empty_daily_prices_cache() -> DailyPricesCache:
    return {
        trading_enums.DailyPricesCacheKeys.SYMBOLS: {},
        trading_enums.DailyPricesCacheKeys.SOURCES: {},
    }


def empty_latest_tickers_cache() -> LatestTickersCache:
    return {
        trading_enums.LatestTickersCacheKeys.UPDATED_AT: None,
        trading_enums.LatestTickersCacheKeys.CLOSES: {},
    }
