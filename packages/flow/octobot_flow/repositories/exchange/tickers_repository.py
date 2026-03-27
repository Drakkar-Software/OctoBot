import typing

import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools
import octobot_trading.exchange_data
import octobot_trading.exchanges
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.util.exchange_data as exchange_data_import

import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import
import octobot_flow.constants


_TICKER_CACHE = octobot_trading.exchange_data.TickerCache(
    ttl=octobot_flow.constants.TICKER_CACHE_TTL,
    maxsize=50
)

class TickersRepository(base_exchange_repository_import.BaseExchangeRepository):

    async def fetch_tickers(self, symbols: typing.Optional[list[str]]) -> dict[str, dict]:
        if symbols == []:
            return {}
        if isinstance(symbols, list) and len(symbols) == 1:
            return {
                symbols[0]: await exchanges_test_tools.get_price_ticker(self.exchange_manager, symbols[0]) # type: ignore
            }
        if not (tickers := _TICKER_CACHE.get_all_tickers(
            self.exchange_manager.exchange_name,
            octobot_trading.exchanges.get_exchange_type(self.exchange_manager).value,
            self.exchange_manager.is_sandboxed
        )):
            tickers = await exchanges_test_tools.get_all_currencies_price_ticker(
                self.exchange_manager, symbols=None # force fetching all tickers
            )
            self.set_tickers_cache(
                self.exchange_manager.exchange_name,
                octobot_trading.exchanges.get_exchange_type(self.exchange_manager).value,
                self.exchange_manager.is_sandboxed,
                tickers
            )
        return tickers

    @staticmethod
    def get_cached_market_price(exchange_internal_name, exchange_type, sandboxed: bool, symbol: str) -> float:
        try:
            return _TICKER_CACHE.get_all_tickers(exchange_internal_name, exchange_type, sandboxed)[symbol][ # type: ignore
                trading_enums.ExchangeConstantsTickersColumns.CLOSE.value
            ]
        except TypeError as err:
            # symbol not found in cache
            raise KeyError(err) from err

    @staticmethod
    def get_cached_market_price_from_exchange_data(
        exchange_data: exchange_data_import.ExchangeData, symbol: str
    ) -> float:
        return TickersRepository.get_cached_market_price(
            exchange_data.exchange_details.name, exchange_data.auth_details.exchange_type,
            exchange_data.auth_details.sandboxed, symbol,
        )

    @staticmethod
    def set_tickers_cache(exchange_name: str, exchange_type: str, sandboxed: bool, tickers: dict):
        _TICKER_CACHE.set_all_tickers(exchange_name, exchange_type, sandboxed, tickers, replace_all=False)

    @staticmethod
    def reset_tickers_cache():
        _TICKER_CACHE.reset_all_tickers_cache()
