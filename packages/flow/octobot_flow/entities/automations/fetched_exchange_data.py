import dataclasses
import typing
import decimal

import octobot_commons.dataclasses
import octobot_commons.logging
import octobot_trading.exchanges.util.exchange_data as exchange_data_import
import octobot_trading.exchanges
import octobot_trading.storage.orders_storage
import octobot_trading.api
import octobot_trading.enums
import octobot_trading.constants
import octobot_trading.personal_data

import octobot_flow.enums



@dataclasses.dataclass
class FetchedExchangeAccountElements(octobot_commons.dataclasses.MinimizableDataclass, octobot_commons.dataclasses.UpdatableDataclass):
    portfolio: exchange_data_import.PortfolioDetails = dataclasses.field(default_factory=exchange_data_import.PortfolioDetails)
    orders: exchange_data_import.OrdersDetails = dataclasses.field(default_factory=exchange_data_import.OrdersDetails)
    positions: list[exchange_data_import.PositionDetails] = dataclasses.field(default_factory=list)
    trades: list[dict] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if self.portfolio and isinstance(self.portfolio, dict):
            self.portfolio = exchange_data_import.PortfolioDetails.from_dict(self.portfolio)
        if self.orders and isinstance(self.orders, dict):
            self.orders = exchange_data_import.OrdersDetails.from_dict(self.orders)
        if self.positions and isinstance(self.positions[0], dict):
            self.positions = [
                exchange_data_import.PositionDetails.from_dict(position) for position in self.positions
            ]

    def sync_from_exchange_manager(
        self, exchange_manager: octobot_trading.exchanges.ExchangeManager
    ) -> list[octobot_flow.enums.ChangedElements]:
        changed_elements = []
        if self.sync_orders_from_exchange_manager(exchange_manager):
            changed_elements.append(octobot_flow.enums.ChangedElements.ORDERS)
        if self._sync_trades_from_exchange_manager(exchange_manager):
            changed_elements.append(octobot_flow.enums.ChangedElements.TRADES)
        if self.sync_portfolio_from_exchange_manager(exchange_manager):
            changed_elements.append(octobot_flow.enums.ChangedElements.PORTFOLIO)
        if self.sync_positions_from_exchange_manager(exchange_manager):
            changed_elements.append(octobot_flow.enums.ChangedElements.POSITIONS)
        return changed_elements

    def sync_orders_from_exchange_manager(self, exchange_manager: octobot_trading.exchanges.ExchangeManager) -> bool:
        previous_orders = self.orders
        updated_open_orders_exchange_ids = set()
        updated_open_orders = []
        updated_missing_orders = []
        for order in octobot_trading.api.get_open_orders(exchange_manager):
            if order.is_self_managed():
                octobot_commons.logging.get_logger(self.__class__.__name__).error(
                    f"Self managed order created. This type of [{exchange_manager.exchange_name}] "
                    f"order is not supported, order is ignored. Order: {order}"
                )
                continue
            updated_open_orders_exchange_ids.add(order.exchange_order_id)
            updated_open_orders.append(
                octobot_trading.storage.orders_storage._format_order(order, exchange_manager)
            )
        updated_missing_orders = [
            order
            for exchange_id, order in octobot_trading.personal_data.get_enriched_orders_by_exchange_id(previous_orders.open_orders).items()
            if exchange_id not in updated_open_orders_exchange_ids
        ]
        self.orders.open_orders = updated_open_orders
        self.orders.missing_orders = updated_missing_orders
        return previous_orders != self.orders

    def _sync_trades_from_exchange_manager(self, exchange_manager: octobot_trading.exchanges.ExchangeManager) -> bool:
        previous_trades = self.trades
        self.trades = octobot_trading.api.get_trade_history(exchange_manager, as_dict=True)
        return previous_trades != self.trades

    def sync_portfolio_from_exchange_manager(self, exchange_manager: octobot_trading.exchanges.ExchangeManager) -> bool:
        previous_portfolio = self.portfolio.content
        self.portfolio.content = {
            key: values
            for key, values in octobot_trading.api.get_portfolio(exchange_manager, as_decimal=False).items()
            if any(value for value in values.values())  # skip 0 value assets
        }
        return previous_portfolio != self.portfolio.content

    def sync_positions_from_exchange_manager(self, exchange_manager: octobot_trading.exchanges.ExchangeManager) -> bool:
        previous_positions = self.positions
        self.positions = [
            exchange_data_import.PositionDetails(position.to_dict(), position.symbol_contract.to_dict())
            for position in octobot_trading.api.get_positions(exchange_manager)
        ]
        return previous_positions != self.positions


@dataclasses.dataclass
class FetchedExchangePublicData(octobot_commons.dataclasses.MinimizableDataclass):
    markets: list[exchange_data_import.MarketDetails] = dataclasses.field(default_factory=list)
    tickers: dict[str, dict[str, typing.Any]] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class FetchedExchangeData(octobot_commons.dataclasses.MinimizableDataclass):
    public_data: FetchedExchangePublicData = dataclasses.field(default_factory=FetchedExchangePublicData)
    authenticated_data: FetchedExchangeAccountElements = dataclasses.field(default_factory=FetchedExchangeAccountElements)

    def __post_init__(self):
        if self.public_data and isinstance(self.public_data, dict):
            self.public_data = FetchedExchangePublicData.from_dict(self.public_data)
        if self.authenticated_data and isinstance(self.authenticated_data, dict):
            self.authenticated_data = FetchedExchangeAccountElements.from_dict(self.authenticated_data)

    def get_last_price(self, symbol: str) -> decimal.Decimal:
        # use if as in most cases, tickers are not available for all symbols
        if symbol in self.public_data.tickers:
            try:
                return decimal.Decimal(str(
                    self.public_data.tickers[symbol][
                        octobot_trading.enums.ExchangeConstantsTickersColumns.CLOSE.value
                    ]
                ))
            except (KeyError, decimal.DecimalException):
                return octobot_trading.constants.ZERO
        else:
            return octobot_trading.constants.ZERO
