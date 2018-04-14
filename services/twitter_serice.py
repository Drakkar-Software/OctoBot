import twitter

from config.cst import *
from services.abstract_service import *


class TwitterService(AbstractService):

    def __init__(self):
        AbstractService.__init__(self)
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
        return CONFIG_TWITTER;

    def get_endpoint(self):
        return self.twitter_api
