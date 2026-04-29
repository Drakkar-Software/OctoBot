#  Drakkar-Software OctoBot-Services
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
import abc

import octobot_commons.constants as common_constants
import octobot_commons.pretty_printer as pretty_printer
import octobot_commons.timestamp_util as timestamp_util
import octobot_commons.dict_util as dict_util

import octobot_trading.api as trading_api
import octobot_trading.constants as trading_constants

import octobot_services.interfaces as interfaces
import octobot_services.constants as constants
import octobot_commons.constants as commons_constants


class AbstractBotInterface(interfaces.AbstractInterface):
    __metaclass__ = abc.ABCMeta

    @staticmethod
    def enable(config, is_enabled, associated_config=None):
        if constants.CONFIG_INTERFACES not in config:
            config[constants.CONFIG_INTERFACES] = {}
        if associated_config not in config[constants.CONFIG_INTERFACES]:
            config[constants.CONFIG_INTERFACES][associated_config] = {}
        config[constants.CONFIG_INTERFACES][associated_config][common_constants.CONFIG_ENABLED_OPTION] = is_enabled

    @staticmethod
    def is_enabled(config, associated_config=None):
        return constants.CONFIG_INTERFACES in config \
               and associated_config in config[constants.CONFIG_INTERFACES] \
               and common_constants.CONFIG_ENABLED_OPTION in config[constants.CONFIG_INTERFACES][associated_config] \
               and config[constants.CONFIG_INTERFACES][associated_config][common_constants.CONFIG_ENABLED_OPTION]

    @staticmethod
    def _is_valid_user(user_name, associated_config=None):
        config_interface = interfaces.get_global_config()[constants.CONFIG_CATEGORY_SERVICES][associated_config]

        white_list = config_interface[constants.CONFIG_USERNAMES_WHITELIST] \
            if constants.CONFIG_USERNAMES_WHITELIST in config_interface else None

        is_valid = not white_list or user_name in white_list or f"@{user_name}" in white_list

        return is_valid, white_list

    @staticmethod
    def get_command_configuration(markdown=False):
        _, bold, code = pretty_printer.get_markers(markdown)
        message = f"{bold}My configuration:{bold}{interfaces.EOL}{interfaces.EOL}"

        message += f"{bold}Traders: {bold}{interfaces.EOL}"
        if interfaces.has_trader():
            has_real_trader, has_simulated_trader = interfaces.has_real_and_or_simulated_traders()
            if has_real_trader:
                message += f"{code}- Real trader{code}{interfaces.EOL}"
            if has_simulated_trader:
                message += f"{code}- Simulated trader{code}{interfaces.EOL}"
        else:
            message += f"{code}- No activated trader{code}{interfaces.EOL}"

        message += f"{interfaces.EOL}{bold}Exchanges:{bold}{interfaces.EOL}"
        for exchange_name in trading_api.get_exchange_names():
            message += f"{code}- {exchange_name.capitalize()}{code}{interfaces.EOL}"

        try:
            import octobot_evaluators.api as evaluators_api
            import octobot_evaluators.enums as evaluators_enums
            tentacle_setup_config = interfaces.get_bot_api().get_tentacles_setup_config()
            message += f"{interfaces.EOL}{bold}Evaluators:{bold}{interfaces.EOL}"
            evaluators = evaluators_api.get_evaluator_classes_from_type(
                evaluators_enums.EvaluatorMatrixTypes.TA.value, tentacle_setup_config)
            evaluators += evaluators_api.get_evaluator_classes_from_type(
                evaluators_enums.EvaluatorMatrixTypes.SOCIAL.value, tentacle_setup_config)
            evaluators += evaluators_api.get_evaluator_classes_from_type(
                evaluators_enums.EvaluatorMatrixTypes.REAL_TIME.value, tentacle_setup_config)
            for evaluator in evaluators:
                message += f"{code}- {evaluator.get_name()}{code}{interfaces.EOL}"

            message += f"{interfaces.EOL}{bold}Strategies:{bold}{interfaces.EOL}"
            for strategy in evaluators_api.get_evaluator_classes_from_type(
                    evaluators_enums.EvaluatorMatrixTypes.STRATEGIES.value, tentacle_setup_config):
                message += f"{code}- {strategy.get_name()}{code}{interfaces.EOL}"
        except ImportError:
            message += f"{interfaces.EOL}{bold}Impossible to retrieve evaluation configuration: requires OctoBot-Evaluators " \
                       f"package installed{bold}{interfaces.EOL}"
        try:
            trading_mode = interfaces.get_bot_api().get_trading_mode()
        except IndexError:
            # no activated trader
            trading_mode = None
        if trading_mode:
            message += f"{interfaces.EOL}{bold}Trading mode:{bold}{interfaces.EOL}"
            message += f"{code}- {trading_mode.get_name()}{code}"

        return message

    @staticmethod
    def get_command_market_status(markdown=False):
        _, bold, code = pretty_printer.get_markers(markdown)
        message = f"{bold}My cryptocurrencies evaluations are:{bold} {interfaces.EOL}{interfaces.EOL}"
        at_least_one_currency = False
        for currency_pair, currency_info in interfaces.get_currencies_with_status().items():
            at_least_one_currency = True
            message += f"{code}{currency_pair}:{code}{interfaces.EOL}"
            for _, evaluation in currency_info.items():
                message += f"{code}- {evaluation[2].capitalize()}: {evaluation[0]}{code}{interfaces.EOL}"
        if not at_least_one_currency:
            message += f"{code}{interfaces.NO_CURRENCIES_MESSAGE}{code}{interfaces.EOL}"
        risk = interfaces.get_risk()
        if risk:
            message += f"{interfaces.EOL}{code}My current risk is: {interfaces.get_risk()}{code}"
        return message

    @staticmethod
    def _print_trades(trades_history, trader_str, markdown=False):
        _, bold, code = pretty_printer.get_markers(markdown)
        trades_history_string = f"{bold}{trader_str}{bold}{code}Trades :{interfaces.EOL}{code}"
        if trades_history:
            for trade in trades_history:
                exchange_name = trading_api.get_trade_exchange_name(trade)
                trades_history_string += \
                    f"{pretty_printer.trade_pretty_printer(exchange_name, trade, markdown=markdown)}{interfaces.EOL}"
        else:
            trades_history_string += f"{code}No trade yet.{code}"
        return trades_history_string

    @staticmethod
    def get_command_trades_history(markdown=False):
        has_real_trader, has_simulated_trader = interfaces.has_real_and_or_simulated_traders()
        real_trades_history, simulated_trades_history = interfaces.get_trades_history()

        trades_history_string = ""
        if has_real_trader:
            trades_history_string += AbstractBotInterface._print_trades(real_trades_history,
                                                                        trading_constants.REAL_TRADER_STR,
                                                                        markdown)

        if has_simulated_trader:
            trades_history_string += f"{interfaces.EOL}" \
                                     f"{AbstractBotInterface._print_trades(simulated_trades_history, trading_constants.SIMULATOR_TRADER_STR, markdown)}"

        if not trades_history_string:
            trades_history_string = interfaces.NO_TRADER_MESSAGE

        return trades_history_string

    @staticmethod
    def _print_open_orders(open_orders, trader_str, markdown=False):
        _, bold, code = pretty_printer.get_markers(markdown)
        orders_string = f"{bold}{trader_str}{bold}{code}Open orders :{code}{interfaces.EOL}"
        if open_orders:
            for order in open_orders:
                exchange_name = trading_api.get_order_exchange_name(order).capitalize()
                orders_string += pretty_printer.open_order_pretty_printer(exchange_name,
                                                                          trading_api.order_to_dict(order),
                                                                          markdown=markdown) + interfaces.EOL
        else:
            orders_string += f"{code}No open order yet.{code}"
        return orders_string

    @staticmethod
    def get_command_open_orders(markdown=False):
        has_real_trader, has_simulated_trader = interfaces.has_real_and_or_simulated_traders()
        portfolio_real_open_orders, portfolio_simulated_open_orders = interfaces.get_all_open_orders()

        orders_string = ""
        if has_real_trader:
            orders_string += AbstractBotInterface._print_open_orders(portfolio_real_open_orders,
                                                                     trading_constants.REAL_TRADER_STR,
                                                                     markdown)

        if has_simulated_trader:
            message = AbstractBotInterface._print_open_orders(portfolio_simulated_open_orders,
                                                              trading_constants.SIMULATOR_TRADER_STR,
                                                              markdown)
            orders_string += f"{interfaces.EOL}{message}"

        if not orders_string:
            orders_string = interfaces.NO_TRADER_MESSAGE

        return orders_string

    @staticmethod
    def get_command_fees(markdown=False):
        _, bold, _ = pretty_printer.get_markers(markdown)
        real_trader_fees, simulated_trader_fees = interfaces.get_total_paid_fees()
        result_str = ""
        if real_trader_fees is not None:
            result_str = f"{bold}{trading_constants.REAL_TRADER_STR}{bold}{constants.PAID_FEES_STR}: " \
                         f"{pretty_printer.pretty_print_dict(real_trader_fees, markdown=markdown)}"
        if simulated_trader_fees is not None:
            result_str = f"{result_str}\n{bold}{trading_constants.SIMULATOR_TRADER_STR}{bold}" \
                         f"{constants.PAID_FEES_STR}: " \
                         f"{pretty_printer.pretty_print_dict(simulated_trader_fees, markdown=markdown)}"
        if not result_str:
            result_str = interfaces.NO_TRADER_MESSAGE
        return result_str

    @staticmethod
    async def get_command_sell_all_currencies():
        try:
            await interfaces.async_cancel_all_open_orders()
            nb_created_orders = len(await interfaces.async_sell_all_currencies())
            if nb_created_orders:
                return f"Currencies sold in {nb_created_orders} order{'s' if nb_created_orders > 1 else ''}."
            else:
                return "Nothing to sell."
        except Exception as e:
            return f"An error occurred: {e.__class__.__name__}"

    @staticmethod
    async def get_command_sell_all(currency):
        try:
            await interfaces.async_cancel_all_open_orders(currency)
            nb_created_orders = len(await interfaces.async_sell_all(currency))
            if nb_created_orders:
                return f"{currency} sold in {nb_created_orders} order{'s' if nb_created_orders > 1 else ''}."
            else:
                return f"Nothing to sell for {currency}."
        except Exception as e:
            return f"An error occurred: {e.__class__.__name__}"

    @staticmethod
    def _print_portfolio(
        current_val, ref_market, portfolio, currency_values, trader_str, markdown=False
    ):
        _, bold, code = pretty_printer.get_markers(markdown)
        portfolios_string = (
            f"{bold}{trader_str}{bold}Portfolio value : "
            f"{bold}{pretty_printer.get_min_string_from_number(current_val)} {ref_market}{bold}"
            f"{interfaces.EOL}"
        )
        portfolio_str = pretty_printer.global_portfolio_pretty_print(
            global_portfolio=portfolio, currency_values=currency_values, 
            ref_market_name=ref_market, markdown=markdown)

        if not portfolio_str:
            portfolio_str = "Nothing there."
        portfolios_string += f"{interfaces.EOL}{code}{portfolio_str}{code}"
        return portfolios_string

    @staticmethod
    def get_command_portfolio(markdown=False):
        has_real_trader, has_simulated_trader, \
        portfolio_real_current_value, portfolio_simulated_current_value = interfaces.get_portfolio_current_value()
        reference_market = interfaces.get_reference_market()
        real_global_portfolio, simulated_global_portfolio = interfaces.get_global_portfolio_currencies_amounts()
        currency_values = interfaces.get_global_portfolio_currencies_values()

        portfolios_string = ""
        if has_real_trader:
            portfolios_string += AbstractBotInterface._print_portfolio(
                portfolio_real_current_value,
                reference_market,
                real_global_portfolio,
                currency_values,
                trading_constants.REAL_TRADER_STR,
                markdown,
            )

        if has_simulated_trader:
            portfolio_str = AbstractBotInterface._print_portfolio(
                portfolio_simulated_current_value,
                reference_market,
                simulated_global_portfolio,
                currency_values,
                trading_constants.SIMULATOR_TRADER_STR,
                markdown,
            )
            portfolios_string += f"{interfaces.EOL}{portfolio_str}"

        if not portfolios_string:
            portfolios_string = interfaces.NO_TRADER_MESSAGE

        return portfolios_string

    @staticmethod
    def get_command_profitability(markdown=False):
        _, bold, code = pretty_printer.get_markers(markdown)
        has_real_trader, has_simulated_trader, \
        real_global_profitability, simulated_global_profitability, \
        real_percent_profitability, simulated_percent_profitability, \
        real_no_trade_profitability, simulated_no_trade_profitability, \
        market_average_profitability = interfaces.get_global_profitability()
        profitability_string = ""
        if has_real_trader:
            real_profitability_pretty = pretty_printer.portfolio_profitability_pretty_print(
                real_global_profitability, None, interfaces.get_reference_market())
            profitability_string = \
                f"{bold}{trading_constants.REAL_TRADER_STR}{bold}Global profitability : {code}{real_profitability_pretty}" \
                f"({pretty_printer.get_min_string_from_number(real_percent_profitability, 2)}%){code}, market: {code}" \
                f"{pretty_printer.get_min_string_from_number(market_average_profitability, 2)}%{code}, initial portfolio:" \
                f" {code}{pretty_printer.get_min_string_from_number(real_no_trade_profitability, 2)}%{code}{interfaces.EOL}"
        if has_simulated_trader:
            simulated_profitability_pretty = \
                pretty_printer.portfolio_profitability_pretty_print(
                    simulated_global_profitability, None, interfaces.get_reference_market())
            profitability_string += \
                f"{bold}{trading_constants.SIMULATOR_TRADER_STR}{bold}Global profitability : {code}" \
                f"{simulated_profitability_pretty}" \
                f"({pretty_printer.get_min_string_from_number(simulated_percent_profitability, 2)}%){code}, " \
                f"market: {code}{pretty_printer.get_min_string_from_number(market_average_profitability, 2)}%{code}, " \
                f"initial portfolio: {code}" \
                f"{pretty_printer.get_min_string_from_number(simulated_no_trade_profitability, 2)}%{code}"
        if not profitability_string:
            profitability_string = interfaces.NO_TRADER_MESSAGE

        return profitability_string

    @staticmethod
    def get_command_ping():
        return f"I'm alive since " \
               f"{timestamp_util.convert_timestamp_to_datetime(interfaces.get_bot_api().get_start_time(), '%Y-%m-%d %H:%M:%S', local_timezone=True)}."

    @staticmethod
    def get_command_version():
        return f"{interfaces.AbstractInterface.project_name} {interfaces.AbstractInterface.project_version}"

    @staticmethod
    def get_command_start(markdown=False):
        if markdown:
            return "Hello, I'm [OctoBot](https://github.com/Drakkar-Software/OctoBot), type /help to know my skills."
        else:
            return "Hello, I'm OctoBot, type /help to know my skills."

    @staticmethod
    async def set_command_portfolios_refresh():
        return await interfaces.async_trigger_portfolios_refresh()

    @staticmethod
    def set_command_risk(new_risk):
        updated_risk = interfaces.set_risk(new_risk)
        risk_config = {
            commons_constants.CONFIG_TRADING: {
                commons_constants.CONFIG_RISK: float(updated_risk)
            }
        }
        AbstractBotInterface._update_edited_config(risk_config)
        return updated_risk

    @staticmethod
    def set_command_stop():
        interfaces.get_bot_api().stop_bot()

    async def set_command_pause(self):
        await interfaces.async_cancel_all_open_orders()
        interfaces.set_enable_trading(False)
        self.paused = True

    def set_command_resume(self):
        interfaces.set_enable_trading(True)
        self.paused = False

    @staticmethod
    def set_command_restart():
        interfaces.get_bot_api().restart_bot()

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
                end_index = len(first_part) - 1

            if end_index < len(message) - 1:
                remaining = message[end_index + 1:]
                return messages_list + AbstractBotInterface._split_messages_if_too_long(remaining, max_length,
                                                                                        preferred_separator)
            else:
                return messages_list
        else:
            return [message]

    @staticmethod
    def _update_edited_config(partial_config_update):
        config = interfaces.get_edited_config(dict_only=False)
        dict_util.nested_update_dict(config.config, partial_config_update)
        config.save()
