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
import octobot_commons.tentacles_management as tentacles_management

import octobot_services.managers as managers
import octobot_services.service_feeds as service_feeds


def get_available_backtestable_feeds() -> list:
    feeds = tentacles_management.get_all_classes_from_parent(service_feeds.AbstractServiceFeed)
    return [feed for feed in feeds if feed.BACKTESTING_ENABLED]


def is_service_used_by_backtestable_feed(service_class) -> bool:
    backtestable = get_available_backtestable_feeds()
    for feed in backtestable:
        if feed.REQUIRED_SERVICES and service_class in feed.REQUIRED_SERVICES:
            return True
    return False


def create_service_feed_factory(config, main_async_loop, bot_id, backtesting=None, importer=None) -> service_feeds.ServiceFeedFactory:
    return service_feeds.ServiceFeedFactory(config, main_async_loop, bot_id, backtesting, importer=importer)


def get_service_feed(service_feed_class, bot_id) -> service_feeds.AbstractServiceFeed:
    try:
        return service_feeds.ServiceFeeds.instance().get_service_feed(bot_id, service_feed_class.get_name())
    except TypeError:
        raise RuntimeError(f"can't get {service_feed_class} instance: service feed has not been properly created yet")


async def start_service_feed(service_feed: service_feeds.AbstractServiceFeed,
                             backtesting_enabled: bool,
                             edited_config: dict) -> bool:
    return await managers.ServiceFeedManager.start_service_feed(service_feed, backtesting_enabled, edited_config)


async def stop_service_feed(service_feed: service_feeds.AbstractServiceFeed) -> None:
    await managers.ServiceFeedManager.stop_service_feed(service_feed)


async def clear_bot_id_feeds(bot_id: str) -> None:
    service_feeds.ServiceFeeds.instance().clear_bot_id_feeds(bot_id)
