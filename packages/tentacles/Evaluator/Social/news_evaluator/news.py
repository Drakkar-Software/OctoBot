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

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.tentacles_management as tentacles_management
import octobot_services.constants as services_constants
import octobot_evaluators.evaluators as evaluators
import tentacles.Services.Services_feeds as Services_feeds
import tentacles.Evaluator.Util as EvaluatorUtil


# disable inheritance to disable tentacle visibility. Disabled as starting from feb 9 2023, API is now paid only
# class TwitterNewsEvaluator(evaluators.SocialEvaluator):
class TwitterNewsEvaluator:
    SERVICE_FEED_CLASS = Services_feeds.TwitterServiceFeed if hasattr(Services_feeds, 'TwitterServiceFeed') else None

    # max time to live for a pulse is 10min
    _EVAL_MAX_TIME_TO_LIVE = 10 * commons_constants.MINUTE_TO_SECONDS
    # absolute value above which a notification is triggered
    _EVAL_NOTIFICATION_THRESHOLD = 0.6

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.count = 0
        self.sentiment_analyser = None
        self.is_self_refreshing = True
        self.accounts_by_cryptocurrency = {}
        self.hashtags_by_cryptocurrency = {}

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        cryptocurrencies = []
        config_cryptocurrencies = self.UI.user_input(
            commons_constants.CONFIG_CRYPTO_CURRENCIES, commons_enums.UserInputTypes.OBJECT_ARRAY,
            cryptocurrencies, inputs, other_schema_values={"minItems": 1, "uniqueItems": True},
            item_title="Crypto currency",
            title="Crypto currencies to watch."
        )
        # init one user input to generate user input schema and default values
        cryptocurrencies.append(self._init_cryptocurrencies(inputs, "Bitcoin", ["BTCFoundation"], []))
        # remove other symbols data to avoid unnecessary entries
        self.accounts_by_cryptocurrency = self._get_config_elements(config_cryptocurrencies,
                                                                    services_constants.CONFIG_TWITTERS_ACCOUNTS)
        self.hashtags_by_cryptocurrency = self._get_config_elements(config_cryptocurrencies,
                                                                    services_constants.CONFIG_TWITTERS_HASHTAGS)
        self.feed_config[services_constants.CONFIG_TWITTERS_ACCOUNTS] = self.accounts_by_cryptocurrency
        self.feed_config[services_constants.CONFIG_TWITTERS_HASHTAGS] = self.hashtags_by_cryptocurrency

    def _init_cryptocurrencies(self, inputs, cryptocurrency, accounts, hashtags):
        return {
            commons_constants.CONFIG_CRYPTO_CURRENCY:
                self.UI.user_input(commons_constants.CONFIG_CRYPTO_CURRENCY, commons_enums.UserInputTypes.TEXT,
                                cryptocurrency, inputs, other_schema_values={"minLength": 2},
                                parent_input_name=commons_constants.CONFIG_CRYPTO_CURRENCIES, array_indexes=[0],
                                title="Crypto currency name"),
            services_constants.CONFIG_TWITTERS_ACCOUNTS:
                self.UI.user_input(services_constants.CONFIG_TWITTERS_ACCOUNTS, commons_enums.UserInputTypes.STRING_ARRAY,
                                accounts, inputs, other_schema_values={"uniqueItems": True},
                                parent_input_name=commons_constants.CONFIG_CRYPTO_CURRENCIES, array_indexes=[0],
                                item_title="Twitter account name",
                                title="Twitter accounts to watch"),
            services_constants.CONFIG_TWITTERS_HASHTAGS:
                self.UI.user_input(services_constants.CONFIG_TWITTERS_HASHTAGS, commons_enums.UserInputTypes.STRING_ARRAY,
                                hashtags, inputs, other_schema_values={"uniqueItems": True},
                                parent_input_name=commons_constants.CONFIG_CRYPTO_CURRENCIES, array_indexes=[0],
                                item_title="Hashtag",
                                title="Twitter hashtags to watch (without the # character), "
                                      "warning: might trigger evaluator for irrelevant tweets.")
        }

    @classmethod
    def get_is_cryptocurrencies_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not cryptocurrency dependant else False
        """
        return False

    @classmethod
    def get_is_cryptocurrency_name_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not cryptocurrency name dependant else False
        """
        return False

    def _print_tweet(self, tweet_text, tweet_url, note, count=""):
        self.logger.debug(f"Current note : {note} | {count} : {self.cryptocurrency_name} : Link: {tweet_url} Text : "
                          f"{tweet_text.encode('utf-8', 'ignore')}")

    async def _feed_callback(self, data):
        if self._is_interested_by_this_notification(data[services_constants.CONFIG_TWEET_DESCRIPTION]):
            self.count += 1
            note = self._get_tweet_sentiment(data[services_constants.CONFIG_TWEET],
                                             data[services_constants.CONFIG_TWEET_DESCRIPTION])
            tweet_url = f"https://twitter.com/ProducToken/status/{data['tweet']['id']}"
            if note != commons_constants.START_PENDING_EVAL_NOTE:
                self._print_tweet(data[services_constants.CONFIG_TWEET_DESCRIPTION], tweet_url, note, str(self.count))
            await self._check_eval_note(note)

    # only set eval note when something is happening
    async def _check_eval_note(self, note):
        if note != commons_constants.START_PENDING_EVAL_NOTE:
            if abs(note) > self._EVAL_NOTIFICATION_THRESHOLD:
                self.eval_note = note
                self.save_evaluation_expiration_time(self._compute_notification_time_to_live(self.eval_note))
                await self.evaluation_completed(self.cryptocurrency, eval_time=self.get_current_exchange_time())

    @staticmethod
    def _compute_notification_time_to_live(evaluation):
        return TwitterNewsEvaluator._EVAL_MAX_TIME_TO_LIVE * abs(evaluation)

    def _get_tweet_sentiment(self, tweet, tweet_text, is_a_quote=False):
        try:
            if is_a_quote:
                return -1 * self.sentiment_analyser.analyse(tweet_text)
            else:
                padding_name = "########"
                author_screen_name = tweet['user']['screen_name'] if "screen_name" in tweet['user'] \
                    else padding_name
                author_name = tweet['user']['name'] if "name" in tweet['user'] else padding_name
                if author_screen_name in self.accounts_by_cryptocurrency[self.cryptocurrency_name] \
                        or author_name in self.accounts_by_cryptocurrency[self.cryptocurrency_name]:
                    return -1 * self.sentiment_analyser.analyse(tweet_text)
        except KeyError:
            pass

        # ignore # for the moment (too much of bullshit)
        return commons_constants.START_PENDING_EVAL_NOTE

    def _is_interested_by_this_notification(self, notification_description):
        # true if in twitter accounts
        try:
            for account in self.accounts_by_cryptocurrency[self.cryptocurrency_name]:
                if account.lower() in notification_description:
                    return True
        except KeyError:
            return False
        # false if it's a RT of an unfollowed account
        if notification_description.startswith("rt"):
            return False

        # true if contains symbol
        if self.cryptocurrency_name.lower() in notification_description:
            return True

        # true if in hashtags
        if self.hashtags_by_cryptocurrency:
            for hashtags in self.hashtags_by_cryptocurrency[self.cryptocurrency_name]:
                if hashtags.lower() in notification_description:
                    return True
            return False

    def _get_config_elements(self, config_cryptocurrencies, key):
        if config_cryptocurrencies:
            return {
                cc[commons_constants.CONFIG_CRYPTO_CURRENCY]: cc[key]
                for cc in config_cryptocurrencies
                if cc[commons_constants.CONFIG_CRYPTO_CURRENCY] == self.cryptocurrency_name
            }
        return {}

    async def prepare(self):
        self.sentiment_analyser = tentacles_management.get_single_deepest_child_class(EvaluatorUtil.TextAnalysis)()


NEWS_CONFIG_LANGUAGE = "language"

# Should use any feed available to fetch crypto news (coindesk, etc.)
class CryptoNewsEvaluator(evaluators.SocialEvaluator):
    SERVICE_FEED_CLASS = Services_feeds.CoindeskServiceFeed

    def __init__(self, tentacles_setup_config):
        evaluators.SocialEvaluator.__init__(self, tentacles_setup_config)
        self.stats_analyser = None   
        self.language = None

    def init_user_inputs(self, inputs: dict) -> None:
        self.language = self.UI.user_input(NEWS_CONFIG_LANGUAGE,
                               commons_enums.UserInputTypes.TEXT,
                               self.language, inputs,
                               title="Language to use to fetch crypto news.",
                               options=["en", "fr"])
        self.feed_config = {
            services_constants.CONFIG_COINDESK_TOPICS: [services_constants.COINDESK_TOPIC_NEWS],
            services_constants.CONFIG_COINDESK_LANGUAGE: self.language
        }

    @classmethod
    def get_is_cryptocurrencies_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not cryptocurrency dependant else False
        """
        return True

    @classmethod
    def get_is_cryptocurrency_name_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not cryptocurrency name dependant else False
        """
        return True

    async def _feed_callback(self, data):
        if self._is_interested_by_this_notification(data[services_constants.FEED_METADATA]):
            latest_news = self.get_data_cache(self.get_current_exchange_time(), key=services_constants.COINDESK_TOPIC_NEWS)
            if latest_news is not None and len(latest_news) > 0:
                sentiment_sum = 0
                news_count = 0
                news_titles = []
                for news in latest_news:
                    sentiment = news.sentiment
                    sentiment_sum += 0 if sentiment is None else -1 if sentiment == "NEGATIVE" else 1 if sentiment == "POSITIVE" else 0
                    news_count += 1
                    news_titles.append(news.title)
                
                if news_count > 0:  
                    self.eval_note = sentiment_sum / news_count
                    await self.evaluation_completed(
                        cryptocurrency=None,
                        eval_time=self.get_current_exchange_time(), 
                        eval_note_description=f"Overall news sentiment: {'POSITIVE' if self.eval_note > 0 else 'NEGATIVE' if self.eval_note < 0 else 'NEUTRAL'}. News titles: " + "; ".join(news_titles)
                    )
                else:
                    self.debug(f"No news found")

    def _is_interested_by_this_notification(self, notification_description):
        return notification_description == services_constants.COINDESK_TOPIC_NEWS

    async def prepare(self):
        self.sentiment_analyser = tentacles_management.get_single_deepest_child_class(EvaluatorUtil.TextAnalysis)()
