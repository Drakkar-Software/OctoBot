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

from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram.constants import MAX_MESSAGE_LENGTH

from config import CONFIG_INTERFACES_TELEGRAM
from interfaces.bots import EOL, UNAUTHORIZED_USER_MESSAGE
from interfaces.bots.interface_bot import InterfaceBot
from tools.pretty_printer import escape_markdown

# Telegram interface bot
# telegram markdown reminder: *bold*, _italic_, `code`, [text_link](http://github.com/)


class TelegramApp(InterfaceBot):

    HANDLED_CHATS = ["private"]

    def __init__(self, config, telegram_service):
        super().__init__(config)
        self.config = config
        self.paused = False
        self.telegram_service = telegram_service
        self.telegram_service.register_user(self.get_name())
        self.telegram_service.add_handlers(self.get_bot_handlers())
        self.telegram_service.add_error_handler(self.command_error)
        self.telegram_service.register_text_polling_handler(self.HANDLED_CHATS, self.echo)

        # bot will start when OctoBot's dispatchers will start

    @classmethod
    def get_name(cls):
        return cls.__name__

    def get_bot_handlers(self):
        return [
            CommandHandler("start", self.command_start),
            CommandHandler("ping", self.command_ping),
            CommandHandler(["portfolio", "pf"], self.command_portfolio),
            CommandHandler(["open_orders", "oo"], self.command_open_orders),
            CommandHandler(["trades_history", "th"], self.command_trades_history),
            CommandHandler(["profitability", "pb"], self.command_profitability),
            CommandHandler(["fees", "fs"], self.command_fees),
            CommandHandler("sell_all", self.command_sell_all),
            CommandHandler("sell_all_currencies", self.command_sell_all_currencies),
            CommandHandler("set_risk", self.command_risk),
            CommandHandler(["market_status", "ms"], self.command_market_status),
            CommandHandler(["configuration", "cf"], self.command_configuration),
            CommandHandler(["refresh_real_trader", "rrt"], self.command_real_traders_refresh),
            CommandHandler(["version", "v"], self.command_version),
            CommandHandler("stop", self.command_stop),
            CommandHandler("help", self.command_help),
            CommandHandler(["pause", "resume"], self.command_pause_resume),
            MessageHandler(Filters.command, self.command_unknown)
        ]

    @staticmethod
    def command_unknown(_, update):
        if TelegramApp._is_valid_user(update):
            TelegramApp._send_message(update, f"`Unfortunately, I don't know the command:` "
                                              f"{escape_markdown(update.effective_message.text)}.")

    @staticmethod
    def command_help(_, update):
        if TelegramApp._is_valid_user(update):
            message = "* - My OctoBot skills - *" + EOL + EOL
            message += "/start: `Displays my startup message.`" + EOL
            message += "/ping: `Shows for how long I'm working.`" + EOL
            message += "/portfolio or /pf: `Displays my current portfolio.`" + EOL
            message += "/open\_orders or /oo: `Displays my current open orders.`" + EOL
            message += "/trades\_history or /th: `Displays my trades history since I started.`" + EOL
            message += "/profitability or /pb: `Displays the profitability I made since I started.`" + EOL
            message += "/market\_status or /ms: `Displays my understanding of the market and my risk parameter.`" + EOL
            message += "/fees or /fs: `Displays the total amount of fees I paid since I started.`" + EOL
            message += "/configuration or /cf: `Displays my traders, exchanges, evaluators, strategies and trading " \
                       "mode.`" + EOL
            message += "* - Trading Orders - *" + EOL
            message += "/sell\_all : `Cancels all my orders related to the currency in parameter and instantly " \
                       "liquidate my holdings in this currency for my reference market.`" + EOL
            message += "/sell\_all\_currencies : `Cancels all my orders and instantly liquidate all my currencies " \
                       "for my reference market.`" + EOL
            message += "* - Management - *" + EOL
            message += "/set\_risk: `Changes my current risk setting into your command's parameter.`" + EOL
            message += "/refresh\_real\_trader or /rrt: `Force OctoBot's real trader data refresh using exchange " \
                       "data. Should normally not be necessary.`" + EOL
            message += "/pause or /resume: `Pause or resume me.`" + EOL
            message += "/stop: `Stops me.`" + EOL
            message += "/version or /v: `Displays my current software version.`" + EOL
            message += "/help: `Displays this help.`"
            update.message.reply_markdown(message)
        elif TelegramApp._is_authorized_chat(update):
            update.message.reply_text(UNAUTHORIZED_USER_MESSAGE)

    @staticmethod
    def get_command_param(command_name, update):
        return update.message.text.replace(command_name, "").strip()

    @staticmethod
    def command_start(_, update):
        if TelegramApp._is_valid_user(update):
            TelegramApp._send_message(update, InterfaceBot.get_command_start(markdown=True))
        elif TelegramApp._is_authorized_chat(update):
            TelegramApp._send_message(update, UNAUTHORIZED_USER_MESSAGE)

    @staticmethod
    def command_stop(_, update):
        # TODO add confirmation
        if TelegramApp._is_valid_user(update):
            TelegramApp._send_message(update, "_I'm leaving this world..._")
            InterfaceBot.set_command_stop()

    @staticmethod
    def command_version(_, update):
        if TelegramApp._is_valid_user(update):
            TelegramApp._send_message(update, f"`{InterfaceBot.get_command_version()}`")

    def command_pause_resume(self, _, update):
        if TelegramApp._is_valid_user(update):
            if self.paused:
                TelegramApp._send_message(update,
                                          f"_Resuming..._{EOL}`I will restart trading when I see opportunities !`")
                self.set_command_resume()
            else:
                TelegramApp._send_message(update, f"_Pausing..._{EOL}`I'm cancelling my orders.`")
                self.set_command_pause()

    @staticmethod
    def command_ping(_, update):
        if TelegramApp._is_valid_user(update):
            TelegramApp._send_message(update, f"`{InterfaceBot.get_command_ping()}`")

    @staticmethod
    def command_risk(_, update):
        if TelegramApp._is_valid_user(update):
            try:
                result_risk = InterfaceBot.set_command_risk(float(TelegramApp.get_command_param("/set_risk", update)))
                TelegramApp._send_message(update, f"`Risk successfully set to {result_risk}.`")
            except Exception:
                TelegramApp._send_message(update, "`Failed to set new risk, please provide a number between 0 and 1.`")

    @staticmethod
    def command_profitability(_, update):
        if TelegramApp._is_valid_user(update):
            TelegramApp._send_message(update, InterfaceBot.get_command_profitability(markdown=True))

    @staticmethod
    def command_fees(_, update):
        if TelegramApp._is_valid_user(update):
            TelegramApp._send_message(update, InterfaceBot.get_command_fees(markdown=True))

    @staticmethod
    def command_sell_all_currencies(_, update):
        if TelegramApp._is_valid_user(update):
            TelegramApp._send_message(update, f"`{InterfaceBot.get_command_sell_all_currencies()}`")

    @staticmethod
    def command_sell_all(_, update):
        if TelegramApp._is_valid_user(update):
            currency = TelegramApp.get_command_param("/sell_all", update)
            if not currency:
                TelegramApp._send_message(update, "`Require a currency in parameter of this command.`")
            else:
                TelegramApp._send_message(update, f"`{InterfaceBot.get_command_sell_all(currency)}`")

    @staticmethod
    def command_portfolio(_, update):
        if TelegramApp._is_valid_user(update):
            TelegramApp._send_message(update, InterfaceBot.get_command_portfolio(markdown=True))

    @staticmethod
    def command_open_orders(_, update):
        if TelegramApp._is_valid_user(update):
            TelegramApp._send_message(update, InterfaceBot.get_command_open_orders(markdown=True))

    @staticmethod
    def command_trades_history(_, update):
        if TelegramApp._is_valid_user(update):
            TelegramApp._send_message(update, InterfaceBot.get_command_trades_history(markdown=True))

    # refresh current order lists and portfolios and reload tham from exchanges
    @staticmethod
    def command_real_traders_refresh(_, update):
        if TelegramApp._is_valid_user(update):
            result = "Refresh"
            try:
                InterfaceBot.set_command_real_traders_refresh()
                TelegramApp._send_message(update, f"`{result} successful`")
            except Exception as e:
                TelegramApp._send_message(update, f"`{result} failure: {e}`")

    # Displays my trades, exchanges, evaluators, strategies and trading
    @staticmethod
    def command_configuration(_, update):
        if TelegramApp._is_valid_user(update):
            try:
                TelegramApp._send_message(update, InterfaceBot.get_command_configuration(markdown=True))
            except Exception:
                TelegramApp._send_message(update, "`I'm unfortunately currently unable to show you my configuration. "
                                                  "Please wait for my initialization to complete.`")

    @staticmethod
    def command_market_status(_, update):
        if TelegramApp._is_valid_user(update):
            try:
                TelegramApp._send_message(update, InterfaceBot.get_command_market_status(markdown=True))
            except Exception:
                TelegramApp._send_message(update, "`I'm unfortunately currently unable to show you my market "
                                                  "evaluations, please retry in a few seconds.`")

    @staticmethod
    def command_error(_, update, error):
        TelegramApp.get_logger().exception(error)
        if TelegramApp._is_valid_user(update):
            TelegramApp._send_message(update,
                                      f"Failed to perform this command {update.message.text} : `{error}`")

    @staticmethod
    def echo(_, update):
        if TelegramApp._is_valid_user(update):
            TelegramApp._send_message(update, update.effective_message["text"], markdown=False)

    @staticmethod
    def enable(config, is_enabled, associated_config=CONFIG_INTERFACES_TELEGRAM):
        InterfaceBot.enable(config, is_enabled, associated_config=associated_config)

    @staticmethod
    def is_enabled(config, associated_config=CONFIG_INTERFACES_TELEGRAM):
        return InterfaceBot.is_enabled(config, associated_config=associated_config)

    @staticmethod
    def _is_authorized_chat(update):
        return update.effective_chat["type"] in TelegramApp.HANDLED_CHATS

    @staticmethod
    def _is_valid_user(update, associated_config=CONFIG_INTERFACES_TELEGRAM):

        # only authorize users from a private chat
        if not TelegramApp._is_authorized_chat(update):
            return False

        update_username = update.effective_chat["username"]

        is_valid, white_list = InterfaceBot._is_valid_user(update_username, associated_config=associated_config)

        if white_list and not is_valid:
            TelegramApp.get_logger().error(f"An unauthorized Telegram user is trying to talk to me: username: "
                                           f"{update_username}, first_name: {update.effective_chat['first_name']}, "
                                           f"text: {update.effective_message['text']}")

        return is_valid

    @staticmethod
    def _send_message(update, message, markdown=True):
        messages = InterfaceBot._split_messages_if_too_long(message, MAX_MESSAGE_LENGTH, EOL)
        for m in messages:
            if markdown:
                update.message.reply_markdown(m)
            else:
                update.message.reply_text(m)
