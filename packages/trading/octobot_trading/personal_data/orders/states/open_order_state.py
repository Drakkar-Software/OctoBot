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

import octobot_trading.enums as enums
import octobot_trading.personal_data.orders.order_state as order_state
import octobot_trading.personal_data.orders.states.order_state_factory as order_state_factory
import octobot_trading.personal_data.portfolios.portfolio_util as portfolio_util


class OpenOrderState(order_state.OrderState):
    def __init__(self, order, is_from_exchange_data, enable_associated_orders_creation=True,
        is_already_counted_in_available_funds=False
    ):
        super().__init__(
            order, is_from_exchange_data, enable_associated_orders_creation=enable_associated_orders_creation,
            is_already_counted_in_available_funds=is_already_counted_in_available_funds
        )
        self.state = enums.States.OPEN if \
            is_from_exchange_data \
            or self.order.simulated \
            or self.order.is_self_managed() \
            or self.order.status is enums.OrderStatus.OPEN \
            else enums.States.OPENING

        self.has_terminated = False
        self._is_not_open_anymore = asyncio.Event()

    def is_open(self) -> bool:
        """
        :return: True if the Order is considered as open
        """
        return not (self.is_pending() or self.is_refreshing())

    async def initialize_impl(self, forced=False) -> None:
        if forced:
            self.state = enums.States.OPEN

        if (
            self.order.exchange_manager.exchange_personal_data.orders_manager.are_exchange_orders_initialized
            or self.order.exchange_manager.exchange_personal_data.portfolio_manager.enable_portfolio_available_update_from_order
        ):
            # update the availability of the currency in the portfolio if order is not
            # from exchange initialization (otherwise it's already taken into account in portfolio)
            portfolio_manager = self.order.exchange_manager.exchange_personal_data.portfolio_manager
            before_order_details = portfolio_util.filter_empty_values(
                portfolio_util.portfolio_to_float(portfolio_manager.portfolio.portfolio)
            )
            portfolio_manager.refresh_portfolio_available_from_order(self.order, True)
            after_order_details = portfolio_util.filter_empty_values(
                portfolio_util.portfolio_to_float(portfolio_manager.portfolio.portfolio)
            )
            self.get_logger().debug(
                f"Updated [{self.order.exchange_manager.exchange_name}] portfolio available after new open order. "
                f"Before order: {before_order_details}. After order: {after_order_details}"
            )

        return await super().initialize_impl()

    async def on_refresh_successful(self):
        """
        Verify the order is properly created and still OrderStatus.OPEN
        """
        # skip refresh process if the current order state is not the same as the one triggering this
        # on_refresh_successful to avoid synchronization issues (state already got refreshed by another mean)
        if self.order is None:
            self.get_logger().debug(f"on_refresh_successful triggered on cleared order: ignoring update.")
        elif self.state is self.order.state.state:
            if self.order.status is enums.OrderStatus.OPEN:
                self.state = enums.States.OPEN
                await self.update()
            else:
                if self.order.status is enums.OrderStatus.CLOSED:
                    self.order.status = enums.OrderStatus.FILLED
                    self.order.state = None
                self.set_is_not_open_anymore()
                await order_state_factory.create_order_state(self.order, is_from_exchange_data=True)
        else:
            self.get_logger().debug(f"on_refresh_successful triggered from previous state "
                                    f"after state change on {self.order}")

    def set_is_not_open_anymore(self):
        if not self._is_not_open_anymore.is_set():
            self._is_not_open_anymore.set()

    def __del__(self):
        super(OpenOrderState, self).__del__()
        self.set_is_not_open_anymore()

    async def wait_for_next_state(self, timeout) -> None:
        # terminate can't be used to follow state transition in open orders
        await asyncio.wait_for(self._is_not_open_anymore.wait(), timeout=timeout)

    async def terminate(self):
        """
        Should wait for being replaced by a FillOrderState or a CancelOrderState
        """
        if not self.has_terminated:
            self.log_event_message(enums.StatesMessages.OPEN)

            if self.order.is_in_active_inactive_transition:
                # replace previous (inactive) order instance by this active order
                self.order.exchange_manager.exchange_personal_data.orders_manager.replace_order(
                    self.order.order_id, self.order
                )
            else:
                # notify order manager of a new open order
                await self.order.exchange_manager.exchange_personal_data.handle_order_instance_update(
                    self.order, should_notify=True
                )
            self.has_terminated = True

    def is_pending(self) -> bool:
        return self.state is enums.States.OPENING
