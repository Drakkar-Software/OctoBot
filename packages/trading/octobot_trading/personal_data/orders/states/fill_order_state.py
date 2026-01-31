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
import octobot_commons.html_util as html_util

import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.personal_data.orders.order_state as order_state
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_trading.personal_data.orders.states.order_state_factory as order_state_factory


class FillOrderState(order_state.OrderState):
    MAX_SYNCHRONIZATION_ATTEMPTS = 5

    def __init__(self, order, is_from_exchange_data, enable_associated_orders_creation=True,
        is_already_counted_in_available_funds=False
    )   :
        super().__init__(
            order, is_from_exchange_data, enable_associated_orders_creation=enable_associated_orders_creation,
            is_already_counted_in_available_funds=is_already_counted_in_available_funds
        )
        self.state = enums.OrderStates.FILLING \
            if ((
                    (not self.order.simulated and not self.order.is_self_managed())
                    and not self.is_status_filled()
                ) or self.is_status_pending()) \
            else enums.OrderStates.FILLED

    async def initialize_impl(self, forced=False) -> None:
        if forced:
            self._force_final_state()
        return await super().initialize_impl()

    def _force_final_state(self):
        self.state = enums.OrderStates.FILLED
        self.order.status = enums.OrderStatus.FILLED

    def is_pending(self) -> bool:
        return self.state is enums.OrderStates.FILLING

    def is_filled(self) -> bool:
        return self.state is enums.OrderStates.FILLED

    def is_status_pending(self) -> bool:
        return self.order.status is enums.OrderStatus.PARTIALLY_FILLED

    def is_status_filled(self) -> bool:
        return not self.is_status_pending() and self.order.status in constants.FILL_ORDER_STATUS_SCOPE

    def allows_new_status(self, status) -> bool:
        """
        Don't allow going from filling to open
        :return: True if the given status is compatible with the current state
        """
        return status in constants.FILL_ORDER_STATUS_SCOPE or status in constants.CANCEL_ORDER_STATUS_SCOPE

    async def on_refresh_successful(self):
        """
        Synchronize the filling status with the exchange
        can be a partially filled
        can also be still pending
        or be fully filled
        """
        self.get_logger().info(f"on_refresh_successful [{self.order.status}] for {self.order}")
        if self.order.is_partially_filled():
            self.get_logger().info(f"Partially filled order: {str(self.order)}")
            # notify order partially filled
            await self.order.exchange_manager.exchange_personal_data.handle_order_update_notification(
                self.order, enums.OrderUpdateType.STATE_CHANGE
            )
        elif self.order.status in constants.FILL_ORDER_STATUS_SCOPE:
            self.state = enums.OrderStates.FILLED
            await self.update()
        else:
            await order_state_factory.create_order_state(self.order, is_from_exchange_data=True,
                                                         ignore_states=[enums.States.OPEN])

    async def terminate(self):
        """
        Perform order filling updates
        Replace the order state by a close state
        `force_close = True` because we know that the order is successfully filled.
        """
        try:
            self.ensure_not_cleared(self.order)

            self.log_event_message(enums.StatesMessages.FILLED)

            # call filling actions
            self.order.on_fill_actions()
            
            self.ensure_not_cleared(self.order)

            # set executed time
            self.order.executed_time = self.order.generate_executed_time()
            
            # compute trading fees
            try:
                if self.order.exchange_manager is not None and not self.order.has_exchange_fetched_fees():
                    self.order.fee = self.order.get_computed_fee()
            except KeyError:
                self.get_logger().error(f"Fail to compute trading fees for {self.order}.")

            async with order_util.ensure_orders_relevancy(
                order=self.order, enable_associated_orders_creation=self.enable_associated_orders_creation
            ):
                # Trigger order group
                if self.order.order_group and self.enable_associated_orders_creation:
                    await self.order.order_group.on_fill(self.order)

                # always make sure this order has not been cleared when the is a risk to avoid AttributeError
                self.ensure_not_cleared(self.order)
                # update portfolio with filled order and position if any
                async with self.order.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.lock:
                    self.ensure_not_cleared(self.order)
                    await self.order.exchange_manager.exchange_personal_data.\
                        handle_portfolio_and_position_update_from_order(self.order, expect_filled_order_update=True)

                # notify order filled
                await self.order.exchange_manager.exchange_personal_data.handle_order_update_notification(
                    self.order, enums.OrderUpdateType.STATE_CHANGE
                )

                # call order on_filled callback
                await self.order.on_filled(self.enable_associated_orders_creation)

            # set close state
            await self.order.on_close(force_close=True)  # TODO force ?
        except Exception as e:
            self.get_logger().exception(
                e, True, f"Fail to execute fill state termination : {html_util.get_html_summary_if_relevant(e)}."
            )
            raise
