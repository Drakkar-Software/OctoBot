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
import time
import asyncio

import octobot_trading.constants
import octobot_trading.enums as enums
import octobot_trading.errors
import octobot_trading.exchange_channel as exchange_channel
import octobot_trading.personal_data.orders.order_state as order_state


class PendingCreationOrderState(order_state.OrderState):

    def __init__(self, order, is_from_exchange_data, enable_associated_orders_creation=True,
        is_already_counted_in_available_funds=False
    ):
        super().__init__(
            order, is_from_exchange_data, enable_associated_orders_creation=enable_associated_orders_creation,
            is_already_counted_in_available_funds=is_already_counted_in_available_funds
        )
        self.state = enums.States.PENDING_CREATION

    async def _synchronize_with_exchange(self, force_synchronization: bool = False) -> None:
        """
        Ask OrdersChannel Internal producer to refresh the order from the exchange
        :param force_synchronization: When True, for the update of the order from the exchange
        :return: the result of OrdersProducer.update_order_from_exchange()
        """
        try:
            t0 = time.time()
            iteration = 0
            # Retries might be necessary if the order is being filled while requesting and the 1st refresh
            # is not updating the state.
            # Loop here until we get a clear answer as the order is not yet open and therefore not in orders manager.
            # If it turns out to be instantly closed, OctoBot will miss it as is will never be fetched with
            # open orders refresh.
            self.ensure_not_cleared(self.order)
            self.get_logger().info(
                f"Synchronizing [{self._underlying_refreshed_state.value}] order {self.order} "
                f"with {self.order.exchange_manager.exchange_name} exchange"
            )
            while self.order.is_pending_creation() \
                    and time.time() - t0 < octobot_trading.constants.INDIVIDUAL_ORDER_SYNC_TIMEOUT:
                iteration += 1
                self.synchronization_attempts += 1
                await exchange_channel.get_chan(
                    octobot_trading.constants.ORDERS_CHANNEL,
                    self.order.exchange_manager.id
                ).get_internal_producer().update_order_from_exchange(
                    order=self.order,
                    wait_for_refresh=True,
                    force_job_execution=True,
                )
                if self.order.is_pending_creation():
                    message = f"Failed to receive an order update ({iteration} attempts). " \
                      f"Retrying in {self.PENDING_REFRESH_INTERVAL} seconds."
                    self.ensure_not_cleared(self.order)
                    if self.order.exchange_manager.exchange.EXPECT_POSSIBLE_ORDER_NOT_FOUND_DURING_ORDER_CREATION:
                        self.get_logger().debug(message)
                    else:
                        self.get_logger().error(
                            f"{message} This works but is unexpected on {self.order.exchange_manager.exchange_name}. "
                            f"Please report it if you see it."
                        )
                    await asyncio.sleep(self.PENDING_REFRESH_INTERVAL)
                    self.ensure_not_cleared(self.order)
            if self.order.is_pending_creation():
                self.get_logger().error(
                    f"Order state is still pending after {octobot_trading.constants.INDIVIDUAL_ORDER_SYNC_TIMEOUT}s and "
                    f"{iteration} retries. Something is wrong."
                )
            else:
                if iteration > 1:
                    self.get_logger().debug(f"Received pending order state update after {iteration} iterations")
        except octobot_trading.errors.InvalidOrderState:
            self.get_logger().debug(f"Skipping exchange synchronisation as order has already been closed.")

    def is_created(self) -> bool:
        """
        :return: True if the Order is created
        """
        # order is created on exchange but not open yet
        return True

    def is_open(self) -> bool:
        """
        :return: True if the Order is considered as open
        """
        return False

    async def on_refresh_successful(self):
        pass

    async def terminate(self):
        """
        Should wait for being replaced by an OpenOrderState or be cancelled
        """
        self.log_event_message(enums.StatesMessages.PENDING_CREATION)

    def is_pending(self) -> bool:
        return True
