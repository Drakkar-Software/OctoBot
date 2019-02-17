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
    CONFIG_GROUP_MESSAGE, CONFIG_GROUP_MESSAGE_DESCRIPTION
from services.Dispatchers.abstract_dispatcher import AbstractDispatcher
from services.Dispatchers.dispatcher_exception import DispatcherException
from services import TelegramService


class TelegramDispatcher(AbstractDispatcher):

    HANDLED_CHAT = "group"

    def __init__(self, config, main_async_loop):
        super().__init__(config, main_async_loop)
        self.social_config = {}

        # check presence of telegram instance
        if TelegramService.is_setup_correctly(self.config):
            self.service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM][CONFIG_SERVICE_INSTANCE]
            self.is_setup_correctly = True
        else:
            if TelegramService.should_be_ready(config):
                self.logger.warning(self.REQUIRED_SERVICE_ERROR_MESSAGE)
            self.is_setup_correctly = False

    # merge new config into existing config
    def update_social_config(self, config):
        if not TelegramService.is_setup_correctly(self.config):
            raise DispatcherException(f"{self.get_name()} is not usable: {self.REQUIRED_SERVICE_ERROR_MESSAGE}. "
                                      "Evaluators using Telegram channels information can't work.")
        if CONFIG_TELEGRAM_CHANNEL in self.social_config:
            self.social_config[CONFIG_TELEGRAM_CHANNEL].extend(chanel for chanel in config[CONFIG_TELEGRAM_CHANNEL]
                                                               if chanel not in
                                                               self.social_config[CONFIG_TELEGRAM_CHANNEL])
        else:
            self.social_config[CONFIG_TELEGRAM_CHANNEL] = config[CONFIG_TELEGRAM_CHANNEL]
        if self._something_to_watch():
            self._register_to_service()

    def _register_to_service(self):
        if not self.service.is_registered(self.get_name()):
            self.service.register_user(self.get_name())
            self.service.register_text_polling_handler(self.HANDLED_CHAT, self.dispatcher_callback)

    def dispatcher_callback(self, _, update):
        if update.effective_chat["title"] in self.social_config[CONFIG_TELEGRAM_CHANNEL]:
            message = update.message.text
            message_desc = str(update)
            self.notify_registered_clients_if_interested(message_desc,
                                                         {CONFIG_GROUP_MESSAGE: update,
                                                          CONFIG_GROUP_MESSAGE_DESCRIPTION: message.lower()
                                                          }
                                                         )

    def _something_to_watch(self):
        return CONFIG_TELEGRAM_CHANNEL in self.social_config \
               and self.social_config[CONFIG_TELEGRAM_CHANNEL]

    @staticmethod
    def _get_service_layer_dispatcher():
        return TelegramService

    def _get_data(self):
        pass

    def _start_dispatcher(self):
        return True
