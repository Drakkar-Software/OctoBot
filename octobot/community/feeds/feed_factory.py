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
import octobot.enums
import octobot.community.feeds.community_ws_feed as community_ws_feed
import octobot.community.feeds.community_mqtt_feed as community_mqtt_feed


def community_feed_factory(feed_url: str, authenticator, feed_type: octobot.enums.CommunityFeedType):
    if feed_type is octobot.enums.CommunityFeedType.WebsocketFeed:
        return community_ws_feed.CommunityWSFeed(feed_url, authenticator)
    if feed_type is octobot.enums.CommunityFeedType.MQTTFeed:
        return community_mqtt_feed.CommunityMQTTFeed(feed_url, authenticator)
    raise NotImplementedError(f"Unsupported feed type: {feed_type}")
