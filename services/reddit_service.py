import praw

from config.cst import *
from services.abstract_service import *


class RedditService(AbstractService):

    def __init__(self):
        super().__init__()
        self.reddit_api = None

    @staticmethod
    def is_setup_correctly(config):
        if CONFIG_REDDIT in config[CONFIG_CATEGORY_SERVICES] \
                and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT]:
            return True
        else:
            return False

    def prepare(self):
        if not self.reddit_api:
            self.reddit_api = praw.Reddit(client_id=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT]["client_id"],
                                          client_secret=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT]["client_secret"],
                                          password=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT]["password"],
                                          user_agent='bot',
                                          username=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT]["username"])

    def get_type(self):
        return CONFIG_REDDIT

    def get_endpoint(self):
        return self.reddit_api

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_REDDIT in self.config[CONFIG_CATEGORY_SERVICES] \
               and "client_id" in self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT] \
               and "client_secret" in self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT] \
               and "password" in self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT] \
               and "username" in self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT]
