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
import telethon

import octobot_services.channel as services_channel
import octobot_services.constants as services_constants
import octobot_services.service_feeds as service_feeds
import tentacles.Services.Services_bases as Services_bases


class TelegramApiServiceFeedChannel(services_channel.AbstractServiceFeedChannel):
    pass


class TelegramApiServiceFeed(service_feeds.AbstractServiceFeed):
    FEED_CHANNEL = TelegramApiServiceFeedChannel
    REQUIRED_SERVICES = [Services_bases.TelegramApiService]

    def __init__(self, config, main_async_loop, bot_id, backtesting=None, importer=None):
        super().__init__(config, main_async_loop, bot_id, backtesting=backtesting, importer=importer)
        self.feed_config = {
            services_constants.CONFIG_TELEGRAM_ALL_CHANNEL: True,
        }

    def update_feed_config(self, config):
        pass

    def _add_event_handler(self):
        self.services[0].add_event_handler(self.message_handler, telethon.events.NewMessage)

    async def message_handler(self, event):
        try:
            display_name = self.get_display_name(await event.get_sender())
            if self.feed_config[services_constants.CONFIG_TELEGRAM_ALL_CHANNEL]:
                media_output_path = None
                if event.message.media is not None:
                    media_output_path = await self.services[0].download_media_from_message(message=event.message,
                                                                                           source=display_name)
                await self.feed_send_coroutine(
                    {
                        services_constants.CONFIG_MESSAGE_SENDER: display_name,
                        services_constants.CONFIG_MESSAGE_CONTENT: event.text,
                        services_constants.CONFIG_IS_GROUP_MESSAGE: event.is_group,
                        services_constants.CONFIG_IS_CHANNEL_MESSAGE: event.is_channel,
                        services_constants.CONFIG_IS_PRIVATE_MESSAGE: event.is_private,
                        services_constants.CONFIG_MEDIA_PATH: media_output_path,
                    }
                )
            else:
                self.logger.debug(f"Ignored message from {display_name}: not in followed telegram users "
                                  f"(message: {event.text})")
        except Exception as e:
            self.logger.error(f"Fail to parse incoming message : {e}")

    def get_display_name(self, entity):
        if isinstance(entity, telethon.types.User):
            if entity.last_name and entity.first_name:
                return f"{entity.first_name} {entity.last_name}"
            elif entity.first_name:
                return entity.first_name
            elif entity.last_name:
                return entity.last_name
            else:
                return ""
        elif isinstance(entity, (telethon.types.Chat, telethon.types.ChatForbidden, telethon.types.Channel)):
            return entity.title
        return ""

    def _something_to_watch(self):
        return self.feed_config[services_constants.CONFIG_TELEGRAM_ALL_CHANNEL]

    @staticmethod
    def _get_service_layer_service_feed():
        return Services_bases.TelegramApiService

    def _initialize(self):
        self._add_event_handler()

    async def _start_service_feed(self):
        return True
