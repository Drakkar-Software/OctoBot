#  Drakkar-Software OctoBot-Services
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
import abc
import typing

import async_channel.channels as channels

import octobot_commons.asyncio_tools as asyncio_tools
import octobot_backtesting.api as backtesting_api

import octobot_services.abstract_service_user as abstract_service_user
import octobot_services.channel as service_channels
import octobot_services.util as util


class AbstractServiceFeed(abstract_service_user.AbstractServiceUser,
                          util.ReturningStartable,
                          service_channels.AbstractServiceFeedChannelProducer):
    __metaclass__ = abc.ABCMeta

    # Override FEED_CHANNEL with a dedicated channel
    FEED_CHANNEL = None

    # Set simulator class when available in order to use it in backtesting for this feed
    SIMULATOR_CLASS = None
    IS_SIMULATOR_CLASS = False

    # Whether this feed supports historical data collection for backtesting
    BACKTESTING_ENABLED = False

    _SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC = 10
    DELAY_BETWEEN_STREAMS_QUERIES = 5
    REQUIRED_SERVICE_ERROR_MESSAGE = "Required services are not ready, service feed can't start"

    def __init__(self, config, main_async_loop, bot_id, backtesting=None, importer=None):
        abstract_service_user.AbstractServiceUser.__init__(self, config)
        try:
            channel = channels.set_chan(self.FEED_CHANNEL(), None)
        except ValueError:
            channel = channels.get_chan(self.FEED_CHANNEL.get_name())
        service_channels.AbstractServiceFeedChannelProducer.__init__(self, channel)
        self.feed_config = {}
        self.main_async_loop = main_async_loop
        self.bot_id = bot_id
        self.services = None
        self.should_stop = False
        self.data_cache = None

        # backtesting
        self.backtesting = backtesting
        self.is_backtesting = backtesting is not None and self.BACKTESTING_ENABLED == True
        self.social_data_importer = importer
        self.time_consumer = None

    # Override update_feed_config if any need in the extending feed
    def update_feed_config(self, config):
        pass

    # Override this method if the service feed implementation is using a dispatcher handled in the service layer
    # (ie: TelegramServiceFeed)
    @staticmethod
    def _get_service_layer_service_feed() -> object:
        return None

    # Override this method to specify the feed reception process
    @abc.abstractmethod
    async def _start_service_feed(self):
        raise NotImplementedError("start_dispatcher not implemented")

    @abc.abstractmethod
    def _something_to_watch(self):
        raise NotImplementedError("_something_to_watch not implemented")

    @abc.abstractmethod
    def _initialize(self):
        raise NotImplementedError("_initialize not implemented")

    async def _init_channel(self):
        channel = channels.get_chan(self.FEED_CHANNEL.get_name())
        await channel.register_producer(self)
        if self.is_backtesting:
            await self._resume_time_consumer()

    # Call _notify_consumers to send data to consumers
    def _notify_consumers(self, data):
        try:
            # send notification only if is a notification channel is running
            channels.get_chan(self.FEED_CHANNEL.get_name())
            asyncio_tools.run_coroutine_in_asyncio_loop(self.feed_send_coroutine(data), self.main_async_loop)
        except KeyError:
            self.logger.error("Can't send notification data: no initialized channel found")

    # Call _async_notify_consumers to send data to consumers (same as _notify_consumers but directly from async context)
    async def _async_notify_consumers(self, data):
        try:
            # send notification only if is a notification channel is running
            channels.get_chan(self.FEED_CHANNEL.get_name())
            await self.feed_send_coroutine(data)
        except KeyError:
            self.logger.error("Can't send notification data: no initialized channel found")

    async def feed_send_coroutine(self, data):
        await self.send(
            {
                "data": data
            }
        )

    async def _run(self, should_init=True):
        self.is_running = True
        service_level_service_feed_if_any = self._get_service_layer_service_feed()
        if self._something_to_watch():
            if should_init:
                self._initialize()
                await self._init_channel()
            if self.services is not None:
                for service in self.services:
                    if service_level_service_feed_if_any is not None \
                            and not service.is_running():
                        await service.start_service_feed()
            if not await self._start_service_feed():
                self.logger.warning("Nothing can be monitored even though there is something to watch"
                                    ", feed is going closing.")
        else:
            self.logger.info("Nothing to monitor, feed is closing.")
            self.is_running = False
        return True

    def get_data_cache(self, current_time: float, key: typing.Optional[str] = None):
        if self.data_cache is None:
            return None

        if key is not None:
            return self.data_cache.get(key, None)

        return self.data_cache

    async def _async_run(self) -> bool:
        self.logger.info("Initializing feed reception ...")
        self.services = [service.instance() for service in self.REQUIRED_SERVICES] if self.REQUIRED_SERVICES else []
        return await self._run()

    async def resume(self) -> bool:
        self.should_stop = False
        self.logger.info("Resuming feed reception ...")
        return await self._run(should_init=False)

    async def stop(self):
        if self.is_running:
            self.should_stop = True
            self.is_running = False
        if self.is_backtesting:
            await self._stop_and_pause_time_consumer()

    async def pause(self):
        if self.is_backtesting:
            await self._pause_time_consumer()

    def _get_time_channel(self):
        return channels.get_chan(
            backtesting_api.get_backtesting_time_channel_name(self.backtesting)
        )

    async def _pause_time_consumer(self) -> None:
        if self.time_consumer is not None:
            await self._get_time_channel().remove_consumer(self.time_consumer)

    async def _stop_and_pause_time_consumer(self) -> None:
        try:
            await self._pause_time_consumer()
        except KeyError:
            pass
        self.time_consumer = None

    async def _resume_time_consumer(self) -> None:
        if self.time_consumer is None:
            self.time_consumer = await self._get_time_channel().new_consumer(self.handle_timestamp)

    async def handle_timestamp(self, timestamp, **kwargs) -> None:
        pass

    async def get_historical_data(
        self,
        start_timestamp,
        end_timestamp,
        symbols=None,
        source=None,
        **kwargs
    ) -> typing.AsyncIterator[list[dict]]:
        """
        Fetch historical data from the feed for the given time range.
        Override this method in feeds that support historical data collection.

        :param start_timestamp: milliseconds timestamp (int/float) for start of range
        :param end_timestamp: milliseconds timestamp (int/float) for end of range
        :param symbols: optional list of symbols to filter by
        :param source: optional source/topic to fetch
        :param kwargs: additional feed-specific parameters
        :return: async generator yielding batches (lists) of event dicts
        :rtype: typing.AsyncIterator[list[dict]]

        Each event dict should have at least:
        - timestamp: milliseconds timestamp (int/float)
        - payload: dict with event data
        - channel: optional str
        - symbol: optional str
        """
        raise NotImplementedError("get_historical_data is not implemented for this feed")

    @classmethod
    def get_historical_sources(cls) -> list:
        """
        Return the list of source/topic ids supported by get_historical_data.
        Override in feeds that support historical data to return their source ids.
        """
        return []
