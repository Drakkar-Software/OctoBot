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

import time
from prawcore.exceptions import RequestException, ResponseException, OAuthException, InvalidToken, ServerError

from config import CONFIG_CATEGORY_SERVICES, CONFIG_REDDIT, CONFIG_SERVICE_INSTANCE, CONFIG_REDDIT_SUBREDDITS, \
    HOURS_TO_SECONDS, DAYS_TO_SECONDS, CONFIG_REDDIT_ENTRY, CONFIG_REDDIT_ENTRY_WEIGHT

from services.Dispatchers.abstract_dispatcher import AbstractDispatcher
from services import RedditService


class RedditDispatcher(AbstractDispatcher):

    MAX_CONNECTION_ATTEMPTS = 10

    def __init__(self, config, main_async_loop):
        super().__init__(config, main_async_loop)
        self.subreddits = None
        self.counter = 0
        self.connect_attempts = 0
        self.social_config = {}
        self.credentials_ok = False

        # check presence of twitter instance
        if RedditService.is_setup_correctly(self.config):
            self.service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT][CONFIG_SERVICE_INSTANCE]
            self.is_setup_correctly = True
        else:
            if RedditService.should_be_ready(config):
                self.logger.warning(self.REQUIRED_SERVICE_ERROR_MESSAGE)
            self.is_setup_correctly = False

    # merge new config into existing config
    def update_social_config(self, config):
        if CONFIG_REDDIT_SUBREDDITS in self.social_config:
            self.social_config[CONFIG_REDDIT_SUBREDDITS] = {**self.social_config[CONFIG_REDDIT_SUBREDDITS],
                                                            **config[CONFIG_REDDIT_SUBREDDITS]}
        else:
            self.social_config[CONFIG_REDDIT_SUBREDDITS] = config[CONFIG_REDDIT_SUBREDDITS]

    def _init_subreddits(self):
        self.subreddits = ""
        for symbol in self.social_config[CONFIG_REDDIT_SUBREDDITS]:
            for subreddit in self.social_config[CONFIG_REDDIT_SUBREDDITS][symbol]:
                if subreddit not in self.subreddits:
                    if self.subreddits:
                        self.subreddits = self.subreddits + "+" + subreddit
                    else:
                        self.subreddits = self.subreddits + subreddit

    def _get_data(self):
        if not self.subreddits:
            self._init_subreddits()

    def _something_to_watch(self):
        return CONFIG_REDDIT_SUBREDDITS in self.social_config and self.social_config[CONFIG_REDDIT_SUBREDDITS]

    def _start_listener(self):
        subreddit = self.service.get_endpoint().subreddit(self.subreddits)
        start_time = time.time()
        for entry in subreddit.stream.submissions():
            self.credentials_ok = True
            self.connect_attempts = 0
            self.counter += 1
            # check if we are in the 100 history or if it's a new entry (new posts are more valuables)
            # the older the entry is, the les weight it gets
            entry_age_when_dispatcher_started_in_sec = start_time - entry.created_utc
            # entry_weight = 0
            if entry_age_when_dispatcher_started_in_sec > 0:
                # entry in history => weight proportional to entry's age
                # last 12 hours: weight = 4
                # last 2 days: weight = 3
                # last 7 days: weight = 2
                # older: weight = 1
                if entry_age_when_dispatcher_started_in_sec / HOURS_TO_SECONDS <= 12:
                    entry_weight = 4
                elif entry_age_when_dispatcher_started_in_sec / DAYS_TO_SECONDS <= 2:
                    entry_weight = 3
                elif entry_age_when_dispatcher_started_in_sec / DAYS_TO_SECONDS <= 7:
                    entry_weight = 2
                else:
                    entry_weight = 1
            else:
                # new entry => max weight
                entry_weight = 5
            subreddit_name = entry.subreddit.display_name.lower()
            self.notify_registered_clients_if_interested(subreddit_name,
                                                         {CONFIG_REDDIT_ENTRY: entry,
                                                          CONFIG_REDDIT_ENTRY_WEIGHT: entry_weight}
                                                         )

    def _start_dispatcher(self):
        while self.keep_running and self.connect_attempts < self.MAX_CONNECTION_ATTEMPTS:
            try:
                self._start_listener()
            except RequestException:
                # probably a connexion loss, try again
                time.sleep(self._SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC)
            except InvalidToken as e:
                # expired, try again
                self.logger.error(f"Error when receiving Reddit feed: '{e}'")
                self.logger.exception(e)
                self.logger.info(f"Try to continue after {self._SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC} seconds.")
                time.sleep(self._SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC)
            except ServerError as e:
                # server error, try again
                self.logger.error("Error when receiving Reddit feed: '{e}'")
                self.logger.exception(e)
                self.logger.info(f"Try to continue after {self._SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC} seconds.")
                time.sleep(self._SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC)
            except OAuthException as e:
                self.logger.error(f"Error when receiving Reddit feed: '{e}' this may mean that reddit login info "
                                  f"in config.json are wrong")
                self.logger.exception(e)
                self.keep_running = False
            except ResponseException as e:
                message_complement = "this may mean that reddit login info in config.json are invalid." \
                    if not self.credentials_ok else \
                    f"Try to continue after {self._SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC} seconds."
                self.logger.error(f"Error when receiving Reddit feed: '{e}' this may mean {message_complement}")
                self.logger.exception(e)
                if not self.credentials_ok:
                    self.connect_attempts += 1
                else:
                    self.connect_attempts += 0.1
                time.sleep(self._SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC)
            except Exception as e:
                self.logger.error(f"Error when receiving Reddit feed: '{e}'")
                self.logger.exception(e)
                self.keep_running = False
        return False
