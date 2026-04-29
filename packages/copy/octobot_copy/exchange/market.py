import decimal
import typing

import octobot_commons.logging as commons_logging
import octobot_commons.symbols
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.personal_data as trading_personal_data

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges


class MarketInterface:
    def __init__(self, exchange_manager: "octobot_trading.exchanges.ExchangeManager"):
        self._exchange_manager: "octobot_trading.exchanges.ExchangeManager" = exchange_manager

    def get_traded_symbols(self) -> typing.Iterable[octobot_commons.symbols.Symbol]:
        return self._exchange_manager.exchange_config.traded_symbols

    def is_symbol_tradable(self, symbol: str) -> bool:
        return symbol in self._exchange_manager.exchange_symbols_data.exchange_symbol_data

    async def get_up_to_date_price(self, symbol: str) -> decimal.Decimal:
        return await trading_personal_data.get_up_to_date_price(
            self._exchange_manager,
            symbol,
            timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT,
        )

    def get_potentially_outdated_price(self, symbol: str) -> (decimal.Decimal, bool):
        return trading_personal_data.get_potentially_outdated_price(
            self._exchange_manager,
            symbol,
        )

    async def ensure_contract_loaded(self, symbol: str) -> None:
        try:
            await self._exchange_manager.exchange.get_pair_contract_async(symbol)
        except trading_errors.ContractExistsError:
            commons_logging.get_logger(self.__class__.__name__).info(
                f"Contract for {symbol} has been loaded."
            )

    def is_market_open_for_order_type(self, symbol: str, order_type: trading_enums.TraderOrderType) -> bool:
        return self._exchange_manager.exchange.is_market_open_for_order_type(symbol, order_type)

    def get_market_status(self, symbol: str, *, with_fixer: bool = False):
        return self._exchange_manager.exchange.get_market_status(symbol, with_fixer=with_fixer)
