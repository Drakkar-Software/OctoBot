#  Drakkar-Software OctoBot
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
from octobot.channels.octobot_channel import OctoBotChannelProducer
from octobot.constants import CONFIG_KEY
from octobot_backtesting.api.backtesting import is_backtesting_enabled
from octobot_services.api.service_feeds import create_service_feed_factory, start_service_feed, stop_service_feed


class ServiceFeedProducer(OctoBotChannelProducer):
    """EvaluatorFactory class:
    - Create service feeds
    """

    def __init__(self, channel, octobot):
        super().__init__(channel)
        self.octobot = octobot

        self.service_feeds = []

    async def start(self):
        in_backtesting = is_backtesting_enabled(self.octobot.config)
        service_feed_factory = create_service_feed_factory(self.octobot.config,
                                                           self.octobot.async_loop,
                                                           self.octobot.bot_id)
        self.service_feeds = [await self.create_feed(service_feed_factory, feed)
                              for feed in service_feed_factory.get_available_service_feeds(in_backtesting)]

    async def create_feed(self, service_feed_factory, feed):
        service_feed = service_feed_factory.create_service_feed(feed)
        if not await start_service_feed(service_feed, False, self.octobot.get_edited_config(CONFIG_KEY)):
            self.logger.error(f"Failed to start {service_feed.get_name()}. Evaluators requiring this service feed "
                              f"might not work properly")
        return service_feed

    async def stop(self):
        for service_feed in self.service_feeds:
            await stop_service_feed(service_feed)
