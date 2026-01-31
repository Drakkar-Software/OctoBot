#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import asyncio
import typing
import contextlib
import decimal
import copy

import octobot_commons.logging as logging

import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.errors as errors
import octobot_trading.personal_data.orders.states as orders_states
import octobot_trading.exchanges
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_trading.personal_data.orders.trailing_profiles as trailing_profiles
import octobot_trading.personal_data.orders.order_group as order_group_import
import octobot_trading.personal_data.orders.order_state as order_state_import
import octobot_trading.personal_data.orders.decimal_order_adapter as decimal_order_adapter
import octobot_trading.personal_data.orders.triggers.base_trigger as base_trigger_import
import octobot_trading.personal_data.orders.cancel_policies.order_cancel_policy as order_cancel_policy_import
import octobot_trading.personal_data.orders.cancel_policies.cancel_policy_factory as cancel_policy_factory
import octobot_trading.util as util


class Order(util.Initializable):
    """
    Order class will represent an open order in the specified exchange
    In simulation it will also define rules to be filled / canceled
    It is also use to store creation & fill values of the order
    """
    CHECK_ORDER_STATUS_AFTER_INIT_DELAY = 2
    SUPPORTS_GROUPING = True    # False when orders of this type can't be grouped
    USE_ORIGIN_QUANTITY_AS_FILLED_QUANTITY = False

    def __init__(self, trader, side=None):
        super().__init__()
        self.trader: octobot_trading.exchanges.Trader = trader
        self.exchange_manager: octobot_trading.exchanges.ExchangeManager = trader.exchange_manager
        self.lock: asyncio.Lock = asyncio.Lock()
        self.is_synchronized_with_exchange: bool = False
        self.is_from_this_octobot: bool = True
        self.simulated: bool = trader.simulate

        self.logger_name: typing.Optional[str] = None
        self.order_id: str = order_util.generate_order_id()        # used id; kept through instances and trading signals
        self.exchange_order_id: str = trader.parse_order_id(None)  # given by the exchange, local to the user account
        self.status: enums.OrderStatus = enums.OrderStatus.OPEN
        self.symbol: str = None # type: ignore
        self.currency: typing.Optional[str] = None
        self.market: typing.Optional[str] = None
        self.quantity_currency: typing.Optional[str] = None
        self.taker_or_maker: typing.Optional[str] = None
        self.timestamp: float = 0
        self.side: enums.TradeOrderSide = side # type: ignore
        self.trigger_above: bool = None # type: ignore
        self.tag: str = None # type: ignore
        self.associated_entry_ids: typing.Optional[list[str]] = None
        self.broker_applied: bool = False

        # original order attributes
        self.creation_time: float = self.exchange_manager.exchange.get_exchange_current_time()
        self.origin_price: decimal.Decimal = constants.ZERO
        self.created_last_price: decimal.Decimal = constants.ZERO
        self.origin_quantity: decimal.Decimal = constants.ZERO
        self.origin_stop_price: decimal.Decimal = constants.ZERO

        # order type attributes
        self.order_type: enums.TraderOrderType = None # type: ignore
        # raw exchange order type, used to create order dict
        self.exchange_order_type: typing.Optional[enums.TradeOrderType] = None

        # filled order attributes
        self.filled_quantity: decimal.Decimal = constants.ZERO
        self.filled_price: decimal.Decimal = constants.ZERO
        self.fee: typing.Optional[dict[str, typing.Any]] = None
        self.fees_currency_side: enums.FeesCurrencySide = enums.FeesCurrencySide.UNDEFINED
        self.total_cost: decimal.Decimal = constants.ZERO
        self.order_profitability: decimal.Decimal = constants.ZERO
        self.executed_time: float = 0

        # canceled order attributes
        self.canceled_time: float = 0

        self.order_group: typing.Optional[order_group_import.OrderGroup] = None
        self.trailing_profile: typing.Optional[trailing_profiles.TrailingProfile] = None

        # order state is initialized in initialize_impl()
        self.state: typing.Optional[order_state_import.OrderState] = None

        # order activity
        self.is_active: bool = True   # When is_active=False order is not pushed to exchanges
        # True when a transition between active and inactive is being made
        self.is_in_active_inactive_transition: bool = False
        # active_trigger is used for active/inactive switch trigger mechanism, it stores relevant data.
        self.active_trigger: typing.Optional[base_trigger_import.BaseTrigger] = None

        # future trading attributes
        # when True: reduce position quantity only without opening a new position if order.quantity > position.quantity
        self.reduce_only: bool = False

        # when True: close the current associated position
        self.close_position: bool = False

        # the associated position side (should be BOTH for One-way Mode ; LONG or SHORT for Hedge Mode)
        self.position_side: typing.Optional[enums.PositionSide] = None

        # Chained orders attributes
        # other orders (as any Order) that should be created when this order is filled
        self.chained_orders: list[Order] = []
        # order that triggered this order creation (when created as a chained order)
        self.triggered_by: typing.Optional[Order] = None
        # if True this orders quantity will be reduced according to the triggering order's paid fees
        self.update_with_triggering_order_fees: bool = False
        # True when this order has been created directly by the exchange (usually as stop loss / take profit
        # when passed as parameter alongside another order)
        self.has_been_bundled: bool = False
        # True when this order is to be opened as a chained order and has not been open yet
        self.is_waiting_for_chained_trigger: bool = False
        # instance of the order that has been created after self has been filled. Used in stop / TP orders
        self.on_filled_artificial_order: typing.Optional[Order] = None

        # Cancel policy, if set
        self.cancel_policy: typing.Optional[order_cancel_policy_import.OrderCancelPolicy] = None

        # Params given to the exchange request when this order is created. Include any exchange specific param here.
        # All params and values in those will be ignored in simulated orders
        self.exchange_creation_params: dict[str, typing.Any] = {}
        # kwargs given to trader.create_order() when this order should be created later on
        self.trader_creation_kwargs: dict[str, typing.Any] = {}

    @classmethod
    def get_name(cls):
        return cls.__name__

    def get_logger_name(self):
        if self.logger_name is None:
            self.logger_name = f"{self.get_name()} | {self.order_id} [exchange id: {self.exchange_order_id}]"
        return self.logger_name

    def update(
        self, symbol=None, order_id="", exchange_order_id=None, status=enums.OrderStatus.OPEN,
        current_price=constants.ZERO, quantity=constants.ZERO, price=constants.ZERO, stop_price=constants.ZERO,
        quantity_filled=constants.ZERO, filled_price=constants.ZERO, average_price=constants.ZERO,
        fee=None, total_cost=constants.ZERO, timestamp=None,
        order_type=None, reduce_only=None, close_position=None, position_side=None, fees_currency_side=None,
        group=None, tag=None, quantity_currency=None, exchange_creation_params=None,
        associated_entry_id=None, trigger_above=None, trailing_profile: trailing_profiles.TrailingProfile=None,
        is_active=None, active_trigger: base_trigger_import.BaseTrigger = None,
        cancel_policy: typing.Optional[order_cancel_policy_import.OrderCancelPolicy] = None,
    ) -> bool:
        changed: bool = False
        should_update_total_cost = False

        price = current_price if (current_price and self.use_current_price_as_origin_price()) else price

        if order_id and self.order_id != order_id:
            self.order_id = order_id

        if exchange_order_id and self.exchange_order_id != exchange_order_id:
            self.exchange_order_id = exchange_order_id

        if symbol and self.symbol != symbol:
            self.currency, self.market = self.exchange_manager.get_exchange_quote_and_base(symbol)
            self.symbol = symbol

        if quantity_currency is None:
            if self.quantity_currency is None and self.symbol is not None:
                self.quantity_currency = order_util.get_order_quantity_currency(self.exchange_manager, self.symbol)
        else:
            self.quantity_currency = quantity_currency

        if status and self.status != status:
            # ensure the order status is compatible with the state to avoid exchange sync issues
            if self.state is None or self.state.allows_new_status(status):
                self.status = status
                changed = True
            else:
                logging.get_logger(self.get_logger_name()).debug(f"Ignored unexpected new status: {status}")
        if not self.status:
            self.status = enums.OrderStatus.OPEN

        if timestamp and self.timestamp != timestamp:
            self.timestamp = timestamp
            # if we have a timestamp, it's a real trader => need to format timestamp if necessary
            self.creation_time = self.exchange_manager.exchange.get_uniformized_timestamp(timestamp)
        if not self.timestamp:
            if not timestamp:
                self.creation_time = self.exchange_manager.exchange.get_exchange_current_time()
            else:
                # if we have a timestamp, it's a real trader => need to format timestamp if necessary
                self.creation_time = self.exchange_manager.exchange.get_uniformized_timestamp(timestamp)
            self.timestamp = self.creation_time

        if status in {enums.OrderStatus.FILLED, enums.OrderStatus.CLOSED} and not self.executed_time:
            self.executed_time = self.timestamp

        if price and self.origin_price != price:
            previous_price = self.origin_price
            self.origin_price = price
            self._on_origin_price_change(
                previous_price, self.exchange_manager.exchange.get_exchange_current_time()
            )
            changed = True
            should_update_total_cost = True

        if fee is not None and self.fee != fee:
            self.fee = fee

        if fees_currency_side is not None and self.fees_currency_side != fees_currency_side:
            self.fees_currency_side = fees_currency_side

        if current_price and self.created_last_price != current_price:
            self.created_last_price = current_price
            changed = True

        if quantity and self.origin_quantity != quantity:
            self.origin_quantity = quantity
            changed = True
            should_update_total_cost = True

        if stop_price and self.origin_stop_price != stop_price:
            self.origin_stop_price = stop_price
            changed = True

        if total_cost and self.total_cost != total_cost:
            self.total_cost = total_cost

        if average_price:
            # try using average price first
            if self.filled_price != average_price:
                self.filled_price = average_price
                should_update_total_cost = True
        else:
            if filled_price and self.filled_price != filled_price:
                self.filled_price = filled_price
                should_update_total_cost = True

        if self.trader.simulate:
            if quantity and (self.is_filled() or self.USE_ORIGIN_QUANTITY_AS_FILLED_QUANTITY):
                # when simulating, only set filled quantity if the order is filled
                self.filled_quantity = quantity
                changed = True
                should_update_total_cost = True

            if quantity_filled and self.filled_quantity != quantity_filled:
                self.filled_quantity = quantity_filled
                changed = True
                should_update_total_cost = True
        else:
            if quantity_filled and self.filled_quantity != quantity_filled:
                self.filled_quantity = quantity_filled
                changed = True
                should_update_total_cost = True

        if order_type:
            self.order_type = order_type
            if self.exchange_order_type is None:
                self.exchange_order_type = _get_trade_order_type(order_type)

        if not self.filled_price and self.filled_quantity and self.total_cost:
            self.filled_price = self.total_cost / self.filled_quantity
            if timestamp is not None:
                self.executed_time = self.exchange_manager.exchange.get_uniformized_timestamp(timestamp)

        if self.taker_or_maker is None:
            self._update_taker_maker()

        if position_side:
            self.position_side = position_side

        if reduce_only is not None:
            self.reduce_only = reduce_only

        if close_position is not None:
            self.close_position = close_position

        if group is not None:
            self.add_to_order_group(group)

        if tag is not None:
            self.tag = tag

        if exchange_creation_params is not None:
            self.exchange_creation_params = exchange_creation_params

        if associated_entry_id is not None:
            self.associate_to_entry(associated_entry_id)

        if trigger_above is not None and self.trigger_above != trigger_above:
            changed = True
            self.trigger_above = trigger_above

        if trailing_profile is not None and self.trailing_profile != trailing_profile:
            changed = True
            self.trailing_profile = trailing_profile

        if is_active is not None and self.is_active != is_active:
            changed = True
            self.is_active = is_active

        if active_trigger is not None and active_trigger != self.active_trigger:
            changed = True
            self.use_active_trigger(active_trigger)

        if cancel_policy is not None and cancel_policy != self.cancel_policy:
            changed = True
            self.cancel_policy = cancel_policy

        if should_update_total_cost and not total_cost:
            self._update_total_cost()

        return changed

    async def create_on_filled_artificial_order(self, enable_associated_orders_creation):
        """
        :return: the equivalent artificial order after trigger price (ex: stop loss => market order)
        """
        await self.on_filled(enable_associated_orders_creation, force_artificial_orders=True)
        if self.on_filled_artificial_order is not None:
            logging.get_logger(self.logger_name).info(f"Created artificial order: {self.on_filled_artificial_order}")
            if self.order_group:
                self.on_filled_artificial_order.add_to_order_group(self.order_group)
        return self.on_filled_artificial_order

    async def initialize_impl(self, **kwargs):
        """
        Initialize order status update tasks
        """
        await orders_states.create_order_state(self, **kwargs)
        if self.is_created() and not self.is_closed():
            await self.update_order_status()
        if not self.is_active:
            await self._ensure_inactive_order_watcher()

    def register_broker_applied_if_enabled(self):
        if not self.simulated and self.trader and self.trader.exchange_manager:
            self.broker_applied = self.trader.exchange_manager.is_broker_enabled

    def _on_origin_price_change(self, previous_price, price_time):
        """
        Called when origin price just changed.
        Override if necessary
        :param previous_price: the previous origin_price
        :param price_time: time starting from when the price should be considered
        """
        if self.order_group and self.order_group.active_order_swap_strategy:
            self.order_group.active_order_swap_strategy.on_order_update(self, price_time)

    def add_chained_order(self, chained_order):
        """
        chained_order will be assigned with the actually created order when this order will be filled
        warning: add_chained_order is not checking if the order should be created instantly (if self is filled).
        :param chained_order: WrappedOrder to be added to this order's chained orders
        """
        self.chained_orders.append(chained_order)

    async def update_order_status(self, force_refresh=False):
        """
        Update_order_status will define the rules for a simulated order to be filled / canceled
        """
        raise NotImplementedError("Update_order_status not implemented")

    def add_to_order_group(self, order_group):
        if not self.is_open() and not self.is_waiting_for_chained_trigger:
            logging.get_logger(self.get_logger_name()).warning(f"Adding order to group however order is not open.")
        self.order_group = order_group

    def get_total_fees(self, currency):
        return order_util.get_fees_for_currency(self.fee, currency)

    def is_created(self) -> bool:
        return self.state is None or self.state.is_created()

    def is_pending_creation(self) -> bool:
        return isinstance(self.state, orders_states.PendingCreationOrderState)

    def is_open(self) -> bool:
        # also check is_initialized to avoid considering uncreated orders as open
        return (
            self.state is None or self.state.is_open() or (
                not self.is_active and self.status is enums.OrderStatus.OPEN and not self.is_waiting_for_chained_trigger
            )
        )

    def is_filled(self) -> bool:
        if self.state is None:
            return self.status is enums.OrderStatus.FILLED
        return self.state.is_filled() or (self.state.is_closed() and self.status is enums.OrderStatus.FILLED)

    def is_cancelled(self) -> bool:
        if self.state is None:
            return self.status is enums.OrderStatus.CANCELED
        return self.state.is_canceled() or (self.state.is_closed() and self.status is enums.OrderStatus.CANCELED)

    def is_cancelling(self) -> bool:
        if self.state is None:
            return self.status is enums.OrderStatus.PENDING_CANCEL
        return self.state.state is enums.OrderStates.CANCELING or self.status is enums.OrderStatus.PENDING_CANCEL

    def is_closed(self) -> bool:
        if self.state is None:
            return self.status is enums.OrderStatus.CLOSED
        return self.state.is_closed() if self.state is not None else self.status is enums.OrderStatus.CLOSED

    def is_refreshing(self) -> bool:
        return self.state is not None and self.state.is_refreshing()

    def is_pending(self) -> bool:
        return self.state is not None and self.state.is_pending()

    def is_refreshing_filling_state(self) -> bool:
        return self._is_refreshing_state(orders_states.FillOrderState)

    def is_refreshing_canceling_state(self) -> bool:
        return self._is_refreshing_state(orders_states.CancelOrderState)

    def is_pending_cancel_state(self) -> bool:
        return self._is_pending_state(orders_states.CancelOrderState)

    def _is_refreshing_state(self, state_type) -> bool:
        return self.is_refreshing() and isinstance(self.state, state_type)

    def _is_pending_state(self, state_type) -> bool:
        return self.is_pending() and isinstance(self.state, state_type)

    def can_be_edited(self) -> bool:
        # orders that are not yet open or already open can be edited
        return self.state is None or (self.state.is_open() and not self.is_refreshing())

    def use_current_price_as_origin_price(self):
        # Override to return True when the current order price can't be set by the user (ex: market orders)
        return False

    def get_position_side(self, future_contract):
        """
        :param future_contract: the associated future contract
        :return: the position side if it can be determined, else raise an InvalidPositionSide
        """
        if self.position_side is not None:
            return self.position_side
        if future_contract.is_one_way_position_mode():
            return enums.PositionSide.BOTH
        raise errors.InvalidPositionSide(f"Can't determine order position side while using hedge position mode")

    @contextlib.contextmanager
    def active_or_inactive_transition(self):
        previous_value = self.is_in_active_inactive_transition
        try:
            self.is_in_active_inactive_transition = True
            yield
        finally:
            self.is_in_active_inactive_transition = previous_value

    def use_active_trigger(self, active_trigger: base_trigger_import.BaseTrigger):
        if active_trigger is None:
            raise ValueError("active_trigger must be provided")
        if self.active_trigger is None:
            self.active_trigger = active_trigger
        elif self.active_trigger.is_pending():
            logging.get_logger(self.get_logger_name()).error(
                f"The current active trigger ({str(self.active_trigger)}) is still pending, canceling it "
                f"and replacing it by this new one, this is works but is unexpected."
            )
            self.active_trigger.clear()
            self.active_trigger = active_trigger
        else:
            self.active_trigger.update_from_other_trigger(active_trigger)

    async def set_as_inactive(self, active_trigger: base_trigger_import.BaseTrigger):
        """
        Marks the instance as inactive and ensures the inactive order watcher is scheduled.
        """
        logging.get_logger(self.get_logger_name()).info("Order is switching to inactive")
        self.use_active_trigger(active_trigger)
        self.is_active = False
        # enforce attributes in case order has been canceled
        self.status = enums.OrderStatus.OPEN
        self.canceled_time = 0
        await self._ensure_inactive_order_watcher()

    def should_become_active(self, price_time: float, current_price: decimal.Decimal) -> bool:
        if self.is_active:
            return False
        if price_time >= self.creation_time:
            return self.active_trigger.triggers(current_price)
        return False

    async def _ensure_inactive_order_watcher(self):
        if self.is_active:
            # order is active, nothing to do
            return
        if self.is_waiting_for_chained_trigger:
            # watcher should be created only when this chained order is created
            # will be called again once the chained order gets created
            return
        if not self.exchange_manager.trader.enable_inactive_orders or self.is_self_managed():
            # can't be inactive
            logging.get_logger(self.get_logger_name()).error(
                f"Unexpected inactive order (simulated={self.simulated} self_managed={self.is_self_managed()}): {self}"
            )
            return
        if self.active_trigger is None:
            logging.get_logger(self.get_logger_name()).error("self.active_trigger is None")
            return
        if self.is_synchronization_enabled():
            logging.get_logger(self.get_logger_name()).debug(
                f"Creating watcher for inactive order: {str(self)} - trigger: {self.active_trigger}"
            )
            await self.active_trigger.create_watcher(self.exchange_manager, self.symbol, self.creation_time)

    @contextlib.contextmanager
    def order_state_creation(self):
        try:
            yield
        except errors.InvalidOrderState as exc:
            logging.get_logger(self.get_logger_name()).exception(exc, True, f"Error when creating order state: {exc}")

    async def on_inactive_from_active(self):
        """
        Update the order to be considered as "confirmed" inactive. Called when the order was active before
        """
        if self.active_trigger is None:
            raise ValueError(
                f"self.active_trigger must be provided to set an order as inactive"
            )
        await self.set_as_inactive(self.active_trigger)
        self.clear_active_order_elements()

    async def on_active_from_inactive(self):
        """
        Update the order to be considered as "confirmed" active => the new active order was created
        Self has already been removed from order manager by the new active order as they share the same order_id
        """
        self.is_active = True
        self.clear()

    async def on_active_trigger(
        self, strategy_timeout: typing.Optional[float], wait_for_fill_callback: typing.Optional[typing.Callable]
    ):
        try:
            if self.is_active:
                logging.get_logger(self.get_logger_name()).error("Skipped active trigger for an already active order.")
                return
            logging.get_logger(self.get_logger_name()).info("Order is becoming active.")
            await order_util.create_as_active_order_using_strategy_if_any(self, strategy_timeout, wait_for_fill_callback)
        except Exception as err:
            logging.get_logger(self.get_logger_name()).exception(
                err,
                True,
                f"Unexpected error ({err.__class__.__name__}: {err}) "
                f"when creating active order from inactive order: {self}"
            )

    async def on_pending_creation(self, is_from_exchange_data=False, enable_associated_orders_creation=True,
        is_already_counted_in_available_funds=False
    ):
        with self.order_state_creation():
            state_class = orders_states.PendingCreationChainedOrderState if self.is_waiting_for_chained_trigger \
                else orders_states.PendingCreationOrderState
            self.state = state_class(
                self, is_from_exchange_data=is_from_exchange_data,
                enable_associated_orders_creation=enable_associated_orders_creation,
                is_already_counted_in_available_funds=is_already_counted_in_available_funds
            )
            await self.state.initialize()

    async def on_open(
        self, force_open=False, is_from_exchange_data=False, enable_associated_orders_creation=True,
        is_already_counted_in_available_funds=False
    ):
        with self.order_state_creation():
            if isinstance(self.state, orders_states.PendingCreationOrderState):
                await self.state.trigger_terminate()
            if isinstance(self.state, orders_states.OpenOrderState):
                if not self.state.is_initialized:
                    logging.get_logger(self.get_logger_name()).error(f"on_open called with existing "
                                                                     f"uninitialized OpenOrderState.")
                # state has already been created and initialized
                return
            self.state = orders_states.OpenOrderState(
                self, is_from_exchange_data=is_from_exchange_data,
                enable_associated_orders_creation=enable_associated_orders_creation,
                is_already_counted_in_available_funds=is_already_counted_in_available_funds
            )
            await self.state.initialize(forced=force_open)

    async def on_fill(
        self, force_fill=False, is_from_exchange_data=False, enable_associated_orders_creation=None,
        is_already_counted_in_available_funds=False
    ):
        enable_associated_orders_creation = self.state.enable_associated_orders_creation \
            if (self.state and enable_associated_orders_creation is None) \
            else (True if enable_associated_orders_creation is None else enable_associated_orders_creation)
        if self.is_in_active_inactive_transition:
            logging.get_logger(self.get_logger_name()).info("Completing active-inactive transition: order is filled")
            self.is_in_active_inactive_transition = False
        if (self.is_open() and not self.is_refreshing()) or self.is_pending_creation():
            with self.order_state_creation():
                self.state = orders_states.FillOrderState(
                    self, is_from_exchange_data=is_from_exchange_data,
                    enable_associated_orders_creation=enable_associated_orders_creation,
                    is_already_counted_in_available_funds=is_already_counted_in_available_funds
                )
                await self.state.initialize(forced=force_fill)
        else:
            logging.get_logger(self.get_logger_name()).debug(f"Trying to fill a refreshing or previously filled "
                                                             f"or canceled order: "
                                                             f"ignored fill call for {self}")

    async def on_close(self, force_close=False, is_from_exchange_data=False, enable_associated_orders_creation=None,
        is_already_counted_in_available_funds=False
    ):
        enable_associated_orders_creation = self.state.enable_associated_orders_creation \
            if (self.state and enable_associated_orders_creation is None) \
            else (True if enable_associated_orders_creation is None else enable_associated_orders_creation)
        with self.order_state_creation():
            self.state = orders_states.CloseOrderState(
                self, is_from_exchange_data=is_from_exchange_data,
                enable_associated_orders_creation=enable_associated_orders_creation,
                is_already_counted_in_available_funds=is_already_counted_in_available_funds
            )
            await self.state.initialize(forced=force_close)

    async def on_cancel(
        self, is_from_exchange_data=False, force_cancel=False, enable_associated_orders_creation=None,
        ignored_order=None, is_already_counted_in_available_funds=False
    ):
        enable_associated_orders_creation = self.state.enable_associated_orders_creation \
            if (self.state and enable_associated_orders_creation is None) \
            else (True if enable_associated_orders_creation is None else enable_associated_orders_creation)
        with self.order_state_creation():
            self.state = orders_states.CancelOrderState(
                self, is_from_exchange_data=is_from_exchange_data,
                enable_associated_orders_creation=enable_associated_orders_creation,
                is_already_counted_in_available_funds=is_already_counted_in_available_funds
            )
            await self.state.initialize(forced=force_cancel, ignored_order=ignored_order)

    def on_fill_actions(self):
        """
        Perform on_fill actions
        """
        self.status = enums.OrderStatus.FILLED

    async def on_filled(self, enable_associated_orders_creation, force_artificial_orders=False):
        """
        Filling complete callback
        """
        if enable_associated_orders_creation:
            await self._trigger_chained_orders(enable_associated_orders_creation)
        elif self.chained_orders:
            logging.get_logger(self.get_logger_name()).info(
                f"Skipped chained orders creation for {len(self.chained_orders)} chained orders: "
                f"enable_associated_orders_creation is {enable_associated_orders_creation}"
            )

    def associate_to_entry(self, entry_order_id):
        if self.associated_entry_ids is None:
            self.associated_entry_ids = []
        if entry_order_id not in self.associated_entry_ids:
            self.associated_entry_ids.append(entry_order_id)
            return True
        return False

    def update_quantity_with_order_fees(self, other_order_or_trade):
        relevant_fees_amount = order_util.get_fees_for_currency(other_order_or_trade.fee, self.quantity_currency)
        if relevant_fees_amount:
            logger = logging.get_logger(self.get_logger_name())
            fees_str = f"Paid {self.quantity_currency} fees: {relevant_fees_amount}, " \
                       f"initial order size: {self.origin_quantity}"
            if relevant_fees_amount >= self.origin_quantity:
                logger.error(f"Impossible to update chained order amount according to triggering order fees: "
                             f"fees are larger than then chained order size. {fees_str}")
                return False
            self.origin_quantity = decimal_order_adapter.decimal_adapt_quantity(
                self.exchange_manager.exchange.get_market_status(self.symbol, with_fixer=False),
                self.origin_quantity - relevant_fees_amount
            )
            fees_str = f"{fees_str}, updated size: {self.origin_quantity}"
            logger.debug(f"Updating chained order quantity with triggering order fees. {fees_str}")
        return True

    async def update_price_if_outdated(self):
        """
        Implement if necessary
        """

    async def _trigger_chained_orders(self, enable_associated_orders_creation):
        logger = logging.get_logger(self.get_logger_name())
        for index, order in enumerate(self.chained_orders):
            if order.is_cleared():
                logger.error(
                    f"Chained order {index + 1}/{len(self.chained_orders)} has been cleared: skipping "
                    f"creation (order: {order})"
                )
                continue
            can_be_created = await order_util.adapt_chained_order_before_creation(self, order)
            if can_be_created and order.should_be_created():
                logger.info(f"Creating chained order {index + 1}/{len(self.chained_orders)}")
                await self._create_triggered_chained_order(order, enable_associated_orders_creation)
            else:
                logger.info(f"Skipping cancelled chained order {index + 1}/{len(self.chained_orders)}")

    async def _create_triggered_chained_order(self, order, enable_associated_orders_creation):
        logger = logging.get_logger(self.get_logger_name())
        try:
            await order_util.create_as_chained_order(order)
        except errors.ExchangeClosedPositionError as err:
            message = (
                f"chained order is cancelled as it can't be created: position is closed "
                f"on exchange ({err}) order: {order.order_id}"
            )
            if order.reduce_only:
                # can happen on reduce only orders
                logger.warning(f"Reduce only {message}")
            else:
                # should not happen on non-reduce only orders
                logger.error(f"Unexpected: Non reduce only {message}")
            # order can't be created: consider it cancelled
            # note: grouped orders will also be skipped as this one is cancelled (should_be_created will be false)
            order.status = enums.OrderStatus.CLOSED
            # clear state to avoid using outdated pending creation state
            order.state = None
            order.clear()
        except errors.ExchangeOrderInstantTriggerError as err:
            logger.info(f"Order would instantly trigger ({err}). Creating artificial order instead.")
            equivalent_order = await order.create_on_filled_artificial_order(enable_associated_orders_creation)
            if equivalent_order is None:
                # should not happen on limit or market only orders
                logger.error(f"Unexpected instant trigger error: {err} when creating chained order {order}")
            else:
                # acceptable: convert this order into its "triggered artificial order" equivalent
                logger.warning(
                    f"Outdated chained order: order trigger price has already been reached. "
                    f"Creating equivalent {equivalent_order.get_name()} artificial order instead. "
                    f"Initial order: {order}, artificial order: {equivalent_order}."
                )
            # note: grouped orders will also be skipped as this one is filled (should_be_created will be false)
            order.status = enums.OrderStatus.CLOSED
            # clear state to avoid using outdated pending creation state
            order.state = None
            order.clear()
        except Exception as err:
            logger.exception(
                err,
                True,
                f"Unexpected error ({err.__class__.__name__}: {err}) when creating chained order: {order}"
            )

    async def set_as_chained_order(self, triggered_by, has_been_bundled, exchange_creation_params,
                                   update_with_triggering_order_fees, **trader_creation_kwargs):
        if triggered_by is self:
            raise errors.ConflictingOrdersError("Impossible to chain an order to itself")
        self.triggered_by = triggered_by
        # update forecasted fees as initial price will now be the triggered_by filling price
        self._update_taker_maker()
        self.update_with_triggering_order_fees = update_with_triggering_order_fees
        self.has_been_bundled = has_been_bundled
        self.exchange_creation_params = exchange_creation_params
        self.trader_creation_kwargs = trader_creation_kwargs
        self.is_waiting_for_chained_trigger = True
        self.status = enums.OrderStatus.PENDING_CREATION
        await self.initialize()

    def should_be_created(self):
        return not self.is_created() and self.is_waiting_for_chained_trigger and \
            not self._are_simultaneously_triggered_grouped_orders_closed()

    def _are_simultaneously_triggered_grouped_orders_closed(self):
        if self.triggered_by is None:
            return False
        for other_order in self.triggered_by.chained_orders:
            if other_order is self:
                continue
            order_to_check = (
                other_order
                if other_order.on_filled_artificial_order is None
                else other_order.on_filled_artificial_order
            )
            if (
                self.order_group is not None and self.order_group is order_to_check.order_group
                and (
                    order_to_check.is_closed()  # grouped order has been closed
                    or not order_to_check.SUPPORTS_GROUPING # grouped order can't be used in groups (anymore)
                )
            ):
                return True
        return False

    def has_exchange_fetched_fees(self):
        if not self.fee:
            return False
        try:
            # requires fees to be from exchange and having a not None exchange original cost
            return self.fee[enums.FeePropertyColumns.IS_FROM_EXCHANGE.value] \
                   and self.fee[enums.FeePropertyColumns.EXCHANGE_ORIGINAL_COST.value] is not None
        except KeyError:
            return False

    def get_computed_fee(self, forced_value=None, use_origin_quantity_and_price=False):
        is_from_exchange = False
        price = self.origin_price if use_origin_quantity_and_price else self.filled_price
        quantity = self.origin_quantity if use_origin_quantity_and_price else self.filled_quantity
        # consider worse case taker fees when using use_origin_quantity_and_price as the order is not filled yet
        taker_or_maker = enums.ExchangeConstantsOrderColumns.TAKER.value \
            if use_origin_quantity_and_price else self.taker_or_maker
        if self.is_cleared():
            # order is cleared, it might have been filled or cancelled. Use existing fees
            return copy.copy(self.fee)
        if self.fees_currency_side is enums.FeesCurrencySide.UNDEFINED:
            computed_fee = self.exchange_manager.exchange.get_trade_fee(
                self.symbol, self.order_type, quantity, price, taker_or_maker
            )
            value = computed_fee[enums.FeePropertyColumns.COST.value]
            currency = computed_fee[enums.FeePropertyColumns.CURRENCY.value]
            is_from_exchange = computed_fee[enums.FeePropertyColumns.IS_FROM_EXCHANGE.value]
        else:
            symbol_fees = self.exchange_manager.exchange.get_fees(self.symbol)
            fees = decimal.Decimal(f"{symbol_fees[taker_or_maker]}")
            if self.fees_currency_side is enums.FeesCurrencySide.CURRENCY:
                value = quantity / price * fees
                currency = self.currency
            else:
                value = quantity * price * fees
                currency = self.market
        return {
            enums.FeePropertyColumns.IS_FROM_EXCHANGE.value: is_from_exchange,
            enums.FeePropertyColumns.COST.value: forced_value if forced_value is not None else value,
            enums.FeePropertyColumns.CURRENCY.value: currency,
        }

    def get_profitability(self):
        if self.filled_price != 0 and self.created_last_price != 0:
            if self.filled_price >= self.created_last_price:
                self.order_profitability = 1 - self.filled_price / self.created_last_price
                if self.side is enums.TradeOrderSide.SELL:
                    self.order_profitability *= -1
            else:
                self.order_profitability = 1 - self.created_last_price / self.filled_price
                if self.side is enums.TradeOrderSide.BUY:
                    self.order_profitability *= -1
        return self.order_profitability

    async def default_exchange_update_order_status(self):
        raw_order = await self.exchange_manager.exchange.get_order(
            self.exchange_order_id, self.symbol, order_type=self.order_type
        )
        new_status = order_util.parse_order_status(raw_order)
        self.is_synchronized_with_exchange = True
        if new_status in {enums.OrderStatus.FILLED, enums.OrderStatus.CLOSED}:
            await self.on_fill()
        elif new_status is enums.OrderStatus.CANCELED:
            await self.trader.cancel_order(self)

    def generate_executed_time(self):
        return self.exchange_manager.exchange.get_exchange_current_time()

    def is_counted_in_available_funds(self) -> bool:
        if self.state and self.state.is_already_counted_in_available_funds:
            return False
        if self.is_active:
            if self.trader.simulate or (
                self.reduce_only and self.exchange_manager and self.exchange_manager.is_future
            ):
                return not (
                    # in trading simulator, stop orders and TP do not lock funds
                    # when trading futures, reduce only stop loss and take profit orders do not lock funds
                    order_util.is_stop_order(self.order_type) or order_util.is_take_profit_order(self.order_type)
                )
            # lock funds when not self-managed
            return not self.is_self_managed()
        # inactive: not locking funds
        return False

    def is_self_managed(self):
        if self.is_cleared():
            return order_util.is_stop_order(self.order_type) or order_util.is_take_profit_order(self.order_type)
        return self.trader.allow_artificial_orders and \
            not self.is_synchronized_with_exchange and \
            not self.exchange_manager.exchange.is_supported_order_type(self.order_type)

    def is_long(self):
        return self.side is enums.TradeOrderSide.BUY

    def is_short(self):
        return self.side is enums.TradeOrderSide.SELL

    def is_partially_filled(self) -> bool:
        return constants.ZERO < self.filled_quantity < self.origin_quantity

    def get_remaining_quantity(self) -> decimal.Decimal:
        return self.origin_quantity - self.filled_quantity

    def get_locked_quantity(self) -> decimal.Decimal:
        return self.filled_quantity if (
            self.is_filled() or self.USE_ORIGIN_QUANTITY_AS_FILLED_QUANTITY
        ) else self.get_remaining_quantity()

    def get_remaining_cost(self) -> decimal.Decimal:
        return self.get_cost(self.get_remaining_quantity())

    def update_from_raw(self, raw_order):
        if self.side is None or self.order_type is None:
            try:
                self._update_type_from_raw(raw_order)
                if self.taker_or_maker is None:
                    self._update_taker_maker()
            except KeyError:
                logging.get_logger(self.__class__.__name__).warning("Failed to parse order side and type")

        # use stop price when available
        price = (
            raw_order.get(enums.ExchangeConstantsOrderColumns.PRICE.value, None)
            or raw_order.get(enums.ExchangeConstantsOrderColumns.STOP_PRICE.value, None)
            or raw_order.get(enums.ExchangeConstantsOrderColumns.STOP_LOSS_PRICE.value, None)
            or raw_order.get(enums.ExchangeConstantsOrderColumns.TAKE_PROFIT_PRICE.value, None)
            or 0.0
        )
        filled_price = decimal.Decimal(str(price))
        # set average price with real average price if available, use filled_price otherwise
        average_price = decimal.Decimal(str(
            raw_order.get(enums.ExchangeConstantsOrderColumns.AVERAGE.value, 0.0) or filled_price
        ))

        return self.update(
            symbol=str(raw_order.get(enums.ExchangeConstantsOrderColumns.SYMBOL.value, None)),
            current_price=decimal.Decimal(str(price)),
            quantity=decimal.Decimal(str(raw_order.get(enums.ExchangeConstantsOrderColumns.AMOUNT.value, 0.0) or 0.0)),
            price=decimal.Decimal(str(price)),
            status=order_util.parse_order_status(raw_order),
            order_id=raw_order.get(enums.ExchangeConstantsOrderColumns.ID.value, None),
            exchange_order_id=str(raw_order.get(enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value, None)),
            quantity_filled=decimal.Decimal(str(raw_order.get(enums.ExchangeConstantsOrderColumns.FILLED.value, 0.0)
                                                or 0.0)),
            filled_price=decimal.Decimal(str(filled_price)),
            average_price=decimal.Decimal(str(average_price)),
            total_cost=decimal.Decimal(str(raw_order.get(enums.ExchangeConstantsOrderColumns.COST.value, 0.0) or 0.0)),
            fee=order_util.parse_raw_fees(raw_order.get(enums.ExchangeConstantsOrderColumns.FEE.value, None)),
            timestamp=raw_order.get(enums.ExchangeConstantsOrderColumns.TIMESTAMP.value, None),
            reduce_only=raw_order.get(enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value, False),
            trigger_above=raw_order.get(enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value, None)
        )

    async def update_from_order(self, other_order):
        self.is_synchronized_with_exchange = other_order.is_synchronized_with_exchange
        self.is_from_this_octobot = other_order.is_from_this_octobot

        self.origin_quantity = other_order.origin_quantity
        self.origin_price = other_order.origin_price
        self.origin_stop_price = other_order.origin_stop_price
        self.symbol = other_order.symbol
        self.currency = other_order.currency
        self.market = other_order.market
        self.quantity_currency = other_order.quantity_currency
        self.taker_or_maker = other_order.taker_or_maker
        self.side = other_order.side

        self.order_id = other_order.order_id
        self.exchange_order_id = other_order.exchange_order_id
        self.status = other_order.status

        self.filled_quantity = other_order.filled_quantity
        self.filled_price = other_order.filled_price
        self.fee = other_order.fee
        self.fees_currency_side = other_order.fees_currency_side
        self.total_cost = other_order.total_cost
        self.order_profitability = other_order.order_profitability
        self.executed_time = other_order.executed_time

        self.canceled_time = other_order.canceled_time

        self.reduce_only = other_order.reduce_only

        self.position_side = other_order.position_side

        self.is_waiting_for_chained_trigger = other_order.is_waiting_for_chained_trigger

        if other_order.state is not None:
            await other_order.state.replace_order(self)

    def update_from_storage_order_details(self, order_details):
        # rebind order attributes that are not stored on exchange
        order_dict = order_details.get(constants.STORAGE_ORIGIN_VALUE, {})
        self.tag = order_dict.get(enums.ExchangeConstantsOrderColumns.TAG.value, self.tag)
        self.broker_applied = order_dict.get(
            enums.ExchangeConstantsOrderColumns.BROKER_APPLIED.value,
            self.broker_applied
        )
        self.order_id = order_dict.get(enums.ExchangeConstantsOrderColumns.ID.value, self.order_id)
        self.exchange_order_id = order_dict.get(enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value,
                                                self.exchange_order_id)
        self.taker_or_maker = enums.ExchangeConstantsMarketPropertyColumns(
            order_dict[enums.ExchangeConstantsOrderColumns.TAKER_OR_MAKER.value]
        ).value if order_dict.get(enums.ExchangeConstantsOrderColumns.TAKER_OR_MAKER.value) else self.taker_or_maker
        self.is_active = order_dict.get(enums.ExchangeConstantsOrderColumns.IS_ACTIVE.value, self.is_active)
        if active_trigger := order_details.get(enums.StoredOrdersAttr.ACTIVE_TRIGGER.value):
            active_trigger_price = (
                decimal.Decimal(str(active_trigger[enums.StoredOrdersAttr.ACTIVE_TRIGGER_PRICE.value]))
                if active_trigger.get(enums.StoredOrdersAttr.ACTIVE_TRIGGER_PRICE.value) else None
            )
            active_trigger_above = active_trigger.get(enums.StoredOrdersAttr.ACTIVE_TRIGGER_ABOVE.value)
            if active_trigger_price is not None and active_trigger_above is not None:
                self.use_active_trigger(
                    order_util.create_order_price_trigger(self, active_trigger_price, active_trigger_above)
                )
            else:
                logging.get_logger(self.__class__.__name__).error(
                    f"Ignored unknown trigger configuration: {active_trigger}"
                )
        if cancel_policy := order_details.get(enums.StoredOrdersAttr.CANCEL_POLICY.value):
            self.cancel_policy = cancel_policy_factory.create_cancel_policy(
                cancel_policy[enums.StoredOrdersAttr.CANCEL_POLICY.value],
                cancel_policy[enums.StoredOrdersAttr.CANCEL_KWARGS.value],
            )
        self.trader_creation_kwargs = order_details.get(enums.StoredOrdersAttr.TRADER_CREATION_KWARGS.value,
                                                        self.trader_creation_kwargs)
        self.exchange_creation_params = order_details.get(enums.StoredOrdersAttr.EXCHANGE_CREATION_PARAMS.value,
                                                          self.exchange_creation_params)
        self.has_been_bundled = order_details.get(enums.StoredOrdersAttr.HAS_BEEN_BUNDLED.value,
                                                  self.has_been_bundled)
        self.associated_entry_ids = order_details.get(enums.StoredOrdersAttr.ENTRIES.value,
                                                      self.associated_entry_ids)
        self.update_with_triggering_order_fees = order_details.get(
            enums.StoredOrdersAttr.UPDATE_WITH_TRIGGERING_ORDER_FEES.value, False
        )
        if trailing_profile := order_details.get(enums.StoredOrdersAttr.TRAILING_PROFILE.value):
            self.trailing_profile = trailing_profiles.create_trailing_profile(
                trailing_profiles.TrailingProfileTypes(
                    trailing_profile[enums.StoredOrdersAttr.TRAILING_PROFILE_TYPE.value]
                ),
                trailing_profile[enums.StoredOrdersAttr.TRAILING_PROFILE_DETAILS.value],
            )

    def consider_as_filled(self):
        self.status = enums.OrderStatus.FILLED
        if self.executed_time == 0:
            self.executed_time = self.timestamp
        if self.filled_quantity == constants.ZERO:
            self.filled_quantity = self.origin_quantity
        if self.filled_price == constants.ZERO:
            self.filled_price = self.origin_price
        self._update_total_cost()

    def _update_total_cost(self):
        # use filled amounts when available
        quantity = self.filled_quantity if self.filled_quantity else self.origin_quantity
        self.total_cost = self.get_cost(quantity)

    def get_cost(self, quantity: decimal.Decimal) -> decimal.Decimal:
        price = self.filled_price if self.filled_price else self.origin_price
        if self.quantity_currency == self.currency:
            # quantity in BTC for BTC/USDT => cost = BTC * price(BTC in USDT)
            return quantity * price
        else:
            # quantity in USDT for BTC/USDT => cost = price(BTC in USDT)
            return quantity

    def update_order_filled_values(self, ideal_price: decimal.Decimal):
        if not self.filled_price:
            # keep order.filled_price if already set (!= 0)
            self.filled_price = order_util.get_valid_filled_price(self, ideal_price)
        if not self.filled_quantity or self.exchange_manager.trader.simulate:
            # keep self.filled_quantity if already set (!= 0) in real trading
            self.filled_quantity = self.origin_quantity
        self._update_total_cost()

    def consider_as_canceled(self):
        self.status = enums.OrderStatus.CANCELED
        if self.canceled_time == 0:
            self.canceled_time = self.timestamp

    def update_order_from_raw(self, raw_order):
        self.status = order_util.parse_order_status(raw_order)
        self.total_cost = decimal.Decimal(str(raw_order[enums.ExchangeConstantsOrderColumns.COST.value] or 0))
        self.filled_quantity = decimal.Decimal(str(raw_order[enums.ExchangeConstantsOrderColumns.FILLED.value] or 0))
        self.filled_price = decimal.Decimal(str(raw_order[enums.ExchangeConstantsOrderColumns.PRICE.value] or 0))
        if not self.filled_price and self.filled_quantity:
            self.filled_price = self.total_cost / self.filled_quantity

        self._update_taker_maker()

        self.fee = order_util.parse_raw_fees(raw_order[enums.ExchangeConstantsOrderColumns.FEE.value])

        self.executed_time = self.trader.exchange_manager.exchange.get_uniformized_timestamp(
            raw_order[enums.ExchangeConstantsOrderColumns.TIMESTAMP.value])

    def _update_type_from_raw(self, raw_order):
        try:
            self.exchange_order_type = enums.TradeOrderType(raw_order[enums.ExchangeConstantsOrderColumns.TYPE.value])
        except ValueError:
            self.exchange_order_type = enums.TradeOrderType.UNKNOWN
        self.side, self.order_type = parse_order_type(raw_order)

    def _get_open_price(self):
        if self.triggered_by is None:
            return self.created_last_price
        return self.triggered_by.get_filling_price()  # pylint: disable=protected-access

    def get_filling_price(self):
        return self.origin_price

    def _should_instant_fill(self):
        # default implementation, to be overridden in subclasses
        return False

    def _update_taker_maker(self):
        if self.order_type in [enums.TraderOrderType.SELL_MARKET,
                               enums.TraderOrderType.BUY_MARKET,
                               enums.TraderOrderType.STOP_LOSS]:
            # always true
            self.taker_or_maker = enums.ExchangeConstantsMarketPropertyColumns.TAKER.value
        else:
            # true 90% of the time: impossible to know for sure the reality
            self.taker_or_maker = (
                enums.ExchangeConstantsMarketPropertyColumns.TAKER if self._should_instant_fill()
                else enums.ExchangeConstantsMarketPropertyColumns.MAKER
            ).value

    def is_synchronization_enabled(self):
        return (
            self.exchange_manager is not None and
            self.exchange_manager.exchange_personal_data.orders_manager.enable_order_auto_synchronization
        )

    def to_dict(self):
        filled_price = self.filled_price if self.filled_price > 0 else self.origin_price
        return {
            enums.ExchangeConstantsOrderColumns.ID.value: self.order_id,
            enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: self.exchange_order_id,
            enums.ExchangeConstantsOrderColumns.SYMBOL.value: self.symbol,
            enums.ExchangeConstantsOrderColumns.PRICE.value: filled_price,
            enums.ExchangeConstantsOrderColumns.STATUS.value: self.status.value,
            enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: self.creation_time or self.timestamp,
            enums.ExchangeConstantsOrderColumns.TYPE.value: self.exchange_order_type.value
            if self.exchange_order_type else None,
            enums.ExchangeConstantsOrderColumns.SIDE.value: self.side.value,
            enums.ExchangeConstantsOrderColumns.AMOUNT.value: self.origin_quantity,
            enums.ExchangeConstantsOrderColumns.COST.value: self.total_cost,
            enums.ExchangeConstantsOrderColumns.QUANTITY_CURRENCY.value: self.quantity_currency,
            enums.ExchangeConstantsOrderColumns.FILLED.value: self.filled_quantity,
            enums.ExchangeConstantsOrderColumns.FEE.value: self.fee,
            enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value: self.reduce_only,
            enums.ExchangeConstantsOrderColumns.TAG.value: self.tag,
            enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value: self.trigger_above,
            enums.ExchangeConstantsOrderColumns.SELF_MANAGED.value: self.is_self_managed(),
            enums.ExchangeConstantsOrderColumns.BROKER_APPLIED.value: self.broker_applied,
            enums.ExchangeConstantsOrderColumns.TAKER_OR_MAKER.value: self.taker_or_maker,
            enums.ExchangeConstantsOrderColumns.IS_ACTIVE.value: self.is_active,
        }

    def clear_active_order_elements(self):
        if self.state is not None:
            self.state.clear()


    def clear(self):
        if self.active_trigger:
            self.active_trigger.clear()
        self.clear_active_order_elements()
        self.trader = None # type: ignore
        self.exchange_manager = None # type: ignore
        self.trader_creation_kwargs = {}

    def is_cleared(self):
        return self.exchange_manager is None

    def to_string(self):
        inactive = "" if self.is_active else "[Inactive] "
        chained_order = "" if self.triggered_by is None else \
            "triggered chained order | " if self.is_created() else "untriggered chained order | "
        tag = f" | tag: {self.tag}" if self.tag else ""
        fees = (
            f"Fees : {self.fee[enums.FeePropertyColumns.COST.value]} {self.fee[enums.FeePropertyColumns.CURRENCY.value]} | "
            if self.fee else ""
        )
        trailing_profile = f"Trailing profile : {self.trailing_profile} | " if self.trailing_profile else ""
        cancel_policy = f"Cancel policy : {self.cancel_policy} | " if self.cancel_policy else ""
        filled_quantity = f" ({self.filled_quantity} Filled)" if self.filled_quantity else ""
        return (
            f"{inactive}{self.symbol} | "
            f"{chained_order}"
            f"{self.order_type.name if self.order_type is not None else 'Unknown'} | "
            f"Price : {str(self.origin_price)} | "
            f"Quantity : {str(self.origin_quantity)}{filled_quantity}{' (Reduce only)' if self.reduce_only else ''} | "
            f"State : {self.state.state.value if self.state is not None else 'Unknown'} | "
            f"{trailing_profile}"
            f"{cancel_policy}"
            f"{fees}"
            f"id : {self.order_id}{tag} "
            f"exchange id: {self.exchange_order_id}"
        )

    def __str__(self):
        return self.to_string()

    def is_to_be_maintained(self):
        return self.trader is not None


def parse_order_type(raw_order) -> (enums.TradeOrderSide, enums.TraderOrderType):
    try:
        side: enums.TradeOrderSide = enums.TradeOrderSide(raw_order[enums.ExchangeConstantsOrderColumns.SIDE.value])
        order_type: enums.TradeOrderType = enums.TradeOrderType.UNKNOWN
        parsed_order_type: typing.Optional[enums.TraderOrderType] = enums.TraderOrderType.UNKNOWN
        try:
            order_type = enums.TradeOrderType(raw_order[enums.ExchangeConstantsOrderColumns.TYPE.value])
        except ValueError as e:
            if raw_order[enums.ExchangeConstantsOrderColumns.TYPE.value] is None:
                # Last chance: try to infer order type from taker / maker status
                if enums.ExchangeConstantsOrderColumns.TAKER_OR_MAKER.value in raw_order:
                    return side, _infer_order_type_from_maker_or_taker(raw_order, side)
                # No order type info: use unknown order type
                return side, enums.TraderOrderType.UNKNOWN
            else:
                # Incompatible order type info: raise error
                raise e

        if order_type is enums.TradeOrderType.UNKNOWN:
            parsed_order_type = enums.TraderOrderType.UNKNOWN
        elif order_type is enums.TradeOrderType.UNSUPPORTED:
            parsed_order_type = enums.TraderOrderType.UNSUPPORTED
        elif side is enums.TradeOrderSide.BUY:
            if order_type is enums.TradeOrderType.LIMIT or order_type == enums.TradeOrderType.LIMIT_MAKER:
                parsed_order_type = enums.TraderOrderType.BUY_LIMIT
            elif order_type is enums.TradeOrderType.MARKET:
                parsed_order_type = enums.TraderOrderType.BUY_MARKET
            else:
                parsed_order_type = _get_sell_and_buy_types(order_type)
        elif side is enums.TradeOrderSide.SELL:
            if order_type is enums.TradeOrderType.LIMIT or order_type is enums.TradeOrderType.LIMIT_MAKER:
                parsed_order_type = enums.TraderOrderType.SELL_LIMIT
            elif order_type is enums.TradeOrderType.MARKET:
                parsed_order_type = enums.TraderOrderType.SELL_MARKET
            else:
                parsed_order_type = _get_sell_and_buy_types(order_type)
        return side, parsed_order_type
    except (KeyError, ValueError):
        return None, None


def _infer_order_type_from_maker_or_taker(raw_order, side):
    is_taker = raw_order[enums.ExchangeConstantsOrderColumns.TAKER_OR_MAKER.value] \
               == enums.ExchangeConstantsOrderColumns.TAKER.value
    if side is enums.TradeOrderSide.BUY:
        if is_taker:
            return enums.TraderOrderType.BUY_MARKET
        return enums.TraderOrderType.BUY_LIMIT
    if is_taker:
        return enums.TraderOrderType.SELL_MARKET
    return enums.TraderOrderType.SELL_LIMIT


def _get_trade_order_type(order_type: enums.TraderOrderType) -> typing.Optional[enums.TradeOrderType]:
    if order_type is enums.TraderOrderType.BUY_LIMIT or order_type is enums.TraderOrderType.SELL_LIMIT:
        return enums.TradeOrderType.LIMIT
    if order_type is enums.TraderOrderType.BUY_MARKET or order_type is enums.TraderOrderType.SELL_MARKET:
        return enums.TradeOrderType.MARKET
    elif order_type is enums.TraderOrderType.TAKE_PROFIT:
        return enums.TradeOrderType.TAKE_PROFIT
    elif order_type is enums.TraderOrderType.TAKE_PROFIT_LIMIT:
        return enums.TradeOrderType.TAKE_PROFIT_LIMIT
    elif order_type is enums.TraderOrderType.STOP_LOSS:
        return enums.TradeOrderType.STOP_LOSS
    elif order_type is enums.TraderOrderType.STOP_LOSS_LIMIT:
        return enums.TradeOrderType.STOP_LOSS_LIMIT
    elif order_type is enums.TraderOrderType.TRAILING_STOP:
        return enums.TradeOrderType.TRAILING_STOP
    elif order_type is enums.TraderOrderType.TRAILING_STOP_LIMIT:
        return enums.TradeOrderType.TRAILING_STOP_LIMIT
    return None


def _get_sell_and_buy_types(order_type) -> typing.Optional[enums.TraderOrderType]:
    if order_type is enums.TradeOrderType.STOP_LOSS:
        return enums.TraderOrderType.STOP_LOSS
    elif order_type is enums.TradeOrderType.STOP_LOSS_LIMIT:
        return enums.TraderOrderType.STOP_LOSS_LIMIT
    elif order_type is enums.TradeOrderType.TAKE_PROFIT:
        return enums.TraderOrderType.TAKE_PROFIT
    elif order_type is enums.TradeOrderType.TAKE_PROFIT_LIMIT:
        return enums.TraderOrderType.TAKE_PROFIT_LIMIT
    elif order_type is enums.TradeOrderType.TRAILING_STOP:
        return enums.TraderOrderType.TRAILING_STOP
    elif order_type is enums.TradeOrderType.TRAILING_STOP_LIMIT:
        return enums.TraderOrderType.TRAILING_STOP_LIMIT
    return None
