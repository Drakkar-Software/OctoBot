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

from octobot_services.api import services
from octobot_services.api import interfaces
from octobot_services.api import service_feeds
from octobot_services.api import notification

from octobot_services.api.services import (
    get_available_services,
    get_available_backtestable_services,
    get_available_ai_services,
    get_available_web_search_services,
    get_ai_service,
    get_web_search_service,
    is_service_class,
    is_service_available_in_backtesting,
    get_service,
    create_service_factory,
    stop_services,
)
from octobot_services.api.interfaces import (
    initialize_global_project_data,
    create_interface_factory,
    is_enabled,
    is_enabled_in_backtesting,
    is_interface_relevant,
    disable_interfaces,
    send_user_command,
    start_interfaces,
    stop_interfaces,
)
from octobot_services.api.service_feeds import (
    create_service_feed_factory,
    get_service_feed,
    get_available_backtestable_feeds,
    is_service_used_by_backtestable_feed,
    start_service_feed,
    stop_service_feed,
    clear_bot_id_feeds,
)
from octobot_services.api.notification import (
    create_notifier_factory,
    create_notification,
    is_enabled_in_config,
    get_enable_notifier,
    set_enable_notifier,
    is_notifier_relevant,
    send_notification,
    process_pending_notifications,
)


LOGGER_TAG = "ServicesApi"

__all__ = [
    "get_available_services",
    "get_available_backtestable_services",
    "get_available_ai_services",
    "get_available_web_search_services",
    "get_ai_service",
    "get_web_search_service",
    "is_service_class",
    "is_service_available_in_backtesting",
    "get_service",
    "create_service_factory",
    "stop_services",
    "initialize_global_project_data",
    "create_interface_factory",
    "is_enabled",
    "is_enabled_in_backtesting",
    "is_interface_relevant",
    "disable_interfaces",
    "send_user_command",
    "start_interfaces",
    "stop_interfaces",
    "create_service_feed_factory",
    "get_service_feed",
    "get_available_backtestable_feeds",
    "is_service_used_by_backtestable_feed",
    "start_service_feed",
    "stop_service_feed",
    "clear_bot_id_feeds",
    "create_notifier_factory",
    "create_notification",
    "is_enabled_in_config",
    "get_enable_notifier",
    "set_enable_notifier",
    "is_notifier_relevant",
    "send_notification",
    "process_pending_notifications",
]
