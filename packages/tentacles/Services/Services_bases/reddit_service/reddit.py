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

import asyncpraw

import octobot_services.constants as services_constants
import octobot_services.services as services
import octobot.constants as constants


class RedditService(services.AbstractService):
    CLIENT_ID = "client-id"
    CLIENT_SECRET = "client-secret"

    def __init__(self):
        super().__init__()
        self.reddit_api = None

    def get_fields_description(self):
        return {
            self.CLIENT_ID: "Your client ID.",
            self.CLIENT_SECRET: "Your client ID secret.",
        }

    def get_default_value(self):
        return {
            self.CLIENT_ID: "",
            self.CLIENT_SECRET: ""
        }

    def get_required_config(self):
        return [self.CLIENT_ID, self.CLIENT_SECRET]

    @classmethod
    def get_help_page(cls) -> str:
        return f"{constants.OCTOBOT_DOCS_URL}/octobot-interfaces/reddit"

    @staticmethod
    def is_setup_correctly(config):
        return services_constants.CONFIG_REDDIT in config[services_constants.CONFIG_CATEGORY_SERVICES] \
               and services_constants.CONFIG_SERVICE_INSTANCE in config[services_constants.CONFIG_CATEGORY_SERVICES][
                   services_constants.CONFIG_REDDIT]

    def create_reddit_api(self):
        self.reddit_api = \
            asyncpraw.Reddit(client_id=
                             self.config[services_constants.CONFIG_CATEGORY_SERVICES][
                                 services_constants.CONFIG_REDDIT][
                                 self.CLIENT_ID],
                             client_secret=
                             self.config[services_constants.CONFIG_CATEGORY_SERVICES][
                                 services_constants.CONFIG_REDDIT][
                                 self.CLIENT_SECRET],
                             user_agent='bot',
                             **self.mocked_asyncpraw_ini()
                             )

    async def prepare(self):
        if not self.reddit_api:
            try:
                self.create_reddit_api()
            except KeyError:
                asyncpraw.createIni()

    def get_type(self):
        return services_constants.CONFIG_REDDIT

    def get_website_url(self):
        return "https://www.reddit.com"

    def get_endpoint(self):
        return self.reddit_api

    def has_required_configuration(self):
        return services_constants.CONFIG_CATEGORY_SERVICES in self.config \
               and services_constants.CONFIG_REDDIT in self.config[services_constants.CONFIG_CATEGORY_SERVICES] \
               and self.check_required_config(
            self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_REDDIT])

    def get_successful_startup_message(self):
        return f"Successfully initialized.", True

    def mocked_asyncpraw_ini(self):
        # asyncpraw praw.ini file is sometimes not found in binary env, mock its values.
        # mock values from https://github.com/praw-dev/praw/blob/master/praw/praw.ini using [DEFAULT]
        # warning, on updating the asycpraw lib, make sure this file did not change
        # last update: 24 aug 2022 with asyncpraw==7.5.0
        # file:
        # [DEFAULT]
        # # A boolean to indicate whether or not to check for package updates.
        # check_for_updates = True
        #
        # # Object to kind mappings
        # comment_kind = t1
        # message_kind = t4
        # redditor_kind = t2
        # submission_kind = t3
        # subreddit_kind = t5
        # trophy_kind = t6
        #
        # # The URL prefix for OAuth-related requests.
        # oauth_url = https: // oauth.reddit.com
        #
        # # The amount of seconds of ratelimit to sleep for upon encountering a specific type of 429 error.
        # ratelimit_seconds = 5
        #
        # # The URL prefix for regular requests.
        # reddit_url = https: // www.reddit.com
        #
        # # The URL prefix for short URLs.
        # short_url = https: // redd.it
        #
        # # The timeout for requests to Reddit in number of seconds
        # timeout = 16
        return {
            "check_for_updates": "False",  # local overwrite to avoid update check at startup

            "comment_kind": "t1",
            "message_kind": "t4",
            "redditor_kind": "t2",
            "submission_kind": "t3",
            "subreddit_kind": "t5",
            "trophy_kind": "t6",

            "oauth_url": "https://oauth.reddit.com",

            "ratelimit_seconds": "5",

            "reddit_url": "https://www.reddit.com",

            "short_url": "https://redd.it",

            "timeout": "16",
        }
