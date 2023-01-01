#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import octobot_backtesting.api as backtesting_api

import octobot_commons.enums as common_enums

import octobot_services.api as service_api
import octobot_services.octobot_channel_consumer as service_channel_consumer

import octobot_tentacles_manager.api as tentacles_manager_api

import octobot.channels as octobot_channels
import octobot.constants as constants


class ServiceFeedProducer(octobot_channels.OctoBotChannelProducer):
    """EvaluatorFactory class:
    - Create service feeds
    """

    def __init__(self, channel, octobot):
        super().__init__(channel)
        self.octobot = octobot
        self.started = False

        self.service_feeds = []

    async def start(self):
        in_backtesting = backtesting_api.is_backtesting_enabled(self.octobot.config)
        service_feed_factory = service_api.create_service_feed_factory(self.octobot.config,
                                                                       self.octobot.async_loop,
                                                                       self.octobot.bot_id)
        for feed in service_feed_factory.get_available_service_feeds(in_backtesting):
            if tentacles_manager_api.is_tentacle_activated_in_tentacles_setup_config(
                    self.octobot.tentacles_setup_config, feed.get_name()):
                await self.create_feed(service_feed_factory, feed, in_backtesting)

    async def start_feeds(self):
        self.started = True
        for feed in self.service_feeds:
            await self.send(bot_id=self.octobot.bot_id,
                            subject=common_enums.OctoBotChannelSubjects.UPDATE.value,
                            action=service_channel_consumer.OctoBotChannelServiceActions.START_SERVICE_FEED.value,
                            data={
                                service_channel_consumer.OctoBotChannelServiceDataKeys.INSTANCE.value: feed,
                                service_channel_consumer.OctoBotChannelServiceDataKeys.EDITED_CONFIG.value:
                                    self.octobot.get_edited_config(constants.CONFIG_KEY, dict_only=False)
                            })

    async def create_feed(self, service_feed_factory, feed, in_backtesting):
        await self.send(bot_id=self.octobot.bot_id,
                        subject=common_enums.OctoBotChannelSubjects.CREATION.value,
                        action=service_channel_consumer.OctoBotChannelServiceActions.SERVICE_FEED.value,
                        data={
                            service_channel_consumer.OctoBotChannelServiceDataKeys.EDITED_CONFIG.value:
                                self.octobot.get_edited_config(constants.CONFIG_KEY, dict_only=False),
                            service_channel_consumer.OctoBotChannelServiceDataKeys.BACKTESTING_ENABLED.value:
                                in_backtesting,
                            service_channel_consumer.OctoBotChannelServiceDataKeys.CLASS.value: feed,
                            service_channel_consumer.OctoBotChannelServiceDataKeys.FACTORY.value: service_feed_factory
                        })

    async def register_service_feed(self, instance):
        self.service_feeds.append(instance)

    async def stop(self):
        self.logger.debug("Stopping ...")
        for service_feed in self.service_feeds:
            await service_api.stop_service_feed(service_feed)
        self.logger.debug("Stopped")
