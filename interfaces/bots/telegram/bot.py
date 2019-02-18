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

from config import CONFIG_INTERFACES_TELEGRAM
from interfaces.bots import EOL, LOGGER, UNAUTHORIZED_USER_MESSAGE
from interfaces.bots.interface_bot import InterfaceBot
from tools.pretty_printer import escape_markdown

# Telegram interface bot
# telegram markdown reminder: *bold*, _italic_, `code`, [text_link](http://github.com/)


class TelegramApp(InterfaceBot):
    def __init__(self, config, telegram_service, telegram_updater):
        super().__init__(config)
        self.config = config
        self.paused = False
        self.telegram_service = telegram_service
        self.telegram_updater = telegram_updater
        self.dispatcher = self.telegram_updater.dispatcher

        self.add_handlers()

        # Start the Bot
        self.telegram_updater.start_polling()

    def add_handlers(self):
        self.dispatcher.add_handler(CommandHandler("start", self.command_start))
        self.dispatcher.add_handler(CommandHandler("ping", self.command_ping))
        self.dispatcher.add_handler(CommandHandler(["portfolio", "pf"], self.command_portfolio))
        self.dispatcher.add_handler(CommandHandler(["open_orders", "oo"], self.command_open_orders))
        self.dispatcher.add_handler(CommandHandler(["trades_history", "th"], self.command_trades_history))
        self.dispatcher.add_handler(CommandHandler(["profitability", "pb"], self.command_profitability))
        self.dispatcher.add_handler(CommandHandler(["fees", "fs"], self.command_fees))
        self.dispatcher.add_handler(CommandHandler("sell_all", self.command_sell_all))
        self.dispatcher.add_handler(CommandHandler("sell_all_currencies", self.command_sell_all_currencies))
        self.dispatcher.add_handler(CommandHandler("set_risk", self.command_risk))
        self.dispatcher.add_handler(CommandHandler(["market_status", "ms"], self.command_market_status))
        self.dispatcher.add_handler(CommandHandler(["configuration", "cf"], self.command_configuration))
        self.dispatcher.add_handler(CommandHandler(["refresh_real_trader", "rrt"], self.command_real_traders_refresh))
        self.dispatcher.add_handler(CommandHandler(["version", "v"], self.command_version))
        self.dispatcher.add_handler(CommandHandler("stop", self.command_stop))
        self.dispatcher.add_handler(CommandHandler("help", self.command_help))
        self.dispatcher.add_handler(CommandHandler(["pause", "resume"], self.command_pause_resume))
        self.dispatcher.add_handler(MessageHandler(Filters.command, self.command_unknown))

        # log all errors
        self.dispatcher.add_error_handler(self.command_error)

        # TEST : unhandled messages
        self.dispatcher.add_handler(MessageHandler(Filters.text, self.echo))

    @staticmethod
    def command_unknown(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_markdown(f"`Unfortunately, I don't know the command:` "
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
        else:
            update.message.reply_text(UNAUTHORIZED_USER_MESSAGE)

    @staticmethod
    def get_command_param(command_name, update):
        return update.message.text.replace(command_name, "").strip()

    @staticmethod
    def command_start(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_markdown(InterfaceBot.get_command_start(markdown=True))
        else:
            update.message.reply_text(UNAUTHORIZED_USER_MESSAGE)

    @staticmethod
    def command_stop(_, update):
        # TODO add confirmation
        if TelegramApp._is_valid_user(update):
            update.message.reply_markdown("_I'm leaving this world..._")
            InterfaceBot.set_command_stop()

    @staticmethod
    def command_version(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_markdown(f"`{InterfaceBot.get_command_version()}`")

    def command_pause_resume(self, _, update):
        if TelegramApp._is_valid_user(update):
            if self.paused:
                update.message.reply_markdown(f"_Resuming..._{EOL}`I will restart trading when i see opportunities !`")
                self.set_command_resume()
            else:
                update.message.reply_markdown(f"_Pausing..._{EOL}`I'm cancelling my orders.`")
                self.set_command_pause()

    @staticmethod
    def command_ping(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_markdown(f"`{InterfaceBot.get_command_ping()}`")

    @staticmethod
    def command_risk(_, update):
        if TelegramApp._is_valid_user(update):
            try:
                result_risk = InterfaceBot.set_command_risk(float(TelegramApp.get_command_param("/set_risk", update)))
                update.message.reply_markdown(f"`Risk successfully set to {result_risk}.`")
            except Exception:
                update.message.reply_markdown("`Failed to set new risk, please provide a number between 0 and 1.`")

    @staticmethod
    def command_profitability(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_markdown(InterfaceBot.get_command_profitability(markdown=True))

    @staticmethod
    def command_fees(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_markdown(InterfaceBot.get_command_fees(markdown=True))

    @staticmethod
    def command_sell_all_currencies(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_markdown(f"`{InterfaceBot.get_command_sell_all_currencies()}`")

    @staticmethod
    def command_sell_all(_, update):
        if TelegramApp._is_valid_user(update):
            currency = TelegramApp.get_command_param("/sell_all", update)
            if not currency:
                update.message.reply_markdown("`Require a currency in parameter of this command.`")
            else:
                update.message.reply_markdown(f"`{InterfaceBot.get_command_sell_all(currency)}`")

    @staticmethod
    def command_portfolio(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_markdown(InterfaceBot.get_command_portfolio(markdown=True))

    @staticmethod
    def command_open_orders(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_markdown(InterfaceBot.get_command_open_orders(markdown=True))

    @staticmethod
    def command_trades_history(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_markdown(InterfaceBot.get_command_trades_history(markdown=True))

    # refresh current order lists and portfolios and reload tham from exchanges
    @staticmethod
    def command_real_traders_refresh(_, update):
        if TelegramApp._is_valid_user(update):
            result = "Refresh"
            try:
                InterfaceBot.set_command_real_traders_refresh()
                update.message.reply_markdown(f"`{result} successful`")
            except Exception as e:
                update.message.reply_markdown(f"`{result} failure: {e}`")

    # Displays my trades, exchanges, evaluators, strategies and trading
    @staticmethod
    def command_configuration(_, update):
        if TelegramApp._is_valid_user(update):
            try:
                update.message.reply_markdown(InterfaceBot.get_command_configuration(markdown=True))
            except Exception:
                update.message.reply_markdown("`I'm unfortunately currently unable to show you my configuration. "
                                              "Please wait for my initialization to complete.`")

    @staticmethod
    def command_market_status(_, update):
        if TelegramApp._is_valid_user(update):
            try:
                update.message.reply_markdown(InterfaceBot.get_command_market_status(markdown=True))
            except Exception:
                update.message.reply_markdown("`I'm unfortunately currently unable to show you my market evaluations, "
                                              "please retry in a few seconds.`")

    @staticmethod
    def command_error(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_text(f"Failed to perform this command : {update.message.text}")

    @staticmethod
    def echo(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_text(update.message.text)

    @staticmethod
    def enable(config, is_enabled, associated_config=CONFIG_INTERFACES_TELEGRAM):
        InterfaceBot.enable(config, is_enabled, associated_config=associated_config)

    @staticmethod
    def is_enabled(config, associated_config=CONFIG_INTERFACES_TELEGRAM):
        return InterfaceBot.is_enabled(config, associated_config=associated_config)

    @staticmethod
    def _is_valid_user(update, associated_config=CONFIG_INTERFACES_TELEGRAM):
        update_username = update.effective_chat["username"]

        is_valid, white_list = InterfaceBot._is_valid_user(update_username, associated_config=associated_config)

        if white_list and not is_valid:
            LOGGER.error(f"An unauthorized Telegram user is trying to talk to me: username: "
                         f"{update_username}, first_name: {update.effective_chat['first_name']}, "
                         f"text: {update.effective_message['text']}")

        return is_valid
