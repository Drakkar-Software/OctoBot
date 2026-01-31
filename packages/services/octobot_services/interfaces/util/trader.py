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
import octobot_commons.logging as logging

import octobot_trading.api as trading_api

import octobot_services.interfaces as interfaces


def has_trader():
    try:
        return trading_api.has_trader(_first_exchange_manager())
    except StopIteration:
        return False


def has_real_and_or_simulated_traders():
    has_real_trader = False
    has_simulated_trader = False
    exchange_managers = interfaces.get_exchange_managers()
    for exchange_manager in exchange_managers:
        if trading_api.is_trader_simulated(exchange_manager):
            has_simulated_trader = True
        else:
            has_real_trader = True
    return has_real_trader, has_simulated_trader


def sell_all_currencies():
    return interfaces.run_in_bot_main_loop(async_sell_all_currencies())


async def async_sell_all_currencies():
    orders = []
    for exchange_manager in interfaces.get_exchange_managers():
        if trading_api.is_trader_existing_and_enabled(exchange_manager):
            orders += await trading_api.sell_all_everything_for_reference_market(exchange_manager)
    return orders


def sell_all(currency):
    return interfaces.run_in_bot_main_loop(async_sell_all(currency))


async def async_sell_all(currency):
    orders = []
    for exchange_manager in interfaces.get_exchange_managers():
        if trading_api.is_trader_existing_and_enabled(exchange_manager):
            orders += await trading_api.sell_currency_for_reference_market(exchange_manager, currency)
    return orders


def set_enable_trading(enable):
    for exchange_manager in interfaces.get_exchange_managers():
        if trading_api.has_trader(exchange_manager):
            if trading_api.is_trader_enabled_in_config_from_exchange_manager(exchange_manager):
                trading_api.set_trading_enabled(exchange_manager, enable)


def _merge_trader_fees(current_fees, exchange_manager):
    current_fees_dict = current_fees if current_fees else {}
    for key, val in trading_api.get_total_paid_trading_fees(exchange_manager).items():
        if key in current_fees_dict:
            current_fees_dict[key] += val
        else:
            current_fees_dict[key] = val
    return current_fees_dict


def get_total_paid_fees(bot=None):
    real_trader_fees = None
    simulated_trader_fees = None

    for exchange_manager in interfaces.get_exchange_managers(bot):
        if trading_api.is_trader_existing_and_enabled(exchange_manager):
            if trading_api.is_trader_simulated(exchange_manager):
                simulated_trader_fees = _merge_trader_fees(simulated_trader_fees, exchange_manager)
            else:
                real_trader_fees = _merge_trader_fees(real_trader_fees, exchange_manager)
    return real_trader_fees, simulated_trader_fees


def get_trades_history(bot_api=None, symbol=None, independent_backtesting=None, since=None, as_dict=False):
    simulated_trades_history = []
    real_trades_history = []

    for exchange_manager in interfaces.get_exchange_managers(bot_api=bot_api,
                                                             independent_backtesting=independent_backtesting):
        if trading_api.is_trader_existing_and_enabled(exchange_manager):
            if trading_api.is_trader_simulated(exchange_manager):
                simulated_trades_history += trading_api.get_trade_history(exchange_manager, None, symbol, since, as_dict)
            else:
                real_trades_history += trading_api.get_trade_history(exchange_manager, None, symbol, since, as_dict)
    return real_trades_history, simulated_trades_history


def set_risk(risk):
    result_risk = None
    for exchange_manager in interfaces.get_exchange_managers():
        if trading_api.has_trader(exchange_manager):
            result_risk = trading_api.set_trader_risk(exchange_manager, risk)
    return result_risk


def get_risk():
    try:
        return trading_api.get_trader_risk(_first_exchange_manager()) \
            if trading_api.has_trader(_first_exchange_manager()) else None
    except StopIteration:
        return None


def get_currencies_with_status():
    evaluations_by_exchange_by_pair = {}
    for exchange_manager in interfaces.get_exchange_managers():
        trading_modes = trading_api.get_trading_modes(exchange_manager)
        for pair in trading_api.get_trading_pairs(exchange_manager):
            if pair not in evaluations_by_exchange_by_pair:
                evaluations_by_exchange_by_pair[pair] = {}
            status_explanation = "N/A"
            status = "N/A"
            for trading_mode in trading_modes:
                if trading_api.get_trading_mode_symbol(trading_mode) == pair \
                        or trading_api.is_trading_mode_symbol_wildcard(trading_mode):
                    status_explanation, status = trading_api.get_trading_mode_current_state(trading_mode)
                    try:
                        status = round(status, 3)
                    except TypeError:
                        pass
                    break
            evaluations_by_exchange_by_pair[pair][trading_api.get_exchange_manager_id(exchange_manager)] = \
                [status_explanation.replace("_", " "), status,
                 trading_api.get_exchange_name(exchange_manager).capitalize()]
    return evaluations_by_exchange_by_pair


def _get_tentacles_values(evaluations, tentacle_type_node, exchange):
    try:
        import octobot_evaluators.api as evaluators_api
    except ImportError:
        logging.get_logger("InterfaceUtil").error("_get_tentacles_values requires OctoBot-Evaluators package installed")
        return {}
    for tentacle_name, tentacle_name_node in evaluators_api.get_children_list(tentacle_type_node).items():
        evaluations[exchange][tentacle_name] = {}
        for cryptocurrency, cc_node in evaluators_api.get_children_list(tentacle_name_node).items():
            evaluations[exchange][tentacle_name][cryptocurrency] = {}
            if evaluators_api.has_children(cc_node):
                for symbol, symbol_node in evaluators_api.get_children_list(cc_node).items():
                    if evaluators_api.has_children(symbol_node):
                        evaluations[exchange][tentacle_name][symbol] = {}
                        for time_frame, time_frame_node in evaluators_api.get_children_list(symbol_node).items():
                            evaluations[exchange][tentacle_name][symbol][time_frame] = \
                                evaluators_api.get_value(time_frame_node)
                    else:
                        evaluations[exchange][tentacle_name][symbol] = evaluators_api.get_value(symbol_node)
            else:
                evaluations[exchange][tentacle_name][cryptocurrency] = evaluators_api.get_value(cc_node)


def get_matrix_list():
    try:
        import octobot_evaluators.api as evaluators_api
    except ImportError:
        logging.get_logger("InterfaceUtil").error("get_matrix_list requires OctoBot-Evaluators package installed")
        return {}
    evaluations = {}
    matrix = evaluators_api.get_matrix(interfaces.get_bot_api().get_matrix_id())
    for exchange, exchange_node in evaluators_api.get_node_children_by_names(matrix).items():
        evaluations[exchange] = {}
        for tentacle_type_node in evaluators_api.get_children_list(exchange_node).values():
            _get_tentacles_values(evaluations, tentacle_type_node, exchange)
    return evaluations


def _first_exchange_manager():
    return next(iter(interfaces.get_exchange_managers()))
