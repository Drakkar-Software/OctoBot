#  Drakkar-Software OctoBot-Tentacles
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
import threading
# comment imports to remove twitter from dependencies when tentacle is disabled
# import twitter

import octobot_services.channel as services_channel
import octobot_services.constants as services_constants
import octobot_services.service_feeds as service_feeds
import tentacles.Services.Services_bases as Services_bases


# disable inheritance to disable tentacle visibility. Disabled as starting from feb 9 2023, API is now paid only
# class TwitterServiceFeedChannel(services_channel.AbstractServiceFeedChannel):
class TwitterServiceFeedChannel:
    pass


# disable inheritance to disable tentacle visibility. Disabled as starting from feb 9 2023, API is now paid only
# class TwitterServiceFeed(service_feeds.AbstractServiceFeed, threading.Thread):
class TwitterServiceFeed:
    FEED_CHANNEL = TwitterServiceFeedChannel
    REQUIRED_SERVICES = [Services_bases.TwitterService]

    def __init__(self, config, main_async_loop, bot_id, backtesting=None, importer=None):
        super().__init__(config, main_async_loop, bot_id, backtesting=backtesting, importer=importer)
        threading.Thread.__init__(self, name=self.get_name())
        self.user_ids = []
        self.hashtags = []
        self.counter = 0

    async def _inner_start(self) -> bool:
        threading.Thread.start(self)
        return True

    # merge new config into existing config
    def update_feed_config(self, config):
        if services_constants.CONFIG_TWITTERS_ACCOUNTS in self.feed_config:
            self.feed_config[services_constants.CONFIG_TWITTERS_ACCOUNTS] = {
                **self.feed_config[services_constants.CONFIG_TWITTERS_ACCOUNTS],
                **config[services_constants.CONFIG_TWITTERS_ACCOUNTS]}
        else:
            self.feed_config[services_constants.CONFIG_TWITTERS_ACCOUNTS] = config[
                services_constants.CONFIG_TWITTERS_ACCOUNTS]

        if services_constants.CONFIG_TWITTERS_HASHTAGS in self.feed_config:
            self.feed_config[services_constants.CONFIG_TWITTERS_HASHTAGS] = {
                **self.feed_config[services_constants.CONFIG_TWITTERS_HASHTAGS],
                **config[services_constants.CONFIG_TWITTERS_HASHTAGS]}
        else:
            self.feed_config[services_constants.CONFIG_TWITTERS_HASHTAGS] = config[
                services_constants.CONFIG_TWITTERS_HASHTAGS]

    def _init_users_accounts(self):
        tempo_added_accounts = []
        for symbol in self.feed_config[services_constants.CONFIG_TWITTERS_ACCOUNTS]:
            for account in self.feed_config[services_constants.CONFIG_TWITTERS_ACCOUNTS][symbol]:
                if account not in tempo_added_accounts:
                    tempo_added_accounts.append(account)
                    try:
                        self.user_ids.append(str(self.services[0].get_user_id(account)))
                    except twitter.TwitterError as e:
                        self.logger.error(account + " : " + str(e))

    def _init_hashtags(self):
        for symbol in self.feed_config[services_constants.CONFIG_TWITTERS_HASHTAGS]:
            for hashtag in self.feed_config[services_constants.CONFIG_TWITTERS_HASHTAGS][symbol]:
                if hashtag not in self.hashtags:
                    self.hashtags.append(hashtag)

    def _initialize(self):
        if not self.user_ids:
            self._init_users_accounts()
        if not self.hashtags:
            self._init_hashtags()

    def _something_to_watch(self):
        return (services_constants.CONFIG_TWITTERS_HASHTAGS in self.feed_config and self.feed_config[
            services_constants.CONFIG_TWITTERS_HASHTAGS]) \
               or (services_constants.CONFIG_TWITTERS_ACCOUNTS in self.feed_config and self.feed_config[
            services_constants.CONFIG_TWITTERS_ACCOUNTS])

    async def _start_listener(self):
        for tweet in self.services[0].get_endpoint().GetStreamFilter(follow=self.user_ids,
                                                                     track=self.hashtags,
                                                                     stall_warnings=True):
            self.counter += 1
            string_tweet = self.services[0].get_tweet_text(tweet)
            if string_tweet:
                tweet_desc = str(tweet).lower()
                self._notify_consumers(
                    {
                        services_constants.FEED_METADATA: tweet_desc,
                        services_constants.CONFIG_TWEET: tweet,
                        services_constants.CONFIG_TWEET_DESCRIPTION: string_tweet.lower()
                    }
                )

    async def _start_service_feed(self):
        while not self.should_stop:
            try:
                await self._start_listener()
            except twitter.error.TwitterError as e:
                self.logger.exception(e, True, f"Error when receiving Twitter feed: {e.message} ({e})")
                self.should_stop = True
            except Exception as e:
                self.logger.exception(e, True, f"Error when receiving Twitter feed: ({e})")
                self.should_stop = True
        return False
