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

import json
import notifiers
from tools.logging.logging_util import get_logger

import ccxt
import requests

from config import CONFIG_EVALUATOR, COIN_MARKET_CAP_CURRENCIES_LIST_URL, CONFIG_EXCHANGES, TESTED_EXCHANGES, \
    UPDATED_CONFIG_SEPARATOR, CONFIG_TRADING_TENTACLES, CONFIG_NOTIFIER_IGNORE, EVALUATOR_ACTIVATION, \
    SIMULATOR_TESTED_EXCHANGES
from interfaces import get_bot
from services import AbstractService
from services import NotifierService
from tools.config_manager import ConfigManager
from tools.class_inspector import get_class_from_string, evaluator_parent_inspection, trading_mode_parent_inspection
from evaluator.abstract_evaluator import AbstractEvaluator
from backtesting.backtesting import Backtesting


def get_edited_config():
    return get_bot().get_edited_config()


def _get_evaluator_config():
    return get_edited_config()[CONFIG_EVALUATOR]


def get_evaluator_startup_config():
    return get_bot().get_startup_config()[CONFIG_EVALUATOR]


def _get_trading_config():
    return get_edited_config()[CONFIG_TRADING_TENTACLES]


def get_trading_startup_config():
    return get_bot().get_startup_config()[CONFIG_TRADING_TENTACLES]


def _get_advanced_class_details(class_name, klass, is_trading_mode=False, is_strategy=False):
    from evaluator.Util.advanced_manager import AdvancedManager
    name = "name"
    description = "description"
    requirements = "requirements"
    requirements_count_key = "requirements-min-count"
    default_config_key = "default-config"
    details = {}
    config = get_bot().get_config()
    advanced_class = AdvancedManager.get_class(config, klass)
    if advanced_class and advanced_class.get_name() != class_name:
        details[name] = advanced_class.get_name()
        details[description] = advanced_class.get_description()
        if is_trading_mode:
            required_strategies, required_strategies_count = klass.get_required_strategies_names_and_count()
            details[requirements] = [strategy for strategy in required_strategies]
            details[requirements_count_key] = required_strategies_count
        elif is_strategy:
            details[requirements] = [evaluator for evaluator in advanced_class.get_required_evaluators(config)]
            details[default_config_key] = [evaluator for evaluator in advanced_class.get_default_evaluators(config)]
    return details


def _get_strategy_activation_state():
    import trading.trader.modes as modes
    import evaluator.Strategies as strategies
    trading_mode_key = "trading-modes"
    strategies_key = "strategies"
    description = "description"
    advanced_class_key = "advanced_class"
    strategy_config = {
        trading_mode_key: {},
        strategies_key: {}
    }
    strategy_config_classes = {
        trading_mode_key: {},
        strategies_key: {}
    }

    trading_config = _get_trading_config()
    for key, val in trading_config.items():
        config_class = get_class_from_string(key, modes.AbstractTradingMode, modes, trading_mode_parent_inspection)
        if config_class:
            strategy_config[trading_mode_key][key] = {}
            strategy_config[trading_mode_key][key][EVALUATOR_ACTIVATION] = val
            strategy_config[trading_mode_key][key][description] = config_class.get_description()
            strategy_config[trading_mode_key][key][advanced_class_key] = \
                _get_advanced_class_details(key, config_class, is_trading_mode=True)
            strategy_config_classes[trading_mode_key][key] = config_class

    evaluator_config = _get_evaluator_config()
    for key, val in evaluator_config.items():
        config_class = get_class_from_string(key, strategies.StrategiesEvaluator,
                                             strategies, evaluator_parent_inspection)
        if config_class:
            strategy_config[strategies_key][key] = {}
            strategy_config[strategies_key][key][EVALUATOR_ACTIVATION] = val
            strategy_config[strategies_key][key][description] = config_class.get_description()
            strategy_config[strategies_key][key][advanced_class_key] = \
                _get_advanced_class_details(key, config_class, is_strategy=True)
            strategy_config_classes[strategies_key][key] = config_class

    return strategy_config, strategy_config_classes


def _get_required_element(elements_config):
    advanced_class_key = "advanced_class"
    requirements = "requirements"
    required_elements = set()
    for element_type in elements_config.values():
        for element_name, element in element_type.items():
            if element[EVALUATOR_ACTIVATION]:
                if element[advanced_class_key] and requirements in element[advanced_class_key]:
                    required_elements = required_elements.union(element[advanced_class_key][requirements])
                elif requirements in element:
                    required_elements = required_elements.union(element[requirements])
    return required_elements


def _add_strategies_requirements(strategies, strategy_config):
    strategies_key = "strategies"
    requirements_key = "requirements"
    advanced_class_key = "advanced_class"
    required = "required"
    default_config_key = "default-config"
    config = get_bot().get_config()
    required_elements = _get_required_element(strategy_config)
    for classKey, klass in strategies.items():
        if not strategy_config[strategies_key][classKey][advanced_class_key]:
            # no need for requirement if advanced class: requirements are already in advanced class
            strategy_config[strategies_key][classKey][requirements_key] = \
                [evaluator for evaluator in klass.get_required_evaluators(config)]
            strategy_config[strategies_key][classKey][default_config_key] = \
                [evaluator for evaluator in klass.get_default_evaluators(config)]
        strategy_config[strategies_key][classKey][required] = classKey in required_elements


def _add_trading_modes_requirements(trading_modes, strategy_config):
    trading_mode_key = "trading-modes"
    requirements_key = "requirements"
    default_config_key = "default-config"
    requirements_count_key = "requirements-min-count"
    for classKey, klass in trading_modes.items():
        try:
            required_strategies, required_strategies_count = klass.get_required_strategies_names_and_count()
            if required_strategies:
                strategy_config[trading_mode_key][classKey][requirements_key] = \
                    [strategy for strategy in required_strategies]
                strategy_config[trading_mode_key][classKey][default_config_key] = \
                    [strategy for strategy in klass.get_default_strategies()]
                strategy_config[trading_mode_key][classKey][requirements_count_key] = required_strategies_count
            else:
                strategy_config[trading_mode_key][classKey][requirements_key] = []
                strategy_config[trading_mode_key][classKey][requirements_count_key] = 0
        except Exception as e:
            get_logger("Configuration").exception(e)


def get_strategy_config():
    strategy_config, strategy_config_classes = _get_strategy_activation_state()
    _add_trading_modes_requirements(strategy_config_classes["trading-modes"], strategy_config)
    _add_strategies_requirements(strategy_config_classes["strategies"], strategy_config)
    return strategy_config


def get_in_backtesting_mode():
    return Backtesting.enabled(get_bot().get_config())


def _fill_evaluator_config(evaluator_name, activated, eval_type_key,
                           evaluator_type, detailed_config, is_strategy=False):
    description = "description"
    advanced_class_key = "advanced_class"
    klass = get_class_from_string(evaluator_name, AbstractEvaluator, evaluator_type, evaluator_parent_inspection)
    if klass:
        detailed_config[eval_type_key][evaluator_name] = {}
        detailed_config[eval_type_key][evaluator_name][EVALUATOR_ACTIVATION] = activated
        detailed_config[eval_type_key][evaluator_name][description] = klass.get_description()
        detailed_config[eval_type_key][evaluator_name][advanced_class_key] = \
            _get_advanced_class_details(evaluator_name, klass, is_strategy=is_strategy)
        return True, klass
    return False, klass


def get_evaluator_detailed_config():
    import evaluator.TA as ta
    import evaluator.Social as social
    import evaluator.RealTime as rt
    import evaluator.Strategies as strat
    social_key = "social"
    ta_key = "ta"
    rt_key = "real-time"
    strategies_key = "strategies"
    required_key = "required"
    detailed_config = {
        social_key: {},
        ta_key: {},
        rt_key: {}
    }
    strategy_config = {
        strategies_key: {}
    }
    strategy_class_by_name = {}
    evaluator_config = _get_evaluator_config()
    for evaluator_name, activated in evaluator_config.items():
        is_TA, klass = _fill_evaluator_config(evaluator_name, activated, ta_key, ta, detailed_config)
        if not is_TA:
            is_social, klass = _fill_evaluator_config(evaluator_name, activated, social_key, social, detailed_config)
            if not is_social:
                is_real_time, klass = _fill_evaluator_config(evaluator_name, activated, rt_key, rt, detailed_config)
                if not is_real_time:
                    is_strategy, klass = _fill_evaluator_config(evaluator_name, activated, strategies_key,
                                                                strat, strategy_config, is_strategy=True)
                    if is_strategy:
                        strategy_class_by_name[evaluator_name] = klass

    _add_strategies_requirements(strategy_class_by_name, strategy_config)
    required_elements = _get_required_element(strategy_config)
    for eval_type in detailed_config.values():
        for eval_name, eval_details in eval_type.items():
            eval_details[required_key] = eval_name in required_elements

    detailed_config["activated_strategies"] = [s for s, details in strategy_config[strategies_key].items()
                                               if details[EVALUATOR_ACTIVATION]]
    return detailed_config


def update_evaluator_config(new_config):
    current_config = _get_evaluator_config()
    try:
        ConfigManager.update_evaluator_config(new_config, current_config)
        return True
    except Exception:
        return False


def update_trading_config(new_config):
    current_config = _get_trading_config()
    try:
        ConfigManager.update_trading_config(new_config, current_config)
        return True
    except Exception:
        return False


def update_global_config(new_config, delete=False):
    current_edited_config = get_edited_config()
    ConfigManager.update_global_config(new_config, current_edited_config, update_input=True, delete=delete)
    return True


def get_services_list():
    services = {}
    services_names = []
    for service in AbstractService.__subclasses__():
        if service != NotifierService:
            srv = service()
            services[srv.get_type()] = srv
            services_names.append(srv.get_type())
    for notifier_service in notifiers.core.all_providers():
        if notifier_service not in CONFIG_NOTIFIER_IGNORE:
            NotifierService.NOTIFIER_PROVIDER_TYPE = notifiers.get_notifier(notifier_service)
            srv = NotifierService()
            services[srv.get_provider_name()] = srv
            services_names.append(srv.get_provider_name())
    return services, services_names


def get_symbol_list(exchanges):
    result = []

    for exchange in exchanges:
        try:
            inst = getattr(ccxt, exchange)({'verbose': False})
            inst.load_markets()
            result += inst.symbols
        except Exception as e:
            get_logger("Configuration").error(f"error when loading symbol list for {exchange}: {e}")

    # filter symbols with a "." or no "/" because bot can't handle them for now
    symbols = [res for res in result if "/" in res]

    return list(set(symbols))


def get_all_symbol_list():
    try:
        currencies_list = json.loads(requests.get(COIN_MARKET_CAP_CURRENCIES_LIST_URL).text)
        return {
            currency_data["name"]: currency_data["symbol"]
            for currency_data in currencies_list["data"]
        }
    except Exception as e:
        get_logger("Configuration").error(f"Failed to get currencies list from coinmarketcap : {e}")
        return dict()


def get_full_exchange_list(remove_config_exchanges=False):
    g_config = get_bot().get_config()
    if remove_config_exchanges:
        user_exchanges = [e for e in g_config[CONFIG_EXCHANGES]]
        full_exchange_list = list(set(ccxt.exchanges) - set(user_exchanges))
    else:
        full_exchange_list = list(set(ccxt.exchanges))
    # can't handle exchanges containing UPDATED_CONFIG_SEPARATOR character in their name
    return [exchange for exchange in full_exchange_list if UPDATED_CONFIG_SEPARATOR not in exchange]


def get_tested_exchange_list():
    full_exchange_list = list(set(ccxt.exchanges))
    return [exchange for exchange in TESTED_EXCHANGES if exchange in full_exchange_list]


def get_simulated_exchange_list():
    full_exchange_list = list(set(ccxt.exchanges))
    return [exchange for exchange in SIMULATOR_TESTED_EXCHANGES if exchange in full_exchange_list]


def get_other_exchange_list(remove_config_exchanges=False):
    full_list = get_full_exchange_list(remove_config_exchanges)
    return [exchange for exchange in full_list
            if exchange not in TESTED_EXCHANGES and exchange not in SIMULATOR_TESTED_EXCHANGES]


def get_current_exchange():
    g_config = get_bot().get_config()
    exchanges = g_config[CONFIG_EXCHANGES]
    if exchanges:
        return next(iter(exchanges))
    else:
        return "binance"
