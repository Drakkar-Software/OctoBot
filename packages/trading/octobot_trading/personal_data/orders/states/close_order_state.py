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
import octobot_trading.enums as enums
import octobot_trading.personal_data.orders.order_state as order_state


class CloseOrderState(order_state.OrderState):
    def __init__(self, order, is_from_exchange_data, enable_associated_orders_creation=True,
        is_already_counted_in_available_funds=False, force_close=True
    ):
        super().__init__(
            order, is_from_exchange_data, enable_associated_orders_creation=enable_associated_orders_creation,
            is_already_counted_in_available_funds=is_already_counted_in_available_funds
        )
        self.state = enums.States.CLOSED if is_from_exchange_data or force_close or self.order.simulated \
            else enums.States.CLOSING

    async def initialize_impl(self, forced=False) -> None:
        if forced:
            self.state = enums.States.CLOSED
        return await super().initialize_impl()

    def is_pending(self) -> bool:
        return self.state is enums.States.CLOSING

    def is_closed(self) -> bool:
        return self.state is enums.States.CLOSED

    async def on_refresh_successful(self):
        """
        Verify the order is properly closed
        """
        if self.order is None or self.order.is_cleared():
            self.get_logger().debug("Skipping on_refresh_successful as order is cleared")
            return
        if self.order.status is enums.OrderStatus.CLOSED:
            self.state = enums.States.CLOSED
            await self.update()

    async def terminate(self):
        """
        Handle order to trade conversion
        """
        try:
            if self.order.is_in_active_inactive_transition:
                # orders that are in active/inactive transition should not generate trades nor be removed from open_orders
                self.get_logger().info(
                    f"Skipping {enums.StatesMessages.CLOSED} state terminate for {self.order} as "
                    f"it is in active/inactive transition"
                )
                await self.order.on_inactive_from_active()
            else:
                self.log_event_message(enums.StatesMessages.CLOSED)

                # add to trade history and notify
                self.ensure_not_cleared(self.order)
                await self.order.exchange_manager.exchange_personal_data.handle_trade_instance_update(
                    self.order.trader.convert_order_to_trade(self.order)
                )

                # remove order from open_orders
                self.order.exchange_manager.exchange_personal_data.orders_manager.remove_order_instance(self.order)
        except Exception as e:
            self.get_logger().exception(
                e, True, f"Fail to execute close state termination : {html_util.get_html_summary_if_relevant(e)}."
            )
            raise

    async def _synchronize_with_exchange(self, force_synchronization=False):
        # Nothing to synchronize
        pass
