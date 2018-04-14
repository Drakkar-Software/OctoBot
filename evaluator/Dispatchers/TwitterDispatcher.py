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
        self.social_config = None
        self.twitter_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][CONFIG_SERVICE_INSTANCE]

    def set_social_config(self, config):
        self.social_config = config

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

    def dispatch_notification_to_clients(self, data):
        string_tweet = self.twitter_service.tweet_to_string(data, 0)
        for key in self.registered_list:
            if key.lower() in string_tweet.lower():
                self.notify_registered_evaluator_clients(key, {CONFIG_TWEET: data})

        # to be called by dispatcher only

    def run(self):
        self.get_data()
        for tweet in self.twitter_service.get_endpoint().GetStreamFilter(follow=self.user_ids, track=self.hashtags):
            self.counter += 1
            self.dispatch_notification_to_clients(tweet)
