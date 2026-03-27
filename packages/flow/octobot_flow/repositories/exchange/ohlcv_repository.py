import cachetools

import octobot_commons.constants as commons_constants_import
import octobot_flow.constants as constants_import
import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import
import octobot_trading.exchanges as exchanges_import
import octobot_trading.exchanges.util.exchange_data as exchange_data_import
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools

_OHLCV_CACHE: cachetools.TTLCache[tuple, exchange_data_import.MarketDetails] = cachetools.TTLCache(
    maxsize=512,
    ttl=constants_import.OHLCV_CACHE_TTL,
)


def _ohlcv_cache_key(
    exchange_manager: exchanges_import.ExchangeManager,
    symbol: str,
    time_frame: str,
    limit: int,
) -> tuple:
    exchange_type = exchanges_import.get_exchange_type(exchange_manager).value
    scope_key = (
        f"{exchange_manager.exchange_name}_"
        f"{exchange_type or commons_constants_import.CONFIG_EXCHANGE_SPOT}_"
        f"{exchange_manager.is_sandboxed}"
    )
    return (scope_key, symbol, time_frame, limit)


class OhlcvRepository(base_exchange_repository_import.BaseExchangeRepository):

    async def fetch_ohlcv(
        self, symbol: str, time_frame: str, limit: int
    ) -> exchange_data_import.MarketDetails:
        key = _ohlcv_cache_key(self.exchange_manager, symbol, time_frame, limit)
        if cached := _OHLCV_CACHE.get(key):
            return cached
        market = await exchanges_test_tools.fetch_ohlcv(
            self.exchange_manager, symbol, time_frame, limit
        )
        _OHLCV_CACHE[key] = market
        return market

    @staticmethod
    def reset_ohlcv_cache() -> None:
        _OHLCV_CACHE.clear()
