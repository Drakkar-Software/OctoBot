from random import randint
import twitter
import unicodedata
from evaluator.unique_evaluator import *

from config.cst import *
from evaluator.Social.social_evaluator import NewsSocialEvaluator


class TwitterNewsEvaluator(NewsSocialEvaluator, UniqueEvaluatorDispatcher, UniqueEvaluatorClient):
    def __init__(self):
        NewsSocialEvaluator.__init__(self)
        UniqueEvaluatorClient.__init__(self)
        UniqueEvaluatorDispatcher.__init__(self)
        self.enabled = False
        self.is_threaded = True
        self.twitter_service = None
        self.user_ids = []
        self.hashtags = []
        self.count = 0
        self.symbol = ""

    def init_users_accounts(self):
        for symbol in self.social_config[CONFIG_TWITTERS_ACCOUNTS]:
            for account in self.social_config[CONFIG_TWITTERS_ACCOUNTS][symbol]:
                try:
                    self.user_ids.append(str(self.twitter_service.get_user_id(account)))
                except twitter.TwitterError as e:
                    self.logger.error(account + " : " + str(e))

    def init_hashtags(self):
        for symbol in self.social_config[CONFIG_TWITTERS_HASHTAGS]:
            for hashtag in self.social_config[CONFIG_TWITTERS_HASHTAGS][symbol]:
                self.hashtags.append(hashtag)

    def get_data(self):
        if not self.user_ids:
            self.init_users_accounts()
        if not self.hashtags:
            self.init_hashtags()

    def prepare(self):
        super(TwitterNewsEvaluator, self).prepare()
        self.twitter_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][CONFIG_SERVICE_INSTANCE]

    def eval(self):
        v = randint(0, 100)
        if v > 95:
            self.notify_evaluator_threads(self.__class__.__name__)

    def tweet_to_string(self, tweet, count):
        string = ""
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

    def get_dispatcher_class(self):
        return TwitterNewsEvaluator

    def receive_notification_data(self, data):
        self.count += 1
        self.print_tweet(data[CONFIG_TWEET], self.count)

    def dispatch_notification_to_clients(self, data):
        string_tweet = self.tweet_to_string(data, 0)
        for key in self.registered_list:
            if key.lower() in string_tweet.lower():
                self.notify_registered_evaluator_clients(key, {CONFIG_TWEET: data})

    # to be called by dispatcher only
    def run(self):
        self.get_data()
        for tweet in self.twitter_service.get_endpoint().GetStreamFilter(follow=self.user_ids, track=self.hashtags):
            self.count += 1
            self.dispatch_notification_to_clients(tweet)


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
