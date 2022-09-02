#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
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
import octobot_commons.logging as bot_logging


class AbstractFeed:
    def __init__(self, feed_url, authenticator):
        self.logger: bot_logging.BotLogger = bot_logging.get_logger(
            self.__class__.__name__
        )
        self.feed_url = feed_url
        self.should_stop = False
        self.authenticator = authenticator
        self.feed_callbacks = {}
        self.is_subscribed = False

    async def start(self):
        raise NotImplementedError("start is not implemented")

    async def stop(self):
        raise NotImplementedError("stop is not implemented")

    async def register_feed_callback(self, channel_type, callback, identifier=None):
        raise NotImplementedError("register_feed_callback is not implemented")

    async def send(self, message, channel_type, identifier, **kwargs):
        raise NotImplementedError("send is not implemented")

    def can_connect(self):
        return True
