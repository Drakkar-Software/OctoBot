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
import octobot_trading.personal_data.state as state_class


class PositionState(state_class.State):
    def __init__(self, position, is_from_exchange_data):
        super().__init__(is_from_exchange_data)

        # related position
        self.position = position

        self._has_state_changed = asyncio.Event()

    def has_to_be_async_synchronized(self):
        return False

    def is_active(self) -> bool:
        """
        :return: True if the Position has a non-zero size
        """
        return False

    def is_liquidated(self) -> bool:
        """
        :return: True if the instance is considered as liquidated
        """
        return False

    def log_event_message(self, state_message, error=None):
        """
        Log a position state event
        """
        if state_message is enums.StatesMessages.ALREADY_SYNCHRONIZING:
            self.get_logger().debug(f"Trying to update a refreshing state for position: {self.position}")
        elif state_message is enums.StatesMessages.SYNCHRONIZING_ERROR:
            self.get_logger().exception(error, True, f"Error when synchronizing position {self.position}: {error}")
        else:
            self.get_logger().info(f"{self.position} {state_message.value} on "
                                   f"{self.position.exchange_manager.exchange_name}")

    async def _synchronize_with_exchange(self, force_synchronization: bool = False) -> None:
        """
        Ask PositionsChannel Internal producer to refresh the position from the exchange
        :param force_synchronization: When True, for the update of the position from the exchange
        :return: the result of PositionsProducer.update_position_from_exchange()
        """
        self.synchronization_attempts += 1
        return self.position.exchange_manager.exchange_personal_data.positions_manager.\
            refresh_real_trader_position(self.position, force_job_execution=force_synchronization)

    def set_is_changing_state(self):
        if not self._has_state_changed.is_set():
            self._has_state_changed.set()

    def __del__(self):
        """
        Call set_is_changing_state in case this state has not been updated
        """
        self.set_is_changing_state()
        super().__del__()

    async def wait_for_next_state(self, timeout) -> None:
        if self._has_state_changed.is_set():
            return
        await asyncio.wait_for(self._has_state_changed.wait(), timeout=timeout)

    def clear(self):
        """
        Clear references
        """
        self.position = None
