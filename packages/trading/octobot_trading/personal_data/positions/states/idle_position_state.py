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

import octobot_trading.enums as enums
import octobot_trading.personal_data.positions.position_state as position_state
import octobot_trading.personal_data.positions.states.position_state_factory as position_state_factory


class IdlePositionState(position_state.PositionState):
    """
    ActivePositionState is the state of a position that has size of zero
    """
    def __init__(self, position, is_from_exchange_data):
        super().__init__(position, is_from_exchange_data)
        self.state = enums.States.OPEN if is_from_exchange_data \
                                          or self.position.simulated \
                                          or self.position.status is enums.PositionStatus.OPEN \
            else enums.States.OPENING

        self.has_terminated = False

    def is_open(self) -> bool:
        """
        :return: True if the Position is considered as open
        """
        return not (self.is_pending() or self.is_refreshing())

    async def initialize_impl(self, forced=False) -> None:
        if forced:
            self.state = enums.States.OPEN
        return await super().initialize_impl()

    def _is_compatible_size(self):
        return self.position.is_idle()

    async def on_refresh_successful(self):
        """
        Verify the position is properly created and still PositionStatus.OPEN
        """
        # skip refresh process if the current position state is not the same as the one triggering this
        # on_refresh_successful to avoid synchronization issues (state already got refreshed by another mean)
        if self.position is None:
            self.get_logger().warning(f"on_refresh_successful triggered on cleared position: ignoring update.")
        elif self.state is self.position.state.state:
            if self.position.status is enums.PositionStatus.OPEN and self._is_compatible_size():
                self.state = enums.States.OPEN
                await self.update()
            else:
                position_state_factory.create_position_state(self.position, is_from_exchange_data=True)
                if self.position.state.has_to_be_async_synchronized():
                    await self.position.state.initialize()
        else:
            self.get_logger().debug(f"on_refresh_successful triggered from previous state "
                                    f"after state change on {self.position}")

    async def _synchronize_with_exchange(self, force_synchronization: bool = False) -> None:
        # Disable open position synchronization for now, let position updater refresh positions
        pass

    def sync_terminate(self):
        """
        Should wait for being replaced by an ActivePositionState or LiquidatePositionState
        """
        if not self.has_terminated:
            self.log_event_message(enums.StatesMessages.OPEN)

            if not self.position.mark_price:
                # set position mark price
                self.position.mark_price = decimal.Decimal(
                    self.position.exchange_manager.exchange_symbols_data.
                        get_exchange_symbol_data(self.position.symbol).prices_manager.mark_price
                )

            self.has_terminated = True

    async def terminate(self):
        self.sync_terminate()

    def is_pending(self) -> bool:
        return self.state is enums.States.OPENING
