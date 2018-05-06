import telegram

from config.cst import *
from services.abstract_service import *


class TelegramService(AbstractService):

    def __init__(self):
        super().__init__()
        self.telegram_api = None

    @staticmethod
    def is_setup_correctly(config):
        if CONFIG_SERVICES_TELEGRAM in config[CONFIG_CATEGORY_SERVICES] \
                and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_SERVICES_TELEGRAM]:
            return True
        else:
            return False

    def prepare(self):
        if not self.telegram_api:
            self.telegram_api = telegram.Bot(token=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_SERVICES_TELEGRAM][CONFIG_TOKEN])

    def get_type(self):
        return CONFIG_SERVICES_TELEGRAM

    def get_endpoint(self):
        return self.telegram_api

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_SERVICES_TELEGRAM in self.config[CONFIG_CATEGORY_SERVICES] \
               and "token" in self.config[CONFIG_CATEGORY_SERVICES][CONFIG_SERVICES_TELEGRAM] \
