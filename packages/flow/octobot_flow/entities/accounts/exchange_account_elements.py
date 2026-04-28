import dataclasses
import typing

import octobot_commons.logging
import octobot_trading.exchanges.util.exchange_data as exchange_data_import
import octobot_trading.exchanges
import octobot_trading.storage.orders_storage
import octobot_trading.api
import octobot_trading.enums
import octobot_trading.constants
import octobot_trading.personal_data

import octobot_flow.enums
import octobot_flow.entities.accounts.account_elements as account_elements_import


@dataclasses.dataclass
class ExchangeAccountElements(account_elements_import.AccountElements):
    """
    Defines the ideal exchange account state of an automation. Only contains sharable data
    """
    orders: exchange_data_import.OrdersDetails = dataclasses.field(default_factory=exchange_data_import.OrdersDetails)
    positions: list[exchange_data_import.PositionDetails] = dataclasses.field(default_factory=list)
    trades: list[dict] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        if self.orders and isinstance(self.orders, dict):
            self.orders = exchange_data_import.OrdersDetails.from_dict(self.orders)
        if self.positions and isinstance(self.positions[0], dict):
            self.positions = [
                exchange_data_import.PositionDetails.from_dict(position) for position in self.positions # type: ignore
            ]
        if self.trades and isinstance(self.trades[0], dict):
            self.trades = [
                dict(trade) for trade in self.trades # type: ignore
            ]

    def has_pending_chained_orders(self) -> bool:
        for order in self.orders.missing_orders:
            if order.get(octobot_trading.constants.STORAGE_ORIGIN_VALUE, {}).get(octobot_trading.enums.StoredOrdersAttr.CHAINED_ORDERS.value):
                return True
        return False

    def has_pending_groups(self) -> bool:
        # TODO
        return False

    def sync_from_exchange_manager(
        self,
        exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
        transactions: list[dict]
    ) -> list[octobot_flow.enums.ChangedElements]:
        changed_elements = self.sync_from_transactions(transactions)
        if exchange_manager:
            if self.sync_orders_from_exchange_manager(exchange_manager):
                changed_elements.append(octobot_flow.enums.ChangedElements.ORDERS)
            if self.sync_portfolio_from_exchange_manager(exchange_manager):
                changed_elements.append(octobot_flow.enums.ChangedElements.PORTFOLIO)
            if self.sync_positions_from_exchange_manager(exchange_manager):
                changed_elements.append(octobot_flow.enums.ChangedElements.POSITIONS)
            if self._sync_trades_from_exchange_manager(exchange_manager):
                changed_elements.append(octobot_flow.enums.ChangedElements.TRADES)
        return changed_elements

    def append_new_trades_deduped(self, trades: list[dict]) -> bool:
        exchange_trade_id_key = octobot_trading.enums.ExchangeConstantsOrderColumns.EXCHANGE_TRADE_ID.value
        exchange_order_exchange_id_key = octobot_trading.enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value

        def _identity_key(trade: dict) -> typing.Optional[tuple[str, typing.Hashable]]:
            exchange_trade_id = trade.get(exchange_trade_id_key)
            if exchange_trade_id is not None:
                return exchange_trade_id_key, exchange_trade_id
            exchange_order_exchange_id = trade.get(exchange_order_exchange_id_key)
            if exchange_order_exchange_id is not None:
                return exchange_order_exchange_id_key, exchange_order_exchange_id
            return None

        known_trade_keys: set[tuple[str, typing.Hashable]] = set()
        for trade in self.trades:
            key = _identity_key(trade)
            if key is not None:
                known_trade_keys.add(key)
        added = False
        for trade in trades:
            key = _identity_key(trade)
            if key is None or key in known_trade_keys:
                continue
            known_trade_keys.add(key)
            self.trades.append(dict(trade))
            added = True
        return added

    def merge_trades_from_exchange_account_elements(
        self,
        other: "ExchangeAccountElements",
    ) -> bool:
        """Append trades from ``other`` excluding exchange trade ids already on ``self``."""
        return self.append_new_trades_deduped(other.trades)

    def merge_synchronized_snapshots(
        self,
        snapshots: list["ExchangeAccountElements"],
    ) -> list[octobot_flow.enums.ChangedElements]:
        """
        Merge ordered external snapshots into this account: upsert trades/transactions by stable id,
        then replace orders/portfolio/positions (and name when set) from the last snapshot.
        """
        if not snapshots:
            return []
        trades_changed = False
        transactions_changed = False
        for snapshot in snapshots:
            if self.merge_trades_from_exchange_account_elements(snapshot):
                trades_changed = True
            if self.merge_transactions_from_account_elements(snapshot):
                transactions_changed = True
        last_snapshot = snapshots[-1]
        orders_changed = self.orders != last_snapshot.orders
        portfolio_changed = self.portfolio != last_snapshot.portfolio
        positions_changed = self.positions != last_snapshot.positions
        self.orders = last_snapshot.orders
        self.portfolio = last_snapshot.portfolio
        self.positions = list(last_snapshot.positions)
        if last_snapshot.name is not None:
            self.name = last_snapshot.name
        changed: list[octobot_flow.enums.ChangedElements] = []
        if trades_changed:
            changed.append(octobot_flow.enums.ChangedElements.TRADES)
        if transactions_changed:
            changed.append(octobot_flow.enums.ChangedElements.TRANSACTIONS)
        if orders_changed:
            changed.append(octobot_flow.enums.ChangedElements.ORDERS)
        if portfolio_changed:
            changed.append(octobot_flow.enums.ChangedElements.PORTFOLIO)
        if positions_changed:
            changed.append(octobot_flow.enums.ChangedElements.POSITIONS)
        return changed

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

    def _sync_trades_from_exchange_manager(self, exchange_manager: octobot_trading.exchanges.ExchangeManager) -> bool:
        previous_trades_count = len(self.trades)
        if update_trades := octobot_trading.api.get_trade_history(exchange_manager, as_dict=True):
            self.append_new_trades_deduped(update_trades)
        return previous_trades_count != len(self.trades)
