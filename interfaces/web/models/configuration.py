import json
from tools.logging.logging_util import get_logger

import ccxt
import requests

from config.cst import CONFIG_EVALUATOR, COIN_MARKET_CAP_CURRENCIES_LIST_URL, CONFIG_EXCHANGES, \
    UPDATED_CONFIG_SEPARATOR, CONFIG_TRADING_TENTACLES
from interfaces import get_bot
from services import AbstractService
from tools.config_manager import ConfigManager
from tools.class_inspector import get_class_from_string, evaluator_parent_inspection, trading_mode_parent_inspection, \
    get_deep_class_from_string
from evaluator.Util.advanced_manager import AdvancedManager
from evaluator.abstract_evaluator import AbstractEvaluator


def get_edited_config():
    return get_bot().get_edited_config()


def _get_evaluator_config():
    return get_edited_config()[CONFIG_EVALUATOR]


def get_evaluator_startup_config():
    return get_bot().get_startup_config()[CONFIG_EVALUATOR]


def _get_trading_config():
    return get_edited_config()[CONFIG_TRADING_TENTACLES]


def _get_trading_startup_config():
    return get_bot().get_startup_config()[CONFIG_TRADING_TENTACLES]


def _get_advanced_class_details(class_name, klass, is_trading_mode=False, is_strategy=False):
    name = "name"
    description = "description"
    requirements = "requirements"
    details = {}
    config = get_bot().get_config()
    advanced_class = AdvancedManager.get_class(config, klass)
    if advanced_class and advanced_class.get_name() != class_name:
        details[name] = advanced_class.get_name()
        details[description] = advanced_class.get_description()
        if is_trading_mode:
            details[requirements] = [strategy.get_name() for strategy in advanced_class.get_required_strategies(config)]
        elif is_strategy:
            details[requirements] = [evaluator for evaluator in advanced_class.get_required_evaluators(config)]
    return details


def _get_strategy_activation_state(startup_config=False):
    import trading.trader.modes as modes
    import evaluator.Strategies as strategies
    trading_mode_key = "trading-modes"
    strategies_key = "strategies"
    activation = "activation"
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
    evaluator_config = get_evaluator_startup_config() if startup_config else _get_evaluator_config()
    for key, val in evaluator_config.items():
        config_class = get_class_from_string(key, strategies.StrategiesEvaluator,
                                             strategies, evaluator_parent_inspection)
        if config_class:
            strategy_config[strategies_key][key] = {}
            strategy_config[strategies_key][key][activation] = val
            strategy_config[strategies_key][key][description] = config_class.get_description()
            strategy_config[strategies_key][key][advanced_class_key] = \
                _get_advanced_class_details(key, config_class, False)
            strategy_config_classes[strategies_key][key] = config_class

    trading_config = _get_trading_startup_config() if startup_config else _get_trading_config()
    for key, val in trading_config.items():
        config_class = get_class_from_string(key, modes.AbstractTradingMode, modes, trading_mode_parent_inspection)
        if config_class:
            strategy_config[trading_mode_key][key] = {}
            strategy_config[trading_mode_key][key][activation] = val
            strategy_config[trading_mode_key][key][description] = config_class.get_description()
            strategy_config[trading_mode_key][key][advanced_class_key] = \
                _get_advanced_class_details(key, config_class, True)
            strategy_config_classes[trading_mode_key][key] = config_class

    return strategy_config, strategy_config_classes


def _get_strategies_requirements(strategies, strategy_config):
    strategies_key = "strategies"
    requirements_key = "requirements"
    advanced_class_key = "advanced_class"
    config = get_bot().get_config()
    for classKey, klass in strategies.items():
        if not strategy_config[strategies_key][classKey][advanced_class_key]:
            # no need for requirement if advanced class: requirements are already in advanced class
            strategy_config[strategies_key][classKey][requirements_key] = \
                [evaluator for evaluator in klass.get_required_evaluators(config)]


def _get_trading_modes_requirements(trading_modes, strategy_config):
    trading_mode_key = "trading-modes"
    requirements_key = "requirements"
    for classKey, klass in trading_modes.items():
        strategy_config[trading_mode_key][classKey][requirements_key] = \
            [strategy.get_name() for strategy in klass.get_required_strategies()]


def get_strategy_startup_config():
    strategy_config, _ = _get_strategy_activation_state(startup_config=True)
    return strategy_config


def get_strategy_config():
    strategy_config, strategy_config_classes = _get_strategy_activation_state(startup_config=False)
    _get_trading_modes_requirements(strategy_config_classes["trading-modes"], strategy_config)
    _get_strategies_requirements(strategy_config_classes["strategies"], strategy_config)
    return strategy_config


def _fill_evaluator_config(evaluator_name, activated, eval_type_key, evaluator_type, detailed_config):
    activation = "activation"
    description = "description"
    advanced_class_key = "advanced_class"
    klass = get_class_from_string(evaluator_name, AbstractEvaluator, evaluator_type, evaluator_parent_inspection)
    if klass:
        detailed_config[eval_type_key][evaluator_name] = {}
        detailed_config[eval_type_key][evaluator_name][activation] = activated
        detailed_config[eval_type_key][evaluator_name][description] = klass.get_description()
        detailed_config[eval_type_key][evaluator_name][advanced_class_key] = \
            _get_advanced_class_details(evaluator_name, klass)
        return True
    return False


def get_evaluator_detailed_config():
    import evaluator.TA as ta
    import evaluator.Social as social
    import evaluator.RealTime as rt
    social_key = "social"
    ta_key = "ta"
    rt_key = "real-time"
    detailed_config = {
        social_key: {},
        ta_key: {},
        rt_key: {}
    }
    evaluator_config = _get_evaluator_config()
    for evaluator_name, activated in evaluator_config.items():
        is_TA = _fill_evaluator_config(evaluator_name, activated, ta_key, ta, detailed_config)
        if not is_TA:
            is_social = _fill_evaluator_config(evaluator_name, activated, social_key, social, detailed_config)
            if not is_social:
                _fill_evaluator_config(evaluator_name, activated, rt_key, rt, detailed_config)
    return detailed_config


def update_evaluator_config(new_config):
    current_config = _get_evaluator_config()
    try:
        ConfigManager.update_evaluator_config(new_config, current_config)
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
        srv = service()
        services[srv.get_type()] = srv
        services_names.append(srv.get_name())
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


def get_full_exchange_list(remove_config_exchanges=False):
    g_config = get_bot().get_config()
    if remove_config_exchanges:
        user_exchanges = [e for e in g_config[CONFIG_EXCHANGES]]
        full_exchange_list = list(set(ccxt.exchanges) - set(user_exchanges))
    else:
        full_exchange_list = list(set(ccxt.exchanges))
    # can't handle exchanges containing UPDATED_CONFIG_SEPARATOR character in their name
    return [exchange for exchange in full_exchange_list if UPDATED_CONFIG_SEPARATOR not in exchange]


def get_current_exchange():
    g_config = get_bot().get_config()
    exchanges = g_config[CONFIG_EXCHANGES]
    if exchanges:
        return next(iter(exchanges))
    else:
        return "binance"
