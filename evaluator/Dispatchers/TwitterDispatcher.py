import logging
import twitter

from config.cst import *
from evaluator.evaluator_dispatcher import EvaluatorDispatcher


class TwitterDispatcher(EvaluatorDispatcher):
    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.user_ids = []
        self.hashtags = []
        self.counter = 0
        self.social_config = {}

        #check presence of twitter instance
        if CONFIG_TWITTER in self.config[CONFIG_CATEGORY_SERVICES] \
            and CONFIG_SERVICE_INSTANCE in self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER]:
            self.twitter_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][CONFIG_SERVICE_INSTANCE]
            self.is_setup_correctly = True
        else:
            self.is_setup_correctly = False

    # merge new config into existing config
    def update_social_config(self, config):
        if CONFIG_TWITTERS_ACCOUNTS in self.social_config:
            self.social_config[CONFIG_TWITTERS_ACCOUNTS] = {**self.social_config[CONFIG_TWITTERS_ACCOUNTS]
                                                            , **config[CONFIG_TWITTERS_ACCOUNTS]}
        else:
            self.social_config[CONFIG_TWITTERS_ACCOUNTS] = config[CONFIG_TWITTERS_ACCOUNTS]
        if CONFIG_TWITTERS_HASHTAGS in self.social_config:
            self.social_config[CONFIG_TWITTERS_HASHTAGS] = {**self.social_config[CONFIG_TWITTERS_HASHTAGS]
                                                            , **config[CONFIG_TWITTERS_HASHTAGS]}
        else:
            self.social_config[CONFIG_TWITTERS_HASHTAGS] = config[CONFIG_TWITTERS_HASHTAGS]

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

    def something_to_watch(self):
        return (CONFIG_TWITTERS_HASHTAGS in self.social_config
                and self.social_config[CONFIG_TWITTERS_HASHTAGS]) \
                or (CONFIG_TWITTERS_ACCOUNTS in self.social_config
                    and self.social_config[CONFIG_TWITTERS_ACCOUNTS])

    def run(self):
        if self.something_to_watch():
            self.get_data()
            try:
                for tweet in self.twitter_service.get_endpoint().GetStreamFilter(follow=self.user_ids
                                                                                 , track=self.hashtags):
                    self.counter += 1
                    string_tweet = self.twitter_service.tweet_to_string(tweet, 0).lower()
                    self.notify_registered_clients_if_interested(string_tweet, {CONFIG_TWEET: tweet})
            except twitter.error.TwitterError as e:
                self.logger.error("Error when receiving Twitter feed: " + str(e.message))
        else:
            self.logger.warning("Nothing to monitor, dispatcher is going to sleep.")
