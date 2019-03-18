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
    REAL_TRADER_STR, SIMULATOR_TRADER_STR, PROJECT_NAME, LONG_VERSION, PAID_FEES_STR
from interfaces import get_bot, get_reference_market
from interfaces.bots import EOL, NO_CURRENCIES_MESSAGE, NO_TRADER_MESSAGE
from interfaces.trading_util import has_real_and_or_simulated_traders, get_currencies_with_status, get_risk, \
    force_real_traders_refresh, get_trades_history, get_global_portfolio_currencies_amounts, get_global_profitability, \
    set_risk, set_enable_trading, cancel_all_open_orders, get_portfolio_current_value, get_open_orders, \
    get_total_paid_fees, sell_all_currencies, sell_all
from tools.logging.logging_util import get_logger
from tools.pretty_printer import PrettyPrinter
from tools.timestamp_util import convert_timestamp_to_datetime


class InterfaceBot:

    def __init__(self, config):
        self.config = config
        self.paused = False

    @classmethod
    def get_logger(cls):
        return get_logger(cls.__name__)

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
    def get_command_configuration(markdown=False):
        _, b, c = PrettyPrinter.get_markets(markdown)
        message = f"{b}My configuration:{b}{EOL}{EOL}"

        message += f"{b}Traders: {b}{EOL}"
        has_real_trader, has_simulated_trader = has_real_and_or_simulated_traders()
        if has_real_trader:
            message += f"{c}- Real trader{c}{EOL}"
        if has_simulated_trader:
            message += f"{c}- Simulated trader{c}{EOL}"

        message += f"{EOL}{b}Exchanges:{b}{EOL}"
        for exchange in get_bot().get_exchanges_list().values():
            message += f"{c}- {exchange.get_name()}{c}{EOL}"

        message += f"{EOL}{b}Evaluators:{b}{EOL}"
        first_evaluator = next(iter(get_bot().get_symbols_tasks_manager().values())).get_evaluator()
        evaluators = copy.copy(first_evaluator.get_social_eval_list())
        evaluators += first_evaluator.get_ta_eval_list()
        evaluators += first_evaluator.get_real_time_eval_list()
        for evaluator in evaluators:
            message += f"{c}- {evaluator.get_name()}{c}{EOL}"

        first_symbol_evaluator = next(iter(get_bot().get_symbol_evaluator_list().values()))
        first_exchange = next(iter(get_bot().get_exchanges_list().values()))
        message += f"{EOL}{b}Strategies:{b}{EOL}"
        for strategy in first_symbol_evaluator.get_strategies_eval_list(first_exchange):
            message += f"{c}- {strategy.get_name()}{c}{EOL}"

        message += f"{EOL}{b}Trading mode:{b}{EOL}"
        message += f"{c}- {next(iter(get_bot().get_exchange_trading_modes().values())).get_name()}{c}"

        return message

    @staticmethod
    def get_command_market_status(markdown=False):
        _, b, c = PrettyPrinter.get_markets(markdown)
        message = f"{b}My cryptocurrencies evaluations are:{b} {EOL}{EOL}"
        at_least_one_currency = False
        for currency_pair, currency_info in get_currencies_with_status().items():
            at_least_one_currency = True
            message += f"{c}{currency_pair}:{c}{EOL}"
            for exchange_name, evaluation in currency_info.items():
                message += f"{c}- {exchange_name}: {evaluation[0]}{c}{EOL}"
        if not at_least_one_currency:
            message += f"{c}{NO_CURRENCIES_MESSAGE}{c}{EOL}"
        message += f"{EOL}{c}My current risk is: {get_risk()}{c}"

        return message

    @staticmethod
    def _print_trades(trades_history, trader_str, markdown=False):
        _, b, c = PrettyPrinter.get_markets(markdown)
        trades_history_string = f"{b}{trader_str}{b}{c}Trades :{EOL}{c}"
        if trades_history:
            for trade in trades_history:
                trades_history_string += f"{PrettyPrinter.trade_pretty_printer(trade, markdown=markdown)}{EOL}"
        else:
            trades_history_string += f"{c}No trade yet.{c}"
        return trades_history_string

    @staticmethod
    def get_command_trades_history(markdown=False):
        has_real_trader, has_simulated_trader = has_real_and_or_simulated_traders()
        real_trades_history, simulated_trades_history = get_trades_history()

        trades_history_string = ""
        if has_real_trader:
            trades_history_string += InterfaceBot._print_trades(real_trades_history, REAL_TRADER_STR, markdown)

        if has_simulated_trader:
            trades_history_string += \
                f"{EOL}{InterfaceBot._print_trades(simulated_trades_history, SIMULATOR_TRADER_STR, markdown)}"

        if not trades_history_string:
            trades_history_string = NO_TRADER_MESSAGE

        return trades_history_string

    @staticmethod
    def _print_open_orders(open_orders, trader_str, markdown=False):
        _, b, c = PrettyPrinter.get_markets(markdown)
        orders_string = f"{b}{trader_str}{b}{c}Open orders :{c}{EOL}"
        if open_orders:
            for order in open_orders:
                orders_string += PrettyPrinter.open_order_pretty_printer(order, markdown=markdown) + EOL
        else:
            orders_string += f"{c}No open order yet.{c}"
        return orders_string

    @staticmethod
    def get_command_open_orders(markdown=False):
        _, b, c = PrettyPrinter.get_markets(markdown)
        has_real_trader, has_simulated_trader = has_real_and_or_simulated_traders()
        portfolio_real_open_orders, portfolio_simulated_open_orders = get_open_orders()

        orders_string = ""
        if has_real_trader:
            orders_string += InterfaceBot._print_open_orders(portfolio_real_open_orders, REAL_TRADER_STR, markdown)

        if has_simulated_trader:
            orders_string += f"{EOL}" \
                f"{InterfaceBot._print_open_orders(portfolio_simulated_open_orders, SIMULATOR_TRADER_STR, markdown)}"

        if not orders_string:
            orders_string = NO_TRADER_MESSAGE

        return orders_string

    @staticmethod
    def get_command_fees(markdown=False):
        _, b, _ = PrettyPrinter.get_markets(markdown)
        real_trader_fees, simulated_trader_fees = get_total_paid_fees()
        result_str = ""
        if real_trader_fees is not None:
            result_str = f"{b}{REAL_TRADER_STR}{b}{PAID_FEES_STR}: " \
                f"{PrettyPrinter.pretty_print_dict(real_trader_fees, markdown=markdown)}"
        if simulated_trader_fees is not None:
            result_str = f"{result_str}\n{b}{SIMULATOR_TRADER_STR}{b}{PAID_FEES_STR}: " \
                f"{PrettyPrinter.pretty_print_dict(simulated_trader_fees, markdown=markdown)}"
        if not result_str:
            result_str = NO_TRADER_MESSAGE
        return result_str

    @staticmethod
    def get_command_sell_all_currencies():
        try:
            cancel_all_open_orders()
            nb_created_orders = len(sell_all_currencies())
            if nb_created_orders:
                return f"Currencies sold in {nb_created_orders} order{'s' if nb_created_orders > 1 else ''}."
            else:
                return "Nothing to sell."
        except Exception as e:
            return f"An error occurred: {e.__class__.__name__}"

    @staticmethod
    def get_command_sell_all(currency):
        try:
            cancel_all_open_orders(currency)
            nb_created_orders = len(sell_all(currency))
            if nb_created_orders:
                return f"{currency} sold in {nb_created_orders} order{'s' if nb_created_orders > 1 else ''}."
            else:
                return f"Nothing to sell for {currency}."
        except Exception as e:
            return f"An error occurred: {e.__class__.__name__}"

    @staticmethod
    def _print_portfolio(current_val, ref_market, portfolio, trader_str, markdown=False):
        _, b, c = PrettyPrinter.get_markets(markdown)
        portfolios_string = f"{b}{trader_str}{b}Portfolio value : " \
            f"{b}{PrettyPrinter.get_min_string_from_number(current_val)} {ref_market}{b}" \
            f"{EOL}"
        portfolio_str = PrettyPrinter.global_portfolio_pretty_print(portfolio, markdown=markdown)
        if not portfolio_str:
            portfolio_str = "Nothing there."
        portfolios_string += f"{b}{trader_str}{b}Portfolio : {EOL}{c}{portfolio_str}{c}"
        return portfolios_string

    @staticmethod
    def get_command_portfolio(markdown=False):
        _, b, c = PrettyPrinter.get_markets(markdown)
        has_real_trader, has_simulated_trader, \
          portfolio_real_current_value, portfolio_simulated_current_value = get_portfolio_current_value()
        reference_market = get_reference_market()
        real_global_portfolio, simulated_global_portfolio = get_global_portfolio_currencies_amounts()

        portfolios_string = ""
        if has_real_trader:
            portfolios_string += InterfaceBot._print_portfolio(portfolio_real_current_value, reference_market,
                                                               real_global_portfolio, REAL_TRADER_STR, markdown)

        if has_simulated_trader:
            portfolio_str = InterfaceBot._print_portfolio(portfolio_simulated_current_value, reference_market,
                                                          simulated_global_portfolio, SIMULATOR_TRADER_STR, markdown)
            portfolios_string += f"{EOL}{portfolio_str}"

        if not portfolios_string:
            portfolios_string = NO_TRADER_MESSAGE

        return portfolios_string

    @staticmethod
    def get_command_profitability(markdown=False):
        _, b, c = PrettyPrinter.get_markets(markdown)
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
            profitability_string = \
                f"{b}{REAL_TRADER_STR}{b}Global profitability : {c}{real_profitability_pretty}" \
                f"({PrettyPrinter.get_min_string_from_number(real_percent_profitability, 2)}%){c}, market: {c}" \
                f"{PrettyPrinter.get_min_string_from_number(market_average_profitability, 2)}%{c}, initial portfolio:" \
                f" {c}{PrettyPrinter.get_min_string_from_number(real_no_trade_profitability, 2)}%{c}{EOL}"
        if has_simulated_trader:
            simulated_profitability_pretty = \
                PrettyPrinter.portfolio_profitability_pretty_print(simulated_global_profitability,
                                                                   None,
                                                                   get_reference_market())
            profitability_string += \
                f"{b}{SIMULATOR_TRADER_STR}{b}Global profitability : {c}{simulated_profitability_pretty}" \
                f"({PrettyPrinter.get_min_string_from_number(simulated_percent_profitability, 2)}%){c}, " \
                f"market: {c}{PrettyPrinter.get_min_string_from_number(market_average_profitability, 2)}%{c}, " \
                f"initial portfolio: {c}" \
                f"{PrettyPrinter.get_min_string_from_number(simulated_no_trade_profitability, 2)}%{c}"
        if not profitability_string:
            profitability_string = NO_TRADER_MESSAGE

        return profitability_string

    @staticmethod
    def get_command_ping():
        return f"I'm alive since {convert_timestamp_to_datetime(get_bot().start_time, '%Y-%m-%d %H:%M:%S')}."

    @staticmethod
    def get_command_version():
        return f"{PROJECT_NAME} {LONG_VERSION}"

    @staticmethod
    def get_command_start(markdown=False):
        if markdown:
            return "Hello, I'm [OctoBot](https://github.com/Drakkar-Software/OctoBot), type /help to know my skills."
        else:
            return "Hello, I'm OctoBot, type /help to know my skills."

    @staticmethod
    def set_command_real_traders_refresh():
        return force_real_traders_refresh()

    @staticmethod
    def set_command_risk(new_risk):
        return set_risk(new_risk)

    @staticmethod
    def set_command_stop():
        get_bot().stop()
        return os._exit(0)

    def set_command_pause(self):
        cancel_all_open_orders()
        set_enable_trading(False)
        self.paused = True

    def set_command_resume(self):
        set_enable_trading(True)
        self.paused = False

    @staticmethod
    def _split_messages_if_too_long(message, max_length, preferred_separator):
        if len(message) >= max_length:
            # split message using preferred_separator as separator
            messages_list = []
            first_part = message[:max_length]
            end_index = first_part.rfind(preferred_separator)
            if end_index != -1:
                messages_list.append(message[:end_index])
            else:
                messages_list.append(message[:max_length])
                end_index = len(first_part)-1

            if end_index < len(message) - 1:
                remaining = message[end_index+1:]
                return messages_list + InterfaceBot._split_messages_if_too_long(remaining, max_length,
                                                                                preferred_separator)
            else:
                return messages_list
        else:
            return [message]
