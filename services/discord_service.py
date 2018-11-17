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

import discord
from config.cst import *

from config import CONFIG_DISCORD, CONFIG_SERVICE_INSTANCE, CONFIG_CATEGORY_SERVICES
from services.abstract_service import *


class DiscordService(AbstractService):
    REQUIRED_CONFIG = {"token": "", "channel_id": ""}

    def __init__(self):
        super().__init__()
        self.discord_api = None
        self.discord_thread = None
        self.discord_channel = None

    @staticmethod
    def is_setup_correctly(config):
        return CONFIG_DISCORD in config[CONFIG_CATEGORY_SERVICES] \
               and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_DISCORD]

    def prepare(self):
        if not self.discord_api or not self.discord_thread:
            self.discord_api = discord.Client()
            self.discord_channel = discord.Object(id=
                                                  self.config[CONFIG_CATEGORY_SERVICES][CONFIG_DISCORD]["channel_id"])

            self.discord_thread = Thread(target=self.discord_api.run,
                                         args=(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_DISCORD]["token"], ))
            self.discord_thread.start()

    def get_type(self):
        return CONFIG_DISCORD

    def get_endpoint(self):
        return self.discord_api

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_DISCORD in self.config[CONFIG_CATEGORY_SERVICES] \
               and self.check_required_config(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_DISCORD])

    def send_message(self, content, error_on_failure=True):
        try:
            self.discord_api.send_message(destination=self.discord_channel, content=content)
            return True
        except Exception as e:
            error = f"Failed to execute send message : {e} with content:{content}"
            if error_on_failure:
                self.logger.error(error)
            else:
                self.logger.info(error)
        return None

    def get_successful_startup_message(self):
        return f"Successfully initialized."

    def stop(self):
        self.discord_api.logout()
        self.discord_thread = None
