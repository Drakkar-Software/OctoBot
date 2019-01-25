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
            update.message.reply_text("Unfortunately, I don't know the command: {0}".
                                      format(update.effective_message.text))

    @staticmethod
    def command_help(_, update):
        if TelegramApp._is_valid_user(update):
            message = "My OctoBot skills:" + EOL + EOL
            message += "/start: Displays my startup message." + EOL
            message += "/ping: Shows for how long I'm working." + EOL
            message += "/portfolio or /pf: Displays my current portfolio." + EOL
            message += "/open_orders or /oo: Displays my current open orders." + EOL
            message += "/trades_history or /th: Displays my trades history since I started." + EOL
            message += "/profitability or /pb: Displays the profitability I made since I started." + EOL
            message += "/market_status or /ms: Displays my understanding of the market and my risk parameter." + EOL
            message += "/configuration or /cf: Displays my traders, exchanges, evaluators, strategies and trading " \
                       "mode." + EOL
            message += "/refresh_real_trader or /rrt: Force OctoBot's real trader data refresh using exchange data. " \
                       "Should normally not be necessary." + EOL
            message += "/set_risk: Changes my current risk setting into your command's parameter." + EOL
            message += "/pause or /resume: Pause or resume me." + EOL
            message += "/version or /v: Displays my current software version." + EOL
            message += "/stop: Stops me." + EOL
            message += "/help: Displays this help."
            update.message.reply_text(message)
        else:
            update.message.reply_text(UNAUTHORIZED_USER_MESSAGE)

    @staticmethod
    def get_command_param(command_name, update):
        return update.message.text.replace(command_name, "")

    @staticmethod
    def command_start(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_text(InterfaceBot.get_command_start())
        else:
            update.message.reply_text(UNAUTHORIZED_USER_MESSAGE)

    @staticmethod
    def command_stop(_, update):
        # TODO add confirmation
        if TelegramApp._is_valid_user(update):
            update.message.reply_text("I'm leaving this world...")
            InterfaceBot.set_command_stop()

    @staticmethod
    def command_version(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_text(InterfaceBot.get_command_version())

    def command_pause_resume(self, _, update):
        if TelegramApp._is_valid_user(update):
            if self.paused:
                update.message.reply_text(f"Resuming...{EOL}I will restart trading when i see opportunities !")
                self.set_command_resume()
            else:
                update.message.reply_text(f"Pausing...{EOL}I'm cancelling my orders.")
                self.set_command_pause()

    @staticmethod
    def command_ping(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_text(InterfaceBot.get_command_ping())

    @staticmethod
    def command_risk(_, update):
        if TelegramApp._is_valid_user(update):
            try:
                InterfaceBot.set_command_risk(float(TelegramApp.get_command_param("/set_risk", update)))
                update.message.reply_text("New risk set successfully.")
            except Exception:
                update.message.reply_text("Failed to set new risk, please provide a number between 0 and 1.")

    @staticmethod
    def command_profitability(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_text(InterfaceBot.get_command_profitability())

    @staticmethod
    def command_portfolio(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_text(InterfaceBot.get_command_portfolio())

    @staticmethod
    def command_open_orders(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_text(InterfaceBot.get_command_open_orders())

    @staticmethod
    def command_trades_history(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_text(InterfaceBot.get_command_trades_history())

    # refresh current order lists and portfolios and reload tham from exchanges
    @staticmethod
    def command_real_traders_refresh(_, update):
        if TelegramApp._is_valid_user(update):
            result = "Refresh"
            try:
                InterfaceBot.set_command_real_traders_refresh()
                update.message.reply_text(result + " successful")
            except Exception as e:
                update.message.reply_text(f"{result} failure: {e}")

    # Displays my trades, exchanges, evaluators, strategies and trading
    @staticmethod
    def command_configuration(_, update):
        if TelegramApp._is_valid_user(update):
            try:
                update.message.reply_text(InterfaceBot.get_command_configuration())
            except Exception:
                update.message.reply_text("I'm unfortunately currently unable to show you my configuration. "
                                          "Please wait for my initialization to complete.")

    @staticmethod
    def command_market_status(_, update):
        if TelegramApp._is_valid_user(update):
            try:
                update.message.reply_text(InterfaceBot.get_command_market_status())
            except Exception:
                update.message.reply_text("I'm unfortunately currently unable to show you my market evaluations, "
                                          "please retry in a few seconds.")

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
