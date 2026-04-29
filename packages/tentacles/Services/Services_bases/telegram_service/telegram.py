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
import logging
import typing
import telegram
import telegram.ext
import telegram.request
import telegram.error

import octobot_commons.logging as bot_logging
import octobot_services.constants as services_constants
import octobot_services.enums as services_enums
import octobot_services.services as services
import octobot.constants as constants


class TelegramService(services.AbstractService):
    CONNECT_TIMEOUT = 7  # default is 5, use 7 to take slow connections into account
    CHAT_ID = "chat-id"
    LOGGERS = ["telegram._bot", "telegram.ext.Updater", "telegram.ext.ExtBot",
               "hpack.hpack", "hpack.table"]

    def __init__(self):
        super().__init__()
        self.telegram_app: telegram.ext.Application = None
        self._has_bot = False
        self.chat_id = None
        self.users = []
        self.text_chat_dispatcher = {}
        self._bot_url = None
        self.connected = False

    def get_fields_description(self):
        return {
            self.CHAT_ID: "ID of your chat.",
            services_constants.CONFIG_TOKEN: "Token given by 'botfather'.",
            services_constants.CONFIG_USERNAMES_WHITELIST: "List of telegram usernames (user's @ identifier without "
                                                           "@) allowed to talk to your OctoBot. This allows you to "
                                                           "limit your OctoBot's telegram interactions to specific "
                                                           "users only. No access restriction if left empty."
        }

    def get_default_value(self):
        return {
            self.CHAT_ID: "",
            services_constants.CONFIG_TOKEN: "",
            services_constants.CONFIG_USERNAMES_WHITELIST: [],
        }

    def get_required_config(self):
        return [self.CHAT_ID, services_constants.CONFIG_TOKEN]

    def get_read_only_info(self) -> list[services.ReadOnlyInfo]:
        return [
            services.ReadOnlyInfo(
                'Connected to:', self._bot_url, services_enums.ReadOnlyInfoType.CLICKABLE
            )
        ] if self._bot_url else []

    @classmethod
    def get_help_page(cls) -> str:
        return f"{constants.OCTOBOT_DOCS_URL}/octobot-interfaces/telegram"

    @staticmethod
    def is_setup_correctly(config):
        return services_constants.CONFIG_TELEGRAM in config[services_constants.CONFIG_CATEGORY_SERVICES] \
               and services_constants.CONFIG_SERVICE_INSTANCE in config[services_constants.CONFIG_CATEGORY_SERVICES][
                   services_constants.CONFIG_TELEGRAM]

    async def prepare(self):
        if not self.telegram_app:
            bot_logging.set_logging_level(self.LOGGERS, logging.WARNING)
            self.chat_id = self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_TELEGRAM][
                self.CHAT_ID]
            # force http 1.1 requests to avoid the following issue:
            # Invalid input ConnectionInputs.RECV_WINDOW_UPDATE in state ConnectionState.CLOSED
            # from https://github.com/python-telegram-bot/python-telegram-bot/issues/3556
            self.telegram_app = telegram.ext.ApplicationBuilder()\
                .token(
                self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_TELEGRAM][
                    services_constants.CONFIG_TOKEN]
                )\
                .request(telegram.request.HTTPXRequest(
                    connect_timeout=self.CONNECT_TIMEOUT
                ))\
                .get_updates_request(telegram.request.HTTPXRequest(
                    connect_timeout=self.CONNECT_TIMEOUT
                ))\
                .build()
            try:
                await self._start_app()
            except telegram.error.InvalidToken as e:
                self.logger.error(f"Telegram configuration error: {e} Your Telegram token is invalid.")
            except telegram.error.NetworkError as e:
                self.log_connection_error_message(e)

    async def _start_app(self):
        self.logger.debug("Initializing telegram connection")
        self.connected = True
        await self.telegram_app.initialize()
        if self.telegram_app.post_init:
            await self.telegram_app.post_init(self.telegram_app)

    async def _start_bot(self, polling_error_callback):
        self._has_bot = True
        await self.telegram_app.updater.start_polling(error_callback=polling_error_callback)
        await self.telegram_app.start()

    async def _stop_app(self):
        await self.telegram_app.shutdown()
        if self.telegram_app.post_shutdown:
            await self.telegram_app.post_shutdown(self.telegram_app)
        self.connected = False

    async def _stop_bot(self):
        if self.telegram_app.updater.running:
            # await self.telegram_app.updater.shutdown()
            try:
                await self.telegram_app.updater.stop()
            except telegram.error.TimedOut as err:
                # can happen, ignore error
                self.logger.debug(f"Ignored {err} when stopping telegram bot")
        if self.telegram_app.running:
            await self.telegram_app.stop()
        if self.telegram_app.post_stop:
            await self.telegram_app.post_stop(self.telegram_app)
        self._has_bot = False

    def register_text_polling_handler(self, chat_types: telegram.constants.ChatType, handler):
        for chat_type in chat_types:
            self.text_chat_dispatcher[chat_type] = handler

    async def text_handler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
        chat_type = update.effective_chat.type
        if chat_type in self.text_chat_dispatcher:
            await self.text_chat_dispatcher[chat_type](update, context)
        else:
            self.logger.info(f"No handler for telegram update of type {chat_type}, update: {update}")

    def add_text_handler(self):
        self.telegram_app.add_handler(
            telegram.ext.MessageHandler(telegram.ext.filters.TEXT, self.text_handler)
        )

    def add_handlers(self, handlers):
        self.telegram_app.add_handlers(handlers)

    def add_error_handler(self, handler):
        self.telegram_app.add_error_handler(handler)

    def is_registered(self, user_key):
        return user_key in self.users

    def register_user(self, user_key):
        self.users.append(user_key)

    async def start_bot(self, polling_error_callback):
        try:
            if not self._has_bot and self.users:
                await self._start_bot(polling_error_callback)
                self.logger.debug("Started telegram bot")
                self.add_text_handler()
        except Exception as e:
            raise e

    def is_running(self):
        return self.telegram_app and self.telegram_app.running

    def get_type(self):
        return services_constants.CONFIG_TELEGRAM

    def get_website_url(self):
        return "https://telegram.org/"

    def get_endpoint(self):
        return self.telegram_app

    async def stop(self):
        if self.connected:
            if self._has_bot:
                await self._stop_bot()
            await self._stop_app()

    @staticmethod
    def get_is_enabled(config):
        return services_constants.CONFIG_CATEGORY_SERVICES in config \
               and services_constants.CONFIG_TELEGRAM in config[services_constants.CONFIG_CATEGORY_SERVICES]

    def has_required_configuration(self):
        return services_constants.CONFIG_CATEGORY_SERVICES in self.config \
               and services_constants.CONFIG_TELEGRAM in self.config[services_constants.CONFIG_CATEGORY_SERVICES] \
               and self.check_required_config(
            self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_TELEGRAM]) \
               and self.get_is_enabled(self.config)

    async def send_message(self, content, markdown=False, reply_to_message_id=None) -> typing.Optional[telegram.Message]:
        if not self.chat_id:
            self.logger.warning(
                "Impossible to send telegram message: please provide a chat id in telegram configuration."
            )
            return None
        kwargs = {}
        if markdown:
            kwargs[services_constants.MESSAGE_PARSE_MODE] = telegram.constants.ParseMode.MARKDOWN
        try:
            if content:
                return await self.telegram_app.bot.send_message(
                    chat_id=self.chat_id, text=content, reply_to_message_id=reply_to_message_id, **kwargs
                )
        except telegram.error.TimedOut:
            # retry on failing
            try:
                return await self.telegram_app.bot.send_message(
                    chat_id=self.chat_id, text=content, reply_to_message_id=reply_to_message_id, **kwargs
                )
            except telegram.error.TimedOut as e:
                self.logger.error(f"Failed to send message : {e}")
        except telegram.error.InvalidToken as e:
            self.logger.error(f"Failed to send message ({e}): invalid telegram configuration.")
        return None

    def _fetch_bot_url(self):
        self._bot_url = f"https://web.telegram.org/#/im?p={self.telegram_app.bot.name}"
        return self._bot_url

    def get_successful_startup_message(self):
        try:
            self.telegram_app.bot.name
        except RuntimeError:
            # raised by telegram_app.bot.name property when not properly initialized (invalid token, etc)
            # error has already been logged in prepare()
            return "", False
        return f"Successfully initialized and accessible at: {self._fetch_bot_url()}.", True
