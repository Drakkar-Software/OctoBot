import twitter
import unicodedata

from config.cst import *
from services.abstract_service import *


class TwitterService(AbstractService):

    def __init__(self):
        super().__init__()
        self.twitter_api = None

    def get_user_id(self, user_account):
        user = self.twitter_api.GetUser(screen_name=user_account)
        return user.id

    def get_history(self, user_id):
        return self.twitter_api.GetUserTimeline(user_id=user_id)

    def prepare(self):
        if not self.twitter_api:
            self.twitter_api = twitter.Api(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER]["api-key"],
                                           self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER]["api-secret"],
                                           self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER]["access-token"],
                                           self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER]["access-token-secret"])

    def get_type(self):
        return CONFIG_TWITTER

    def get_endpoint(self):
        return self.twitter_api

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_TWITTER in self.config[CONFIG_CATEGORY_SERVICES] \
               and "api-key" in self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER] \
               and "api-secret" in self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER] \
               and "access-token" in self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER] \
               and "access-token-secret" in self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER]

    def tweet_to_string(self, tweet, counter, symbol=""):
        string = ""
        try:
            string = str(counter) + ": [extended] " + symbol + " " + str(
                unicodedata.normalize('NFKD', str(tweet["extended_tweet"]["full_text"])).encode('ascii', 'ignore'))
        except KeyError as e:
            try:
                string = str(counter) + ": [shorted] " + symbol + " " + str(
                    unicodedata.normalize('NFKD', str(tweet["text"])).encode('ascii', 'ignore'))
            except Exception as e2:
                self.logger.error(e2)
        return string
