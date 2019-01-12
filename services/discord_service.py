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
import asyncio

from config import CONFIG_DISCORD, CONFIG_SERVICE_INSTANCE, CONFIG_CATEGORY_SERVICES
from interfaces.bots.discord import DISCORD_API
from services.abstract_service import *


class DiscordService(AbstractService):
    REQUIRED_CONFIG = {"token": "", "channel_id": ""}

    def __init__(self):
        super().__init__()
        self.discord_client = None
        self.discord_channel = None

    @staticmethod
    def is_setup_correctly(config):
        return CONFIG_DISCORD in config[CONFIG_CATEGORY_SERVICES] \
               and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_DISCORD]

    async def prepare(self):
        self.discord_client = DISCORD_API.run(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_DISCORD]["token"])
        self.discord_channel = discord.Object(id=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_DISCORD]["channel_id"])
        await DISCORD_API.wait_until_ready()

    @staticmethod
    @DISCORD_API.event
    async def on_ready():
        print('Logged in as')
        print(DISCORD_API.user.name)
        print(DISCORD_API.user.id)
        print('------')

    def get_type(self):
        return CONFIG_DISCORD

    def get_endpoint(self):
        return DISCORD_API

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_DISCORD in self.config[CONFIG_CATEGORY_SERVICES] \
               and self.check_required_config(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_DISCORD])

    async def send_message(self, content, error_on_failure=True):
        try:
            await DISCORD_API.send_message(destination=self.discord_channel, content=content)
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
        DISCORD_API.logout()
        self.discord_client = None
