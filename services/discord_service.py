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
import asyncio

import discord

from config import CONFIG_DISCORD, CONFIG_SERVICE_INSTANCE, CONFIG_CATEGORY_SERVICES
from services.abstract_service import *


class DiscordService(AbstractService):
    REQUIRED_CONFIG = {"token": "", "channel_id": ""}

    def __init__(self):
        super().__init__()
        self.discord_client = DiscordClient()
        self.discord_app = None

    @staticmethod
    def is_setup_correctly(config):
        return CONFIG_DISCORD in config[CONFIG_CATEGORY_SERVICES] \
               and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_DISCORD]

    async def prepare(self):
        asyncio.run_coroutine_threadsafe(self.discord_client.start(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_DISCORD]["token"]), asyncio.get_event_loop())
        while not self.discord_client.is_ready():
            await asyncio.sleep(1)

        if not self.discord_app:
            pass

    def get_type(self):
        return CONFIG_DISCORD

    def get_endpoint(self):
        return self.discord_client

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_DISCORD in self.config[CONFIG_CATEGORY_SERVICES] \
               and self.check_required_config(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_DISCORD])

    async def send_message(self, content, error_on_failure=True):
        try:
            # asyncio.run_coroutine_threadsafe(self.discord_channel.send(content), asyncio.get_event_loop())
            await self.discord_client.send_message(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_DISCORD]["channel_id"],
                                                   content)
            return True
        except Exception as e:
            error = f"Failed to execute send message : {e} with content:{content}"
            if error_on_failure:
                self.logger.error(error)
            else:
                self.logger.info(error)
        return None

    def get_successful_startup_message(self):
        return f"Successfully initialized.", True

    def stop(self):
        asyncio.run_coroutine_threadsafe(self.discord_client.logout(), asyncio.get_event_loop())
        self.discord_client = None


class DiscordClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def send_message(self, channel, content):
        await self.get_channel(channel).send(content)

    async def on_message(self, message):
        # we do not want the bot to reply to itself
        if message.author.id == self.user.id:
            return

        if message.content.startswith('!hello'):
            await message.channel.send('Hello {0.author.mention}'.format(message))
