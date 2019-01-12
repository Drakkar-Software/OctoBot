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

import praw

from config import *
from services.abstract_service import *


class RedditService(AbstractService):
    CLIENT_ID = "client-id"
    CLIENT_SECRET = "client-secret"
    PASSWORD = "password"
    USERNAME = "username"

    REQUIRED_CONFIG = [CLIENT_ID, CLIENT_SECRET, PASSWORD, USERNAME]

    # Used in configuration interfaces
    CONFIG_FIELDS_DESCRIPTION = {
        CLIENT_ID: "Your client ID.",
        CLIENT_SECRET: "Your client ID secret.",
        PASSWORD: "Your Reddit username.",
        USERNAME: "Your Reddit password."
    }
    CONFIG_DEFAULT_VALUE = {
        CLIENT_ID: "",
        CLIENT_SECRET: "",
        PASSWORD: "",
        USERNAME: ""
    }
    HELP_PAGE = "https://github.com/Drakkar-Software/OctoBot/wiki/Reddit-interface#reddit-interface"

    def __init__(self):
        super().__init__()
        self.reddit_api = None

    @staticmethod
    def is_setup_correctly(config):
        return CONFIG_REDDIT in config[CONFIG_CATEGORY_SERVICES] \
                and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT]

    async def prepare(self):
        if not self.reddit_api:
            self.reddit_api = \
                praw.Reddit(client_id=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT][self.CLIENT_ID],
                            client_secret=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT][self.CLIENT_SECRET],
                            password=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT][self.PASSWORD],
                            user_agent='bot',
                            username=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT][self.USERNAME])

    def get_type(self):
        return CONFIG_REDDIT

    def get_endpoint(self):
        return self.reddit_api

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_REDDIT in self.config[CONFIG_CATEGORY_SERVICES] \
               and self.check_required_config(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT])

    def get_successful_startup_message(self):
        return f"Successfully initialized using {self.config[CONFIG_CATEGORY_SERVICES][CONFIG_REDDIT][self.USERNAME]}" \
               f" account.", True
