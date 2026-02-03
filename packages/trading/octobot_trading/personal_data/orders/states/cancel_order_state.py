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
import octobot_commons.html_util as html_util

import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.personal_data.orders.order_state as order_state
import octobot_trading.personal_data.orders.states.order_state_factory as order_state_factory


class CancelOrderState(order_state.OrderState):
    MAX_SYNCHRONIZATION_ATTEMPTS = 5

    def __init__(self, order, is_from_exchange_data, enable_associated_orders_creation=True,
        is_already_counted_in_available_funds=False
    ):
        super().__init__(
            order, is_from_exchange_data, enable_associated_orders_creation=enable_associated_orders_creation,
            is_already_counted_in_available_funds=is_already_counted_in_available_funds
        )
        self.state = enums.OrderStates.CANCELING \
            if ((not self.order.simulated and not self.is_status_cancelled()) or self.is_status_pending()) \
            else enums.OrderStates.CANCELED

    async def initialize_impl(self, forced=False, ignored_order=None) -> None:
        if forced:
            self._force_final_state()

        if (
            self.order.order_group and self.enable_associated_orders_creation
            and not self.order.is_in_active_inactive_transition
        ):
            await self.order.order_group.on_cancel(self.order, ignored_orders=[ignored_order])

        await super().initialize_impl()

    def is_pending(self) -> bool:
        return self.state is enums.OrderStates.CANCELING

    def is_canceled(self) -> bool:
        return self.state is enums.OrderStates.CANCELED

    def is_status_pending(self) -> bool:
        return self.order.status is enums.OrderStatus.PENDING_CANCEL and not self.order.simulated

    def is_status_cancelled(self) -> bool:
        return not self.is_status_pending() and self.order.status in constants.CANCEL_ORDER_STATUS_SCOPE

    def _force_final_state(self):
        self.state = enums.OrderStates.CANCELED
        self.order.status = enums.OrderStatus.CANCELED

    def allows_new_status(self, status) -> bool:
        """
        Don't allow going from canceling to open
        :return: True if the given status is compatible with the current state
        """
        return status in constants.CANCEL_ORDER_STATUS_SCOPE or status in constants.FILL_ORDER_STATUS_SCOPE

    async def _synchronize_with_exchange(self, force_synchronization: bool = False) -> None:
        """
        Ask OrdersChannel Internal producer to refresh the order from the exchange
        :param force_synchronization: When True, for the update of the order from the exchange
        :return: the result of OrdersProducer.update_order_from_exchange()
        """
        if not self.has_already_been_synchronized_once:
            # If we want to sync this state, it means the order is being canceled by the exchange but is not
            # fully canceled yet. Giving some time to the exchange before re-requesting it.
            self.get_logger().info(
                f"{self.__class__.__name__} still pending, synchronizing in {self.PENDING_REFRESH_INTERVAL}s"
            )
            await asyncio.sleep(self.PENDING_REFRESH_INTERVAL)
        await super()._synchronize_with_exchange(force_synchronization=force_synchronization)

    async def on_refresh_successful(self):
        """
        Verify the order is properly canceled
        """
        if self.is_status_pending():
            await self.update()
        elif self.order.status in constants.CANCEL_ORDER_STATUS_SCOPE:
            self.state = enums.OrderStates.CANCELED
            await self.update()
        else:
            await order_state_factory.create_order_state(self.order, is_from_exchange_data=True,
                                                         ignore_states=[enums.States.OPEN])

    async def terminate(self):
        """
        Replace the order state by a close state
        `force_close = True` because we know that the order is successfully cancelled.
        """
        try:
            self.log_event_message(enums.StatesMessages.CANCELLED)
            self.ensure_not_cleared(self.order)

            # set cancel time
            self.order.canceled_time = self.order.exchange_manager.exchange.get_exchange_current_time()

            # update portfolio after close
            async with self.order.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.lock:
                self.ensure_not_cleared(self.order)
                await self.order.exchange_manager.exchange_personal_data.\
                    handle_portfolio_and_position_update_from_order(self.order, require_exchange_update=False)

            # notify order cancelled
            await self.order.exchange_manager.exchange_personal_data.handle_order_update_notification(
                self.order, enums.OrderUpdateType.STATE_CHANGE
            )

            # set close state
            await self.order.on_close(force_close=True)  # TODO force ?
        except Exception as e:
            self.get_logger().exception(
                e, True, f"Fail to execute cancel state termination : {html_util.get_html_summary_if_relevant(e)}."
            )
            raise
