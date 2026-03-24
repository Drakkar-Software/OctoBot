import typing

import octobot_trading.modes as trading_modes

import octobot_copy.exchange.exchange_private_data as exchange_private_data
import octobot_copy.exchange.exchange_public_data as exchange_public_data

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges


class ExchangeInterface:
    def __init__(
        self,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
        trading_mode: typing.Optional["trading_modes.AbstractTradingMode"] = None,
    ):
        self._exchange_manager: "octobot_trading.exchanges.ExchangeManager" = exchange_manager
        self.public_data: exchange_public_data.ExchangePublicData = (
            exchange_public_data.ExchangePublicData(exchange_manager)
        )
        self.private_data: exchange_private_data.ExchangePrivateData = (
            exchange_private_data.ExchangePrivateData(exchange_manager, trading_mode, self.public_data)
        )

    @property
    def exchange_name(self) -> str:
        return self._exchange_manager.exchange_name
