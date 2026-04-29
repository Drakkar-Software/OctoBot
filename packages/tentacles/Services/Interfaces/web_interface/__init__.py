#  Drakkar-Software OctoBot-Tentacles
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
import collections
import logging
import abc
import os.path

import octobot_commons.logging as bot_logging
import octobot_commons.timestamp_util as timestamp_util
import octobot_services.enums as services_enums


class Notifier:
    @abc.abstractmethod
    def send_notifications(self) -> bool:
        raise NotImplementedError("send_notifications is not implemented")


notifiers = {}


def register_notifier(notification_key, notifier):
    if notification_key not in notifiers:
        notifiers[notification_key] = []
    notifiers[notification_key].append(notifier)


GENERAL_NOTIFICATION_KEY = "general_notifications"
BACKTESTING_NOTIFICATION_KEY = "backtesting_notifications"
DATA_COLLECTOR_NOTIFICATION_KEY = "data_collector_notifications"
SOCIAL_DATA_COLLECTOR_NOTIFICATION_KEY = "social_data_collector_notifications"
STRATEGY_OPTIMIZER_NOTIFICATION_KEY = "strategy_optimizer_notifications"
DASHBOARD_NOTIFICATION_KEY = "dashboard_notifications"

import octobot_commons.constants as commons_constants
if not commons_constants.USE_MINIMAL_LIBS:
    # Make WebInterface visible to imports
    from tentacles.Services.Interfaces.web_interface.web import WebInterface


# disable server logging
for logger in ('engineio.server', 'socketio.server', 'geventwebsocket.handler'):
    logging.getLogger(logger).setLevel(logging.WARNING)

MAX_NOTIFICATION_HISTORY_SIZE = 1000
MAX_NOTIFICATION_AT_ONCE = 10
notifications_history = collections.deque(maxlen=MAX_NOTIFICATION_HISTORY_SIZE)
notifications = collections.deque(maxlen=MAX_NOTIFICATION_AT_ONCE)
# Different from notifications_history: this list "should" never be cleared by more recent notifications.
# maxsize is here just in case to avoid memory leaks
critical_notifications = collections.deque(maxlen=MAX_NOTIFICATION_HISTORY_SIZE)

TIME_AXIS_TITLE = "Time"


def dir_last_updated(folder):
    update_times = [
        os.path.getmtime(os.path.join(root_path, f))
        for root_path, dirs, files in os.walk(folder)
        for f in files
    ]
    return str(max(update_times + [0]))  # add 0 not to crash if no files are found


LAST_UPDATED_STATIC_FILES = 0


def update_registered_plugins(plugins):
    global LAST_UPDATED_STATIC_FILES
    last_update_time = max(
        float(LAST_UPDATED_STATIC_FILES),
        float(dir_last_updated(os.path.join(os.path.dirname(__file__), "static")))
    )
    for plugin in plugins:
        if plugin.static_folder:
            last_update_time = max(
                last_update_time,
                float(dir_last_updated(plugin.static_folder))
            )
    LAST_UPDATED_STATIC_FILES = last_update_time


def flush_notifications():
    notifications.clear()


def _send_notification(notification_key, **kwargs) -> bool:
    if notification_key in notifiers:
        return any(notifier.all_clients_send_notifications(**kwargs)
                   for notifier in notifiers[notification_key])
    return False


def send_general_notifications(**kwargs):
    if _send_notification(GENERAL_NOTIFICATION_KEY, **kwargs):
        flush_notifications()


def send_backtesting_status(**kwargs):
    _send_notification(BACKTESTING_NOTIFICATION_KEY, **kwargs)


def send_data_collector_status(**kwargs):
    _send_notification(DATA_COLLECTOR_NOTIFICATION_KEY, **kwargs)


def send_social_data_collector_status(**kwargs):
    _send_notification(SOCIAL_DATA_COLLECTOR_NOTIFICATION_KEY, **kwargs)


def send_strategy_optimizer_status(**kwargs):
    _send_notification(STRATEGY_OPTIMIZER_NOTIFICATION_KEY, **kwargs)


def send_new_trade(dict_new_trade, exchange_id, symbol):
    _send_notification(DASHBOARD_NOTIFICATION_KEY, exchange_id=exchange_id, trades=[dict_new_trade], symbol=symbol)


def send_order_update(dict_order, exchange_id, symbol):
    _send_notification(DASHBOARD_NOTIFICATION_KEY, exchange_id=exchange_id, order=dict_order, symbol=symbol)


async def add_notification(level: services_enums.NotificationLevel, title, message, sound=None):
    notification = {
        "Level": level.value,
        "Title": title,
        "Message": message.replace("<br>", " "),
        "Sound": sound,
        "Time": timestamp_util.get_now_time()
    }
    notifications.append(notification)
    notifications_history.append(notification)
    if level == services_enums.NotificationLevel.CRITICAL:
        critical_notifications.append(notification)
    send_general_notifications()


def get_notifications() -> list:
    return list(notifications)


def get_notifications_history() -> list:
    return list(notifications_history)


def get_critical_notifications() -> list:
    return list(critical_notifications)


def get_logs():
    return bot_logging.logs_database[bot_logging.LOG_DATABASE]


def get_errors_count():
    return bot_logging.logs_database[bot_logging.LOG_NEW_ERRORS_COUNT]


def flush_errors_count():
    bot_logging.reset_errors_count()
