# pylint: disable=C0415, W0603, W1508, R0913, C0103
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
import contextlib
import logging
import typing

import octobot_commons.constants as constants
import octobot_commons.timestamp_util as timestamp_util
import octobot_commons.html_util as html_util

LOG_DATABASE = "log_db"
LOG_NEW_ERRORS_COUNT = "log_new_errors_count"

BACKTESTING_NEW_ERRORS_COUNT: str = "log_backtesting_errors_count"

logs_database = {
    LOG_DATABASE: [],
    LOG_NEW_ERRORS_COUNT: 0,
    BACKTESTING_NEW_ERRORS_COUNT: 0,
}

error_notifier_callbacks = []

LOGS_MAX_COUNT = 1000

STORED_LOG_MIN_LEVEL = logging.WARNING
ENABLE_WEB_INTERFACE_LOGS = True
ERROR_PUBLICATION_ENABLED = True
SHOULD_PUBLISH_LOGS_WHEN_RE_ENABLED = False


def _default_callback(*_, **__):
    pass


_ERROR_CALLBACK = _default_callback
_LOG_CALLBACK: typing.Union[None, typing.Callable[[str], str]] = None


def set_global_logger_level(level, handler_levels=None) -> None:
    """
    Set the global logger level
    :param level: the level to set
    """
    logger = logging.getLogger()
    logger.setLevel(level)
    levels = handler_levels or [level] * len(logger.handlers)
    for handler, updated_level in zip(logger.handlers, levels):
        handler.setLevel(updated_level)


def get_global_logger_level() -> object:
    """
    Return the global logger level
    :return: the global logger level
    """
    return logging.getLogger().getEffectiveLevel()


@contextlib.contextmanager
def temporary_log_level(level):
    """
    Sets the log level to the given level inside this context
    """
    previous_level = get_global_logger_level()
    try:
        set_global_logger_level(level)
        yield
    finally:
        set_global_logger_level(previous_level)


def get_logger_level_per_handler() -> list:
    """
    Return the global logger level
    :return: order handles logging levels
    """
    return [handler.level for handler in logging.getLogger().handlers]


def get_logger(logger_name="Anonymous"):
    """
    Return the logger from the logger_name
    :param logger_name: the logger name
    :return: the logger from the logger name
    """
    return BotLogger(logger_name)


def set_logging_level(logger_names, level) -> None:
    """
    Set the logging level for the logger names
    :param logger_names: the logger names
    :param level: the level to set
    """
    for name in logger_names:
        logging.getLogger(name).setLevel(level)


def add_log(level, source, message, keep_log=True, call_notifiers=True):
    """
    Add a log to the log database
    :param level: the log level
    :param source: the log source
    :param message: the log message
    :param keep_log: if the log should be stored
    :param call_notifiers: if the log should trigger the notifiers
    """
    if keep_log:
        logs_database[LOG_DATABASE].append(
            {
                "Time": timestamp_util.get_now_time(),
                "Level": logging.getLevelName(level),
                "Source": str(source),
                "Message": message,
            }
        )
        if len(logs_database[LOG_DATABASE]) > LOGS_MAX_COUNT:
            logs_database[LOG_DATABASE].pop(0)
        # do not count this error if keep_log is False
        if level >= logging.ERROR:
            logs_database[LOG_NEW_ERRORS_COUNT] += 1
            logs_database[BACKTESTING_NEW_ERRORS_COUNT] += 1
    if call_notifiers:
        for callback in error_notifier_callbacks:
            callback()


def get_errors_count(counter=LOG_NEW_ERRORS_COUNT):
    """
    Return the error count according to the specified counter
    :param counter: the counter to use
    :return: the error count
    """
    return logs_database[counter]


def reset_errors_count(counter=LOG_NEW_ERRORS_COUNT):
    """
    Reset the specified counter error count
    :param counter: the counter to use
    """
    logs_database[counter] = 0


def register_error_notifier(callback):
    """
    Register an error notifier
    :param callback: the callback to call when the notifier is triggered
    """
    error_notifier_callbacks.append(callback)


class BotLogger:
    """
    The bot logger that manage all OctoBot's logs
    """

    def __init__(self, logger_name):
        self.logger_name = logger_name
        self.logger = logging.getLogger(logger_name)

    def debug(self, message: str, *args, **kwargs) -> None:
        """
        Called for a debug log
        :param message: the log message
        """
        message = self._process_log_callback(message)
        self.logger.debug(message, *args, **kwargs)
        self._publish_log_if_necessary(message, logging.DEBUG)

    def info(self, message: str, *args, **kwargs) -> None:
        """
        Called for an info log
        :param message: the log message
        """
        message = self._process_log_callback(message)
        self.logger.info(message, *args, **kwargs)
        self._publish_log_if_necessary(message, logging.INFO)

    def warning(self, message: str, *args, **kwargs) -> None:
        """
        Called for a warning log
        :param message: the log message
        """
        message = self._process_log_callback(message)
        self.logger.warning(message, *args, **kwargs)
        self._publish_log_if_necessary(message, logging.WARNING)

    def error(self, message: str, *args, skip_post_callback=False, **kwargs) -> None:
        """
        Called for an error log
        :param message: the log message
        :param skip_post_callback: when True, the error callback wont be called
        """
        message = self._process_log_callback(message)
        self.logger.error(message, *args, **kwargs)
        self._publish_log_if_necessary(message, logging.ERROR)
        self._post_callback_if_necessary(None, message, skip_post_callback)

    def exception(
        self,
        exception: Exception,
        publish_error_if_necessary: bool = True,
        error_message: str = None,
        include_exception_name: bool = True,
        skip_post_callback: bool = False,
        **kwargs,
    ) -> None:
        """
        Called for an exception log
        :param exception: the log exception
        :param publish_error_if_necessary: if the error should be published
        :param error_message: the log message
        :param include_exception_name: when True adds the __class__.__name__ of the exception at the end of the message
        :param skip_post_callback: when True, the error callback won't be called
        """
        extra = kwargs.get("extra", {})
        origin_error_message = error_message
        error_message = (
            self._process_log_callback(error_message)
            if error_message
            else error_message
        )
        extra[constants.EXCEPTION_DESC] = error_message
        html_util.summarize_exception_html_cause_if_relevant(exception)
        self.logger.exception(exception, extra=extra, **kwargs)
        if publish_error_if_necessary:
            message = origin_error_message
            if message is None:
                message = (
                    str(exception) if str(exception) else exception.__class__.__name__
                )
            elif include_exception_name:
                message = f"{message} (error: {exception.__class__.__name__})"
            self.error(
                message,
                skip_post_callback=True,
                extra={constants.IS_EXCEPTION_DESC: True},
            )
        self._post_callback_if_necessary(exception, error_message, skip_post_callback)

    def critical(self, message: str, *args, **kwargs) -> None:
        """
        Called for a critical log
        :param message: the log message
        """
        message = self._process_log_callback(message)
        self.logger.critical(message, *args, **kwargs)
        self._publish_log_if_necessary(message, logging.CRITICAL)

    def fatal(self, message: str, *args, **kwargs) -> None:
        """
        Called for a fatal log
        :param message: the log message
        """
        message = self._process_log_callback(message)
        self.logger.fatal(message, *args, **kwargs)
        self._publish_log_if_necessary(message, logging.FATAL)

    def disable(self, disabled):
        """
        Used to disable or enable this logger
        :param disabled: True to disable
        """
        self.logger.disabled = disabled

    def _process_log_callback(self, message: str) -> str:
        if _LOG_CALLBACK is None:
            return message
        return _LOG_CALLBACK(message)

    def _publish_log_if_necessary(self, message, level) -> None:
        """
        Publish the log message if necessary
        :param message: the log message
        :param level: the log level
        """
        if (
            ENABLE_WEB_INTERFACE_LOGS
            and STORED_LOG_MIN_LEVEL <= level
            and get_global_logger_level() <= level
        ):
            self._web_interface_publish_log(message, level)
            if not ERROR_PUBLICATION_ENABLED and logging.ERROR <= level:
                global SHOULD_PUBLISH_LOGS_WHEN_RE_ENABLED
                SHOULD_PUBLISH_LOGS_WHEN_RE_ENABLED = True

    def _web_interface_publish_log(self, message, level) -> None:
        """
        Publish log to web interface
        :param message: the log message
        :param level: the log level
        """
        add_log(
            level,
            self.logger_name,
            message,
            call_notifiers=ERROR_PUBLICATION_ENABLED,
        )

    @staticmethod
    def register_error_callback(callback):
        """
        :param callback: the callback to be called upon errors and exceptions
        Register callback as the ERROR_CALLBACK
        """
        global _ERROR_CALLBACK
        _ERROR_CALLBACK = callback

    @staticmethod
    def _post_callback_if_necessary(exception, error_message, skip_post_callback):
        if not skip_post_callback:
            _ERROR_CALLBACK(exception, error_message)


def register_log_callback(callback: typing.Union[None, typing.Callable[[str], str]]):
    """
    :param callback: the callback to be called upon any log of any level
    Register callback as the _LOG_CALLBACK
    """
    global _LOG_CALLBACK
    _LOG_CALLBACK = callback


def get_backtesting_errors_count() -> int:
    """
    Get backtesting errors count
    :return: the backtesting errors count
    """
    return get_errors_count(BACKTESTING_NEW_ERRORS_COUNT)


def reset_backtesting_errors() -> None:
    """
    Reset the backtesting errors count
    """
    reset_errors_count(BACKTESTING_NEW_ERRORS_COUNT)


def set_error_publication_enabled(enabled) -> None:
    """
    Set the error publication enabling
    :param enabled: if the error publication is enabled
    """
    global ERROR_PUBLICATION_ENABLED
    global SHOULD_PUBLISH_LOGS_WHEN_RE_ENABLED
    ERROR_PUBLICATION_ENABLED = enabled
    if enabled and SHOULD_PUBLISH_LOGS_WHEN_RE_ENABLED:
        add_log(logging.ERROR, None, None, keep_log=False, call_notifiers=True)
    else:
        SHOULD_PUBLISH_LOGS_WHEN_RE_ENABLED = False


def set_enable_web_interface_logs(enabled):
    """
    Disable or enable errors storage in web interface
    """
    global ENABLE_WEB_INTERFACE_LOGS
    ENABLE_WEB_INTERFACE_LOGS = enabled
