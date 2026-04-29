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
import typing

import octobot_commons.singleton as singleton

import octobot_services.service_feeds as service_feeds


class ServiceFeeds(singleton.Singleton):
    def __init__(self):
        self.service_feeds = {}

    def get_service_feed(self, bot_id: str, feed_name: str) -> typing.Optional[service_feeds.AbstractServiceFeed]:
        try:
            return self.service_feeds[bot_id][feed_name]
        except KeyError:
            return None

    def add_service_feed(self, bot_id: str, feed_name: str, feed: service_feeds.AbstractServiceFeed) -> None:
        if bot_id not in self.service_feeds:
            self.service_feeds[bot_id] = {}
        self.service_feeds[bot_id][feed_name] = feed

    def clear_bot_id_feeds(self, bot_id: str) -> None:
        self.service_feeds.pop(bot_id, None)
