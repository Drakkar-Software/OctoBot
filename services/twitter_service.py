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

import requests

import twitter
from twitter.api import CHARACTER_LIMIT
from twitter.twitter_utils import calc_expected_status_length

from config import *
from services.abstract_service import *


class TwitterService(AbstractService):
    API_KEY = "api-key"
    API_SECRET = "api-secret"
    ACCESS_TOKEN = "access-token"
    ACCESS_TOKEN_SECRET = "access-token-secret"

    def __init__(self):
        super().__init__()
        self.twitter_api = None

    def get_fields_description(self):
        return {
            self.API_KEY: "Your Twitter API key.",
            self.API_SECRET: "Your Twitter API-secret key.",
            self.ACCESS_TOKEN: "Your Twitter access token key.",
            self.ACCESS_TOKEN_SECRET: "Your Twitter access token secret key."
        }

    def get_default_value(self):
        return {
            self.API_KEY: "",
            self.API_SECRET: "",
            self.ACCESS_TOKEN: "",
            self.ACCESS_TOKEN_SECRET: ""
        }

    def get_required_config(self):
        return [self.API_KEY, self.API_SECRET, self.ACCESS_TOKEN, self.ACCESS_TOKEN_SECRET]

    @classmethod
    def get_help_page(cls) -> str:
        return "https://github.com/Drakkar-Software/OctoBot/wiki/Twitter-interface#twitter-interface"

    @staticmethod
    def is_setup_correctly(config):
        return CONFIG_TWITTER in config[CONFIG_CATEGORY_SERVICES] \
               and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER]

    def get_user_id(self, user_account):
        user = self.twitter_api.GetUser(screen_name=user_account)
        return user.id

    def get_history(self, user_id):
        return self.twitter_api.GetUserTimeline(user_id=user_id)

    async def prepare(self):
        if not self.twitter_api:
            self.twitter_api = twitter.Api(
                self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][self.API_KEY],
                self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][self.API_SECRET],
                self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][self.ACCESS_TOKEN],
                self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][self.ACCESS_TOKEN_SECRET],
                sleep_on_rate_limit=True
            )

    def get_type(self):
        return CONFIG_TWITTER

    def get_endpoint(self):
        return self.twitter_api

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_TWITTER in self.config[CONFIG_CATEGORY_SERVICES] \
               and self.check_required_config(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER])

    @staticmethod
    def decode_tweet(tweet):
        if "extended_tweet" in tweet and "full_text" in tweet:
            return tweet["extended_tweet"]["full_text"]
        elif "text" in tweet:
            return tweet["text"]
        return ""

    async def post(self, content, error_on_failure=True):
        try:
            return await self.split_tweet_content(content=content, tweet_id=None)
        except Exception as e:
            error = f"Failed to send tweet : {e} tweet:{content}"
            if error_on_failure:
                self.logger.error(error)
            else:
                self.logger.info(error)
        return None

    async def respond(self, tweet_id, content, error_on_failure=True):
        try:
            return await self.split_tweet_content(content=content, tweet_id=tweet_id)
        except Exception as e:
            error = f"Failed to send response tweet : {e} tweet:{content}"
            if error_on_failure:
                self.logger.error(error)
            else:
                self.logger.info(error)
        return None

    async def split_tweet_content(self, content, counter=None, counter_max=None, tweet_id=None):
        # add twitter counter at the beginning
        if counter is not None and counter_max is not None:
            content = f"{counter}/{counter_max} {content}"
            counter += 1

        # get the current content size
        post_size = calc_expected_status_length(content)

        # check if the current content size can be posted
        if post_size > CHARACTER_LIMIT:

            # calculate the number of post required for the whole content
            if not counter_max:
                counter_max = post_size // CHARACTER_LIMIT
                counter = 1

            # post the current tweet
            post = self.twitter_api.PostUpdate(status=content[:CHARACTER_LIMIT], in_reply_to_status_id=tweet_id)

            # recursive call for all post while content > CHARACTER_LIMIT
            await self.split_tweet_content(content[CHARACTER_LIMIT:],
                                           counter=counter,
                                           counter_max=counter_max,
                                           tweet_id=tweet_id)

            return post
        else:
            return self.twitter_api.PostUpdate(status=content[:CHARACTER_LIMIT], in_reply_to_status_id=tweet_id)

    def get_tweet_text(self, tweet):
        try:
            return TwitterService.decode_tweet(tweet)
        except Exception as e2:
            self.logger.error(e2)
        return ""

    @staticmethod
    def get_twitter_id_from_url(url):
        return str(url).split("/")[-1]

    def get_tweet(self, tweet_id):
        return self.twitter_api.GetStatus(tweet_id)

    def _get_twitter_url(self):
        return f"https://twitter.com/{self.twitter_api.VerifyCredentials().screen_name}"

    def get_successful_startup_message(self):
        try:
            return f"Successfully initialized and accessible at: {self._get_twitter_url()}.", True
        except requests.exceptions.ConnectionError as e:
            self.log_connection_error_message(e)
            return "", False
