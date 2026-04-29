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
import asyncio
import time
import asyncprawcore.exceptions
import logging

import octobot_commons.constants as commons_constants
import octobot_services.channel as services_channel
import octobot_services.constants as services_constants
import octobot_services.service_feeds as service_feeds
import tentacles.Services.Services_bases as Services_bases


class RedditServiceFeedChannel(services_channel.AbstractServiceFeedChannel):
    pass


class RedditServiceFeed(service_feeds.AbstractServiceFeed):
    FEED_CHANNEL = RedditServiceFeedChannel
    REQUIRED_SERVICES = [Services_bases.RedditService]

    MAX_CONNECTION_ATTEMPTS = 10

    def __init__(self, config, main_async_loop, bot_id, backtesting=None, importer=None):
        service_feeds.AbstractServiceFeed.__init__(self, config, main_async_loop, bot_id, backtesting=backtesting, importer=importer)
        self.subreddits = None
        self.counter = 0
        self.connect_attempts = 0
        self.credentials_ok = False
        self.listener_task = None

    # merge new config into existing config
    def update_feed_config(self, config):
        if services_constants.CONFIG_REDDIT_SUBREDDITS in self.feed_config:
            self.feed_config[services_constants.CONFIG_REDDIT_SUBREDDITS] = {
                **self.feed_config[services_constants.CONFIG_REDDIT_SUBREDDITS],
                **config[services_constants.CONFIG_REDDIT_SUBREDDITS]}
        else:
            self.feed_config[services_constants.CONFIG_REDDIT_SUBREDDITS] = config[
                services_constants.CONFIG_REDDIT_SUBREDDITS]

    def _init_subreddits(self):
        self.subreddits = ""
        for symbol in self.feed_config[services_constants.CONFIG_REDDIT_SUBREDDITS]:
            for subreddit in self.feed_config[services_constants.CONFIG_REDDIT_SUBREDDITS][symbol]:
                if subreddit not in self.subreddits:
                    if self.subreddits:
                        self.subreddits = self.subreddits + "+" + subreddit
                    else:
                        self.subreddits = self.subreddits + subreddit

    def _initialize(self):
        if not self.subreddits:
            self._init_subreddits()

    def _something_to_watch(self):
        return services_constants.CONFIG_REDDIT_SUBREDDITS in self.feed_config and self.feed_config[
            services_constants.CONFIG_REDDIT_SUBREDDITS]

    @staticmethod
    def _get_entry_weight(entry_age):
        if entry_age > 0:
            # entry in history => weight proportional to entry's age
            # last 12 hours: weight = 4
            # last 2 days: weight = 3
            # last 7 days: weight = 2
            # older: weight = 1
            if entry_age / commons_constants.HOURS_TO_SECONDS <= 12:
                return 4
            elif entry_age / commons_constants.DAYS_TO_SECONDS <= 2:
                return 3
            elif entry_age / commons_constants.DAYS_TO_SECONDS <= 7:
                return 2
            else:
                return 1
        # new entry => max weight
        return 5

    async def _start_listener(self):
        # avoid debug log at each asyncprawcore fetch
        logging.getLogger("asyncprawcore").setLevel(logging.WARNING)
        subreddit = await self.services[0].get_endpoint().subreddit(self.subreddits)
        start_time = time.time()
        async for entry in subreddit.stream.submissions():
            self.credentials_ok = True
            self.connect_attempts = 0
            self.counter += 1
            # check if we are in the 100 history or if it's a new entry (new posts are more valuables)
            # the older the entry is, the les weight it gets
            entry_age_when_feed_started_in_sec = start_time - entry.created_utc
            entry_weight = self._get_entry_weight(entry_age_when_feed_started_in_sec)
            await self._async_notify_consumers(
                {
                    services_constants.FEED_METADATA: entry.subreddit.display_name.lower(),
                    services_constants.CONFIG_REDDIT_ENTRY: entry,
                    services_constants.CONFIG_REDDIT_ENTRY_WEIGHT: entry_weight
                }
            )

    async def _start_listener_task(self):
        while not self.should_stop and self.connect_attempts < self.MAX_CONNECTION_ATTEMPTS:
            try:
                await self._start_listener()
            except asyncprawcore.exceptions.RequestException:
                # probably a connexion loss, try again
                time.sleep(self._SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC)
            except asyncprawcore.exceptions.InvalidToken as e:
                # expired, try again
                self.logger.exception(e, True, f"Error when receiving Reddit feed: '{e}'")
                self.logger.info(f"Try to continue after {self._SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC} seconds.")
                time.sleep(self._SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC)
            except asyncprawcore.exceptions.ServerError as e:
                # server error, try again
                self.logger.exception(e, True, "Error when receiving Reddit feed: '{e}'")
                self.logger.info(f"Try to continue after {self._SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC} seconds.")
                time.sleep(self._SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC)
            except asyncprawcore.exceptions.OAuthException as e:
                self.logger.exception(e, True, f"Error when receiving Reddit feed: '{e}' this may mean that reddit "
                                               f"login info in config.json are wrong")
                self.keep_running = False
                self.should_stop = True
            except asyncprawcore.exceptions.ResponseException as e:
                message_complement = "this may mean that reddit login info in config.json are invalid." \
                    if not self.credentials_ok else \
                    f"Try to continue after {self._SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC} seconds."
                self.logger.exception(e, True,
                                      f"Error when receiving Reddit feed: '{e}' this may mean {message_complement}")
                if not self.credentials_ok:
                    self.connect_attempts += 1
                else:
                    self.connect_attempts += 0.1
                time.sleep(self._SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC)
            except Exception as e:
                self.logger.exception(e, True, f"Error when receiving Reddit feed: '{e}'")
                self.keep_running = False
                self.should_stop = True
        return False

    async def _start_service_feed(self):
        self.listener_task = asyncio.create_task(self._start_listener_task())
        return True

    async def stop(self):
        await super().stop()
        if self.listener_task is not None:
            self.listener_task.cancel()
            self.listener_task = None
