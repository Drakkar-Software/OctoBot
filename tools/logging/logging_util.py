import logging

from tools.logging import add_log


def set_global_logger_level(level):
    logger = logging.getLogger()
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


def get_global_logger_level():
    return logging.getLogger().getEffectiveLevel()


def get_logger(logger_name="Anonymous"):
    return BotLogger(logger_name)


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

    def exception(self, message):
        self.logger.exception(message)
        self._publish_log_if_necessary(message, logging.ERROR)

    def critical(self, message):
        self.logger.critical(message)
        self._publish_log_if_necessary(message, logging.CRITICAL)

    def fatal(self, message):
        self.logger.fatal(message)
        self._publish_log_if_necessary(message, logging.FATAL)

    def _publish_log_if_necessary(self, message, level):
        if get_global_logger_level() <= level:
            self._web_interface_publish_log(message, level)

    def _web_interface_publish_log(self, message, level):
        add_log(level, self.logger_name, message)
