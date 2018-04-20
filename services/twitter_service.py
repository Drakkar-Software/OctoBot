import twitter

from config.cst import *
from services.abstract_service import *


class TwitterService(AbstractService):

    def __init__(self):
        super().__init__()
        self.twitter_api = None

    @staticmethod
    def is_setup_correctly(config):
        if CONFIG_TWITTER in config[CONFIG_CATEGORY_SERVICES] \
                and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER]:
            return True
        else:
            return False

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

    @staticmethod
    def decode_tweet(tweet):
        try:
            return tweet["extended_tweet"]["full_text"]
        except KeyError:
            return tweet["text"]

    def post(self, content):
        try:
            return self.twitter_api.PostUpdate(status=content)
        except Exception as e:
            self.logger.error("Failed to send tweet : {0}".format(e))
            return None

    def respond(self, tweet_id, content):
        try:
            return self.twitter_api.PostUpdate(status=content, in_reply_to_status_id=tweet_id)
        except Exception as e:
            self.logger.error("Failed to send tweet : {0}".format(e))
            return None

    def tweet_to_string(self, tweet):
        try:
            return TwitterService.decode_tweet(tweet)
        except Exception as e2:
            self.logger.error(e2)
        return ""
