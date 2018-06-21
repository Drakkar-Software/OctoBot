import logging
import time
from prawcore.exceptions import RequestException, ResponseException, OAuthException

from config.cst import *
from evaluator.Dispatchers.abstract_dispatcher import AbstractDispatcher
from services import RedditService


class RedditDispatcher(AbstractDispatcher):
    def __init__(self, config):
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.subreddits = None
        self.counter = 0
        self.social_config = {}

        # check presence of twitter instance
        if RedditService.is_setup_correctly(self.config):
            self.reddit_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT][CONFIG_SERVICE_INSTANCE]
            self.is_setup_correctly = True
        else:
            self.logger.warning("Required services are not ready")
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
        subreddit = self.reddit_service.get_endpoint().subreddit(self.subreddits)
        start_time = time.time()
        for entry in subreddit.stream.submissions():
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
                                                          CONFIG_REDDIT_ENTRY_WEIGHT: entry_weight})

    def _start_dispatcher(self):
        while self.keep_running:
            try:
                self._start_listener()
            except RequestException:
                # probably a connexion loss, try again
                time.sleep(self._SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC)
            except OAuthException as e:
                self.logger.error("Error when receiving Reddit feed: '{0}' this may mean {1}"
                                  .format(e, "that reddit login info in config.json are wrong."))
                self.logger.exception(e)
                self.keep_running = False
            except ResponseException as e:
                self.logger.error("Error when receiving Reddit feed: '{0}' this may mean {1}"
                                  .format(e, "that reddit configuration in config.json are wrong."))
                self.logger.exception(e)
                self.keep_running = False
            except Exception as e:
                self.logger.error("Error when receiving Reddit feed: '{0}'".format(e))
                self.logger.exception(e)
                self.keep_running = False
