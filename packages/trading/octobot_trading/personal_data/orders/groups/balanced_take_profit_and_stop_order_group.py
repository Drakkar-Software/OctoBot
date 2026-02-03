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
import decimal
import typing

import octobot_commons.logging

import octobot_trading.personal_data.orders.order_group as order_group
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_trading.constants as constants
import octobot_trading.signals as signals
import octobot_trading.errors as errors
import octobot_trading.personal_data.orders.active_order_swap_strategies as active_order_swap_strategies


class BalancedTakeProfitAndStopOrderGroup(order_group.OrderGroup):
    """
    BalancedTakeProfitAndStopOrderGroup is linking orders together in the way that if any order of the group is filled
    order cancelled, orders that are on the other extreme of the setup (extremes being take profits and stop losses)
    are reduced or cancelled symmetrically.
    Mostly used to pair stop and limit orders together in a stop-loss / take-profit setup using multiple stop losses
    and take profits.
    Orders that are the further from their last_created_price are reduced / cancelled first
    """
    TAKE_PROFIT = "take_profit"
    STOP = "stop"
    UPDATE = "update"
    CANCEL = "cancel"
    ORDER = "order"
    UPDATED_QUANTITY = "updated_quantity"
    INITIAL_QUANTITY = "initial_quantity"
    UPDATED_PRICE = "updated_price"
    INITIAL_PRICE = "initial_price"

    def __init__(
        self, name, orders_manager,
        active_order_swap_strategy: typing.Optional[active_order_swap_strategies.ActiveOrderSwapStrategy] = None
    ):
        super().__init__(name, orders_manager, active_order_swap_strategy=active_order_swap_strategy)
        # keep track of orders being balanced to avoid nested balance issues
        self.balancing_orders = []

    async def on_fill(self, filled_order, ignored_orders=None):
        """
        Called when an order referencing this group is filled
        This is called right before updating portfolio for this filled order and the
        order fill publication
        :param filled_order: the filled order
        :param ignored_orders: orders that should be ignored
        """
        await self._balance_orders(filled_order, ignored_orders, True)

    async def on_cancel(self, cancelled_order, ignored_orders=None):
        """
        Called when an order referencing this group is cancelled
        This is called before updating portfolio for this cancelled order and the
        order cancel publication
        :param cancelled_order: the cancelled order
        :param ignored_orders: orders that should be ignored
        """
        await self._balance_orders(cancelled_order, ignored_orders, False)

    def can_create_order(self, order_type, quantity):
        """
        Returns True if there is an imbalance allowing to create an order of this type and with this quantity
        :param order_type: order type to create
        :param quantity: quantity to put in order
        :return: True when an imbalance allows it
        """
        balance = self._get_balance(None, None, False)
        if order_util.is_stop_order(order_type):
            return balance[self.STOP].get_balance() + quantity <= balance[self.TAKE_PROFIT].get_balance()
        return balance[self.TAKE_PROFIT].get_balance() + quantity <= balance[self.STOP].get_balance()

    def get_max_order_quantity(self, order_type):
        """
        Returns The maximum order quantity to reach the order side's balance
        :param order_type: order type to create
        :return: the balancing quantity
        """
        balance = self._get_balance(None, None, False)
        if order_util.is_stop_order(order_type):
            max_quantity = balance[self.TAKE_PROFIT].get_balance() - balance[self.STOP].get_balance()
        else:
            max_quantity = balance[self.STOP].get_balance() - balance[self.TAKE_PROFIT].get_balance()
        return max_quantity if max_quantity > constants.ZERO else constants.ZERO

    async def enable(self, enabled):
        # disable when creating order sequentially (and therefore pause balancing)
        # setting enabled to True will trigger an order balance
        await super().enable(enabled)
        if enabled:
            await self._balance_orders(None, None, False)

    async def adapt_before_order_becoming_active(self, order_to_become_active) -> (list, typing.Callable[[list], None]):
        """
        Called before an order referencing this group is becoming active
        """
        # convert the other order of this group into an inactive order => cancel it on exchange
        deactivated_orders = []
        locally_balancing_orders = []
        try:
            cancel_actions, update_actions = self._get_orders_balance_actions(
                order_to_become_active, None, False, locally_balancing_orders
            )
            self.balancing_orders.extend(locally_balancing_orders)
            for order in cancel_actions:
                self.logger.info(
                    f"Cancelling order [{order}] from order group as paired order "
                    f"is becoming active ({order_to_become_active})"
                )
                if await order_util.update_order_as_inactive_on_exchange(order, False):
                    deactivated_orders.append(order)
            applied_updates = await self._apply_update_order_actions(update_actions, False)
        finally:
            # remove locally_balancing_orders from self.balancing_orders
            self.balancing_orders = [
                order
                for order in self.balancing_orders
                if order not in locally_balancing_orders
            ]

        async def reverse_swap(former_order_to_become_active, _):
            # 1. rollback the "former_order_to_become_active" into inactive state
            await order_util.update_order_as_inactive_on_exchange(former_order_to_become_active, False)
            # 2. in case orders have been canceled on exchange, restore them
            for to_activate_order in deactivated_orders:
                await order_util.create_as_active_order_on_exchange(to_activate_order, False)
            # 3. in case orders have been edited on exchange, restore their previous values
            if reverse_updates := [
                # only reverse amounts, price might have changed when trailing, keep it like this
                self._get_reversed_order_update(update_action, [self.UPDATED_QUANTITY])
                for update_action in applied_updates
            ]:
                self.logger.info(f"Restoring {len(reverse_updates)} orders amounts after swap reset")
                await self._apply_update_order_actions(reverse_updates, False)

        now_maybe_partially_inactive_orders = deactivated_orders + [
            applied_update[self.ORDER] for applied_update in applied_updates
        ]
        return now_maybe_partially_inactive_orders, reverse_swap

    def _default_active_order_swap_strategy(self, timeout: float) -> active_order_swap_strategies.ActiveOrderSwapStrategy:
        """
        Called when an order of this group is becoming active
        """
        return active_order_swap_strategies.StopFirstActiveOrderSwapStrategy(timeout)

    def _get_orders_balance_actions(
        self, closed_order, ignored_orders, filled, balancing_orders: list
    ):
        balance = self._get_balance(closed_order, ignored_orders, filled)
        locally_balancing_orders = balance[self.TAKE_PROFIT].orders + balance[self.STOP].orders
        balancing_orders.extend(locally_balancing_orders)
        take_profit_actions = balance[self.TAKE_PROFIT].get_actions_to_balance(balance[self.STOP].get_balance())
        stop_actions = balance[self.STOP].get_actions_to_balance(balance[self.TAKE_PROFIT].get_balance())
        return (
            take_profit_actions[self.CANCEL] + stop_actions[self.CANCEL],
            take_profit_actions[self.UPDATE] + stop_actions[self.UPDATE]
        )

    async def _balance_orders(self, closed_order, ignored_orders, filled):
        if not self.enabled:
            return
        locally_balancing_orders = []
        async with self.lock_group():
            try:
                updated_orders = False
                cancel_actions, update_actions = self._get_orders_balance_actions(
                    closed_order, ignored_orders, filled, locally_balancing_orders
                )
                self.balancing_orders.extend(locally_balancing_orders)
                for order in cancel_actions:
                    try:
                        self.logger.debug(f"Cancelling order to keep balance, order: {order} as {closed_order} is closed")
                        async with signals.remote_signal_publisher(order.trader.exchange_manager, order.symbol, True):
                            await signals.cancel_order(
                                order.trader.exchange_manager, signals.should_emit_trading_signal(order.trader.exchange_manager),
                                order, ignored_order=closed_order, dependencies=None
                            )
                    except (errors.OrderCancelError, errors.UnexpectedExchangeSideOrderStateError) as err:
                        self.logger.error(f"Skipping order cancel: {err}")
                    updated_orders = True
                updated_orders = bool(
                    await self._apply_update_order_actions(update_actions, True)
                ) or updated_orders
                if not updated_orders:
                    self.logger.debug("Nothing to update, orders are already evenly balanced")
            except Exception as e:
                self.logger.exception(e, True, f"Error when balancing orders: {e}")
            finally:
                # remove locally_balancing_orders from self.balancing_orders
                self.balancing_orders = [
                    order
                    for order in self.balancing_orders
                    if order not in locally_balancing_orders
                ]

    async def _apply_update_order_actions(self, update_actions, emit_trading_signals) -> list:
        applied_updates = []
        for update_data in update_actions:
            order = update_data[self.ORDER]
            update_info = ""
            edited_quantity = None
            edited_price = None
            if (
                update_data[self.UPDATED_QUANTITY] is not None
                and update_data[self.UPDATED_QUANTITY] != order.origin_quantity
            ):
                update_info = f"Updating order quantity to {update_data[self.UPDATED_QUANTITY]} to keep balance. "
                edited_quantity = update_data[self.UPDATED_QUANTITY]
            if self.UPDATED_PRICE in update_data and update_data[self.UPDATED_PRICE] != order.origin_price:
                update_info = f"{update_info}Updating price to {update_data[self.UPDATED_PRICE]}. "
                edited_price = update_data[self.UPDATED_PRICE]
            if edited_quantity or edited_price:
                self.logger.info(f"{update_info}Order: {order}")
                async with signals.remote_signal_publisher(order.trader.exchange_manager, order.symbol, emit_trading_signals):
                    await signals.edit_order(
                        order.trader.exchange_manager,
                        signals.should_emit_trading_signal(order.trader.exchange_manager),
                        order,
                        edited_quantity=edited_quantity,
                        edited_price=edited_price
                    )
                applied_updates.append(update_data)
            else:
                self.logger.info(f"Order already up-to-date, skipped editing: {order}")
        return applied_updates

    def _balances_factory(self, closed_order, filled):
        return {
            self.TAKE_PROFIT: SideBalance(closed_order, filled),
            self.STOP: SideBalance(closed_order, filled)
        }

    def _get_balance(self, closed_order, ignored_orders, filled):
        balance = self._balances_factory(closed_order, filled)
        for order in self.get_group_open_orders():
            if (
                (closed_order is None or order.order_id != closed_order.order_id)
                and (ignored_orders is None or order not in ignored_orders)
                and order not in self.balancing_orders
            ):
                if order_util.is_stop_order(order.order_type):
                    balance[self.STOP].add_order(order)
                else:
                    balance[self.TAKE_PROFIT].add_order(order)
        return balance

    @classmethod
    def _get_reversed_order_update(cls, order_update: dict, included_fields: list) -> dict:
        return {
            cls.ORDER: order_update[cls.ORDER],
            cls.UPDATED_QUANTITY:
                order_update[cls.INITIAL_QUANTITY] if cls.UPDATED_QUANTITY in included_fields else None,
        }


class SideBalance:
    def __init__(self, closed_order, filled):
        self.closed_order = closed_order
        self.are_closed_orders_filled = filled
        self.orders = []

    def add_order(self, order):
        self.orders.append(order)
        # orders are sorted according to their distance from their last created price: the further the earlier in list
        # warning: not working with negative prices
        self.orders = sorted(self.orders, key=lambda o: -abs(o.origin_price-o.created_last_price))

    def get_actions_to_balance(self, target_balance: decimal.Decimal):
        actions = {
            BalancedTakeProfitAndStopOrderGroup.CANCEL: [],
            BalancedTakeProfitAndStopOrderGroup.UPDATE: [],
        }
        balance = self.get_balance()
        balance_update_required = True
        if target_balance < constants.ZERO:
            target_balance = abs(target_balance)
        if balance <= target_balance:
            # only reducing the current balance might be possible
            balance_update_required = False
        to_be_reduced_amount = constants.ZERO
        remaining_orders = list(self.orders)
        if balance_update_required:
            while remaining_orders and balance - to_be_reduced_amount > target_balance:
                order_quantity = remaining_orders[0].origin_quantity
                if balance - to_be_reduced_amount - order_quantity >= target_balance:
                    # cancel order and keep reducing
                    actions[BalancedTakeProfitAndStopOrderGroup.CANCEL].append(remaining_orders.pop(0))
                    to_be_reduced_amount += order_quantity
                else:
                    # update order and stop reducing
                    actions[BalancedTakeProfitAndStopOrderGroup.UPDATE].append(
                        self.get_order_update(
                            remaining_orders.pop(0),
                            target_balance - (balance - to_be_reduced_amount - order_quantity)
                        )
                    )
                    break
        for order in remaining_orders:
            # check for other kind of update if any
            actions[BalancedTakeProfitAndStopOrderGroup.UPDATE].append(
                self.get_order_update(order, None)
            )
        return actions

    def get_order_update(self, order, updated_quantity: typing.Optional[decimal.Decimal]) -> dict:
        return {
            BalancedTakeProfitAndStopOrderGroup.ORDER: order,
            BalancedTakeProfitAndStopOrderGroup.UPDATED_QUANTITY: updated_quantity,
            BalancedTakeProfitAndStopOrderGroup.INITIAL_QUANTITY: order.origin_quantity,
        }

    def get_balance(self):
        if self.orders:
            return sum(order.origin_quantity for order in self.orders)
        return constants.ZERO

    def get_logger(self):
        return octobot_commons.logging.get_logger(self.__class__.__name__)
