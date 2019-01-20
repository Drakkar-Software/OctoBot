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
import os

from config import CONFIG_INTERFACES, CONFIG_ENABLED_OPTION, CONFIG_CATEGORY_SERVICES, CONFIG_USERNAMES_WHITELIST, \
    REAL_TRADER_STR, SIMULATOR_TRADER_STR
from interfaces import get_bot, get_reference_market
from interfaces.bots import EOL, NO_CURRENCIES_MESSAGE, NO_TRADER_MESSAGE
from interfaces.trading_util import has_real_and_or_simulated_traders, get_currencies_with_status, get_risk, \
    force_real_traders_refresh, get_trades_history, get_global_portfolio_currencies_amounts, get_global_profitability, \
    set_risk, set_enable_trading, cancel_all_open_orders, get_portfolio_current_value, get_open_orders
from tools.logging.logging_util import get_logger
from tools.pretty_printer import PrettyPrinter
from tools.timestamp_util import convert_timestamp_to_datetime


class InterfaceBot:
    def __init__(self, config):
        self.config = config
        self.paused = False
        self.logger = get_logger(self.__class__.__name__)

    @staticmethod
    def enable(config, is_enabled, associated_config=None):
        if CONFIG_INTERFACES not in config:
            config[CONFIG_INTERFACES] = {}
        if associated_config not in config[CONFIG_INTERFACES]:
            config[CONFIG_INTERFACES][associated_config] = {}
        config[CONFIG_INTERFACES][associated_config][CONFIG_ENABLED_OPTION] = is_enabled

    @staticmethod
    def is_enabled(config, associated_config=None):
        return CONFIG_INTERFACES in config \
               and associated_config in config[CONFIG_INTERFACES] \
               and CONFIG_ENABLED_OPTION in config[CONFIG_INTERFACES][associated_config] \
               and config[CONFIG_INTERFACES][associated_config][CONFIG_ENABLED_OPTION]

    @staticmethod
    def _is_valid_user(user_name, associated_config=None):
        config_interface = get_bot().get_config()[CONFIG_CATEGORY_SERVICES][associated_config]

        white_list = config_interface[CONFIG_USERNAMES_WHITELIST] \
            if CONFIG_USERNAMES_WHITELIST in config_interface else None

        is_valid = not white_list or user_name in white_list or f"@{user_name}" in white_list

        return is_valid, white_list

    @staticmethod
    def get_command_configuration():
        message = f"My configuration:{EOL}{EOL}"

        message += "Traders: " + EOL
        has_real_trader, has_simulated_trader = has_real_and_or_simulated_traders()
        if has_real_trader:
            message += "- Real trader" + EOL
        if has_simulated_trader:
            message += "- Simulated trader" + EOL

        message += f"{EOL}Exchanges:{EOL}"
        for exchange in get_bot().get_exchanges_list().values():
            message += f"- {exchange.get_name()}{EOL}"

        message += f"{EOL}Evaluators:{EOL}"
        first_evaluator = next(iter(get_bot().get_symbols_tasks_manager().values())).get_evaluator()
        evaluators = copy.copy(first_evaluator.get_social_eval_list())
        evaluators += first_evaluator.get_ta_eval_list()
        evaluators += first_evaluator.get_real_time_eval_list()
        for evaluator in evaluators:
            message += f"- {evaluator.get_name()}{EOL}"

        first_symbol_evaluator = next(iter(get_bot().get_symbol_evaluator_list().values()))
        first_exchange = next(iter(get_bot().get_exchanges_list().values()))
        message += f"{EOL}Strategies:{EOL}"
        for strategy in first_symbol_evaluator.get_strategies_eval_list(first_exchange):
            message += f"- {strategy.get_name()}{EOL}"

        message += f"{EOL}Trading mode:{EOL}"
        message += f"- {next(iter(get_bot().get_exchange_trading_modes().values())).get_name()}{EOL}"

        return message

    @staticmethod
    def get_command_market_status():
        message = f"My cryptocurrencies evaluations are: {EOL}{EOL}"
        at_least_one_currency = False
        for currency_pair, currency_info in get_currencies_with_status().items():
            at_least_one_currency = True
            message += f"- {currency_pair}:{EOL}"
            for exchange_name, evaluation in currency_info.items():
                message += f"=> {exchange_name}: {evaluation[0]}{EOL}"
        if not at_least_one_currency:
            message += NO_CURRENCIES_MESSAGE + EOL
        message += f"{EOL}My current risk is: {get_risk()}"

        return message

    @staticmethod
    def get_command_trades_history():
        has_real_trader, has_simulated_trader = has_real_and_or_simulated_traders()
        real_trades_history, simulated_trades_history = get_trades_history()

        trades_history_string = ""
        if has_real_trader:
            trades_history_string += f"{REAL_TRADER_STR}Trades :{EOL}"
            for trades in real_trades_history:
                for trade in trades:
                    trades_history_string += PrettyPrinter.trade_pretty_printer(trade) + EOL

        if has_simulated_trader:
            for trades in simulated_trades_history:
                trades_history_string += EOL + f"{SIMULATOR_TRADER_STR}Trades :{EOL}"
                for trade in trades:
                    trades_history_string += PrettyPrinter.trade_pretty_printer(trade) + EOL

        if not trades_history_string:
            trades_history_string = NO_TRADER_MESSAGE

        return trades_history_string

    @staticmethod
    def get_command_open_orders():
        has_real_trader, has_simulated_trader = has_real_and_or_simulated_traders()
        portfolio_real_open_orders, portfolio_simulated_open_orders = get_open_orders()

        orders_string = ""
        if has_real_trader:
            orders_string += f"{REAL_TRADER_STR}Open orders :{EOL}"
            for orders in portfolio_real_open_orders:
                for order in orders:
                    orders_string += PrettyPrinter.open_order_pretty_printer(order) + EOL

        if has_simulated_trader:
            orders_string += EOL + f"{SIMULATOR_TRADER_STR}Open orders :{EOL}"
            for orders in portfolio_simulated_open_orders:
                for order in orders:
                    orders_string += PrettyPrinter.open_order_pretty_printer(order) + EOL

        if not orders_string:
            orders_string = NO_TRADER_MESSAGE

        return orders_string

    @staticmethod
    def get_command_portfolio():
        has_real_trader, has_simulated_trader, \
         portfolio_real_current_value, portfolio_simulated_current_value = get_portfolio_current_value()
        reference_market = get_reference_market()
        real_global_portfolio, simulated_global_portfolio = get_global_portfolio_currencies_amounts()

        portfolios_string = ""
        if has_real_trader:
            portfolios_string += f"{REAL_TRADER_STR}Portfolio value : " \
                f"{PrettyPrinter.get_min_string_from_number(portfolio_real_current_value)} {reference_market}{EOL}"
            portfolios_string += f"{REAL_TRADER_STR}Portfolio : {EOL}" \
                f"{PrettyPrinter.global_portfolio_pretty_print(real_global_portfolio)}{EOL}{EOL}"

        if has_simulated_trader:
            portfolios_string += f"{SIMULATOR_TRADER_STR}Portfolio value : " \
                f"{PrettyPrinter.get_min_string_from_number(portfolio_simulated_current_value)} {reference_market}{EOL}"
            portfolios_string += f"{SIMULATOR_TRADER_STR}Portfolio : {EOL}" \
                f"{PrettyPrinter.global_portfolio_pretty_print(simulated_global_portfolio)}"

        if not portfolios_string:
            portfolios_string = NO_TRADER_MESSAGE

        return portfolios_string

    @staticmethod
    def get_command_profitability():
        has_real_trader, has_simulated_trader, \
         real_global_profitability, simulated_global_profitability, \
         real_percent_profitability, simulated_percent_profitability, \
         real_no_trade_profitability, simulated_no_trade_profitability, \
         market_average_profitability = get_global_profitability()
        profitability_string = ""
        if has_real_trader:
            real_profitability_pretty = PrettyPrinter.portfolio_profitability_pretty_print(real_global_profitability,
                                                                                           None,
                                                                                           get_reference_market())
            profitability_string = f"{REAL_TRADER_STR}Global profitability : {real_profitability_pretty} " \
                f"({PrettyPrinter.get_min_string_from_number(real_percent_profitability, 2)}%), " \
                f"market: {PrettyPrinter.get_min_string_from_number(market_average_profitability, 2)}%, " \
                f"initial portfolio: {PrettyPrinter.get_min_string_from_number(real_no_trade_profitability, 2)}%{EOL}"
        if has_simulated_trader:
            simulated_profitability_pretty = \
                PrettyPrinter.portfolio_profitability_pretty_print(simulated_global_profitability,
                                                                   None,
                                                                   get_reference_market())
            profitability_string += f"{SIMULATOR_TRADER_STR}Global profitability : {simulated_profitability_pretty} " \
                f"({PrettyPrinter.get_min_string_from_number(simulated_percent_profitability, 2)}%), " \
                f"market: {PrettyPrinter.get_min_string_from_number(market_average_profitability, 2)}%, " \
                f"initial portfolio: {PrettyPrinter.get_min_string_from_number(simulated_no_trade_profitability, 2)}%"
        if not profitability_string:
            profitability_string = NO_TRADER_MESSAGE

        return profitability_string

    @staticmethod
    def get_command_ping():
        return f"I'm alive since {convert_timestamp_to_datetime(get_bot().get_start_time(), '%Y-%m-%d %H:%M:%S')}."

    @staticmethod
    def get_command_start():
        return "Hello, I'm OctoBot, type /help to know my skills."

    @staticmethod
    def set_command_real_traders_refresh():
        return force_real_traders_refresh()

    @staticmethod
    def set_command_risk(new_risk):
        return set_risk(new_risk)

    @staticmethod
    def set_command_stop():
        get_bot().stop_threads()
        return os._exit(0)

    def set_command_pause(self):
        cancel_all_open_orders()
        set_enable_trading(False)
        self.paused = True

    def set_command_resume(self):
        set_enable_trading(True)
        self.paused = False
