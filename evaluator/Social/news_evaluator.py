import time
from random import randint
import twitter

from config.cst import *
from evaluator.Social.social_evaluator import NewsSocialEvaluator


class TwitterNewsEvaluator(NewsSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False
        self.is_threaded = True
        self.twitter_api = None
        self.user_ids = []

    def init_api(self):
        self.twitter_api = twitter.Api(self.config["services"]["twitter"]["api-key"],
                                       self.config["services"]["twitter"]["api-secret"],
                                       self.config["services"]["twitter"]["access-token"],
                                       self.config["services"]["twitter"]["access-token-secret"])
        for account in self.config[CONFIG_CRYPTO_CURRENCIES][self.symbol][CONFIG_CRYPTO_TWITTERS]:
            try:
                user = self.twitter_api.GetUser(screen_name=account)
                self.user_ids.append(str(user.id))
            except twitter.TwitterError as e:
                self.logger.error(account + " : " + str(e))

    def get_history(self):
        user = self.twitter_api.GetUser(screen_name="GuillaGjum")
        user_id = str(user.id)
        history = self.twitter_api.GetUserTimeline(user_id=user_id)

    def get_data(self):
        if not self.twitter_api:
            self.init_api()

    def eval(self):
        v = randint(0, 100)
        if v > 95:
            self.notify_evaluator_threads(self.__class__.__name__)

    def run(self):
        self.get_data()
        for tweet in self.twitter_api.GetStreamFilter(follow=self.user_ids):
            self.logger.debug(tweet)


class MediumNewsEvaluator(NewsSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False
        self.is_threaded = False

    def get_data(self):
        pass

    def eval_impl(self):
        self.notify_evaluator_threads(self.__class__.__name__)

    def run(self):
        pass

    def set_default_config(self):
        self.social_config = {
            CONFIG_REFRESH_RATE: 2
        }
