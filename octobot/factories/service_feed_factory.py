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
from octobot_commons.logging.logging_util import get_logger
from octobot_services.api.service_feeds import create_service_feed_factory, start_service_feed


class ServiceFeedFactory:
    """EvaluatorFactory class:
    - Create service feeds
    """

    def __init__(self, octobot):
        self.octobot = octobot

        # Logger
        self.logger = get_logger(self.__class__.__name__)

        self.service_feeds = []

    async def initialize(self):
        in_backtesting = False
        try:
            from octobot_backtesting.api.backtesting import is_backtesting_enabled
            in_backtesting = is_backtesting_enabled(self.octobot.config)
        except ImportError:
            # If can't import octobot_backtesting, this session can't be a backtesting one, nothing to do
            pass
        service_feed_factory = create_service_feed_factory(self.octobot.config,
                                                           self.octobot.async_loop,
                                                           self.octobot.bot_id)
        self.service_feeds = [service_feed_factory.create_service_feed(feed)
                              for feed in service_feed_factory.get_available_service_feeds(in_backtesting)]

    async def create(self):
        for feed in self.service_feeds:
            if not await start_service_feed(feed, False):
                self.logger.error(f"Failed to start {feed.get_name()}. Evaluators requiring this service feed "
                                  f"might not work properly")
