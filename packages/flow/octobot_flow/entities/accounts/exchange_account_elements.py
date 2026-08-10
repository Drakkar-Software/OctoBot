import copy
import dataclasses
import decimal
import typing

import octobot_commons.logging
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
    orders: octobot_trading.exchanges.OrdersDetails = dataclasses.field(default_factory=octobot_trading.exchanges.OrdersDetails)
    positions: list[octobot_trading.exchanges.PositionDetails] = dataclasses.field(default_factory=list)
    trades: list[dict] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        if self.orders and isinstance(self.orders, dict):
            self.orders = octobot_trading.exchanges.OrdersDetails.from_dict(self.orders)
        if self.positions and isinstance(self.positions[0], dict):
            self.positions = [
                octobot_trading.exchanges.PositionDetails.from_dict(position) for position in self.positions # type: ignore
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

    def get_open_orders_symbols(self) -> list[str]:
        if not self.orders.open_orders:
            return []
        return octobot_trading.personal_data.get_symbols_from_orders(
            octobot_trading.exchanges.OrdersDetails(
                open_orders=list(self.orders.open_orders),
            )
        )

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
        previous_count = len(self.trades)
        self.trades = octobot_trading.personal_data.merge_trades_deduped(self.trades, trades)
        return len(self.trades) != previous_count

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

    @classmethod
    def aggregate_snapshots(
        cls,
        snapshots: list["ExchangeAccountElements"],
    ) -> "ExchangeAccountElements":
        """
        Build one account snapshot from per-exchange snapshots (cross-exchange merge).
        Portfolio holdings are summed per asset; orders and positions are concatenated
        (open/missing orders deduped by exchange order id). Trades and transactions are
        merged with existing dedup rules. ``name`` is a sorted, comma-separated list of
        unique exchange names from the inputs.
        """
        if not snapshots:
            return cls()
        if len(snapshots) == 1:
            return copy.deepcopy(snapshots[0])
        aggregated = cls()
        exchange_names = sorted(
            {
                snapshot_name
                for snapshot in snapshots
                if (snapshot_name := snapshot.name)
            }
        )
        if exchange_names:
            aggregated.name = ",".join(exchange_names)
        for snapshot in snapshots:
            aggregated._aggregate_portfolio_from_snapshot(snapshot)
            aggregated._aggregate_orders_from_snapshot(snapshot)
            aggregated.positions.extend(list(snapshot.positions))
            aggregated.append_new_trades_deduped(snapshot.trades)
            aggregated.append_new_transactions_deduped(snapshot.transactions)
        return aggregated

    def _aggregate_portfolio_from_snapshot(self, snapshot: "ExchangeAccountElements") -> None:
        for asset_name, holdings in snapshot.portfolio.content.items():
            if asset_name not in self.portfolio.content:
                self.portfolio.content[asset_name] = dict(holdings)
                continue
            merged_holdings = self.portfolio.content[asset_name]
            for holding_key, holding_value in holdings.items():
                if holding_key in merged_holdings:
                    merged_holdings[holding_key] = self._sum_numeric_holdings(
                        merged_holdings[holding_key],
                        holding_value,
                    )
                else:
                    merged_holdings[holding_key] = holding_value

    @staticmethod
    def _sum_numeric_holdings(
        left_value: typing.Union[float, decimal.Decimal, int],
        right_value: typing.Union[float, decimal.Decimal, int],
    ) -> typing.Union[float, decimal.Decimal]:
        if isinstance(left_value, decimal.Decimal) or isinstance(right_value, decimal.Decimal):
            return decimal.Decimal(str(left_value)) + decimal.Decimal(str(right_value))
        return left_value + right_value

    def _aggregate_orders_from_snapshot(self, snapshot: "ExchangeAccountElements") -> None:
        self.orders.open_orders = self._merge_enriched_orders_deduped(
            self.orders.open_orders,
            snapshot.orders.open_orders,
        )
        self.orders.missing_orders = self._merge_enriched_orders_deduped(
            self.orders.missing_orders,
            snapshot.orders.missing_orders,
        )

    @staticmethod
    def _merge_enriched_orders_deduped(
        existing_orders: list[dict],
        new_orders: list[dict],
    ) -> list[dict]:
        orders_by_exchange_id = octobot_trading.personal_data.get_enriched_orders_by_exchange_id(
            list(existing_orders)
        )
        orders_without_exchange_id = [
            order
            for order in existing_orders
            if order.get(octobot_trading.constants.STORAGE_ORIGIN_VALUE, {}).get(
                octobot_trading.enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value
            )
            is None
        ]
        for order in new_orders:
            exchange_order_id = order.get(octobot_trading.constants.STORAGE_ORIGIN_VALUE, {}).get(
                octobot_trading.enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value
            )
            if exchange_order_id is None:
                orders_without_exchange_id.append(order)
                continue
            orders_by_exchange_id[exchange_order_id] = order
        return list(orders_by_exchange_id.values()) + orders_without_exchange_id

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
        for order in octobot_trading.api.get_pending_creation_orders(exchange_manager):
            if not order.exchange_order_id:
                continue
            if order.is_self_managed():
                octobot_commons.logging.get_logger(self.__class__.__name__).error(
                    f"Self managed order created. This type of [{exchange_manager.exchange_name}] "
                    f"order is not supported, order is ignored. Order: {order}"
                )
                continue
            if order.exchange_order_id in updated_open_orders_exchange_ids:
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
            octobot_trading.exchanges.PositionDetails(position.to_dict(), position.symbol_contract.to_dict())
            for position in octobot_trading.api.get_positions(exchange_manager)
        ]
        return previous_positions != self.positions

    def _sync_trades_from_exchange_manager(self, exchange_manager: octobot_trading.exchanges.ExchangeManager) -> bool:
        previous_trades_count = len(self.trades)
        if update_trades := octobot_trading.api.get_trade_history(exchange_manager, as_dict=True):
            self.append_new_trades_deduped(update_trades)
        return previous_trades_count != len(self.trades)
