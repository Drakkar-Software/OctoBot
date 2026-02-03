#  Drakkar-Software OctoBot-Commons
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

from octobot_commons.logging import logging_util
from octobot_commons.logging.logging_util import (
    BotLogger,
    set_global_logger_level,
    get_global_logger_level,
    temporary_log_level,
    get_logger_level_per_handler,
    get_logger,
    set_logging_level,
    get_backtesting_errors_count,
    reset_backtesting_errors,
    set_error_publication_enabled,
    BACKTESTING_NEW_ERRORS_COUNT,
    LOG_DATABASE,
    LOG_NEW_ERRORS_COUNT,
    logs_database,
    error_notifier_callbacks,
    LOGS_MAX_COUNT,
    add_log,
    get_errors_count,
    reset_errors_count,
    register_error_notifier,
    register_log_callback,
    set_enable_web_interface_logs,
)

__all__ = [
    "BotLogger",
    "set_global_logger_level",
    "get_global_logger_level",
    "temporary_log_level",
    "get_logger_level_per_handler",
    "get_logger",
    "set_logging_level",
    "get_backtesting_errors_count",
    "reset_backtesting_errors",
    "set_error_publication_enabled",
    "BACKTESTING_NEW_ERRORS_COUNT",
    "LOG_DATABASE",
    "LOG_NEW_ERRORS_COUNT",
    "logs_database",
    "error_notifier_callbacks",
    "LOGS_MAX_COUNT",
    "add_log",
    "get_errors_count",
    "reset_errors_count",
    "register_error_notifier",
    "register_log_callback",
    "set_enable_web_interface_logs",
]
