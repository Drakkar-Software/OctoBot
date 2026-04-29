#  Drakkar-Software OctoBot-Backtesting
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
import copy

import async_channel.channels as channels
import async_channel.enums as channel_enums

import octobot_commons.channels_name as channels_name
import octobot_commons.list_util as list_util
import octobot_commons.logging as logging
import octobot_commons.asyncio_tools as asyncio_tools


class ChannelsManager:
    DEFAULT_REFRESH_TIMEOUT = 15

    def __init__(self, exchange_ids, matrix_id, time_chan_name, refresh_timeout=DEFAULT_REFRESH_TIMEOUT):
        self.logger = logging.get_logger(self.__class__.__name__)
        self.exchange_ids = exchange_ids
        self.matrix_id = matrix_id
        self.time_chan_name = time_chan_name
        self.refresh_timeout = refresh_timeout
        self.producers = []
        self.initial_producers = []
        self.iteration_task = None
        self.should_stop = False
        self.producers_by_priority_levels = {}

    async def initialize(self) -> None:
        """
        Initialize Backtesting channels manager
        """
        self.logger.debug("Initializing producers...")
        try:
            self.initial_producers = list_util.flatten_list(
                _get_backtesting_producers(self.time_chan_name) +
                self._get_trading_producers() +
                self._get_evaluator_producers()
            )
            self.producers = copy.copy(self.initial_producers)

            self.producers_by_priority_levels = {
                priority_level.value: self.producers
                for priority_level in channel_enums.ChannelConsumerPriorityLevels
            }

            # Initialize all producers by calling producer.start()
            for producer in list_util.flatten_list(self._get_trading_producers() + self._get_evaluator_producers()):
                await producer.start()
        except Exception as exception:
            self.logger.exception(exception, True, f"Error when initializing backtesting: {exception}")
            raise

    def clear_empty_channels_producers(self):
        self.producers = [
            producer
            for producer in self.initial_producers
            if producer.channel.get_consumers()
        ]

    def update_producers_by_priority_levels(self):
        self.producers_by_priority_levels = {
            priority_level.value: _get_producers_with_priority_level_consumers(self.producers, priority_level.value)
            for priority_level in channel_enums.ChannelConsumerPriorityLevels
            if _check_producers_has_priority_consumers(self.producers, priority_level.value)
        }

    async def handle_new_iteration(self, current_timestamp) -> None:
        for level_key, producers in self.producers_by_priority_levels.items():
            try:
                if _check_producers_consumers_emptiness(producers, level_key):
                    # avoid creating tasks when not necessary
                    continue
                self.iteration_task = self.refresh_priority_level(producers, level_key, True)
                await self.iteration_task
                # trigger waiting events
                await asyncio_tools.wait_asyncio_next_cycle()
                # massive slow down
                # self.iteration_task = await asyncio.wait_for(self.refresh_priority_level(level_key.value, True),
                #                                              timeout=self.refresh_timeout)
            except asyncio.TimeoutError:
                self.logger.error(f"Refreshing priority level {level_key} has been timed out at timestamp "
                                  f"{current_timestamp}.")

    async def refresh_priority_level(self, producers, priority_level: int, join_consumers: bool) -> None:
        while not self.should_stop:
            for producer in producers:
                await producer.synchronized_perform_consumers_queue(priority_level, join_consumers, self.refresh_timeout)
            if _check_producers_consumers_emptiness(self.producers, priority_level):
                break

    def stop(self):
        self.should_stop = True

    def flush(self):
        self.producers = []
        self.initial_producers = []
        self.producers_by_priority_levels = {}
        self.iteration_task = None

    def _get_trading_producers(self):
        import octobot_trading.exchange_channel as exchange_channel
        return [
            _get_channel_producers(exchange_channel.get_chan(channel_name.value, exchange_id))
            for exchange_id in self.exchange_ids
            for channel_name in channels_name.OctoBotTradingChannelsName
        ]

    def _get_evaluator_producers(self):
        import octobot_evaluators.evaluators.channel as evaluators_channel
        return [
            _get_channel_producers(evaluators_channel.get_chan(channel_name.value, self.matrix_id))
            for channel_name in channels_name.OctoBotEvaluatorsChannelsName
        ]


def _get_channel_producers(channel):
    if channel.producers:
        return channel.producers
    return [channel.get_internal_producer()]


def _get_backtesting_producers(time_chan_name):
    return [
        _get_channel_producers(channels.get_chan(channel_name))
        for channel_name in [time_chan_name]
    ]


def _check_producers_consumers_emptiness(producers, priority_level):
    for producer in producers:
        try:
            if not producer.is_consumers_queue_empty(priority_level):
                return False
        except AttributeError:
            if producer.channel is None:
                # channel has been cleared, there is nothing to do
                return True
            else:
                # unexpected, propagate
                raise
    return True


def _check_producers_has_priority_consumers(producers, priority_level):
    for producer in producers:
        if producer.channel.get_prioritized_consumers(priority_level):
            return True
    return False


def _get_producers_with_priority_level_consumers(producers, priority_level):
    return [
        producer
        for producer in producers
        if producer.channel.get_prioritized_consumers(priority_level)
    ]
