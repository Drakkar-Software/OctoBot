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

from config import CONFIG_CATEGORY_SERVICES, CONFIG_TELEGRAM, CONFIG_SERVICE_INSTANCE, CONFIG_TELEGRAM_CHANNEL, \
    CONFIG_GROUP_MESSAGE, CONFIG_GROUP_MESSAGE_DESCRIPTION, CONFIG_TELEGRAM_ALL_CHANNEL
from services.Dispatchers.abstract_dispatcher import AbstractDispatcher
from services.Dispatchers.dispatcher_exception import DispatcherException
from services import TelegramService


class TelegramDispatcher(AbstractDispatcher):

    HANDLED_CHATS = ["group", "channel"]

    def __init__(self, config, main_async_loop):
        super().__init__(config, main_async_loop)
        self.channel_config = {
            CONFIG_TELEGRAM_ALL_CHANNEL: False,
            CONFIG_TELEGRAM_CHANNEL: []
        }

        # check presence of telegram instance
        if TelegramService.is_setup_correctly(self.config):
            self.service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM][CONFIG_SERVICE_INSTANCE]
            self.is_setup_correctly = True
        else:
            if TelegramService.should_be_ready(config):
                self.logger.warning(self.REQUIRED_SERVICE_ERROR_MESSAGE)
            self.is_setup_correctly = False

    # configure the whitelist of Telegram groups/channels to listen to
    # merge new config into existing config
    def update_channel_config(self, config):
        if not TelegramService.is_setup_correctly(self.config):
            raise DispatcherException(f"{self.get_name()} is not usable: {self.REQUIRED_SERVICE_ERROR_MESSAGE}. "
                                      "Evaluators using Telegram channels information can't work.")
        self.channel_config[CONFIG_TELEGRAM_CHANNEL].extend(channel for channel in config[CONFIG_TELEGRAM_CHANNEL]
                                                            if channel not in
                                                            self.channel_config[CONFIG_TELEGRAM_CHANNEL])
        self._register_if_something_to_watch()

    # if True, disable channel whitelist and listen to every group/channel it is invited to
    def set_listen_to_all_groups_and_channels(self, activate=True):
        self.channel_config[CONFIG_TELEGRAM_ALL_CHANNEL] = activate
        self._register_if_something_to_watch()

    def _register_if_something_to_watch(self):
        if self._something_to_watch():
            self._register_to_service()

    def _register_to_service(self):
        if not self.service.is_registered(self.get_name()):
            self.service.register_user(self.get_name())
            self.service.register_text_polling_handler(self.HANDLED_CHATS, self.dispatcher_callback)

    def dispatcher_callback(self, _, update):
        if self.channel_config[CONFIG_TELEGRAM_ALL_CHANNEL] or \
                update.effective_chat["title"] in self.channel_config[CONFIG_TELEGRAM_CHANNEL]:
            message = update.effective_message.text
            message_desc = str(update)
            self.notify_registered_clients_if_interested(message_desc,
                                                         {CONFIG_GROUP_MESSAGE: update,
                                                          CONFIG_GROUP_MESSAGE_DESCRIPTION: message.lower()
                                                          }
                                                         )

    def _something_to_watch(self):
        return self.channel_config[CONFIG_TELEGRAM_ALL_CHANNEL] or self.channel_config[CONFIG_TELEGRAM_CHANNEL]

    @staticmethod
    def _get_service_layer_dispatcher():
        return TelegramService

    def _get_data(self):
        pass

    def _start_dispatcher(self):
        return True
