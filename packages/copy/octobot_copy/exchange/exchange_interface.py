import typing

import octobot_trading.modes as trading_modes

import octobot_copy.exchange.market as exchange_market
import octobot_copy.exchange.orders as exchange_orders
import octobot_copy.exchange.portfolio as exchange_portfolio
import octobot_copy.exchange.positions as exchange_positions

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges


class ExchangeInterface:
    def __init__(
        self,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
        trading_mode: typing.Optional["trading_modes.AbstractTradingMode"] = None,
    ):
        self._exchange_manager: "octobot_trading.exchanges.ExchangeManager" = exchange_manager
        self.market: exchange_market.MarketInterface = exchange_market.MarketInterface(exchange_manager)
        self.portfolio: exchange_portfolio.PortfolioInterface = exchange_portfolio.PortfolioInterface(
            exchange_manager
        )
        self.orders: exchange_orders.OrdersInterface = exchange_orders.OrdersInterface(
            exchange_manager, trading_mode
        )
        self.positions: exchange_positions.PositionsInterface = exchange_positions.PositionsInterface(
            exchange_manager, self.orders, self.market
        )

    @property
    def exchange_name(self) -> str:
        return self._exchange_manager.exchange_name

    def get_time(self) -> float:
        return self._exchange_manager.exchange.get_exchange_current_time()
