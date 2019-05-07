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
from telegram.ext import Updater, MessageHandler, Filters  # , Dispatcher
import logging

from config import CONFIG_TOKEN, CONFIG_USERNAMES_WHITELIST, CONFIG_CATEGORY_SERVICES, CONFIG_TELEGRAM, \
    CONFIG_SERVICE_INSTANCE, MESSAGE_PARSE_MODE, CONFIG_INTERFACES_TELEGRAM, CONFIG_INTERFACES, CONFIG_ENABLED_OPTION
from interfaces.bots.telegram.bot import TelegramApp
from services.abstract_service import AbstractService
from tools.logging.logging_util import set_logging_level


class TelegramService(AbstractService):
    CHAT_ID = "chat-id"

    LOGGERS = ["telegram.bot", "telegram.ext.updater", "telegram.vendor.ptb_urllib3.urllib3.connectionpool"]

    def __init__(self):
        super().__init__()
        self.telegram_api = None
        self.chat_id = None
        self.telegram_app = None
        self.telegram_updater = None
        self.users = []
        self.text_chat_dispatcher = {}

    def get_fields_description(self):
        return {
            self.CHAT_ID: "ID of your chat.",
            CONFIG_TOKEN: "Token given by 'botfather'.",
            CONFIG_USERNAMES_WHITELIST: "List of telegram usernames allowed to talk to your OctoBot. "
                                        "No access restriction if left empty."
        }

    def get_default_value(self):
        return {
            self.CHAT_ID: "",
            CONFIG_TOKEN: "",
            CONFIG_USERNAMES_WHITELIST: [],
        }

    def get_required_config(self):
        return [self.CHAT_ID, CONFIG_TOKEN]

    @classmethod
    def get_help_page(cls) -> str:
        return "https://github.com/Drakkar-Software/OctoBot/wiki/Telegram-interface#telegram-interface"

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
                self.telegram_app = TelegramApp(self.config, self)

        set_logging_level(self.LOGGERS, logging.WARNING)

    def register_text_polling_handler(self, chat_types, handler):
        for chat_type in chat_types:
            self.text_chat_dispatcher[chat_type] = handler

    def text_handler(self, _, update):
        chat_type = update.effective_chat["type"]
        if chat_type in self.text_chat_dispatcher:
            self.text_chat_dispatcher[chat_type](_, update)
        else:
            self.logger.info(f"No handler for telegram update of type {chat_type}, update: {update}")

    def add_text_handler(self):
        self.telegram_updater.dispatcher.add_handler(MessageHandler(Filters.text, self.text_handler))

    def add_handlers(self, handlers):
        for handler in handlers:
            self.telegram_updater.dispatcher.add_handler(handler)

    def add_error_handler(self, handler):
        self.telegram_updater.dispatcher.add_error_handler(handler)

    def is_registered(self, user_key):
        return user_key in self.users

    def register_user(self, user_key):
        self.users.append(user_key)

    def start_dispatcher(self):
        if self.users:
            self.add_text_handler()
            self.telegram_updater.start_polling()

    def get_type(self):
        return CONFIG_TELEGRAM

    def get_endpoint(self):
        return self.telegram_api

    def get_updater(self):
        return self.telegram_updater

    def stop(self):
        if self.telegram_updater:
            self.telegram_updater.dispatcher.running = False
            self.telegram_updater.running = False

    # If this service is enabled
    def get_is_enabled(self, config):
        return super().get_is_enabled(config) \
            and self._check_enabled_option(config)

    @staticmethod
    def _check_enabled_option(config):
        return CONFIG_INTERFACES in config \
            and CONFIG_INTERFACES_TELEGRAM in config[CONFIG_INTERFACES] \
            and CONFIG_ENABLED_OPTION in config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM] \
            and config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM][CONFIG_ENABLED_OPTION] \
            and CONFIG_CATEGORY_SERVICES in config \
            and CONFIG_TELEGRAM in config[CONFIG_CATEGORY_SERVICES]

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_TELEGRAM in self.config[CONFIG_CATEGORY_SERVICES] \
               and self.check_required_config(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM]) \
               and self._check_enabled_option(self.config)

    @classmethod
    def should_be_ready(cls, config):
        return super().should_be_ready(config) and cls._check_enabled_option(config)

    async def send_message(self, content, markdown=False):
        kwargs = {}
        if markdown:
            kwargs[MESSAGE_PARSE_MODE] = telegram.parsemode.ParseMode.MARKDOWN
        try:
            if content:
                self.telegram_api.send_message(chat_id=self.chat_id, text=content, **kwargs)
        except telegram.error.TimedOut:
            # retry on failing
            try:
                self.telegram_api.send_message(chat_id=self.chat_id, text=content, **kwargs)
            except telegram.error.TimedOut as e:
                self.logger.error(f"Failed to send message : {e}")
        except telegram.error.Unauthorized as e:
            self.logger.error(f"Failed to send message ({e}): invalid telegram configuration.")

    def _get_bot_url(self):
        return f"https://web.telegram.org/#/im?p={self.telegram_api.get_me().name}"

    def get_successful_startup_message(self):
        try:
            return f"Successfully initialized and accessible at: {self._get_bot_url()}.", True
        except telegram.error.NetworkError as e:
            self.log_connection_error_message(e)
            return "", False
        except telegram.error.Unauthorized as e:
            self.logger.error(f"Error when connecting to Telegram ({e}): invalid telegram configuration.")
            return "", False
