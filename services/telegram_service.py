import telegram

from config.cst import *
from services.abstract_service import *


class TelegramService(AbstractService):

    def __init__(self):
        super().__init__()
        self.telegram_api = None
        self.chat_id = None

    @staticmethod
    def is_setup_correctly(config):
        if CONFIG_TELEGRAM in config[CONFIG_CATEGORY_SERVICES] \
                and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM]:
            return True
        else:
            return False

    def prepare(self):
        if not self.telegram_api:
            self.chat_id = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM]["chat_id"]
            self.telegram_api = telegram.Bot(
                token=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM][CONFIG_TOKEN])

    def get_type(self):
        return CONFIG_TELEGRAM

    def get_endpoint(self):
        return self.telegram_api

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_TELEGRAM in self.config[CONFIG_CATEGORY_SERVICES] \
               and "token" in self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM] \
               and "chat_id" in self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM]

    def send_message(self, content):
        self.telegram_api.send_message(chat_id=self.chat_id, text=content)
