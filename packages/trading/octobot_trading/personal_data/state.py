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
import contextlib

import octobot_commons.logging as logging

import octobot_trading.enums as enums
import octobot_trading.util as util


class State(util.Initializable):
    PENDING_REFRESH_INTERVAL = 2

    def __init__(self, is_from_exchange_data):
        super().__init__()

        # default state
        self.state: enums.States = enums.States.UNKNOWN

        # state when refreshing, is only indicative and can be outdated du to avoid concurrency issues
        self._underlying_refreshed_state: enums.States = enums.States.UNKNOWN

        # if this state has been created from exchange data or OctoBot internal mechanism
        self.is_from_exchange_data: bool = is_from_exchange_data

        # state lock
        self.lock: asyncio.Lock = asyncio.Lock()

        # set after self.terminate has been executed (with or without raised exception)
        self.terminated: asyncio.Event = asyncio.Event()

        # set at True after synchronize has been called
        self.has_already_been_synchronized_once: bool = False

        # how many times this state has been synchronized
        self.synchronization_attempts: int = 0

    def is_pending(self) -> bool:
        """
        :return: True if the state is pending for update
        """
        return self.state is enums.States.UNKNOWN

    def is_refreshing(self) -> bool:
        """
        :return: True if the state is updating
        """
        return self.state is enums.States.REFRESHING

    def is_open(self) -> bool:
        """
        :return: True if the instance is considered as open
        """
        return not self.is_closed()

    def is_closed(self) -> bool:
        """
        :return: True if the instance is considered as closed
        """
        return False

    def get_logger(self):
        """
        :return: the instance logger
        """
        return logging.get_logger(self.__class__.__name__)

    def log_event_message(self, state_message, error=None):
        """
        Log a state event
        """
        self.get_logger().info(state_message.value)

    async def initialize_impl(self) -> None:
        """
        Default async State initialization process
        """
        await self.update()

    def sync_initialize(self, forced=False):
        """
        Default sync initialization process
        """
        if not self.is_initialized or forced:
            self.sync_update()
            self.is_initialized = True
            return True
        return False

    def sync_update(self):
        if not self.is_refreshing():
            if self.is_pending():
                raise NotImplementedError("can't use sync_update on a pending state")
            else:
                self.trigger_sync_terminate()
        else:
            self.log_event_message(enums.StatesMessages.ALREADY_SYNCHRONIZING)

    async def should_be_updated(self) -> bool:
        """
        Defines if the instance should be updated
        :return: True if the instance should be updated when necessary
        """
        return True

    async def update(self) -> None:
        """
        Update the instance state if necessary.
        Necessary when the state is not already synchronizing and when the instance should be updated.
        Try to fix the pending state or terminate.
        """
        if not self.is_refreshing():
            if self.is_pending() and not await self.should_be_updated():
                self.log_event_message(enums.StatesMessages.SYNCHRONIZING)
                await self.synchronize()
            else:
                await self.trigger_terminate()
        else:
            self.log_event_message(enums.StatesMessages.ALREADY_SYNCHRONIZING)

    async def trigger_terminate(self):
        try:
            async with self.lock:
                await self.terminate()
        finally:
            self.on_terminate()

    def trigger_sync_terminate(self):
        try:
            self.sync_terminate()
        finally:
            self.on_terminate()

    async def synchronize(self, force_synchronization=False, catch_exception=False) -> None:
        """
        Implement the exchange synchronization process
        Should begin by setting the state to REFRESHING
        Should end by :
        - calling terminate if the state is terminated
        - restoring the initial state if nothing has been changed with synchronization or if sync failed
        :param force_synchronization: When True, for the update of the order from the exchange
        :param catch_exception: When False raises the Exception during synchronize_order instead of catching it silently
        """
        try:
            await self.synchronize_with_exchange(force_synchronization=force_synchronization)
        except Exception as e:
            if catch_exception:
                self.log_event_message(enums.StatesMessages.SYNCHRONIZING_ERROR, error=e)
            else:
                raise
        finally:
            self.has_already_been_synchronized_once = self._is_synchronization_enabled()

    async def synchronize_with_exchange(self, force_synchronization: bool = False) -> None:
        """
        Ask the exchange to update the order only if the state is not already refreshing
        When the refreshing process starts set the state to enums.States.REFRESHING
        Restore the previous state if the refresh process fails
        :param force_synchronization: When True, for the update of the order from the exchange
        """
        if not self._is_synchronization_enabled():
            self.get_logger().info(f"Skipped {self.__class__.__name__} exchange synchronization")
            return
        if self.is_refreshing():
            self.log_event_message(enums.StatesMessages.ALREADY_SYNCHRONIZING)
        else:
            async with self.refresh_operation():
                await self._synchronize_with_exchange(force_synchronization=force_synchronization)

    @contextlib.asynccontextmanager
    async def refresh_operation(self):
        self.get_logger().debug("Starting refresh_operation")
        previous_state = self.state
        # don't rely on self._underlying_refreshed_state only to avoid concurrency issues (use local variable instead)
        self._underlying_refreshed_state = previous_state
        async with self.lock:
            self.state = enums.States.REFRESHING
        try:
            yield
        finally:
            async with self.lock:
                if self.state is enums.States.REFRESHING:
                    self.state = previous_state
                self._underlying_refreshed_state = enums.States.UNKNOWN
            self.get_logger().debug("Completed refresh_operation")

    async def _synchronize_with_exchange(self, force_synchronization: bool = False) -> None:
        """
        Called when state should be refreshed
        :param force_synchronization: When True, for the update of the order from the exchange
        """
        raise NotImplementedError("_synchronize_with_exchange not implemented")

    async def terminate(self) -> None:
        """
        Implement the state ending process
        Can be portfolio updates, fees request, orders group updates, Trade creation etc...
        """
        raise NotImplementedError("terminate not implemented")

    def sync_terminate(self) -> None:
        """
        Implement the state ending process
        Can be portfolio updates, fees request, orders group updates, Trade creation etc...
        """
        raise NotImplementedError("sync_terminate not implemented")

    def on_terminate(self) -> None:
        """
        Called after terminate is complete
        """
        self.get_logger().debug(f"{self.__class__.__name__} terminated")
        if not self.terminated.is_set():
            self.terminated.set()

    def __del__(self):
        if not self.terminated.is_set() and self.terminated._waiters:
            self.get_logger().error(f"{self.__class__.__name__} deleted before the terminated "
                                    f"event has been set while tasks are waiting for it. "
                                    f"Force setting event.")
            self.terminated.set()

    async def wait_for_terminate(self, timeout) -> None:
        if self.terminated.is_set():
            return
        await asyncio.wait_for(self.terminated.wait(), timeout=timeout)

    async def wait_for_next_state(self, timeout) -> None:
        raise NotImplementedError("wait_for_next_state is not implemented")

    async def on_refresh_successful(self):
        """
        Called when synchronize succeed to update the instance
        """
        raise NotImplementedError("on_refresh_successful not implemented")

    def _is_synchronization_enabled(self):
        return True

    def clear(self):
        """
        Clear references
        """
        raise NotImplementedError("clear not implemented")
