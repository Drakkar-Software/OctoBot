import typing

import octobot_commons.symbols

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges

class ExchangeInterface:
    def __init__(self, exchange_manager: "octobot_trading.exchanges.ExchangeManager"):
        self._exchange_manager: "octobot_trading.exchanges.ExchangeManager" = exchange_manager

    @property
    def exchange_name(self) -> str:
        return self._exchange_manager.exchange_name

    def get_traded_symbols(self) -> typing.Iterable[octobot_commons.symbols.Symbol]:
        return self._exchange_manager.exchange_config.traded_symbols

    def get_time(self) -> float:
        return self._exchange_manager.exchange.get_exchange_current_time()
