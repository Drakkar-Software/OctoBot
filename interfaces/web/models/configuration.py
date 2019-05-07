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
from tools.logging.logging_util import get_logger
from copy import copy

import ccxt
import requests

from config import CONFIG_EVALUATOR, COIN_MARKET_CAP_CURRENCIES_LIST_URL, CONFIG_EXCHANGES, TESTED_EXCHANGES, \
    UPDATED_CONFIG_SEPARATOR, CONFIG_TRADING_TENTACLES, EVALUATOR_ACTIVATION, EVALUATOR_EVAL_DEFAULT_TYPE, \
    SIMULATOR_TESTED_EXCHANGES, CONFIG_METRICS, CONFIG_ENABLED_OPTION, CONFIG_ADVANCED_CLASSES
from interfaces import get_bot
from services import AbstractService
from tools.config_manager import ConfigManager
from tentacles_management.class_inspector import get_class_from_string, evaluator_parent_inspection, \
    trading_mode_parent_inspection
from evaluator.abstract_evaluator import AbstractEvaluator
from backtesting import backtesting_enabled
from tools.metrics.metrics_manager import MetricsManager


NAME_KEY = "name"
DESCRIPTION_KEY = "description"
REQUIREMENTS_KEY = "requirements"
REQUIREMENTS_COUNT_KEY = "requirements-min-count"
DEFAULT_CONFIG_KEY = "default-config"
TRADING_MODES_KEY = "trading-modes"
STRATEGIES_KEY = "strategies"
ADVANCED_CLASS_KEY = "advanced_class"
TRADING_MODE_KEY = "trading mode"
STRATEGY_KEY = "strategy"
TA_EVALUATOR_KEY = "technical evaluator"
SOCIAL_EVALUATOR_KEY = "social evaluator"
RT_EVALUATOR_KEY = "real time evaluator"
REQUIRED_KEY = "required"
SOCIAL_KEY = "social"
TA_KEY = "ta"
RT_KEY = "real-time"
ACTIVATED_STRATEGIES = "activated_strategies"
BASE_CLASSES_KEY = "base_classes"
EVALUATION_FORMAT_KEY = "evaluation_format"

LOGGER = get_logger("WebConfigurationModel")

DEFAULT_EXCHANGE = "binance"


def get_edited_config():
    return get_bot().edited_config


def _get_evaluator_config():
    return get_edited_config()[CONFIG_EVALUATOR]


def get_evaluator_startup_config():
    return get_bot().startup_config[CONFIG_EVALUATOR]


def _get_trading_config():
    return get_edited_config()[CONFIG_TRADING_TENTACLES]


def get_trading_startup_config():
    return get_bot().startup_config[CONFIG_TRADING_TENTACLES]


def reset_trading_history():
    previous_state_manager = get_bot().exchange_factory.previous_trading_state_manager
    if previous_state_manager:
        previous_state_manager.reset_trading_history()


def is_trading_persistence_activated():
    return get_bot().exchange_factory.previous_trading_state_manager is not None


def _get_advanced_class_details(class_name, klass, is_trading_mode=False, is_strategy=False):
    from tentacles_management.advanced_manager import AdvancedManager
    details = {}
    config = get_bot().get_config()
    advanced_class = AdvancedManager.get_class(config, klass)
    if advanced_class and advanced_class.get_name() != class_name:
        details[NAME_KEY] = advanced_class.get_name()
        details[DESCRIPTION_KEY] = advanced_class.get_description()
        details[BASE_CLASSES_KEY] = [k.get_name() for k in advanced_class.__bases__]
        if is_trading_mode:
            required_strategies, required_strategies_count = klass.get_required_strategies_names_and_count()
            details[REQUIREMENTS_KEY] = [strategy for strategy in required_strategies]
            details[REQUIREMENTS_COUNT_KEY] = required_strategies_count
        elif is_strategy:
            details[REQUIREMENTS_KEY] = [evaluator for evaluator in advanced_class.get_required_evaluators(config)]
            details[DEFAULT_CONFIG_KEY] = [evaluator for evaluator in advanced_class.get_default_evaluators(config)]
    return details


def _get_strategy_activation_state(with_trading_modes):
    import trading.trader.modes as modes
    import evaluator.Strategies as strategies
    strategy_config = {
        TRADING_MODES_KEY: {},
        STRATEGIES_KEY: {}
    }
    strategy_config_classes = {
        TRADING_MODES_KEY: {},
        STRATEGIES_KEY: {}
    }

    if with_trading_modes:
        trading_config = _get_trading_config()
        for key, val in trading_config.items():
            config_class = get_class_from_string(key, modes.AbstractTradingMode, modes, trading_mode_parent_inspection)
            if config_class:
                strategy_config[TRADING_MODES_KEY][key] = {}
                strategy_config[TRADING_MODES_KEY][key][EVALUATOR_ACTIVATION] = val
                strategy_config[TRADING_MODES_KEY][key][DESCRIPTION_KEY] = config_class.get_description()
                strategy_config[TRADING_MODES_KEY][key][ADVANCED_CLASS_KEY] = \
                    _get_advanced_class_details(key, config_class, is_trading_mode=True)
                strategy_config_classes[TRADING_MODES_KEY][key] = config_class

    evaluator_config = _get_evaluator_config()
    for key, val in evaluator_config.items():
        config_class = get_class_from_string(key, strategies.StrategiesEvaluator,
                                             strategies, evaluator_parent_inspection)
        if config_class:
            strategy_config[STRATEGIES_KEY][key] = {}
            strategy_config[STRATEGIES_KEY][key][EVALUATOR_ACTIVATION] = val
            strategy_config[STRATEGIES_KEY][key][DESCRIPTION_KEY] = config_class.get_description()
            strategy_config[STRATEGIES_KEY][key][ADVANCED_CLASS_KEY] = \
                _get_advanced_class_details(key, config_class, is_strategy=True)
            strategy_config_classes[STRATEGIES_KEY][key] = config_class

    return strategy_config, strategy_config_classes


def _get_tentacle_packages():
    import trading.trader.modes as modes
    yield modes, modes.AbstractTradingMode, TRADING_MODE_KEY
    import evaluator.Strategies as strategies
    yield strategies, strategies.StrategiesEvaluator, STRATEGY_KEY
    import evaluator.TA as ta
    yield ta, AbstractEvaluator, TA_EVALUATOR_KEY
    import evaluator.Social as social
    yield social, AbstractEvaluator, SOCIAL_EVALUATOR_KEY
    import evaluator.RealTime as rt
    yield rt, AbstractEvaluator, RT_EVALUATOR_KEY


def _get_activation_state(name, details, is_trading_mode):
    activation_states = _get_trading_config() if is_trading_mode else _get_evaluator_config()
    if ADVANCED_CLASS_KEY in details:
        for parent_class in details[ADVANCED_CLASS_KEY][BASE_CLASSES_KEY]:
            if parent_class in activation_states and activation_states[parent_class]:
                return True
    return name in activation_states and activation_states[name]


def get_tentacle_from_string(name, with_info=True):
    for package, abstract_class, tentacle_type in _get_tentacle_packages():
        is_trading_mode = tentacle_type == TRADING_MODE_KEY
        parent_inspector = trading_mode_parent_inspection if is_trading_mode else evaluator_parent_inspection
        klass = get_class_from_string(name, abstract_class, package, parent_inspector)
        if klass:
            if with_info:
                info = dict()
                info[DESCRIPTION_KEY] = klass.get_description()
                info[NAME_KEY] = name
                for parent_class in klass.__bases__:
                    if hasattr(parent_class, "get_name"):
                        advanced_details = _get_advanced_class_details(parent_class.get_name(), parent_class,
                                                                       is_strategy=(tentacle_type == STRATEGY_KEY))
                        if advanced_details:
                            info[ADVANCED_CLASS_KEY] = advanced_details
                info[EVALUATOR_ACTIVATION] = _get_activation_state(name, info, is_trading_mode)
                if is_trading_mode:
                    _add_trading_mode_requirements_and_default_config(info, klass)
                elif tentacle_type == STRATEGY_KEY:
                    _add_strategy_requirements_and_default_config(info, klass, get_bot().get_config())
                return klass, tentacle_type, info
            else:
                return klass, tentacle_type, None
    return None, None, None


def update_tentacle_config(tentacle_name, config_update):
    try:
        klass, _, _ = get_tentacle_from_string(tentacle_name, with_info=False)
        ConfigManager.update_tentacle_config(klass, config_update)
        return True, f"{tentacle_name} updated"
    except Exception as e:
        LOGGER.exception(e)
        return False, f"Error when updating tentacle config: {e}"


def reset_config_to_default(tentacle_name):
    try:
        klass, _, _ = get_tentacle_from_string(tentacle_name, with_info=False)
        ConfigManager.factory_reset_tentacle_config(klass)
        return True, f"{tentacle_name} configuration reset to default values"
    except Exception as e:
        LOGGER.exception(e)
        return False, f"Error when resetting factory tentacle config: {e}"


def _get_required_element(elements_config):
    advanced_class_key = ADVANCED_CLASS_KEY
    requirements = REQUIREMENTS_KEY
    required_elements = set()
    for element_type in elements_config.values():
        for element_name, element in element_type.items():
            if element[EVALUATOR_ACTIVATION]:
                if element[advanced_class_key] and requirements in element[advanced_class_key]:
                    required_elements = required_elements.union(element[advanced_class_key][requirements])
                elif requirements in element:
                    required_elements = required_elements.union(element[requirements])
    return required_elements


def _add_strategy_requirements_and_default_config(desc, klass, config):
    desc[REQUIREMENTS_KEY] = [evaluator for evaluator in klass.get_required_evaluators(config)]
    desc[DEFAULT_CONFIG_KEY] = [evaluator for evaluator in klass.get_default_evaluators(config)]


def _add_trading_mode_requirements_and_default_config(desc, klass):
    required_strategies, required_strategies_count = klass.get_required_strategies_names_and_count()
    if required_strategies:
        desc[REQUIREMENTS_KEY] = \
            [strategy for strategy in required_strategies]
        desc[DEFAULT_CONFIG_KEY] = \
            [strategy for strategy in klass.get_default_strategies()]
        desc[REQUIREMENTS_COUNT_KEY] = required_strategies_count
    else:
        desc[REQUIREMENTS_KEY] = []
        desc[REQUIREMENTS_COUNT_KEY] = 0


def _add_strategies_requirements(strategies, strategy_config):
    config = get_bot().get_config()
    required_elements = _get_required_element(strategy_config)
    for classKey, klass in strategies.items():
        if not strategy_config[STRATEGIES_KEY][classKey][ADVANCED_CLASS_KEY]:
            # no need for requirement if advanced class: requirements are already in advanced class
            _add_strategy_requirements_and_default_config(strategy_config[STRATEGIES_KEY][classKey], klass, config)
        strategy_config[STRATEGIES_KEY][classKey][REQUIRED_KEY] = classKey in required_elements


def _add_trading_modes_requirements(trading_modes, strategy_config):
    for classKey, klass in trading_modes.items():
        try:
            _add_trading_mode_requirements_and_default_config(strategy_config[TRADING_MODES_KEY][classKey], klass)
        except Exception as e:
            LOGGER.exception(e)


def get_strategy_config(with_trading_modes=True):
    strategy_config, strategy_config_classes = _get_strategy_activation_state(with_trading_modes)
    if with_trading_modes:
        _add_trading_modes_requirements(strategy_config_classes[TRADING_MODES_KEY], strategy_config)
    _add_strategies_requirements(strategy_config_classes[STRATEGIES_KEY], strategy_config)
    return strategy_config


def get_in_backtesting_mode():
    return backtesting_enabled(get_bot().get_config())


def accepted_terms():
    return ConfigManager.accepted_terms(get_edited_config())


def accept_terms(accepted):
    return ConfigManager.accept_terms(get_edited_config(), accepted)


def _fill_evaluator_config(evaluator_name, activated, eval_type_key,
                           evaluator_type, detailed_config, is_strategy=False):
    klass = get_class_from_string(evaluator_name, AbstractEvaluator, evaluator_type, evaluator_parent_inspection)
    if klass:
        detailed_config[eval_type_key][evaluator_name] = {}
        detailed_config[eval_type_key][evaluator_name][EVALUATOR_ACTIVATION] = activated
        detailed_config[eval_type_key][evaluator_name][DESCRIPTION_KEY] = klass.get_description()
        detailed_config[eval_type_key][evaluator_name][EVALUATION_FORMAT_KEY] = "float" \
            if klass.get_eval_type() == EVALUATOR_EVAL_DEFAULT_TYPE else str(klass.get_eval_type())
        detailed_config[eval_type_key][evaluator_name][ADVANCED_CLASS_KEY] = \
            _get_advanced_class_details(evaluator_name, klass, is_strategy=is_strategy)
        return True, klass
    return False, klass


def get_evaluator_detailed_config():
    import evaluator.Strategies as strategies
    import evaluator.TA as ta
    import evaluator.Social as social
    import evaluator.RealTime as rt
    detailed_config = {
        SOCIAL_KEY: {},
        TA_KEY: {},
        RT_KEY: {}
    }
    strategy_config = {
        STRATEGIES_KEY: {}
    }
    strategy_class_by_name = {}
    evaluator_config = _get_evaluator_config()
    for evaluator_name, activated in evaluator_config.items():
        is_TA, klass = _fill_evaluator_config(evaluator_name, activated, TA_KEY, ta, detailed_config)
        if not is_TA:
            is_social, klass = _fill_evaluator_config(evaluator_name, activated, SOCIAL_KEY, social, detailed_config)
            if not is_social:
                is_real_time, klass = _fill_evaluator_config(evaluator_name, activated, RT_KEY, rt, detailed_config)
                if not is_real_time:
                    is_strategy, klass = _fill_evaluator_config(evaluator_name, activated, STRATEGIES_KEY,
                                                                strategies, strategy_config, is_strategy=True)
                    if is_strategy:
                        strategy_class_by_name[evaluator_name] = klass

    _add_strategies_requirements(strategy_class_by_name, strategy_config)
    required_elements = _get_required_element(strategy_config)
    for eval_type in detailed_config.values():
        for eval_name, eval_details in eval_type.items():
            eval_details[REQUIRED_KEY] = eval_name in required_elements

    detailed_config[ACTIVATED_STRATEGIES] = [s for s, details in strategy_config[STRATEGIES_KEY].items()
                                             if details[EVALUATOR_ACTIVATION]]
    return detailed_config


def get_config_activated_trading_mode(edited_config=False):
    from trading.util.trading_config_util import get_activated_trading_mode
    config = get_bot().get_config()
    if edited_config:
        config = copy(get_edited_config())
        # rebind advanced classes to use in get_activated_trading_mode
        config[CONFIG_ADVANCED_CLASSES] = get_bot().get_config()[CONFIG_ADVANCED_CLASSES]
    return get_activated_trading_mode(config)


def update_evaluator_config(new_config, deactivate_others=False):
    current_config = _get_evaluator_config()
    try:
        ConfigManager.update_evaluator_config(new_config, current_config, deactivate_others)
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


def manage_metrics(enable_metrics):
    current_edited_config = get_edited_config()
    if CONFIG_METRICS not in current_edited_config:
        current_edited_config[CONFIG_METRICS] = {CONFIG_ENABLED_OPTION: enable_metrics}
    else:
        current_edited_config[CONFIG_METRICS][CONFIG_ENABLED_OPTION] = enable_metrics
    if enable_metrics and MetricsManager.should_register_bot(current_edited_config):
        MetricsManager.background_get_id_and_register_bot(get_bot())
    ConfigManager.simple_save_config_update(current_edited_config)


def get_metrics_enabled():
    return ConfigManager.get_metrics_enabled(get_edited_config())


def get_services_list():
    services = {}
    services_names = []
    for service in AbstractService.__subclasses__():
        srv = service()
        services[srv.get_type()] = srv
        services_names.append(srv.get_type())
    return services, services_names


def get_symbol_list(exchanges):
    result = []

    for exchange in exchanges:
        try:
            inst = getattr(ccxt, exchange)({'verbose': False})
            inst.load_markets()
            result += inst.symbols
        except Exception as e:
            LOGGER.error(f"error when loading symbol list for {exchange}: {e}")

    # filter symbols with a "." or no "/" because bot can't handle them for now
    symbols = [res for res in result if "/" in res]

    return list(set(symbols))


def get_all_symbol_list():
    try:
        currencies_list = json.loads(requests.get(COIN_MARKET_CAP_CURRENCIES_LIST_URL).text)
        return {
            currency_data[NAME_KEY]: currency_data["symbol"]
            for currency_data in currencies_list["data"]
        }
    except Exception as e:
        LOGGER.error(f"Failed to get currencies list from coinmarketcap : {e}")
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
        return DEFAULT_EXCHANGE
