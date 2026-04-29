#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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

import octobot_commons.configuration as configuration

import octobot.octobot as octobot
import octobot.logger as logger
import octobot.producers as producers

class OctoBotNode(octobot.OctoBot):
    def __init__(self, config: configuration.Configuration, community_authenticator=None, ignore_config=False, reset_trading_history=False, startup_messages=None):
        super().__init__(
            config=config,
            community_authenticator=community_authenticator,
            ignore_config=ignore_config,
            reset_trading_history=reset_trading_history,
            startup_messages=startup_messages
        )

    async def create_producers(self):
        logger_consumer = await logger.init_octobot_chan_logger(self.bot_id)
        self.global_consumer.add_consumer(logger_consumer)
        self.interface_producer = producers.InterfaceProducer(self.global_consumer.octobot_channel, self)

    async def start_producers(self):
        await self.interface_producer.run()
