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
import octobot_commons.logging as logging

import octobot_trading.enums as enums
import octobot_trading.personal_data.positions.position_state as position_state
import octobot_trading.personal_data.orders.order_util as order_util


class LiquidatePositionState(position_state.PositionState):
    def __init__(self, position, is_from_exchange_data, force_liquidate=True):
        super().__init__(position, is_from_exchange_data)
        self.state = enums.PositionStates.LIQUIDATED \
            if is_from_exchange_data or force_liquidate or self.position.simulated else enums.PositionStates.LIQUIDATING

    async def initialize_impl(self, forced=False) -> None:
        if forced:
            self.state = enums.PositionStates.LIQUIDATED
        return await super().initialize_impl()

    def has_to_be_async_synchronized(self):
        return True

    def is_pending(self) -> bool:
        return self.state is enums.PositionStates.LIQUIDATING

    def is_closed(self) -> bool:
        return self.state is enums.PositionStates.LIQUIDATED

    def is_liquidated(self) -> bool:
        return True

    async def on_refresh_successful(self):
        """
        Verify the position is properly closed
        """
        if self.position.status is enums.PositionStatus.LIQUIDATING:
            self.state = enums.PositionStates.LIQUIDATED
            await self.update()

    async def terminate(self):
        """
        Handle position liquidation process
        """
        logging.get_logger(self.position.get_logger_name()).warning(f"{self.position.position_id} is being liquidated")

        # notify position liquidated
        await self.position.exchange_manager.exchange_personal_data.handle_position_update_notification(self.position)

        async with order_util.ensure_orders_relevancy(position=self.position):
            # update portfolio with liquidated position
            async with self.position.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.lock:
                await self.position.update_on_liquidation()

        logging.get_logger(self.position.get_logger_name()).warning(f"{self.position.position_id} has been liquidated")
