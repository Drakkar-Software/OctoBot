#  Drakkar-Software OctoBot-Interfaces
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
import decimal
import logging
import time
import threading
import telegram.ext
import telegram.constants
import telegram.error

import octobot_commons.constants as commons_constants
import octobot_services.constants as services_constants
import octobot_services.interfaces.bots as interfaces_bots
import tentacles.Services.Services_bases as Services_bases


# Telegram bot interface
# telegram markdown reminder: *bold*, _italic_, `code`, [text_link](http://github.com/)


class TelegramBotInterface(interfaces_bots.AbstractBotInterface):
    REQUIRED_SERVICES = [Services_bases.TelegramService]
    HANDLED_CHATS = [telegram.constants.ChatType.PRIVATE]
    LAST_ERROR_TIMESTAMPS = {}
    ERROR_LEVEL_INTERVALS_THRESHOLD = 1 * commons_constants.MINUTE_TO_SECONDS

    def __init__(self, config):
        super().__init__(config)
        self.telegram_service: Services_bases.TelegramService = None

    async def _post_initialize(self, _):
        self.telegram_service = Services_bases.TelegramService.instance()
        self.telegram_service.register_user(self.get_name())
        self.telegram_service.add_handlers(self.get_bot_handlers())
        self.telegram_service.add_error_handler(self.command_error)
        self.telegram_service.register_text_polling_handler(self.HANDLED_CHATS, self.echo)
        return True

    async def _inner_start(self) -> bool:
        if self.telegram_service:
            await self.telegram_service.start_bot(TelegramBotInterface.handle_polling_error)
            return True
        else:
            # debug level log only: error log is already produced in initialize()
            self.get_logger().debug(
                f"Impossible to start bot interface: {self.REQUIRED_SERVICES[0].get_name()} is unavailable."
            )
            return False

    async def stop(self):
        await self.telegram_service.stop()

    def get_bot_handlers(self):
        return [
            telegram.ext.CommandHandler("start", self.command_start),
            telegram.ext.CommandHandler("ping", self.command_ping),
            telegram.ext.CommandHandler(["portfolio", "pf"], self.command_portfolio),
            telegram.ext.CommandHandler(["open_orders", "oo"], self.command_open_orders),
            telegram.ext.CommandHandler(["trades_history", "th"], self.command_trades_history),
            telegram.ext.CommandHandler(["profitability", "pb"], self.command_profitability),
            telegram.ext.CommandHandler(["fees", "fs"], self.command_fees),
            telegram.ext.CommandHandler("sell_all", self.command_sell_all),
            telegram.ext.CommandHandler("sell_all_currencies", self.command_sell_all_currencies),
            telegram.ext.CommandHandler("set_risk", self.command_risk),
            telegram.ext.CommandHandler(["market_status", "ms"], self.command_market_status),
            telegram.ext.CommandHandler(["configuration", "cf"], self.command_configuration),
            telegram.ext.CommandHandler(["refresh_portfolio", "rpf"], self.command_portfolio_refresh),
            telegram.ext.CommandHandler(["version", "v"], self.command_version),
            telegram.ext.CommandHandler("stop", self.command_stop),
            telegram.ext.CommandHandler("restart", self.command_restart),
            telegram.ext.CommandHandler(["help", "h"], self.command_help),
            telegram.ext.CommandHandler(["pause", "resume"], self.command_pause_resume),
            telegram.ext.MessageHandler(telegram.ext.filters.COMMAND, self.command_unknown)
        ]

    @staticmethod
    async def command_unknown(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            await TelegramBotInterface._send_message(
                update,
                f"`Unfortunately, I don't know the command:`"
                f"{telegram.helpers.escape_markdown(update.effective_message.text)}."
            )

    @staticmethod
    async def command_help(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            message = "* - My OctoBot skills - *" + interfaces_bots.EOL + interfaces_bots.EOL
            message += "/start: `Displays my startup message.`" + interfaces_bots.EOL
            message += "/ping: `Shows for how long I'm working.`" + interfaces_bots.EOL
            message += "/portfolio or /pf: `Displays my current portfolio.`" + interfaces_bots.EOL
            message += "/open\_orders or /oo: `Displays my current open orders.`" + interfaces_bots.EOL
            message += "/trades\_history or /th: `Displays my trades history since I started.`" + interfaces_bots.EOL
            message += "/profitability or /pb: `Displays the profitability I made since I started.`" + interfaces_bots.EOL
            message += "/market\_status or /ms: `Displays my understanding of the market and my risk parameter.`" + interfaces_bots.EOL
            message += "/fees or /fs: `Displays the total amount of fees I paid since I started.`" + interfaces_bots.EOL
            message += "/configuration or /cf: `Displays my traders, exchanges, evaluators, strategies and trading " \
                       "mode.`" + interfaces_bots.EOL
            message += "* - Trading Orders - *" + interfaces_bots.EOL
            message += "/sell\_all : `Cancels all my orders related to the currency in parameter and instantly " \
                       "liquidate my holdings in this currency for my reference market.`" + interfaces_bots.EOL
            message += "/sell\_all\_currencies : `Cancels all my orders and instantly liquidate all my currencies " \
                       "for my reference market.`" + interfaces_bots.EOL
            message += "* - Management - *" + interfaces_bots.EOL
            message += "/set\_risk: `Changes my current risk setting into your command's parameter.`" + interfaces_bots.EOL
            message += "/refresh\_portfolio or /rpf : `Forces OctoBot's real trader portfolio refresh using exchange " \
                       "data. Should normally not be necessary.`" + interfaces_bots.EOL
            message += "/pause or /resume: `Pauses or resumes me.`" + interfaces_bots.EOL
            message += "/restart: `Restarts me.`" + interfaces_bots.EOL
            message += "/stop: `Stops me.`" + interfaces_bots.EOL
            message += "/version or /v: `Displays my current software version.`" + interfaces_bots.EOL
            message += "/help: `Displays this help.`"
            await update.effective_message.reply_markdown(message)
        elif TelegramBotInterface._is_authorized_chat(update):
            await update.effective_message.reply_text(interfaces_bots.UNAUTHORIZED_USER_MESSAGE)

    @staticmethod
    async def command_start(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            await TelegramBotInterface._send_message(
                update, interfaces_bots.AbstractBotInterface.get_command_start(markdown=True)
            )
        elif TelegramBotInterface._is_authorized_chat(update):
            await TelegramBotInterface._send_message(update, interfaces_bots.UNAUTHORIZED_USER_MESSAGE)

    @staticmethod
    async def command_restart(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            await TelegramBotInterface._send_message(update, "I'll come back !")
            threading.Thread(
                target=interfaces_bots.AbstractBotInterface.set_command_restart,
                name="Restart bot from telegram command"
            ).start()

    @staticmethod
    async def command_stop(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            await TelegramBotInterface._send_message(update, "_I'm leaving this world..._")
            # start interfaces_bots.AbstractBotInterface.set_command_stop in a new thread to finish the current
            # python-telegram-bot update loop (python-telegram-bot updater can't stop within a loop, therefore
            # to be able to stop the telegram interface, this command has to return before the telegram bot can
            # can be stopped, otherwise telegram#stop ends up deadlocking)
            threading.Thread(
                target=interfaces_bots.AbstractBotInterface.set_command_stop,
                name="Stop bot from telegram command"
            ).start()

    @staticmethod
    async def command_version(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            await TelegramBotInterface._send_message(
                update, f"`{interfaces_bots.AbstractBotInterface.get_command_version()}`"
            )

    async def command_pause_resume(self, update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            if self.paused:
                await TelegramBotInterface._send_message(
                    update,
                    f"_Resuming..._{interfaces_bots.EOL}`I will restart trading when I see opportunities !`"
                )
                self.set_command_resume()
            else:
                await TelegramBotInterface._send_message(
                    update, f"_Pausing..._{interfaces_bots.EOL}`I'm cancelling my orders.`"
                )
                await self.set_command_pause()

    @staticmethod
    async def command_ping(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            await TelegramBotInterface._send_message(
                update, f"`{interfaces_bots.AbstractBotInterface.get_command_ping()}`"
            )

    @staticmethod
    async def command_risk(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            try:
                result_risk = interfaces_bots.AbstractBotInterface.set_command_risk(decimal.Decimal(context.args[0]))
                await TelegramBotInterface._send_message(update, f"`Risk successfully set to {result_risk}.`")
            except Exception:
                await TelegramBotInterface._send_message(
                    update, "`Failed to set new risk, please provide a number between 0 and 1.`"
                )

    @staticmethod
    async def command_profitability(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            await TelegramBotInterface._send_message(
                update, interfaces_bots.AbstractBotInterface.get_command_profitability(markdown=True)
            )

    @staticmethod
    async def command_fees(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            await TelegramBotInterface._send_message(
                update, interfaces_bots.AbstractBotInterface.get_command_fees(markdown=True)
            )

    @staticmethod
    async def command_sell_all_currencies(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            await TelegramBotInterface._send_message(
                update, f"`{await interfaces_bots.AbstractBotInterface.get_command_sell_all_currencies()}`"
            )

    @staticmethod
    async def command_sell_all(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            currency = context.args[0]
            if not currency:
                await TelegramBotInterface._send_message(update, "`Require a currency in parameter of this command.`")
            else:
                await TelegramBotInterface._send_message(
                    update, f"`{await interfaces_bots.AbstractBotInterface.get_command_sell_all(currency)}`"
                )

    @staticmethod
    async def command_portfolio(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            await TelegramBotInterface._send_message(update, interfaces_bots.AbstractBotInterface.get_command_portfolio(
                markdown=True))

    @staticmethod
    async def command_open_orders(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            await TelegramBotInterface._send_message(
                update, interfaces_bots.AbstractBotInterface.get_command_open_orders(markdown=True)
            )

    @staticmethod
    async def command_trades_history(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            await TelegramBotInterface._send_message(
                update, interfaces_bots.AbstractBotInterface.get_command_trades_history(markdown=True)
            )

    # refresh current order lists and portfolios and reload tham from exchanges
    @staticmethod
    async def command_portfolio_refresh(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            result = "Refresh"
            try:
                await interfaces_bots.AbstractBotInterface.set_command_portfolios_refresh()
                await TelegramBotInterface._send_message(update, f"`{result} successful`")
            except Exception as e:
                await TelegramBotInterface._send_message(update, f"`{result} failure: {e}`")

    # Displays my trades, exchanges, evaluators, strategies and trading
    @staticmethod
    async def command_configuration(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            try:
                await TelegramBotInterface._send_message(
                    update,
                    interfaces_bots.AbstractBotInterface.get_command_configuration(markdown=True)
                )
            except Exception:
                await TelegramBotInterface._send_message(
                    update,
                    "`I'm unfortunately currently unable to show you my configuration. "
                    "Please wait for my initialization to complete.`"
                )

    @staticmethod
    async def command_market_status(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            try:
                await TelegramBotInterface._send_message(
                    update, interfaces_bots.AbstractBotInterface.get_command_market_status(markdown=True)
                )
            except Exception:
                await TelegramBotInterface._send_message(
                    update,
                    "`I'm unfortunately currently unable to show you my market evaluations, "
                    "please retry in a few seconds.`"
                )

    @staticmethod
    async def command_error(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if update is None:
            TelegramBotInterface.get_logger().error(
                f"Command error with no telegram update. This should not happen. "
                f"context.error: {context} context: {context}"
            )
            return
        TelegramBotInterface.get_logger().warning("Command receiver error. Please check logs for more details.") \
            if context.error is None else TelegramBotInterface.get_logger().exception(context.error, False)
        if update is not None and TelegramBotInterface._is_valid_user(update):
            await TelegramBotInterface._send_message(
                update, f"Failed to perform this command {update.effective_message.text} : `{context.error}`"
            )

    @staticmethod
    def handle_polling_error(error):
        if isinstance(error, (telegram.error.NetworkError, telegram.error.Conflict)):
            if isinstance(error, telegram.error.Conflict):
                error_message = f"The configured Telegram bot is already connected to a different " \
                                f"software. Please create a different Telegram bot for each of your simultaneous " \
                                f"OctoBots ({error})"
            else:
                error_message = f"Telegram bot error: {error} ({error.__class__.__name__})"
            if TelegramBotInterface.get_error_log_level(error) is logging.ERROR:
                TelegramBotInterface.get_logger().error(error_message)
            elif TelegramBotInterface.get_error_log_level(error) is logging.WARNING:
                TelegramBotInterface.get_logger().warning(error_message)
            else:
                TelegramBotInterface.get_logger().debug(error_message)
        else:
            TelegramBotInterface.get_logger().error(
                f"Unexpected telegram bot error: {error} ({error.__class__.__name__})"
            )

    @staticmethod
    def get_error_log_level(error):
        try:
            if time.time() - TelegramBotInterface.LAST_ERROR_TIMESTAMPS[error.__class__] > \
               TelegramBotInterface.ERROR_LEVEL_INTERVALS_THRESHOLD:
                TelegramBotInterface.LAST_ERROR_TIMESTAMPS[error.__class__] = time.time()
                return logging.ERROR
            return logging.DEBUG
        except KeyError:
            TelegramBotInterface.LAST_ERROR_TIMESTAMPS[error.__class__] = time.time()
            return logging.ERROR

    @staticmethod
    async def echo(update: telegram.Update, _: telegram.ext.ContextTypes.DEFAULT_TYPE):
        if TelegramBotInterface._is_valid_user(update):
            await TelegramBotInterface._send_message(update, update.effective_message.text, markdown=False)

    @staticmethod
    def enable(config, is_enabled, associated_config=services_constants.CONFIG_TELEGRAM):
        interfaces_bots.AbstractBotInterface.enable(config, is_enabled, associated_config=associated_config)

    @staticmethod
    def is_enabled(config, associated_config=services_constants.CONFIG_TELEGRAM):
        return interfaces_bots.AbstractBotInterface.is_enabled(config, associated_config=associated_config)

    @staticmethod
    def _is_authorized_chat(update: telegram.Update):
        return update.effective_chat.type in TelegramBotInterface.HANDLED_CHATS

    @staticmethod
    def _is_valid_user(update: telegram.Update, associated_config=services_constants.CONFIG_TELEGRAM):
        # only authorize users from a private chat
        if not TelegramBotInterface._is_authorized_chat(update):
            return False
        is_valid, white_list = interfaces_bots.AbstractBotInterface._is_valid_user(
            update.effective_chat.username, associated_config=associated_config
        )
        if white_list and not is_valid:
            TelegramBotInterface.get_logger().error(
                f"An unauthorized Telegram user is trying to talk to me: username: {update.effective_chat.username}, "
                f"first_name: {update.effective_chat.first_name}, text: {update.effective_message.text}"
            )
        return is_valid

    @staticmethod
    async def _send_message(update: telegram.Update, message: str, markdown=True):
        messages = interfaces_bots.AbstractBotInterface._split_messages_if_too_long(
            message,
            telegram.constants.MessageLimit.MAX_TEXT_LENGTH,
            interfaces_bots.EOL
        )
        for m in messages:
            if markdown:
                await update.effective_message.reply_markdown(m)
            else:
                await update.effective_message.reply_text(m)
