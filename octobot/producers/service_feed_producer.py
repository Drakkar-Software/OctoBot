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
from octobot_commons.enums import OctoBotChannelSubjects
from octobot_services.api.service_feeds import create_service_feed_factory, stop_service_feed
from octobot_services.consumers.octobot_channel_consumer import OctoBotChannelServiceActions as ServiceActions, \
    OctoBotChannelServiceDataKeys as ServiceKeys
from octobot_tentacles_manager.api.configurator import is_tentacle_activated_in_tentacles_setup_config


class ServiceFeedProducer(OctoBotChannelProducer):
    """EvaluatorFactory class:
    - Create service feeds
    """

    def __init__(self, channel, octobot):
        super().__init__(channel)
        self.octobot = octobot
        self.started = False

        self.service_feeds = []

    async def start(self):
        in_backtesting = is_backtesting_enabled(self.octobot.config)
        service_feed_factory = create_service_feed_factory(self.octobot.config,
                                                           self.octobot.async_loop,
                                                           self.octobot.bot_id)
        for feed in service_feed_factory.get_available_service_feeds(in_backtesting):
            if is_tentacle_activated_in_tentacles_setup_config(self.octobot.tentacles_setup_config,
                                                               feed.get_name()):
                await self.create_feed(service_feed_factory, feed, in_backtesting)

    async def start_feeds(self):
        self.started = True
        for feed in self.service_feeds:
            await self.send(bot_id=self.octobot.bot_id,
                            subject=OctoBotChannelSubjects.UPDATE.value,
                            action=ServiceActions.START_SERVICE_FEED.value,
                            data={
                                ServiceKeys.INSTANCE.value: feed,
                                ServiceKeys.EDITED_CONFIG.value: self.octobot.get_edited_config(CONFIG_KEY)
                            })

    async def create_feed(self, service_feed_factory, feed, in_backtesting):
        await self.send(bot_id=self.octobot.bot_id,
                        subject=OctoBotChannelSubjects.CREATION.value,
                        action=ServiceActions.SERVICE_FEED.value,
                        data={
                            ServiceKeys.EDITED_CONFIG.value: self.octobot.get_edited_config(CONFIG_KEY),
                            ServiceKeys.BACKTESTING_ENABLED.value: in_backtesting,
                            ServiceKeys.CLASS.value: feed,
                            ServiceKeys.FACTORY.value: service_feed_factory
                        })

    async def register_service_feed(self, instance):
        self.service_feeds.append(instance)

    async def stop(self):
        for service_feed in self.service_feeds:
            await stop_service_feed(service_feed)
