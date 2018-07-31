import logging


def set_global_logger_level(level):
    logger = logging.getLogger()
    logger.setLevel(level)
    for handler in logger.parent.handlers:
        handler.setLevel(level)
