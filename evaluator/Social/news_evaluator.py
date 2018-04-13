from random import randint
import twitter
import unicodedata
from evaluator.unique_evaluator import UniqueEvaluator

from config.cst import *
from evaluator.Social.social_evaluator import NewsSocialEvaluator


class TwitterNewsEvaluator(NewsSocialEvaluator, UniqueEvaluator):
    def __init__(self):
        NewsSocialEvaluator.__init__(self)
        UniqueEvaluator.__init__(self)
        self.enabled = False
        self.is_threaded = True
        self.twitter_api = None
        self.user_ids = []
        self.hashtags = []
        self.count = 0
        self.symbol = ""

    def init_api(self):
        if(CONFIG_GLOBAL_UTILS in self.config
                and CONFIG_TWITTER_API_INSTANCE in self.config[CONFIG_GLOBAL_UTILS]
                and self.config[CONFIG_GLOBAL_UTILS][CONFIG_TWITTER_API_INSTANCE]):
            self.twitter_api = self.config[CONFIG_GLOBAL_UTILS][CONFIG_TWITTER_API_INSTANCE]
        else:
            self.twitter_api = twitter.Api(self.config[CONFIG_ADDITIONAL_RESOURCES][CONFIG_TWITTER]["api-key"],
                                           self.config[CONFIG_ADDITIONAL_RESOURCES][CONFIG_TWITTER]["api-secret"],
                                           self.config[CONFIG_ADDITIONAL_RESOURCES][CONFIG_TWITTER]["access-token"],
                                           self.config[CONFIG_ADDITIONAL_RESOURCES][CONFIG_TWITTER]["access-token-secret"])
            if CONFIG_GLOBAL_UTILS not in self.config:
                self.config[CONFIG_GLOBAL_UTILS] = {}
            self.config[CONFIG_GLOBAL_UTILS][CONFIG_TWITTER_API_INSTANCE] = self.twitter_api

    def init_users_accounts(self):
        for symbol in self.social_config[CONFIG_TWITTERS_ACCOUNTS]:
            for account in self.social_config[CONFIG_TWITTERS_ACCOUNTS][symbol]:
                try:
                    user = self.twitter_api.GetUser(screen_name=account)
                    self.user_ids.append(str(user.id))
                except twitter.TwitterError as e:
                    self.logger.error(account + " : " + str(e))

    def init_hashtags(self):
        for symbol in self.social_config[CONFIG_TWITTERS_HASHTAGS]:
            for hashtag in self.social_config[CONFIG_TWITTERS_HASHTAGS][symbol]:
                self.hashtags.append(hashtag)

    def get_history(self):
        user = self.twitter_api.GetUser(screen_name="GuillaGjum")
        user_id = str(user.id)
        history = self.twitter_api.GetUserTimeline(user_id=user_id)

    def get_data(self):
        if not self.user_ids:
            self.init_users_accounts()
        if not self.hashtags:
            self.init_hashtags()

    def prepare(self):
        super(TwitterNewsEvaluator, self).prepare()
        self.init_api()

    def eval(self):
        v = randint(0, 100)
        if v > 95:
            self.notify_evaluator_threads(self.__class__.__name__)

    def tweet_to_string(self, tweet, count):
        string=""
        try:
            string = str(count) + ": [extended] " + self.symbol + " " + str(
                unicodedata.normalize('NFKD', str(tweet["extended_tweet"]["full_text"])).encode('ascii', 'ignore'))
        except Exception as e:
            try:
                string = str(count) + ": [shorted] " + self.symbol + " " + str(
                    unicodedata.normalize('NFKD', str(tweet["text"])).encode('ascii', 'ignore'))
            except Exception as e2:
                self.logger.error(e2)
        return string

    def print_tweet(self, tweet, count):
        self.logger.debug(self.tweet_to_string(tweet, count))

    def receive_notification_data(self, data):
        self.count += 1
        self.print_tweet(data, self.count)

    def process_tweet(self, tweet):
        string_tweet = self.tweet_to_string(tweet, 0)
        for key in self.registered_list:
            if key.lower() in string_tweet.lower():
                self.notify_registered_evaluators(key, tweet)

    def run(self):
        self.get_data()
        for tweet in self.twitter_api.GetStreamFilter(follow=self.user_ids
                , track=self.hashtags):
            self.count += 1
            self.process_tweet(tweet)

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
