#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import twitter

from config import CONFIG_CATEGORY_SERVICES, CONFIG_TWITTERS_ACCOUNTS, CONFIG_SERVICE_INSTANCE, CONFIG_TWITTER, \
    CONFIG_TWITTERS_HASHTAGS, CONFIG_TWEET, CONFIG_TWEET_DESCRIPTION
from services.Dispatchers.abstract_dispatcher import AbstractDispatcher
from services import TwitterService


class TwitterDispatcher(AbstractDispatcher):

    def __init__(self, config, main_async_loop):
        super().__init__(config, main_async_loop)
        self.user_ids = []
        self.hashtags = []
        self.counter = 0
        self.social_config = {}

        # check presence of twitter instance
        if TwitterService.is_setup_correctly(self.config):
            self.service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][CONFIG_SERVICE_INSTANCE]
            self.is_setup_correctly = True
        else:
            if TwitterService.should_be_ready(config):
                self.logger.warning(self.REQUIRED_SERVICE_ERROR_MESSAGE)
            self.is_setup_correctly = False

    # merge new config into existing config
    def update_social_config(self, config):
        if CONFIG_TWITTERS_ACCOUNTS in self.social_config:
            self.social_config[CONFIG_TWITTERS_ACCOUNTS] = {**self.social_config[CONFIG_TWITTERS_ACCOUNTS],
                                                            **config[CONFIG_TWITTERS_ACCOUNTS]}
        else:
            self.social_config[CONFIG_TWITTERS_ACCOUNTS] = config[CONFIG_TWITTERS_ACCOUNTS]

        if CONFIG_TWITTERS_HASHTAGS in self.social_config:
            self.social_config[CONFIG_TWITTERS_HASHTAGS] = {**self.social_config[CONFIG_TWITTERS_HASHTAGS],
                                                            **config[CONFIG_TWITTERS_HASHTAGS]}
        else:
            self.social_config[CONFIG_TWITTERS_HASHTAGS] = config[CONFIG_TWITTERS_HASHTAGS]

    def _init_users_accounts(self):
        tempo_added_accounts = []
        for symbol in self.social_config[CONFIG_TWITTERS_ACCOUNTS]:
            for account in self.social_config[CONFIG_TWITTERS_ACCOUNTS][symbol]:
                if account not in tempo_added_accounts:
                    tempo_added_accounts.append(account)
                    try:
                        self.user_ids.append(str(self.service.get_user_id(account)))
                    except twitter.TwitterError as e:
                        self.logger.error(account + " : " + str(e))

    def _init_hashtags(self):
        for symbol in self.social_config[CONFIG_TWITTERS_HASHTAGS]:
            for hashtag in self.social_config[CONFIG_TWITTERS_HASHTAGS][symbol]:
                if hashtag not in self.hashtags:
                    self.hashtags.append(hashtag)

    def _get_data(self):
        if not self.user_ids:
            self._init_users_accounts()
        if not self.hashtags:
            self._init_hashtags()

    def _something_to_watch(self):
        return (CONFIG_TWITTERS_HASHTAGS in self.social_config
                and self.social_config[CONFIG_TWITTERS_HASHTAGS]) \
               or (CONFIG_TWITTERS_ACCOUNTS in self.social_config
                   and self.social_config[CONFIG_TWITTERS_ACCOUNTS])

    def _start_listener(self):
        for tweet in self.service.get_endpoint().GetStreamFilter(follow=self.user_ids,
                                                                 track=self.hashtags,
                                                                 stall_warnings=True):
            self.counter += 1
            string_tweet = self.service.get_tweet_text(tweet)
            if string_tweet:
                tweet_desc = str(tweet).lower()
                self.notify_registered_clients_if_interested(tweet_desc,
                                                             {CONFIG_TWEET: tweet,
                                                              CONFIG_TWEET_DESCRIPTION: string_tweet.lower()
                                                              }
                                                             )

    def _start_dispatcher(self):
        while self.keep_running:
            try:
                self._start_listener()
            except twitter.error.TwitterError as e:
                self.logger.error(f"Error when receiving Twitter feed: {e.message} ({e})")
                self.logger.exception(e)
                self.keep_running = False
            except Exception as e:
                self.logger.error(f"Error when receiving Twitter feed ({e}) ")
                self.logger.exception(e)
                self.keep_running = False
        return False
