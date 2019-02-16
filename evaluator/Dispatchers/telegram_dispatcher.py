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

from config import *
from evaluator.Dispatchers.abstract_dispatcher import AbstractDispatcher
from services import TelegramService


class TelegramDispatcher(AbstractDispatcher):

    HANDLED_CHAT = "private"

    def __init__(self, config, main_async_loop):
        super().__init__(config, main_async_loop)
        self.social_config = {}

        # check presence of telegram instance
        if TelegramService.is_setup_correctly(self.config):
            self.service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM][CONFIG_SERVICE_INSTANCE]
            self.service.register_user(self.get_name())
            self.service.register_text_polling_handler(self.HANDLED_CHAT, self.dispatcher_callback)
            self.is_setup_correctly = True
        else:
            if TelegramService.should_be_ready(config):
                self.logger.warning("Required services are not ready, dispatcher can't start")
            self.is_setup_correctly = False

    # merge new config into existing config
    def update_social_config(self, config):
        if CONFIG_TELEGRAM_CHANNEL in self.social_config:
            self.social_config[CONFIG_TELEGRAM_CHANNEL] = {**self.social_config[CONFIG_TELEGRAM_CHANNEL],
                                                           **config[CONFIG_TELEGRAM_CHANNEL]}
        else:
            self.social_config[CONFIG_TELEGRAM_CHANNEL] = config[CONFIG_TELEGRAM_CHANNEL]

    def dispatcher_callback(self, _, update):
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
