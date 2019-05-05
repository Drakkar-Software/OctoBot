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

import logging

from config import STORED_LOG_MIN_LEVEL, BACKTESTING_NEW_ERRORS_COUNT
from tools.logging import add_log, reset_errors_count, get_errors_count


def set_global_logger_level(level):
    logger = logging.getLogger()
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


def get_global_logger_level():
    return logging.getLogger().getEffectiveLevel()


def get_logger(logger_name="Anonymous"):
    return BotLogger(logger_name)


def set_logging_level(logger_names, level):
    for name in logger_names:
        logging.getLogger(name).setLevel(level)


class BotLogger:

    def __init__(self, logger_name):
        self.logger_name = logger_name
        self.logger = logging.getLogger(logger_name)

    def debug(self, message):
        self.logger.debug(message)
        self._publish_log_if_necessary(message, logging.DEBUG)

    def info(self, message):
        self.logger.info(message)
        self._publish_log_if_necessary(message, logging.INFO)

    def warning(self, message):
        self.logger.warning(message)
        self._publish_log_if_necessary(message, logging.WARNING)

    def error(self, message):
        self.logger.error(message)
        self._publish_log_if_necessary(message, logging.ERROR)

    def exception(self, message, publish_error_if_necessary=False):
        self.logger.exception(message)
        if publish_error_if_necessary:
            self._publish_log_if_necessary(message, logging.ERROR)

    def critical(self, message):
        self.logger.critical(message)
        self._publish_log_if_necessary(message, logging.CRITICAL)

    def fatal(self, message):
        self.logger.fatal(message)
        self._publish_log_if_necessary(message, logging.FATAL)

    def _publish_log_if_necessary(self, message, level):
        if STORED_LOG_MIN_LEVEL <= level and get_global_logger_level() <= level:
            self._web_interface_publish_log(message, level)

    def _web_interface_publish_log(self, message, level):
        add_log(level, self.logger_name, message)

    @staticmethod
    def get_backtesting_errors():
        return get_errors_count(BACKTESTING_NEW_ERRORS_COUNT)

    @staticmethod
    def reset_backtesting_errors():
        reset_errors_count(BACKTESTING_NEW_ERRORS_COUNT)
