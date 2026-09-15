import typing

import octobot_trading.exchange_data
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.exchanges.util.exchange_data as exchange_data_import

import octobot_flow.entities
import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import
import octobot_trading.constants as trading_constants


class TickersRepository(base_exchange_repository_import.BaseExchangeRepository):

    @classmethod
    async def ensure_temporary_ticker_channel(cls, exchange_manager) -> None:
        await trading_exchanges.create_exchange_channels(exchange_manager)
        await trading_exchanges.create_producers(
            exchange_manager,
            [octobot_trading.exchange_data.TickerUpdater],
            start_producers=False,
        )

    async def fetch_tickers(self, symbols: typing.Optional[list[str]]) -> dict[str, dict]:
        updater = typing.cast(
            octobot_trading.exchange_data.TickerUpdater,
            self.get_channel_updater(trading_constants.TICKER_CHANNEL)
        )
        return await updater.fetch_all_tickers(symbols)

    @classmethod
    async def fetch_ticker_close_by_symbol(
        cls,
        exchange_manager,
        symbols: list[str],
    ) -> dict[str, float]:
        if not symbols:
            return {}
        tickers_repository = cls(
            exchange_manager,
            known_automations=[],
            fetched_exchange_data=octobot_flow.entities.FetchedExchangeData(),
        )
        tickers = await tickers_repository.fetch_tickers(symbols)
        close_column = trading_enums.ExchangeConstantsTickersColumns.CLOSE.value
        ticker_close_by_symbol: dict[str, float] = {}
        for symbol, ticker in tickers.items():
            close_price = ticker.get(close_column)
            if close_price is not None:
                ticker_close_by_symbol[symbol] = float(close_price)
        return ticker_close_by_symbol

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
