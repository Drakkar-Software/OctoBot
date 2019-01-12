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

import telegram
from telegram.ext import Updater  # , Dispatcher
import logging

from config import *
from interfaces.bots.telegram.bot import TelegramApp
from services.abstract_service import *
from tools.logging.logging_util import set_logging_level


class TelegramService(AbstractService):
    CHAT_ID = "chat-id"

    REQUIRED_CONFIG = [CHAT_ID, CONFIG_TOKEN]

    # Used in configuration interfaces
    CONFIG_FIELDS_DESCRIPTION = {
        CHAT_ID: "ID of your chat.",
        CONFIG_TOKEN: "Token given by 'botfather'.",
        CONFIG_USERNAMES_WHITELIST: "List of telegram usernames allowed to talk to your OctoBot. "
                                    "No access restriction if left empty."
    }
    CONFIG_DEFAULT_VALUE = {
        CHAT_ID: "",
        CONFIG_TOKEN: "",
        CONFIG_USERNAMES_WHITELIST: [],
    }
    HELP_PAGE = "https://github.com/Drakkar-Software/OctoBot/wiki/Telegram-interface#telegram-interface"

    LOGGERS = ["telegram.bot", "telegram.ext.updater", "telegram.vendor.ptb_urllib3.urllib3.connectionpool"]

    def __init__(self):
        super().__init__()
        self.telegram_api = None
        self.chat_id = None
        self.telegram_app = None
        self.telegram_updater = None

    @staticmethod
    def is_setup_correctly(config):
        return CONFIG_TELEGRAM in config[CONFIG_CATEGORY_SERVICES] \
                and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM]

    async def prepare(self):
        if not self.telegram_api:
            self.chat_id = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM][self.CHAT_ID]
            self.telegram_api = telegram.Bot(
                token=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM][CONFIG_TOKEN])

        if not self.telegram_app:
            if not self.telegram_updater:
                self.telegram_updater = Updater(
                    token=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM][CONFIG_TOKEN])

            if TelegramApp.is_enabled(self.config):
                self.telegram_app = TelegramApp(self.config, self, self.telegram_updater)

        set_logging_level(self.LOGGERS, logging.WARNING)

    def get_type(self):
        return CONFIG_TELEGRAM

    def get_endpoint(self):
        return self.telegram_api

    def get_updater(self):
        return self.telegram_updater

    def stop(self):
        if self.telegram_updater:
            # __exception_event.is_set()
            # self.telegram_updater.dispatcher.__stop_event.set()
            # self.telegram_updater.__exception_event.set()
            # self.telegram_updater.dispatcher.__exception_event.set()
            self.telegram_updater.dispatcher.running = False
            self.telegram_updater.running = False
            # self.telegram_updater.dispatcher.running = False
            # self.telegram_updater.stop()

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_TELEGRAM in self.config[CONFIG_CATEGORY_SERVICES]  \
               and self.check_required_config(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM]) \
               and CONFIG_INTERFACES in self.config \
               and CONFIG_INTERFACES_TELEGRAM in self.config[CONFIG_INTERFACES] \
               and CONFIG_ENABLED_OPTION in self.config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM] \
               and self.config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM][CONFIG_ENABLED_OPTION]

    def send_message(self, content):
        try:
            if content:
                self.telegram_api.send_message(chat_id=self.chat_id, text=content)
        except telegram.error.TimedOut:
            # retry on failing
            try:
                self.telegram_api.send_message(chat_id=self.chat_id, text=content)
            except telegram.error.TimedOut as e:
                self.logger.error(f"failed to send message : {e}")

    def _get_bot_url(self):
        return f"https://web.telegram.org/#/im?p={self.telegram_api.get_me().name}"

    def get_successful_startup_message(self):
        try:
            return f"Successfully initialized and accessible at: {self._get_bot_url()}.", True
        except telegram.error.NetworkError as e:
            self.log_connection_error_message(e)
            return "", False
