import logging


class TelegramApp:
    def __init__(self, config, telegram_service):
        self.config = config
        self.telegram_service = telegram_service
        self.logger = logging.getLogger(self.__class__.__name__)


