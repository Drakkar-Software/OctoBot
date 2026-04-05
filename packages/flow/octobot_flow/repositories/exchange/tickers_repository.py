import typing

import octobot_trading.exchange_data
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.util.exchange_data as exchange_data_import

import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import
import octobot_trading.constants as trading_constants


class TickersRepository(base_exchange_repository_import.BaseExchangeRepository):

    async def fetch_tickers(self, symbols: typing.Optional[list[str]]) -> dict[str, dict]:
        updater = typing.cast(
            octobot_trading.exchange_data.TickerUpdater,
            self.get_channel_updater(trading_constants.TICKER_CHANNEL)
        )
        return await updater.fetch_all_tickers(symbols)

    @staticmethod
    def get_cached_market_price(exchange_internal_name, exchange_type, sandboxed: bool, symbol: str) -> float:
        try:
            cache = octobot_trading.exchange_data.TickerUpdater.get_ticker_cache()
            return cache.get_all_tickers(exchange_internal_name, exchange_type, sandboxed)[symbol][ # type: ignore
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
