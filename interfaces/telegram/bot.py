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

import copy
from tools.logging.logging_util import get_logger
import os

from telegram.ext import CommandHandler, MessageHandler, Filters

from config import *
from interfaces import get_reference_market, get_bot
from interfaces.trading_util import get_portfolio_current_value, get_open_orders, get_trades_history, \
    get_global_portfolio_currencies_amounts, set_risk, get_risk, get_global_profitability, get_currencies_with_status, \
    cancel_all_open_orders, set_enable_trading, has_real_and_or_simulated_traders, force_real_traders_refresh
from tools.pretty_printer import PrettyPrinter
from tools.timestamp_util import convert_timestamp_to_datetime


class TelegramApp:
    EOL = "\n"
    NO_TRADER_MESSAGE = "No trader is activated in my config/config.json file.\n" \
                        "See https://github.com/Drakkar-Software/OctoBot/wiki if you need help with my configuration."
    NO_CURRENCIES_MESSAGE = "No cryptocurrencies are in my config/config.json file.\n" \
                            "See https://github.com/Drakkar-Software/OctoBot/wiki/Configuration#cryptocurrencies " \
                            "if you need help with my cryptocurrencies configuration."
    UNAUTHORIZED_USER_MESSAGE = "Hello, I dont talk to strangers."
    LOGGER = get_logger(__name__)

    def __init__(self, config, telegram_service, telegram_updater):
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
            message = "My OctoBot skills:" + TelegramApp.EOL + TelegramApp.EOL
            message += "/start: Displays my startup message." + TelegramApp.EOL
            message += "/ping: Shows for how long I'm working." + TelegramApp.EOL
            message += "/portfolio or /pf: Displays my current portfolio." + TelegramApp.EOL
            message += "/open_orders or /oo: Displays my current open orders." + TelegramApp.EOL
            message += "/trades_history or /th: Displays my trades history since I started." + TelegramApp.EOL
            message += "/profitability or /pb: Displays the profitability I made since I started." + TelegramApp.EOL
            message += "/market_status or /ms: Displays my understanding of the market and my risk parameter." \
                       + TelegramApp.EOL
            message += "/configuration or /cf: Displays my traders, exchanges, evaluators, strategies and trading " \
                       "mode." + TelegramApp.EOL
            message += "/refresh_real_trader or /rrt: Force OctoBot's real trader data refresh using exchange data. " \
                       "Should normally not be necessary." + TelegramApp.EOL
            message += "/set_risk: Changes my current risk setting into your command's parameter." + TelegramApp.EOL
            message += "/pause or /resume: Pause or resume me." + TelegramApp.EOL
            message += "/stop: Stops me." + TelegramApp.EOL
            message += "/help: Displays this help."
            update.message.reply_text(message)
        else:
            update.message.reply_text(TelegramApp.UNAUTHORIZED_USER_MESSAGE)

    @staticmethod
    def get_command_param(command_name, update):
        return update.message.text.replace(command_name, "")

    @staticmethod
    def command_start(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_text("Hello, I'm OctoBot, type /help to know my skills.")
        else:
            update.message.reply_text(TelegramApp.UNAUTHORIZED_USER_MESSAGE)

    @staticmethod
    def command_stop(_, update):
        # TODO add confirmation
        if TelegramApp._is_valid_user(update):
            update.message.reply_text("I'm leaving this world...")
            get_bot().stop_threads()
            os._exit(0)

    def command_pause_resume(self, _, update):
        if TelegramApp._is_valid_user(update):
            if self.paused:
                update.message.reply_text("Resuming...{0}I will restart trading when i see opportunities !"
                                          .format(TelegramApp.EOL))
                set_enable_trading(True)
                self.paused = False
            else:
                update.message.reply_text("Pausing...{}I'm cancelling my orders.".format(TelegramApp.EOL))
                cancel_all_open_orders()
                set_enable_trading(False)
                self.paused = True

    @staticmethod
    def command_ping(s, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_text("I'm alive since {0}.".format(
                convert_timestamp_to_datetime(get_bot().get_start_time(), '%Y-%m-%d %H:%M:%S')))

    @staticmethod
    def command_risk(_, update):
        if TelegramApp._is_valid_user(update):
            try:
                risk = float(TelegramApp.get_command_param("/set_risk", update))
                set_risk(risk)
                update.message.reply_text("New risk set successfully.")
            except Exception:
                update.message.reply_text("Failed to set new risk, please provide a number between 0 and 1.")

    @staticmethod
    def command_profitability(_, update):
        if TelegramApp._is_valid_user(update):
            has_real_trader, has_simulated_trader, \
                real_global_profitability, simulated_global_profitability, \
                real_percent_profitability, simulated_percent_profitability, \
                real_no_trade_profitability, simulated_no_trade_profitability, \
                market_average_profitability = get_global_profitability()
            profitability_string = ""
            if has_real_trader:
                profitability_string = "{0}Global profitability : {1} ({2}%), market: {3}%, initial portfolio: {4}%{5}"\
                    .format(
                        REAL_TRADER_STR,
                        PrettyPrinter.portfolio_profitability_pretty_print(real_global_profitability,
                                                                           None,
                                                                           get_reference_market()),
                        PrettyPrinter.get_min_string_from_number(real_percent_profitability, 2),
                        PrettyPrinter.get_min_string_from_number(market_average_profitability, 2),
                        PrettyPrinter.get_min_string_from_number(real_no_trade_profitability, 2),
                        TelegramApp.EOL)
            if has_simulated_trader:
                profitability_string += "{0}Global profitability : {1} ({2}%), market: {3}%, initial portfolio: {4}%"\
                    .format(
                        SIMULATOR_TRADER_STR,
                        PrettyPrinter.portfolio_profitability_pretty_print(simulated_global_profitability,
                                                                           None,
                                                                           get_reference_market()),
                        PrettyPrinter.get_min_string_from_number(simulated_percent_profitability, 2),
                        PrettyPrinter.get_min_string_from_number(market_average_profitability, 2),
                        PrettyPrinter.get_min_string_from_number(simulated_no_trade_profitability, 2))
            if not profitability_string:
                profitability_string = TelegramApp.NO_TRADER_MESSAGE
            update.message.reply_text(profitability_string)

    @staticmethod
    def command_portfolio(_, update):
        if TelegramApp._is_valid_user(update):
            has_real_trader, has_simulated_trader, \
                portfolio_real_current_value, portfolio_simulated_current_value = get_portfolio_current_value()
            reference_market = get_reference_market()
            real_global_portfolio, simulated_global_portfolio = get_global_portfolio_currencies_amounts()

            portfolios_string = ""
            if has_real_trader:
                portfolios_string += "{0}Portfolio value : {1} {2}{3}".format(
                    REAL_TRADER_STR,
                    PrettyPrinter.get_min_string_from_number(portfolio_real_current_value),
                    reference_market,
                    TelegramApp.EOL)
                portfolios_string += "{0}Portfolio : {2}{1}{2}{2}".format(
                    REAL_TRADER_STR,
                    PrettyPrinter.global_portfolio_pretty_print(real_global_portfolio),
                    TelegramApp.EOL)

            if has_simulated_trader:
                portfolios_string += "{0}Portfolio value : {1} {2}{3}".format(
                    SIMULATOR_TRADER_STR,
                    PrettyPrinter.get_min_string_from_number(portfolio_simulated_current_value),
                    reference_market,
                    TelegramApp.EOL)
                portfolios_string += "{0}Portfolio : {2}{1}".format(
                    SIMULATOR_TRADER_STR,
                    PrettyPrinter.global_portfolio_pretty_print(simulated_global_portfolio),
                    TelegramApp.EOL)

            if not portfolios_string:
                portfolios_string = TelegramApp.NO_TRADER_MESSAGE
            update.message.reply_text(portfolios_string)

    @staticmethod
    def command_open_orders(_, update):
        if TelegramApp._is_valid_user(update):
            has_real_trader, has_simulated_trader = has_real_and_or_simulated_traders()
            portfolio_real_open_orders, portfolio_simulated_open_orders = get_open_orders()

            orders_string = ""
            if has_real_trader:
                orders_string += "{0}Open orders :{1}".format(REAL_TRADER_STR, TelegramApp.EOL)
                for orders in portfolio_real_open_orders:
                    for order in orders:
                        orders_string += PrettyPrinter.open_order_pretty_printer(order) + TelegramApp.EOL

            if has_simulated_trader:
                orders_string += TelegramApp.EOL + "{0}Open orders :{1}".format(SIMULATOR_TRADER_STR,
                                                                                TelegramApp.EOL)
                for orders in portfolio_simulated_open_orders:
                    for order in orders:
                        orders_string += PrettyPrinter.open_order_pretty_printer(order) + TelegramApp.EOL

            if not orders_string:
                orders_string = TelegramApp.NO_TRADER_MESSAGE

            update.message.reply_text(orders_string)

    @staticmethod
    def command_trades_history(_, update):
        if TelegramApp._is_valid_user(update):
            has_real_trader, has_simulated_trader = has_real_and_or_simulated_traders()
            real_trades_history, simulated_trades_history = get_trades_history()

            trades_history_string = ""
            if has_real_trader:
                trades_history_string += "{0}Trades :{1}".format(REAL_TRADER_STR, TelegramApp.EOL)
                for trades in real_trades_history:
                    for trade in trades:
                        trades_history_string += PrettyPrinter.trade_pretty_printer(trade) + TelegramApp.EOL

            if has_simulated_trader:
                for trades in simulated_trades_history:
                    trades_history_string += TelegramApp.EOL + "{0}Trades :{1}".format(SIMULATOR_TRADER_STR,
                                                                                       TelegramApp.EOL)
                    for trade in trades:
                        trades_history_string += PrettyPrinter.trade_pretty_printer(trade) + TelegramApp.EOL

            if not trades_history_string:
                trades_history_string = TelegramApp.NO_TRADER_MESSAGE

            update.message.reply_text(trades_history_string)

    # refresh current order lists and portfolios and reload tham from exchanges
    @staticmethod
    def command_real_traders_refresh(_, update):
        if TelegramApp._is_valid_user(update):
            result = "Refresh"
            try:
                force_real_traders_refresh()
                update.message.reply_text(result + " successful")
            except Exception as e:
                update.message.reply_text(f"{result} failure: {e}")

    # Displays my trades, exchanges, evaluators, strategies and trading
    @staticmethod
    def command_configuration(_, update):
        if TelegramApp._is_valid_user(update):
            try:
                message = "My configuration:{0}{0}".format(TelegramApp.EOL)

                message += "Traders: " + TelegramApp.EOL
                has_real_trader, has_simulated_trader = has_real_and_or_simulated_traders()
                if has_real_trader:
                    message += "- Real trader" + TelegramApp.EOL
                if has_simulated_trader:
                    message += "- Simulated trader" + TelegramApp.EOL

                message += "{0}Exchanges:{0}".format(TelegramApp.EOL)
                for exchange in get_bot().get_exchanges_list().values():
                    message += "- {0}{1}".format(exchange.get_name(), TelegramApp.EOL)

                message += "{0}Evaluators:{0}".format(TelegramApp.EOL)
                first_evaluator = next(iter(get_bot().get_symbols_tasks_manager().values())).get_evaluator()
                evaluators = copy.copy(first_evaluator.get_social_eval_list())
                evaluators += first_evaluator.get_ta_eval_list()
                evaluators += first_evaluator.get_real_time_eval_list()
                for evaluator in evaluators:
                    message += "- {0}{1}".format(evaluator.get_name(), TelegramApp.EOL)

                first_symbol_evaluator = next(iter(get_bot().get_symbol_evaluator_list().values()))
                first_exchange = next(iter(get_bot().get_exchanges_list().values()))
                message += "{0}Strategies:{0}".format(TelegramApp.EOL)
                for strategy in first_symbol_evaluator.get_strategies_eval_list(first_exchange):
                    message += "- {0}{1}".format(strategy.get_name(), TelegramApp.EOL)

                message += "{0}Trading mode:{0}".format(TelegramApp.EOL)
                message += "- {0}{1}".format(next(iter(get_bot().get_exchange_trading_modes().values())).get_name(),
                                             TelegramApp.EOL)
                update.message.reply_text(message)
            except Exception:
                update.message.reply_text("I'm unfortunately currently unable to show you my configuration. "
                                          "Please wait for my initialization to complete.")

    @staticmethod
    def command_market_status(_, update):
        if TelegramApp._is_valid_user(update):
            try:
                message = f"My cryptocurrencies evaluations are: {TelegramApp.EOL}{TelegramApp.EOL}"
                at_least_one_currency = False
                for currency_pair, currency_info in get_currencies_with_status().items():
                    at_least_one_currency = True
                    message += f"- {currency_pair}:{TelegramApp.EOL}"
                    for exchange_name, evaluation in currency_info.items():
                        message += f"=> {exchange_name}: {evaluation[0]}{TelegramApp.EOL}"
                if not at_least_one_currency:
                    message += TelegramApp.NO_CURRENCIES_MESSAGE + TelegramApp.EOL
                message += f"{TelegramApp.EOL}My current risk is: {get_risk()}"
                update.message.reply_text(message)
            except Exception:
                update.message.reply_text("I'm unfortunately currently unable to show you my market evaluations, " +
                                          "please retry in a few seconds.")

    @staticmethod
    def command_error(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_text("Failed to perform this command : {0}".format(update.message.text))

    @staticmethod
    def echo(_, update):
        if TelegramApp._is_valid_user(update):
            update.message.reply_text(update.message.text)

    @staticmethod
    def enable(config, is_enabled):
        if CONFIG_INTERFACES not in config:
            config[CONFIG_INTERFACES] = {}
        if CONFIG_INTERFACES_TELEGRAM not in config[CONFIG_INTERFACES]:
            config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM] = {}
        config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM][CONFIG_ENABLED_OPTION] = is_enabled

    @staticmethod
    def is_enabled(config):
        return CONFIG_INTERFACES in config \
               and CONFIG_INTERFACES_TELEGRAM in config[CONFIG_INTERFACES] \
               and CONFIG_ENABLED_OPTION in config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM] \
               and config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM][CONFIG_ENABLED_OPTION]

    @staticmethod
    def _is_valid_user(update):
        update_username = update.effective_chat["username"]
        config_telegram = get_bot().get_config()[CONFIG_CATEGORY_SERVICES][CONFIG_INTERFACES_TELEGRAM]
        telegram_usernames_white_list = config_telegram[CONFIG_USERNAMES_WHITELIST] \
            if CONFIG_USERNAMES_WHITELIST in config_telegram else None

        is_valid = not telegram_usernames_white_list \
            or update_username in telegram_usernames_white_list \
            or f"@{update_username}" in telegram_usernames_white_list

        if telegram_usernames_white_list and not is_valid:
            TelegramApp.LOGGER.error(f"An unauthorized Telegram user is trying to talk to me: username: "
                                     f"{update_username}, first_name: {update.effective_chat['first_name']}, "
                                     f"text: {update.effective_message['text']}")

        return is_valid
