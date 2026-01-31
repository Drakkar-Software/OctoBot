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
import dataclasses
import typing
import octobot_commons.logging
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_trading.enums as enums
import octobot_trading.constants as constants


@dataclasses.dataclass
class ActiveOrderSwapStrategy:
    """
    Will wait up to the given timeout for the non-priority orders to be filled.
    If it is not filled during this time, priority will be re-created and lower priority order will
    return to inactive.
    """
    swap_timeout: float = constants.ACTIVE_ORDER_STRATEGY_SWAP_TIMEOUT
    trigger_price_configuration: str = enums.ActiveOrderSwapTriggerPriceConfiguration.FILLING_PRICE.value

    def is_priority_order(self, order) -> bool:
        raise NotImplementedError("is_priority_order is not implemented")

    async def apply_inactive_orders(
        self, orders: list, 
        trigger_above_by_order_id: typing.Optional[dict[str, bool]] = None
    ):
        for order in orders:
            trigger_above = trigger_above_by_order_id.get(
                order.order_id, order.trigger_above
            ) if trigger_above_by_order_id else order.trigger_above
            trigger_price = self._get_trigger_price(order)
            if self.is_priority_order(order):
                # still register active trigger in case this order becomes inactive
                order.update(
                    active_trigger=order_util.create_order_price_trigger(order, trigger_price, trigger_above)
                )
            else:
                await order.set_as_inactive(
                    order_util.create_order_price_trigger(order, trigger_price, trigger_above)
                )

    def on_order_update(self, order, update_time):
        if order.active_trigger:
            order.active_trigger.update(
                trigger_price=self._get_trigger_price(order), min_trigger_time=update_time,
                update_event=order.is_synchronization_enabled()
            )

    def _get_trigger_price(self, order) -> decimal.Decimal:
        if self.trigger_price_configuration == enums.ActiveOrderSwapTriggerPriceConfiguration.FILLING_PRICE.value:
            return order.get_filling_price()
        if self.trigger_price_configuration == enums.ActiveOrderSwapTriggerPriceConfiguration.ORDER_PARAMS_ONLY.value:
            if order.active_trigger is None or order.active_trigger.trigger_price is None:
                raise ValueError(
                    f"order.active_trigger.trigger_price must be set when using "
                    f"ActiveOrderSwapTriggerPriceConfiguration.ORDER_PARAMS_ONLY. Order: {order}"
                )
            return order.active_trigger.trigger_price
        raise ValueError(f"Unknown trigger price configuration: {self.trigger_price_configuration}")

    async def execute(
        self,
        inactive_order,
        wait_for_fill_callback: typing.Optional[typing.Callable],
        timeout: typing.Optional[float]
    ):
        if inactive_order.order_group is None:
            raise NotImplementedError(f"Input order is not part of a group, this is unexpected: {inactive_order}")
        timeout = self.swap_timeout if timeout is None else timeout
        # strategies should not be executed concurrently or in parallel with other group triggers
        async with inactive_order.order_group.lock_group():
            active_order, now_maybe_partially_inactive_orders, reverse_update_callback = (
                await self._update_group_and_activate_order(inactive_order)
            )
            if active_order is None:
                raise ValueError("No active order was created")
            if not any(self.is_priority_order(inactive_order) for inactive_order in now_maybe_partially_inactive_orders):
                # nothing else to do: no priority order has been deactivated
                return
            # priority order have been deactivated: if newly active order doesn't get filled within timeout,
            # to should get back to inactivity and priority orders should get back to active
            logger = octobot_commons.logging.get_logger(active_order.get_logger_name())
            logger.info(f"Waiting for newly active order to be filled timeout={timeout}s")
            await (
                wait_for_fill_callback(active_order, timeout) if wait_for_fill_callback
                else order_util.wait_for_order_fill(active_order, timeout, True)
            )
            if active_order.is_open() and not (active_order.is_filled() or active_order.is_closed()):
                logger.warning(
                    f"Newly active order was not filled within {timeout}, reversing active "
                    f"order to re-activate priority orders."
                )
                await reverse_update_callback(active_order, now_maybe_partially_inactive_orders)

    async def _update_group_and_activate_order(self, inactive_order) -> (list, typing.Callable[[list], None]):
        if inactive_order.is_active is True:
            raise ValueError(f"Order is active already: {inactive_order}")
        # 1. cancel/edit the other order(s) that need to be canceled first and then create this order
        now_maybe_partially_inactive_orders, reverse_update_callback = \
            await inactive_order.order_group.adapt_before_order_becoming_active(inactive_order)
        # 2. update this order as active
        active_order = await order_util.create_as_active_order_on_exchange(inactive_order, False)
        return active_order, now_maybe_partially_inactive_orders, reverse_update_callback
