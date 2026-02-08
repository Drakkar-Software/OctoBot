#  Drakkar-Software OctoBot-Interfaces
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
import asyncio
import logging
import os.path as path
import ccxt
import ccxt.async_support
import copy
import requests.adapters
import urllib3.util.retry
import typing

import gc

import octobot_evaluators.constants as evaluators_constants
import octobot_evaluators.evaluators as evaluators
import octobot_evaluators.api as evaluators_api
import octobot_services.api as services_api
import octobot_services.constants as services_constants
import octobot_services.interfaces.util as interfaces_util
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_tentacles_manager.constants as tentacles_manager_constants
import octobot_trading.api as trading_api
import octobot_trading.constants as trading_constants
import octobot_trading.modes as trading_modes
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.storage as trading_storage
import octobot_trading.enums as trading_enums
import octobot_commons.constants as commons_constants
import octobot_commons.logging as bot_logging
import octobot_commons.enums as commons_enums
import octobot_commons.databases as commons_databases
import octobot_commons.configuration as configuration
import octobot_commons.dict_util as dict_util
import octobot_commons.tentacles_management as tentacles_management
import octobot_commons.time_frame_manager as time_frame_manager
import octobot_commons.authentication as authentication
import octobot_commons.symbols as commons_symbols
import octobot_commons.symbols as symbol_utils
import octobot_commons.display as display
import octobot_commons.errors as commons_errors
import octobot_commons.aiohttp_util as aiohttp_util
import octobot_commons.html_util as html_util
import octobot_commons
import octobot_backtesting.api as backtesting_api
import octobot.errors as errors
import octobot.community as community
import octobot.constants as octobot_constants
import octobot.enums as octobot_enums
import octobot.configuration_manager as configuration_manager
import octobot.databases_util as octobot_databases_util
import tentacles.Services.Interfaces.web_interface.constants as constants
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.models.json_schemas as json_schemas
import tentacles.Services.Interfaces.web_interface.models.trading as models_trading
import tentacles.Services.Interfaces.web_interface.plugins as web_plugins

NAME_KEY = "name"
SHORT_NAME_KEY = "n"
SYMBOL_KEY = "s"
ID_KEY = "i"
EXCLUDED_CURRENCY_SUBNAME = tuple(("X Long", "X Short"))
DESCRIPTION_KEY = "description"
REQUIREMENTS_KEY = "requirements"
COMPATIBLE_TYPES_KEY = "compatible-types"
REQUIREMENTS_COUNT_KEY = "requirements-min-count"
DEFAULT_CONFIG_KEY = "default-config"
TRADING_MODES_KEY = "trading-modes"
STRATEGIES_KEY = "strategies"
TRADING_MODE_KEY = "trading mode"
EXCHANGE_KEY = "exchange"
WEB_PLUGIN_KEY = "web plugin"
STRATEGY_KEY = "strategy"
TA_EVALUATOR_KEY = "technical evaluator"
SOCIAL_EVALUATOR_KEY = "social evaluator"
RT_EVALUATOR_KEY = "real time evaluator"
SCRIPTED_EVALUATOR_KEY = "scripted evaluator"
REQUIRED_KEY = "required"
SOCIAL_KEY = "social"
TA_KEY = "ta"
RT_KEY = "real-time"
SCRIPTED_KEY = "scripted"
ACTIVATED_STRATEGIES = "activated_strategies"
BASE_CLASSES_KEY = "base_classes"
EVALUATION_FORMAT_KEY = "evaluation_format"
CONFIG_KEY = "config"
DISPLAYED_ELEMENTS_KEY = "displayed_elements"

# tentacles from which configuration is not handled in strategies / evaluators configuration and that can be groupped
GROUPPABLE_NON_TRADING_STRATEGY_RELATED_TENTACLES = [
    tentacles_manager_constants.TENTACLES_BACKTESTING_PATH,
    tentacles_manager_constants.TENTACLES_SERVICES_PATH,
    tentacles_manager_constants.TENTACLES_TRADING_PATH
]
# tentacles for which configuration can be done in the tentacles tab of profile config
EXTRA_CONFIGURABLE_TENTACLES_TYPES = [
    tentacles_manager_constants.TENTACLES_INTERFACES_PATH
]
_TENTACLE_CONFIG_CACHE = {}

DEFAULT_EXCHANGE = "binance"
MERGED_CCXT_EXCHANGES = {
    result.__name__: [merged_exchange.__name__ for merged_exchange in merged]
    for result, merged in (
        (ccxt.async_support.kucoin, (ccxt.async_support.kucoinfutures, )),
        (ccxt.async_support.binance, (ccxt.async_support.binanceusdm, ccxt.async_support.binancecoinm)),
        (ccxt.async_support.htx, (ccxt.async_support.huobi, )),
    )
}
REMOVED_CCXT_EXCHANGES = set().union(*(set(v) for v in MERGED_CCXT_EXCHANGES.values()))
_FULL_EXCHANGE_LIST: typing.List[str] = None # type: ignore # should be accessed through get_or_init_FULL_EXCHANGE_LIST
AUTO_FILLED_EXCHANGES = None


def _get_currency_dict(name, symbol, identifier):
    return {
        SHORT_NAME_KEY: name,
        SYMBOL_KEY: symbol.upper(),
        ID_KEY: identifier
    }

# buffers to faster config page loading
markets_by_exchanges = {}
all_symbols_dict = {}
exchange_logos = {}
# can't fetch symbols from coinmarketcap.com (which is in ccxt but is not an exchange and has a paid api)
exchange_symbol_fetch_blacklist = {"coinmarketcap"}
_LOGGER = None

def _get_logger():
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = bot_logging.get_logger("WebConfigurationModel")
    return _LOGGER


def _get_evaluators_tentacles_activation():
    try:
        return tentacles_manager_api.get_tentacles_activation(interfaces_util.get_edited_tentacles_config())[
            tentacles_manager_constants.TENTACLES_EVALUATOR_PATH]
    except KeyError:
        return {}


def _get_trading_tentacles_activation():
    try:
        return tentacles_manager_api.get_tentacles_activation(interfaces_util.get_edited_tentacles_config())[
            tentacles_manager_constants.TENTACLES_TRADING_PATH]
    except KeyError:
        return {}


def _get_services_tentacles_activation():
    try:
        return tentacles_manager_api.get_tentacles_activation(interfaces_util.get_edited_tentacles_config())[
            tentacles_manager_constants.TENTACLES_SERVICES_PATH]
    except KeyError:
        return {}


def get_evaluators_tentacles_startup_activation():
    try:
        return tentacles_manager_api.get_tentacles_activation(interfaces_util.get_startup_tentacles_config())[
            tentacles_manager_constants.TENTACLES_EVALUATOR_PATH]
    except KeyError:
        return {}


def get_trading_tentacles_startup_activation():
    try:
        return tentacles_manager_api.get_tentacles_activation(interfaces_util.get_startup_tentacles_config())[
            tentacles_manager_constants.TENTACLES_TRADING_PATH]
    except KeyError:
        return {}


def get_tentacle_documentation(name, media_url, missing_tentacles: set = None):
    try:
        doc_content = tentacles_manager_api.get_tentacle_documentation(name)
        if doc_content:
            resource_url = \
                f"{media_url}/{tentacles_manager_api.get_tentacle_resources_path(name).replace(path.sep, '/')}/"
            # patch resources paths into the tentacle resource path
            return doc_content.replace(f"\n\n", "<br><br>")\
                .replace(f"{tentacles_manager_constants.TENTACLE_RESOURCES}/", resource_url)
    except KeyError as e:
        if missing_tentacles is None or name not in missing_tentacles:
            _get_logger().error(f"Impossible to load tentacle documentation for {name} ({e.__class__.__name__}: {e}). "
                                f"This is probably an issue with the {name} tentacle matadata.json file, please "
                                f"make sure this file is accurate and is referring {name} in the 'tentacles' list.")
        return ""
    except TypeError:
        # can happen when tentacles metadata.json are invalid
        return ""

def _get_strategy_activation_state(
        with_trading_modes, media_url, missing_tentacles: set, whitelist=None, backtestable_only=False
):
    import tentacles.Trading.Mode as modes
    import tentacles.Evaluator.Strategies as strategies
    strategy_config = {
        TRADING_MODES_KEY: {},
        STRATEGIES_KEY: {}
    }
    strategy_config_classes = {
        TRADING_MODES_KEY: {},
        STRATEGIES_KEY: {}
    }

    if with_trading_modes:
        trading_config = _get_trading_tentacles_activation()
        for key, val in trading_config.items():
            if whitelist and key not in whitelist:
                continue
            config_class = tentacles_management.get_class_from_string(
                key, trading_modes.AbstractTradingMode, modes, tentacles_management.trading_mode_parent_inspection
            )
            if config_class:
                if not backtestable_only or (backtestable_only and config_class.is_backtestable()):
                    strategy_config[TRADING_MODES_KEY][key] = {}
                    strategy_config[TRADING_MODES_KEY][key][constants.ACTIVATION_KEY] = val
                    strategy_config[TRADING_MODES_KEY][key][DESCRIPTION_KEY] = get_tentacle_documentation(
                        key, media_url
                    )
                    strategy_config_classes[TRADING_MODES_KEY][key] = config_class
            else:
                _add_to_missing_tentacles_if_missing(key, missing_tentacles)

    evaluator_config = _get_evaluators_tentacles_activation()
    for key, val in evaluator_config.items():
        if whitelist and key not in whitelist:
            continue
        config_class = tentacles_management.get_class_from_string(key, evaluators.StrategyEvaluator,
                                                                  strategies,
                                                                  tentacles_management.evaluator_parent_inspection)
        if config_class:
            strategy_config[STRATEGIES_KEY][key] = {}
            strategy_config[STRATEGIES_KEY][key][constants.ACTIVATION_KEY] = val
            strategy_config[STRATEGIES_KEY][key][DESCRIPTION_KEY] = get_tentacle_documentation(key, media_url)
            strategy_config_classes[STRATEGIES_KEY][key] = config_class
        else:
            _add_to_missing_tentacles_if_missing(key, missing_tentacles)

    return strategy_config, strategy_config_classes


def _add_to_missing_tentacles_if_missing(tentacle_name: str, missing_tentacles: set):
    # if tentacle_name can't be accessed in tentacles manager, this tentacle is not available
    try:
        tentacles_manager_api.get_tentacle_version(tentacle_name)
    except KeyError:
        missing_tentacles.add(tentacle_name)
    except AttributeError:
        _get_logger().debug(f"Missing tentacles data for {tentacle_name}. This is likely due to an error in the "
                            f"associated metadata.json file.")
        missing_tentacles.add(tentacle_name)


def _get_tentacle_packages():
    import tentacles.Trading.Mode as modes
    yield modes, trading_modes.AbstractTradingMode, TRADING_MODE_KEY
    import tentacles.Evaluator.Strategies as strategies
    yield strategies, evaluators.StrategyEvaluator, STRATEGY_KEY
    import tentacles.Evaluator.TA as ta
    yield ta, evaluators.AbstractEvaluator, TA_EVALUATOR_KEY
    import tentacles.Evaluator.Social as social
    yield social, evaluators.AbstractEvaluator, SOCIAL_EVALUATOR_KEY
    import tentacles.Evaluator.RealTime as rt
    yield rt, evaluators.AbstractEvaluator, RT_EVALUATOR_KEY
    import tentacles.Evaluator.Scripted as scripted
    yield scripted, evaluators.ScriptedEvaluator, SCRIPTED_EVALUATOR_KEY
    import tentacles.Trading.Exchange as exchanges
    yield exchanges, trading_exchanges.AbstractExchange, EXCHANGE_KEY
    import tentacles.Services.Interfaces as interfaces
    yield interfaces, web_plugins.AbstractWebInterfacePlugin, WEB_PLUGIN_KEY


def _get_activation_state(name, activation_states):
    return name in activation_states and activation_states[name]


def is_trading_strategy_configuration(tentacle_type):
    return tentacle_type in (
        SCRIPTED_EVALUATOR_KEY, RT_EVALUATOR_KEY, SOCIAL_EVALUATOR_KEY, TA_EVALUATOR_KEY, STRATEGY_KEY, TRADING_MODE_KEY
    )


def get_tentacle_from_string(name, media_url, with_info=True):
    for package, abstract_class, tentacle_type in _get_tentacle_packages():
        parent_inspector = tentacles_management.evaluator_parent_inspection
        if tentacle_type == TRADING_MODE_KEY:
            parent_inspector = tentacles_management.trading_mode_parent_inspection
        if tentacle_type in (EXCHANGE_KEY, WEB_PLUGIN_KEY):
            parent_inspector = tentacles_management.default_parents_inspection
        klass = tentacles_management.get_class_from_string(name, abstract_class, package, parent_inspector)
        if klass:
            if with_info:
                info = {
                    DESCRIPTION_KEY: get_tentacle_documentation(name, media_url),
                    NAME_KEY: name
                }
                if tentacle_type == TRADING_MODE_KEY:
                    _add_trading_mode_requirements_and_default_config(info, klass)
                    activation_states = _get_trading_tentacles_activation()
                elif tentacle_type == EXCHANGE_KEY:
                    activation_states = _get_trading_tentacles_activation()
                elif tentacle_type == WEB_PLUGIN_KEY:
                    activation_states = _get_services_tentacles_activation()
                else:
                    activation_states = _get_evaluators_tentacles_activation()
                    if tentacle_type == STRATEGY_KEY:
                        _add_strategy_requirements_and_default_config(info, klass)
                info[constants.ACTIVATION_KEY] = _get_activation_state(name, activation_states)
                return klass, tentacle_type, info
            else:
                return klass, tentacle_type, None
    return None, None, None


def get_tentacle_user_commands(klass):
    return klass.get_user_commands() if klass is not None and hasattr(klass, "get_user_commands") else {}


async def get_tentacle_config_and_user_inputs(tentacle_class, bot_config, tentacles_setup_config):
    return await tentacle_class.get_raw_config_and_user_inputs(
        bot_config,
        tentacles_setup_config,
        interfaces_util.get_bot_api().get_bot_id()
    )


def get_tentacle_config_and_edit_display(tentacle, tentacle_class=None, profile_id=None):
    config = interfaces_util.get_edited_config()
    tentacles_setup_config = interfaces_util.get_edited_tentacles_config()
    if profile_id:
        config = models.get_profile(profile_id).config
        tentacles_setup_config = models.get_tentacles_setup_config_from_profile_id(profile_id)
    tentacle_class = tentacle_class or tentacles_manager_api.get_tentacle_class_from_string(tentacle)
    config, user_inputs = interfaces_util.run_in_bot_main_loop(
        get_tentacle_config_and_user_inputs(tentacle_class, config, tentacles_setup_config)
    )
    display_elements = display.display_translator_factory()
    display_elements.add_user_inputs(user_inputs)
    return {
        NAME_KEY: tentacle,
        CONFIG_KEY: config or {},
        DISPLAYED_ELEMENTS_KEY: display_elements.to_json()
    }


def are_automations_enabled():
    return octobot_constants.ENABLE_AUTOMATIONS


def is_advanced_interface_enabled():
    return octobot_constants.ENABLE_ADVANCED_INTERFACE


def restart_global_automations():
    interfaces_util.run_in_bot_main_loop(
        interfaces_util.get_bot_api().get_automation().restart(),
        log_exceptions=False
    )


def get_all_automation_steps():
    return interfaces_util.get_bot_api().get_automation().get_all_steps()


def has_at_least_one_running_automation():
    return bool(get_automations_count())


def get_automations_count():
    return len(interfaces_util.get_bot_api().get_automation().automation_details)


def reset_automation_config_to_default():
    try:
        interfaces_util.get_bot_api().get_automation().reset_config()
        return True, f"{interfaces_util.get_bot_api().get_automation().get_name()} configuration reset to default values"
    except Exception as err:
        return False, str(err)


def get_tentacle_config(klass):
    return tentacles_manager_api.get_tentacle_config(interfaces_util.get_edited_tentacles_config(), klass)


def get_cached_tentacle_config(klass):
    """
    Should only be used to read static parts of a tentacle config (like requirements)
    """
    key = klass if isinstance(klass, str) else klass.get_name()
    try:
        return _TENTACLE_CONFIG_CACHE[key]
    except KeyError:
        _TENTACLE_CONFIG_CACHE[key] = get_tentacle_config(klass)
    return _TENTACLE_CONFIG_CACHE[key]


def get_tentacle_config_schema(klass):
    try:
        _get_logger().error("get_tentacle_config_schema")
        with open(tentacles_manager_api.get_tentacle_config_schema_path(klass)) as schema_file:
            return schema_file.read()
    except Exception:
        return ""


def _get_tentacle_activation_desc(name, activated, startup_val, media_url, missing_tentacles: set):
    return {
        constants.TENTACLE_CLASS_NAME: name,
        constants.ACTIVATION_KEY: activated,
        DESCRIPTION_KEY: get_tentacle_documentation(name, media_url, missing_tentacles),
        constants.STARTUP_CONFIG_KEY: startup_val
    }


def _add_tentacles_activation_desc_for_group(activation_by_group, tentacles_activation, startup_tentacles_activation,
                                             root_element, media_url, missing_tentacles: set):
    for tentacle_class_name, activated in tentacles_activation.get(root_element, {}).items():
        startup_val = startup_tentacles_activation[root_element][tentacle_class_name]
        try:
            tentacle = _get_tentacle_activation_desc(tentacle_class_name, activated, startup_val, media_url,
                                                     missing_tentacles)
            group = tentacles_manager_api.get_tentacle_group(tentacle_class_name)
            if group in activation_by_group:
                activation_by_group[group].append(tentacle)
            else:
                activation_by_group[group] = [tentacle]
        except AttributeError:
            # can happen when tentacles metadata.json are invalid
            pass


def get_extra_tentacles_config_desc(media_url, missing_tentacles: set):
    tentacles_descriptions = []
    all_tentacles = {
        tentacle_class.__name__: tentacle_class
        for tentacle_class in tentacles_management.AbstractTentacle.get_all_subclasses()
    }
    for tentacle_type in EXTRA_CONFIGURABLE_TENTACLES_TYPES:
        for tentacle_class_name in tentacles_manager_api.get_tentacles_classes_names_for_type(tentacle_type):
            if tentacle_class_name in all_tentacles and all_tentacles[tentacle_class_name].is_configurable():
                try:
                    tentacles_descriptions.append(
                        _get_tentacle_activation_desc(
                            tentacle_class_name, True, True, media_url, missing_tentacles
                        )
                    )
                except AttributeError:
                    # can happen when tentacles metadata.json are invalid
                    pass
    return tentacles_descriptions


def get_tentacles_activation_desc_by_group(media_url, missing_tentacles: set):
    tentacles_activation = tentacles_manager_api.get_tentacles_activation(interfaces_util.get_edited_tentacles_config())
    startup_tentacles_activation = tentacles_manager_api.get_tentacles_activation(
        interfaces_util.get_startup_tentacles_config())
    activation_by_group = {}
    for root_element in GROUPPABLE_NON_TRADING_STRATEGY_RELATED_TENTACLES:
        try:
            _add_tentacles_activation_desc_for_group(activation_by_group, tentacles_activation,
                                                     startup_tentacles_activation, root_element, media_url,
                                                     missing_tentacles)
        except KeyError:
            pass
    # only return tentacle groups for which there is an activation choice to simplify the config interface
    return {group: tentacles
            for group, tentacles in activation_by_group.items()
            if len(tentacles) > 1}


def update_tentacle_config(tentacle_name, config_update, tentacle_class=None, tentacles_setup_config=None):
    try:
        tentacle_class = tentacle_class or get_tentacle_from_string(tentacle_name, None, with_info=False)[0]
        if tentacle_class is None:
            return False, f"Can't find {tentacle_name} class"
        tentacles_manager_api.update_tentacle_config(
            tentacles_setup_config or interfaces_util.get_edited_tentacles_config(),
            tentacle_class,
            config_update
        )
        return True, f"{tentacle_name} updated"
    except errors.InvalidAutomationConfigError:
        raise # propagate the error to the caller
    except Exception as e:
        _get_logger().exception(e, False)
        return False, f"Error when updating tentacle config: {e}"


def update_copied_trading_id(copy_id):
    import tentacles.Trading.Mode as modes
    return update_tentacle_config(
        modes.RemoteTradingSignalsTradingMode.get_name(),
        {
            "trading_strategy": copy_id
        }
    )


def reset_config_to_default(tentacle_name, tentacle_class=None, tentacles_setup_config=None):
    try:
        tentacle_class = tentacle_class or get_tentacle_from_string(tentacle_name, None, with_info=False)[0]
        tentacles_manager_api.factory_tentacle_reset_config(
            tentacles_setup_config or interfaces_util.get_edited_tentacles_config(),
            tentacle_class
        )
        return True, f"{tentacle_name} configuration reset to default values"
    except FileNotFoundError as e:
        error_message = f"Error when resetting factory tentacle config: no default values file at {e.filename}"
        _get_logger().error(error_message)
        return False, error_message
    except Exception as e:
        _get_logger().exception(e, False)
        return False, f"Error when resetting factory tentacle config: {e}"


def _get_required_element(elements_config):
    requirements = REQUIREMENTS_KEY
    required_elements = set()
    for element_type in elements_config.values():
        for element_name, element in element_type.items():
            if element[constants.ACTIVATION_KEY]:
                if requirements in element:
                    required_elements = required_elements.union(element[requirements])
    return required_elements


def _add_strategy_requirements_and_default_config(desc, klass):
    tentacles_config = interfaces_util.get_startup_tentacles_config()
    strategy_config = get_cached_tentacle_config(klass)
    desc[REQUIREMENTS_KEY] = [evaluator for evaluator in klass.get_required_evaluators(tentacles_config,
                                                                                       strategy_config)]
    desc[COMPATIBLE_TYPES_KEY] = [evaluator for evaluator in klass.get_compatible_evaluators_types(tentacles_config,
                                                                                                   strategy_config)]
    desc[DEFAULT_CONFIG_KEY] = [evaluator for evaluator in klass.get_default_evaluators(tentacles_config,
                                                                                        strategy_config)]


def _add_trading_mode_requirements_and_default_config(desc, klass):
    tentacles_config = interfaces_util.get_startup_tentacles_config()
    mode_config = get_cached_tentacle_config(klass)
    required_strategies, required_strategies_count = klass.get_required_strategies_names_and_count(tentacles_config,
                                                                                                   mode_config)
    if required_strategies:
        desc[REQUIREMENTS_KEY] = \
            [strategy for strategy in required_strategies]
        desc[DEFAULT_CONFIG_KEY] = \
            [strategy for strategy in klass.get_default_strategies(tentacles_config, mode_config)]
        desc[REQUIREMENTS_COUNT_KEY] = required_strategies_count
    else:
        desc[REQUIREMENTS_KEY] = []
        desc[REQUIREMENTS_COUNT_KEY] = 0


def _add_strategies_requirements(strategies, strategy_config):
    required_elements = _get_required_element(strategy_config)
    for classKey, klass in strategies.items():
        _add_strategy_requirements_and_default_config(strategy_config[STRATEGIES_KEY][classKey], klass)
        strategy_config[STRATEGIES_KEY][classKey][REQUIRED_KEY] = classKey in required_elements


def _add_trading_modes_requirements(trading_modes_list, strategy_config):
    for classKey, klass in trading_modes_list.items():
        try:
            _add_trading_mode_requirements_and_default_config(strategy_config[TRADING_MODES_KEY][classKey], klass)
        except Exception as e:
            _get_logger().exception(e, False)


def get_strategy_config(
        media_url, missing_tentacles: set, with_trading_modes=True, whitelist=None, backtestable_only=False
):
    strategy_config, strategy_config_classes = _get_strategy_activation_state(with_trading_modes,
                                                                              media_url,
                                                                              missing_tentacles,
                                                                              whitelist=whitelist,
                                                                              backtestable_only=backtestable_only)
    if with_trading_modes:
        _add_trading_modes_requirements(strategy_config_classes[TRADING_MODES_KEY], strategy_config)
    _add_strategies_requirements(strategy_config_classes[STRATEGIES_KEY], strategy_config)
    return strategy_config


def get_in_backtesting_mode():
    return backtesting_api.is_backtesting_enabled(interfaces_util.get_global_config())


def accepted_terms():
    return interfaces_util.get_edited_config(dict_only=False).accepted_terms()


def accept_terms(accepted):
    return interfaces_util.get_edited_config(dict_only=False).accept_terms(accepted)


def _fill_evaluator_config(evaluator_name, activated, eval_type_key,
                           evaluator_type, detailed_config, media_url, name_filter=None):
    klass = tentacles_management.get_class_from_string(evaluator_name, evaluators.AbstractEvaluator, evaluator_type,
                                                       tentacles_management.evaluator_parent_inspection)
    filtered = name_filter and evaluator_name != name_filter
    if klass:
        if not filtered:
            detailed_config[eval_type_key][evaluator_name] = {}
            detailed_config[eval_type_key][evaluator_name][constants.ACTIVATION_KEY] = activated
            detailed_config[eval_type_key][evaluator_name][DESCRIPTION_KEY] = \
                get_tentacle_documentation(evaluator_name, media_url)
            detailed_config[eval_type_key][evaluator_name][EVALUATION_FORMAT_KEY] = "float" \
                if klass.get_eval_type() == evaluators_constants.EVALUATOR_EVAL_DEFAULT_TYPE \
                else str(klass.get_eval_type())
        return True, klass, filtered
    return False, klass, filtered


def get_evaluator_detailed_config(media_url, missing_tentacles: set, single_strategy=None):
    import tentacles.Evaluator.Strategies as strategies
    import tentacles.Evaluator.TA as ta
    import tentacles.Evaluator.Social as social
    import tentacles.Evaluator.RealTime as rt
    import tentacles.Evaluator.Scripted as scripted
    detailed_config = {
        SOCIAL_KEY: {},
        TA_KEY: {},
        RT_KEY: {},
        SCRIPTED_KEY: {}
    }
    strategy_config = {
        STRATEGIES_KEY: {}
    }
    strategy_class_by_name = {}
    evaluator_config = _get_evaluators_tentacles_activation()
    for evaluator_name, activated in evaluator_config.items():
        is_TA, klass, _ = _fill_evaluator_config(evaluator_name, activated, TA_KEY, ta, detailed_config, media_url)
        if not is_TA:
            is_social, klass, _ = _fill_evaluator_config(evaluator_name, activated, SOCIAL_KEY,
                                                         social, detailed_config, media_url)
            if not is_social:
                is_real_time, klass, _ = _fill_evaluator_config(evaluator_name, activated, RT_KEY,
                                                                rt, detailed_config, media_url)
                if not is_real_time:
                    is_scripted, klass, _ = _fill_evaluator_config(evaluator_name, activated, SCRIPTED_KEY,
                                                                   scripted, detailed_config, media_url)
                    if not is_scripted:
                        is_strategy, klass, filtered = _fill_evaluator_config(evaluator_name, activated, STRATEGIES_KEY,
                                                                              strategies, strategy_config, media_url,
                                                                              name_filter=single_strategy)
                        if is_strategy:
                            if not filtered:
                                strategy_class_by_name[evaluator_name] = klass
                        else:
                            _add_to_missing_tentacles_if_missing(evaluator_name, missing_tentacles)

    _add_strategies_requirements(strategy_class_by_name, strategy_config)
    if required_elements := _get_required_element(strategy_config):
        for eval_type in detailed_config.values():
            for eval_name, eval_details in eval_type.items():
                eval_details[REQUIRED_KEY] = eval_name in required_elements

    detailed_config[ACTIVATED_STRATEGIES] = [
        s
        for s, details in strategy_config[STRATEGIES_KEY].items()
        if details[constants.ACTIVATION_KEY]
    ]
    return detailed_config


def get_config_activated_trading_mode(tentacles_setup_config=None):
    try:
        return trading_api.get_activated_trading_mode(
            tentacles_setup_config or interfaces_util.get_bot_api().get_edited_tentacles_config()
        )
    except commons_errors.ConfigTradingError:
        return None


def get_config_activated_strategies(tentacles_setup_config=None):
    return evaluators_api.get_activated_strategies_classes(
        tentacles_setup_config or interfaces_util.get_bot_api().get_edited_tentacles_config()
    )


def get_config_activated_evaluators(tentacles_setup_config=None):
    return evaluators_api.get_activated_evaluators(
        tentacles_setup_config or interfaces_util.get_bot_api().get_edited_tentacles_config()
    )


def has_futures_exchange():
    for exchange_manager in get_live_trading_enabled_exchange_managers():
        exchange_type = trading_api.get_exchange_type(exchange_manager)
        if exchange_type is trading_enums.ExchangeTypes.FUTURE or exchange_type is trading_enums.ExchangeTypes.OPTION:
            return True
    return False


def update_tentacles_activation_config(new_config, deactivate_others=False, tentacles_setup_configuration=None):
    tentacles_setup_configuration = tentacles_setup_configuration or interfaces_util.get_edited_tentacles_config()
    try:
        updated_config = {
            element_name: activated if isinstance(activated, bool) else activated.lower() == "true"
            for element_name, activated in new_config.items()
        }
        if tentacles_manager_api.update_activation_configuration(
                tentacles_setup_configuration, updated_config, deactivate_others
        ):
            tentacles_manager_api.save_tentacles_setup_configuration(tentacles_setup_configuration)
        return True
    except Exception as e:
        _get_logger().exception(e, True, f"Error when updating tentacles activation {e}")
        return False


def get_active_exchanges():
    return trading_api.get_enabled_exchanges_names(interfaces_util.get_startup_config(dict_only=True))


async def _reset_profile_portfolio_history(current_edited_config):
    models.clear_exchanges_portfolio_history(simulated_only=True)
    if not trading_api.is_trader_simulator_enabled_in_config(current_edited_config.config):
        return
    # also reset portfolio history for exchanges enabled in config that are not enabled in the current instance
    already_reset_exchanges = {
        trading_api.get_exchange_name(exchange_manager): exchange_manager
        for exchange_manager in trading_api.get_exchange_managers_from_exchange_ids(trading_api.get_exchange_ids())
    }
    run_dbs_identifier = octobot_databases_util.get_run_databases_identifier(
        current_edited_config.config,
        interfaces_util.get_edited_tentacles_config()
    )
    enabled_exchanges = trading_api.get_enabled_exchanges_names(current_edited_config.config)
    _get_logger().info(f"Resetting simulated portfolio history for {enabled_exchanges}.")
    for exchange in enabled_exchanges:
        for is_future in (True, False):
            # force reset future and non future historical portfolio
            if exchange not in already_reset_exchanges \
                    or ((trading_api.get_exchange_type(already_reset_exchanges[exchange])
                        == trading_enums.ExchangeTypes.FUTURE) != is_future):
                metadb = commons_databases.MetaDatabase(run_dbs_identifier)
                portfolio_db = metadb.get_historical_portfolio_value_db(
                    trading_api.get_account_type(is_future, False, False, False, True), exchange
                )
                await trading_api.clear_database_storage_history(
                    trading_storage.PortfolioStorage, portfolio_db, False
                )
                await metadb.close()


def _handle_special_fields(current_edited_config, new_config):
    config = current_edited_config.config
    try:
        # replace web interface password by its hash before storage
        web_password_key = constants.UPDATED_CONFIG_SEPARATOR.join([services_constants.CONFIG_CATEGORY_SERVICES,
                                                                    services_constants.CONFIG_WEB,
                                                                    services_constants.CONFIG_WEB_PASSWORD])
        if web_password_key in new_config:
            new_config[web_password_key] = configuration.get_password_hash(new_config[web_password_key])
        # add exchange enabled param if missing
        for key in list(new_config.keys()):
            values = key.split(constants.UPDATED_CONFIG_SEPARATOR)
            if values[0] == commons_constants.CONFIG_EXCHANGES and \
                    values[1] not in config[commons_constants.CONFIG_EXCHANGES]:
                enabled_key = constants.UPDATED_CONFIG_SEPARATOR.join([commons_constants.CONFIG_EXCHANGES,
                                                                       values[1],
                                                                       commons_constants.CONFIG_ENABLED_OPTION])
                if enabled_key not in new_config:
                    new_config[enabled_key] = True
    except KeyError:
        pass


def _handle_simulated_portfolio(current_edited_config, new_config):
    # reset portfolio history if simulated portfolio has changed
    if any(
            f"{commons_constants.CONFIG_SIMULATOR}{constants.UPDATED_CONFIG_SEPARATOR}" \
            f"{commons_constants.CONFIG_STARTING_PORTFOLIO}" in key
            for key in new_config
    ):
        try:
            interfaces_util.run_in_bot_async_executor(
                _reset_profile_portfolio_history(current_edited_config)
            )
        except Exception as err:
            _get_logger().exception(err, True, f"Error when resetting portfolio simulator history {err}")


def update_global_config(new_config, delete=False):
    try:
        current_edited_config = interfaces_util.get_edited_config(dict_only=False)
        if not delete:
            _handle_special_fields(current_edited_config, new_config)
        current_edited_config.update_config_fields(new_config,
                                                   backtesting_api.is_backtesting_enabled(current_edited_config.config),
                                                   constants.UPDATED_CONFIG_SEPARATOR,
                                                   delete=delete)
        _handle_simulated_portfolio(current_edited_config, new_config)
        return True, ""
    except Exception as e:
        _get_logger().exception(e, True, f"Error when updating global config {e}")
        return False, str(e)


def activate_metrics(enable_metrics):
    current_edited_config = interfaces_util.get_edited_config(dict_only=False)
    if commons_constants.CONFIG_METRICS not in current_edited_config.config:
        current_edited_config.config[commons_constants.CONFIG_METRICS] = {
            commons_constants.CONFIG_ENABLED_OPTION: enable_metrics}
    else:
        current_edited_config.config[commons_constants.CONFIG_METRICS][
            commons_constants.CONFIG_ENABLED_OPTION] = enable_metrics
    if enable_metrics and community.CommunityManager.should_register_bot(current_edited_config):
        community.CommunityManager.background_get_id_and_register_bot(interfaces_util.get_bot_api())
    current_edited_config.save()


def activate_beta_env(enable_beta):
    new_env = octobot_enums.CommunityEnvironments.Staging if enable_beta \
        else octobot_enums.CommunityEnvironments.Production
    current_edited_config = interfaces_util.get_edited_config(dict_only=False)
    if octobot_constants.CONFIG_COMMUNITY not in current_edited_config.config:
        current_edited_config.config[octobot_constants.CONFIG_COMMUNITY] = {}
    current_edited_config.config[octobot_constants.CONFIG_COMMUNITY][
        octobot_constants.CONFIG_COMMUNITY_ENVIRONMENT] = new_env.value
    current_edited_config.save()


def get_metrics_enabled():
    return interfaces_util.get_edited_config(dict_only=False).get_metrics_enabled()


def get_beta_env_enabled_in_config():
    return octobot_constants.USE_BETA_EARLY_ACCESS or community.IdentifiersProvider.is_staging_environment_enabled(
        interfaces_util.get_edited_config(dict_only=True)
    )


def get_services_list():
    services = {}
    for service in services_api.get_available_services():
        srv = service.instance()
        if srv.get_required_config():
            # do not add services without a config, ex: GoogleService (nothing to show on the web interface)
            services[srv.get_type()] = srv
    return services


def get_notifiers_list():
    return [service.instance().get_type()
            for notifier in services_api.create_notifier_factory({}).get_available_notifiers()
            for service in notifier.REQUIRED_SERVICES]


def get_enabled_trading_pairs() -> set:
    symbols = set()
    for values in format_config_symbols(interfaces_util.get_edited_config()).values():
        if values[commons_constants.CONFIG_ENABLED_OPTION]:
            symbols = symbols.union(set(values[commons_constants.CONFIG_CRYPTO_PAIRS]))
    return symbols


def get_exchange_available_trading_pairs(exchange_manager, profile=None) -> list:
    return trading_api.get_trading_pairs(exchange_manager) if profile is None else [
        pair
        for pair in trading_api.get_all_exchange_symbols(exchange_manager)
        if pair in trading_api.get_config_symbols(profile.config, True)
    ]


def get_symbol_list(exchanges):
    result = interfaces_util.run_in_bot_async_executor(_load_markets(exchanges))
    return list(set(result))


def get_all_currencies(exchanges):
    symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in get_symbol_list(exchanges)
    ]
    return list(
        set(symbol.base for symbol in symbols).union(set(symbol.quote for symbol in symbols))
    )


def _get_filtered_exchange_symbols(symbols):
    return [res for res in symbols if octobot_commons.MARKET_SEPARATOR in res]


async def _load_market(exchange, results):
    try:
        if exchange in auto_filled_exchanges():
            async with trading_api.get_new_ccxt_client(
                exchange, {}, interfaces_util.get_edited_tentacles_config(), False
            ) as client:
                await client.load_markets()
                symbols = client.symbols
        else:
            async with getattr(ccxt.async_support, exchange)({'verbose': False}) as client:
                client.logger.setLevel(logging.INFO)    # prevent log of each request (huge on market statuses)
                await client.load_markets()
                symbols = client.symbols
        # filter symbols with a "." or no "/" because bot can't handle them for now
        markets_by_exchanges[exchange] = _get_filtered_exchange_symbols(symbols)
        results.append(markets_by_exchanges[exchange])
    except Exception as e:
        _get_logger().exception(e, True, f"error when loading symbol list for {exchange}: {e}")


def _add_merged_exchanges(exchanges):
    extended = list(exchanges)
    for exchange in exchanges:
        if exchange in MERGED_CCXT_EXCHANGES:
            for merged_exchange in MERGED_CCXT_EXCHANGES[exchange]:
                extended.append(merged_exchange)
    return extended


async def _load_markets(exchanges):
    result = []
    results = []
    fetch_coros = []
    exchange_managers = trading_api.get_exchange_managers_from_exchange_ids(
        trading_api.get_exchange_ids()
    )
    exchange_manager_by_exchange_name = {
        trading_api.get_exchange_name(exchange_manager): exchange_manager
        for exchange_manager in exchange_managers
        if not trading_api.get_is_backtesting(exchange_manager)
    }
    for exchange in _add_merged_exchanges(exchanges):
        if exchange not in exchange_symbol_fetch_blacklist:
            if exchange in exchange_manager_by_exchange_name and exchange not in markets_by_exchanges:
                markets_by_exchanges[exchange] = _get_filtered_exchange_symbols(
                    trading_api.get_all_exchange_symbols(exchange_manager_by_exchange_name[exchange])
                )
            if exchange in markets_by_exchanges:
                result += markets_by_exchanges[exchange]
            else:
                fetch_coros.append(_load_market(exchange, results))
    if fetch_coros:
        await asyncio.gather(*fetch_coros)
        for res in results:
            result += res
    return result


def get_config_time_frames() -> list:
    return time_frame_manager.get_config_time_frame(interfaces_util.get_global_config())


def get_timeframes_list(exchanges):
    timeframes_list = []
    allowed_timeframes = set(tf.value for tf in commons_enums.TimeFrames)
    for exchange in exchanges:
        if exchange not in exchange_symbol_fetch_blacklist:
            timeframes_list += interfaces_util.run_in_bot_async_executor(
                    trading_api.get_ccxt_exchange_available_time_frames(
                        exchange, interfaces_util.get_edited_tentacles_config()
                    ))
    return [commons_enums.TimeFrames(time_frame)
            for time_frame in list(set(timeframes_list))
            if time_frame in allowed_timeframes]


def get_strategy_required_time_frames(strategy_class, tentacles_setup_config=None):
    return strategy_class.get_required_time_frames(
        {},
        tentacles_setup_config or interfaces_util.get_edited_tentacles_config()
    )


def format_config_symbols(config):
    for currency, data in config[commons_constants.CONFIG_CRYPTO_CURRENCIES].items():
        if commons_constants.CONFIG_ENABLED_OPTION not in data:
            config[commons_constants.CONFIG_CRYPTO_CURRENCIES][currency] = \
                {**{commons_constants.CONFIG_ENABLED_OPTION: True}, **data}
    return config[commons_constants.CONFIG_CRYPTO_CURRENCIES]


def format_config_symbols_without_enabled_key(config):
    enabled_config = {}
    for currency, data in config[commons_constants.CONFIG_CRYPTO_CURRENCIES].items():
        if data.get(commons_constants.CONFIG_ENABLED_OPTION, False) and data[commons_constants.CONFIG_CRYPTO_PAIRS]:
            enabled_config[currency] = {
                commons_constants.CONFIG_CRYPTO_PAIRS: data[commons_constants.CONFIG_CRYPTO_PAIRS]
            }
    return enabled_config


def _is_legit_currency(currency):
    return not any(sub_name in currency for sub_name in EXCLUDED_CURRENCY_SUBNAME) and len(currency) < 30


def get_all_symbols_list():
    import tentacles.Services.Interfaces.web_interface.flask_util as flask_util
    data_provider = flask_util.BrowsingDataProvider.instance()
    all_currencies = copy.copy(data_provider.get_all_currencies())
    if not all_currencies:
        added_is = set()
        request_response = None
        base_error = "Failed to get currencies list from coingecko.com (this is a display only issue): "
        try:
            # inspired from https://github.com/man-c/pycoingecko
            session = requests.Session()
            retries = urllib3.util.retry.Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504])
            session.mount('http://', requests.adapters.HTTPAdapter(max_retries=retries))
            # first fetch top 250 currencies then add all currencies and their ids
            for url in (f"{constants.CURRENCIES_LIST_URL}1", constants.ALL_SYMBOLS_URL):
                request_response = session.get(url)
                if request_response.status_code == 429:
                    # rate limit issue
                    _get_logger().warning(f"{base_error}Too many requests, retry in a few seconds")
                    break
                for currency_data in request_response.json():
                    if _is_legit_currency(currency_data[NAME_KEY]):
                        currency_id = currency_data["id"]
                        if currency_id not in added_is:
                            added_is.add(currency_id)
                            all_currencies.append(_get_currency_dict(
                                currency_data[NAME_KEY],
                                currency_data["symbol"],
                                currency_id
                            ))
            # fetched_all: save it
            data_provider.set_all_currencies(all_currencies)
        except Exception as e:
            str_error = html_util.get_html_summary_if_relevant(e)
            details = f"code: {request_response.status_code}, error: {str_error}" \
                if request_response else {request_response}
            _get_logger().exception(e, True, f"{base_error}{str_error}")
            _get_logger().debug(f"coingecko.com response {details}")
            return {}
    return all_currencies


def get_all_symbols_list_by_symbol_type(all_symbols, config_symbols):
    spot = "SPOT trading"
    linear = "Futures trading - linear"
    inverse = "Futures trading - inverse"

    def _is_of_type(symbol, trading_type):
        parsed = commons_symbols.parse_symbol(symbol)
        if parsed.is_spot():
            return trading_type == spot
        elif parsed.is_perpetual_future():
            if trading_type == linear:
                return parsed.is_linear()
            if trading_type == inverse:
                return parsed.is_inverse()
        return False
    symbols_by_type = {
        trading_type: [symbol for symbol in all_symbols if _is_of_type(symbol, trading_type)]
        for trading_type in (
            spot, linear, inverse
        )
    }
    symbols_in_config = set().union(*(
        set(currency_details.get('pairs', [])) for currency_details in config_symbols.values()
    ))
    if symbols_in_config:
        listed_symbols = set().union(*(set(symbols) for symbols in symbols_by_type.values()))
        missing_symbols = symbols_in_config - listed_symbols
        if missing_symbols:
            symbols_by_type["Configured (missing on enabled exchanges)"] = list(missing_symbols)
    return symbols_by_type


def get_exchange_logo(exchange_name):
    try:
        return exchange_logos[exchange_name]
    except KeyError:
        try:
            exchange_logos[exchange_name] = {"image": "", "url": ""}
            if isinstance(exchange_name, str) and exchange_name != "Bitcoin":
                exchange_details = interfaces_util.run_in_bot_main_loop(
                    trading_api.get_exchange_details(
                        exchange_name,
                        exchange_name in auto_filled_exchanges(),
                        interfaces_util.get_edited_tentacles_config(),
                        interfaces_util.get_bot_api().get_aiohttp_session()
                    )
                )
                exchange_logos[exchange_name]["image"] = exchange_details.logo_url
                exchange_logos[exchange_name]["url"] = exchange_details.url
        except KeyError:
            pass
    return exchange_logos[exchange_name]


def _get_currency_logo_url(currency_id):
    return f"https://api.coingecko.com/api/v3/coins/{currency_id}?localization=false&tickers=false&market_data=" \
           f"false&community_data=false&developer_data=false&sparkline=false"


async def _fetch_currency_logo(session, data_provider, currency_id):
    if not currency_id:
        return
    async with session.get(_get_currency_logo_url(currency_id)) as resp:
        logo = None
        try:
            json_resp = await resp.json()
            logo = json_resp["image"]["large"]
        except KeyError:
            if resp.status == 429:
                _get_logger().debug(f"Rate limitted when trying to fetch logo for {currency_id}. Will retry later")
            else:
                # not rate limit: problem
                _get_logger().warning(f"Unexpected error when fetching {currency_id} currency logos: "
                                      f"status: {resp.status} text: {await resp.text()}")
        # can't fetch image for some reason, use default
        data_provider.set_currency_logo_url(currency_id, logo, dump=False)


async def _fetch_missing_currency_logos(data_provider, currency_ids):
    # always use certify_aiohttp_client_session to avoid triggering rate limit with test request
    async with aiohttp_util.certify_aiohttp_client_session() as session:
        await asyncio.gather(
            *(
                _fetch_currency_logo(session, data_provider, currency_id)
                for currency_id in currency_ids
                if data_provider.get_currency_logo_url(currency_id) is None
            )
        )
    data_provider.dump_saved_data()


def get_currency_logo_urls(currency_ids):
    import tentacles.Services.Interfaces.web_interface.flask_util as flask_util
    data_provider = flask_util.BrowsingDataProvider.instance()
    if any(
        data_provider.get_currency_logo_url(currency_id) is None
        for currency_id in currency_ids
    ):
        interfaces_util.run_in_bot_async_executor(_fetch_missing_currency_logos(data_provider, currency_ids))
    return [
        {
            "id": currency_id,
            "logo": data_provider.get_currency_logo_url(currency_id)
        }
        for currency_id in currency_ids
    ]


def get_traded_time_frames(exchange_manager, strategies=None, tentacles_setup_config=None) -> list:
    if strategies is None:
        return trading_api.get_relevant_time_frames(exchange_manager)
    strategies_time_frames = []
    for strategy_class in strategies:
        strategies_time_frames += [
            tf.value
            for tf in get_strategy_required_time_frames(strategy_class, tentacles_setup_config)
        ]
    return [
        commons_enums.TimeFrames(time_frame)
        for time_frame in trading_api.get_all_exchange_time_frames(exchange_manager)
        if time_frame in strategies_time_frames
    ]


def get_or_init_FULL_EXCHANGE_LIST():
    global _FULL_EXCHANGE_LIST
    if _FULL_EXCHANGE_LIST is None:
        _FULL_EXCHANGE_LIST = [
            exchange
            for exchange in set(ccxt.async_support.exchanges)
            if exchange not in REMOVED_CCXT_EXCHANGES
        ]
    return _FULL_EXCHANGE_LIST


def auto_filled_exchanges(tentacles_setup_config=None):
    global AUTO_FILLED_EXCHANGES
    if AUTO_FILLED_EXCHANGES is None:
        tentacles_setup_config = tentacles_setup_config or interfaces_util.get_edited_tentacles_config()
        full_exchange_list = get_or_init_FULL_EXCHANGE_LIST()
        AUTO_FILLED_EXCHANGES = [
            exchange_name
            for exchange_name in trading_api.get_auto_filled_exchange_names(tentacles_setup_config)
            if exchange_name not in full_exchange_list
        ]
        full_exchange_list.extend(AUTO_FILLED_EXCHANGES)
    return AUTO_FILLED_EXCHANGES


def get_full_exchange_list(tentacles_setup_config=None):
    auto_filled_exchanges(tentacles_setup_config)
    return get_or_init_FULL_EXCHANGE_LIST()


def get_full_configurable_exchange_list(remove_config_exchanges=False):
    g_config = interfaces_util.get_global_config()
    full_exchange_list = get_or_init_FULL_EXCHANGE_LIST()
    if remove_config_exchanges:
        user_exchanges = [e for e in g_config[commons_constants.CONFIG_EXCHANGES]]
        full_exchange_list = list(set(full_exchange_list) - set(user_exchanges))
    else:
        full_exchange_list = full_exchange_list
    # can't handle exchanges containing UPDATED_CONFIG_SEPARATOR character in their name
    return [
        exchange
        for exchange in full_exchange_list
        if constants.UPDATED_CONFIG_SEPARATOR not in exchange
    ]


def get_default_exchange():
    return ccxt.async_support.binance.__name__


def get_tested_exchange_list():
    return [
        exchange
        for exchange in trading_constants.TESTED_EXCHANGES
        if exchange in get_full_exchange_list()
    ]


def get_simulated_exchange_list():
    return [
        exchange
        for exchange in trading_constants.SIMULATOR_TESTED_EXCHANGES
        if exchange in get_full_exchange_list()
    ]


def get_other_exchange_list(remove_config_exchanges=False):
    full_list = get_full_configurable_exchange_list(remove_config_exchanges)
    return [
        exchange
        for exchange in full_list
        if exchange not in trading_constants.TESTED_EXCHANGES and
           exchange not in trading_constants.SIMULATOR_TESTED_EXCHANGES
    ]


def get_enabled_exchange_types(config_exchanges):
    return {
        config.get(commons_constants.CONFIG_EXCHANGE_TYPE, trading_enums.ExchangeTypes.SPOT.value)
        for config in config_exchanges.values()
        if config.get(commons_constants.CONFIG_ENABLED_OPTION, True)
    }


def get_exchanges_details(exchanges_config) -> dict:
    details = {}
    tentacles_setup_config = interfaces_util.get_edited_tentacles_config()
    import tentacles.Trading.Exchange as exchanges
    for exchange_name in exchanges_config:
        exchange_class = tentacles_management.get_class_from_string(
            exchange_name, trading_exchanges.AbstractExchange,
            exchanges,
            tentacles_management.default_parents_inspection
        )
        details[exchange_name] = {
            "has_websockets": trading_api.supports_websockets(exchange_name, tentacles_setup_config),
            "configurable": False if exchange_class is None else exchange_class.is_configurable(),
            "supported_exchange_types": trading_api.get_supported_exchange_types(
                exchange_name, tentacles_setup_config
            ),
            "default_exchange_type": trading_api.get_default_exchange_type(exchange_name),
        }
    return details


def get_compatibility_result(exchange_name, auth_success, compatible_account, supporter_account,
                             configured_account, supporting_exchange, error_message, exchange_type):
    return {
        "exchange": exchange_name,
        "auth_success": auth_success,
        "compatible_account": compatible_account,
        "supporter_account": supporter_account,
        "configured_account": configured_account,
        "supporting_exchange": supporting_exchange,
        "exchange_type": exchange_type,
        "error_message": error_message
    }


async def _check_account_with_other_exchange_type_if_possible(
    exchange_name: str, checked_config: dict, tentacles_setup_config, is_sandboxed: bool, supported_types: list
):
    is_compatible = False
    auth_success = False
    error = ""
    ignored_type = checked_config.get(commons_constants.CONFIG_EXCHANGE_TYPE, commons_constants.DEFAULT_EXCHANGE_TYPE)
    for supported_type in supported_types:
        if supported_type.value == ignored_type:
            continue
        checked_config[commons_constants.CONFIG_EXCHANGE_TYPE] = supported_type.value
        is_compatible, auth_success, error = await trading_api.is_compatible_account(
            exchange_name,
            checked_config,
            tentacles_setup_config,
            checked_config.get(commons_constants.CONFIG_EXCHANGE_SANDBOXED, False)
        )
        if auth_success:
            return is_compatible, auth_success, error
    # failed auth
    return is_compatible, auth_success, error,


async def _fetch_is_compatible_account(exchange_name, to_check_config,
                                       compatibility_results, is_sponsoring, is_supporter):
    try:
        checked_config = copy.deepcopy(to_check_config)
        tentacles_setup_config = interfaces_util.get_edited_tentacles_config()
        is_compatible, auth_success, error = await trading_api.is_compatible_account(
            exchange_name,
            checked_config,
            tentacles_setup_config,
            checked_config.get(commons_constants.CONFIG_EXCHANGE_SANDBOXED, False)
        )
        if not auth_success:
            supported_types = trading_api.get_supported_exchange_types(exchange_name, tentacles_setup_config)
            if len(supported_types) > 1:
                is_compatible, auth_success, error = await _check_account_with_other_exchange_type_if_possible(
                    exchange_name,
                    checked_config,
                    interfaces_util.get_edited_tentacles_config(),
                    checked_config.get(commons_constants.CONFIG_EXCHANGE_SANDBOXED, False),
                    supported_types
                )
        compatibility_results[exchange_name] = get_compatibility_result(
            exchange_name,
            auth_success,
            is_compatible,
            is_supporter,
            True,
            is_sponsoring,
            error,
            checked_config.get(commons_constants.CONFIG_EXCHANGE_TYPE, commons_constants.DEFAULT_EXCHANGE_TYPE)
        )
    except Exception as err:
        bot_logging.get_logger("ConfigurationWebInterfaceModel").exception(
            err, True, f"Error when checking {exchange_name} exchange credentials: {err}"
        )



def are_compatible_accounts(exchange_details: dict) -> dict:
    compatibility_results = {}
    check_coro = []
    for exchange, exchange_detail in exchange_details.items():
        exchange_name = exchange_detail["exchange"]
        api_key = exchange_detail["apiKey"]
        api_sec = exchange_detail["apiSecret"]
        api_pass = exchange_detail["apiPassword"]
        sandboxed = exchange_detail[commons_constants.CONFIG_EXCHANGE_SANDBOXED]
        to_check_config = copy.deepcopy(interfaces_util.get_edited_config()[commons_constants.CONFIG_EXCHANGES].get(
            exchange_name, {}))
        if _is_real_exchange_value(api_key):
            to_check_config[commons_constants.CONFIG_EXCHANGE_KEY] = configuration.encrypt(api_key).decode()
        if _is_real_exchange_value(api_sec):
            to_check_config[commons_constants.CONFIG_EXCHANGE_SECRET] = configuration.encrypt(api_sec).decode()
        if _is_real_exchange_value(api_pass):
            to_check_config[commons_constants.CONFIG_EXCHANGE_PASSWORD] = configuration.encrypt(api_pass).decode()
        to_check_config[commons_constants.CONFIG_EXCHANGE_SANDBOXED] = sandboxed
        is_compatible = auth_success = is_configured = False
        is_sponsoring = trading_api.is_sponsoring(exchange_name)
        is_supporter = authentication.Authenticator.instance().user_account.supports.is_supporting()
        error = None
        if _is_possible_exchange_config(to_check_config):
            check_coro.append(_fetch_is_compatible_account(exchange_name, to_check_config,
                                                           compatibility_results, is_sponsoring, is_supporter))
        else:
            compatibility_results[exchange_name] = get_compatibility_result(
                exchange_name,
                auth_success,
                is_compatible,
                is_supporter,
                is_configured,
                is_sponsoring,
                error,
                to_check_config.get(
                    commons_constants.CONFIG_EXCHANGE_TYPE,
                    commons_constants.DEFAULT_EXCHANGE_TYPE
                )
            )
    if check_coro:
        async def gather_wrapper(coros):
            await asyncio.gather(*coros)
        interfaces_util.run_in_bot_async_executor(
            gather_wrapper(check_coro)
        )
        # trigger garbage collector as ccxt exchange can be heavy in RAM (20MB+)
        gc.collect()
    return compatibility_results


def _is_possible_exchange_config(exchange_config):
    valid_count = 0
    for key, value in exchange_config.items():
        if key in commons_constants.CONFIG_EXCHANGE_ENCRYPTED_VALUES and _is_real_exchange_value(value):
            valid_count += 1
    # require at least 2 data to consider a configuration possible
    return valid_count >= 2


def _is_real_exchange_value(value):
    placeholder_key = "******"
    if placeholder_key in value:
        return False
    return value not in commons_constants.DEFAULT_CONFIG_VALUES


def get_current_exchange():
    for exchange_manager in interfaces_util.get_exchange_managers():
        return trading_api.get_exchange_name(exchange_manager)
    else:
        return DEFAULT_EXCHANGE


def get_sandbox_exchanges() -> list:
    return [
        trading_api.get_exchange_name(exchange_manager)
        for exchange_manager in interfaces_util.get_exchange_managers()
        if trading_api.get_exchange_manager_is_sandboxed(exchange_manager)
    ]


def get_distribution() -> octobot_enums.OctoBotDistribution:
    return configuration_manager.get_distribution(interfaces_util.get_edited_config())


def change_reference_market_on_config_currencies(old_base_currency: str, new_quote_currency: str) -> bool:
    """
    Change the base currency from old to new for all configured pair
    :return: bool, str
    """
    success = True
    message = "Reference market changed for each pair using the old reference market"
    try:
        config_currencies = format_config_symbols(interfaces_util.get_edited_config())
        for currencies_config in config_currencies.values():
            currencies_config[commons_constants.CONFIG_CRYPTO_PAIRS] = \
                list(set([
                    _change_base(pair, new_quote_currency)
                    for pair in currencies_config[commons_constants.CONFIG_CRYPTO_PAIRS]
                ]))
        interfaces_util.get_edited_config(dict_only=False).save()
    except Exception as e:
        message = f"Error while changing reference market on currencies list: {e}"
        success = False
        bot_logging.get_logger("ConfigurationWebInterfaceModel").exception(e, False)
    return success, message


def _change_base(pair, new_quote_currency):
    parsed_symbol = commons_symbols.parse_symbol(pair)
    parsed_symbol.quote = new_quote_currency
    return parsed_symbol.merged_str_symbol()


def send_command_to_activated_tentacles(command, wait_for_processing=True):
    trading_mode_name = get_config_activated_trading_mode().get_name()
    evaluator_names = [
        evaluator.get_name()
        for evaluator in get_config_activated_evaluators()
    ]
    send_command_to_tentacles(command, [trading_mode_name] + evaluator_names, wait_for_processing=wait_for_processing)


def send_command_to_tentacles(command, tentacle_names: list, wait_for_processing=True):
    for tentacle_name in tentacle_names:
        interfaces_util.run_in_bot_main_loop(
            services_api.send_user_command(
                interfaces_util.get_bot_api().get_bot_id(),
                tentacle_name,
                command,
                None,
                wait_for_processing=wait_for_processing
            )
        )


def reload_scripts():
    try:
        send_command_to_activated_tentacles(commons_enums.UserCommands.RELOAD_SCRIPT.value)
        return {"success": True}
    except Exception as e:
        _get_logger().exception(e, True, f"Failed to reload scripts: {e}")
        raise


def reload_activated_tentacles_config():
    try:
        send_command_to_activated_tentacles(commons_enums.UserCommands.RELOAD_CONFIG.value)
        return {"success": True}
    except Exception as e:
        _get_logger().exception(e, True, f"Failed to reload configurations: {e}")
        raise


def reload_tentacle_config(tentacle_name):
    try:
        send_command_to_tentacles(commons_enums.UserCommands.RELOAD_CONFIG.value, [tentacle_name])
        return {"success": True}
    except Exception as e:
        _get_logger().exception(e, True, f"Failed to reload {tentacle_name} configuration: {e}")
        raise


def update_config_currencies(currencies: dict, replace: bool=False):
    """
    Update the configured currencies dict
    :param currencies: currencies dict
    :param replace: replace the current list
    :return: bool, str
    """
    success = True
    message = "Currencies list updated"
    try:
        config_currencies = interfaces_util.get_edited_config()[commons_constants.CONFIG_CRYPTO_CURRENCIES]
        # prevent format issues
        checked_currencies = {
            currency: {
                commons_constants.CONFIG_CRYPTO_PAIRS: values[commons_constants.CONFIG_CRYPTO_PAIRS],
                commons_constants.CONFIG_ENABLED_OPTION: values.get(commons_constants.CONFIG_ENABLED_OPTION, True)
            }
            for currency, values in currencies.items()
            if (
                isinstance(values.get(commons_constants.CONFIG_ENABLED_OPTION, True), bool)
                and commons_constants.CONFIG_CRYPTO_PAIRS in values
                and isinstance(values[commons_constants.CONFIG_CRYPTO_PAIRS], list)
                and all(isinstance(pair, str) for pair in commons_constants.CONFIG_CRYPTO_PAIRS)
            )
        }
        interfaces_util.get_edited_config()[commons_constants.CONFIG_CRYPTO_CURRENCIES] = (
            checked_currencies if replace
            else configuration.merge_dictionaries_by_appending_keys(
                config_currencies, checked_currencies, merge_sub_array=True
            )
        )
        interfaces_util.get_edited_config(dict_only=False).save()
    except Exception as e:
        message = f"Error while updating currencies list: {e}"
        success = False
        bot_logging.get_logger("ConfigurationWebInterfaceModel").exception(e, False)
    return success, message


def get_config_required_candles_count(exchange_manager):
    return trading_api.get_required_historical_candles_count(exchange_manager)


def get_live_trading_enabled_exchange_managers():
    return [
        exchange_manager
        for exchange_manager in trading_api.get_exchange_managers_from_exchange_ids(trading_api.get_exchange_ids())
        if not trading_api.get_is_backtesting(exchange_manager)
        and trading_api.is_trader_existing_and_enabled(exchange_manager)
    ]


def save_distribution_configuration(
    trading_mode_name: str,
    trading_mode_configuration: dict,
    enabled_exchange: typing.Optional[str],
    trading_pair: typing.Optional[str],
    exchange_configurations: list[dict],
    trading_simulator_configuration: dict,
    simulated_portfolio_configuration: list[dict],
    exchanges_to_enable: typing.Optional[list[str]] = None,
) -> None:
    _save_distribution_tentacle_config(trading_mode_name, trading_mode_configuration)
    _save_distribution_user_config(
        enabled_exchange, trading_pair, exchange_configurations,
        trading_simulator_configuration, simulated_portfolio_configuration,
        exchanges_to_enable,
    )


def _save_distribution_user_config(
    enabled_exchange: typing.Optional[str],
    trading_pair: typing.Optional[str],
    exchange_configurations: list[dict],
    trading_simulator_configuration: dict,
    simulated_portfolio_configuration: list[dict],
    exchanges_to_enable: typing.Optional[list[str]] = None,
) -> None:
    current_edited_config = interfaces_util.get_edited_config(dict_only=False)

    # exchanges: regenerate the whole configuration
    exchange_config_update = json_schemas.json_exchange_config_to_config(
        exchange_configurations, False
    )
    if exchange_config_update and enabled_exchange not in exchange_config_update:
        # removed enabled exchange from exchange configs: use 1st exchange instead
        enabled_exchange = next(iter(exchange_config_update))

    # Determine which exchanges to enable
    if exchanges_to_enable is None:
        exchanges_to_enable = [enabled_exchange] if enabled_exchange else []
    
    for exchange in exchanges_to_enable:
        if exchange and exchange in exchange_config_update:
            # only enable selected exchanges, force spot trading
            exchange_config_update[exchange].update({
                commons_constants.CONFIG_ENABLED_OPTION: True,
                commons_constants.CONFIG_EXCHANGE_TYPE: commons_constants.CONFIG_EXCHANGE_SPOT,
            })
    
    current_exchanges_config = copy.deepcopy(current_edited_config.config[commons_constants.CONFIG_EXCHANGES])
    # nested_update_dict to keep nested key/val that might have been in previous config but are not in update
    # don't pass current_exchanges_config directly to really delete exchanges
    updated_exchange_config = {
        exchange: exchange_config
        for exchange, exchange_config in current_exchanges_config.items()
        if exchange in exchange_config_update
    }
    dict_util.nested_update_dict(updated_exchange_config, exchange_config_update)

    # currencies: regenerate the whole configuration
    updated_currencies_config = {
        trading_pair: {
            commons_constants.CONFIG_ENABLED_OPTION: True,
            commons_constants.CONFIG_CRYPTO_PAIRS: [trading_pair]
        }
    } if trading_pair else {}

    # trader simulator
    simulated_enabled = trading_simulator_configuration[commons_constants.CONFIG_ENABLED_OPTION]
    updated_simulator_config = copy.deepcopy(current_edited_config.config[commons_constants.CONFIG_SIMULATOR])
    previous_simulated_portfolio = copy.deepcopy(
        updated_simulator_config.get(commons_constants.CONFIG_STARTING_PORTFOLIO)
    )
    simulator_config_update = {
        **trading_simulator_configuration, **{
            commons_constants.CONFIG_STARTING_PORTFOLIO: json_schemas.json_simulated_portfolio_to_config(
                simulated_portfolio_configuration
            )
        }
    }
    updated_portfolio = simulator_config_update[commons_constants.CONFIG_STARTING_PORTFOLIO]
    changed_portfolio = _filter_distribution_0_values(previous_simulated_portfolio) != _filter_distribution_0_values(updated_portfolio)
    # replace portfolio to allow asset removal (otherwise nested_update_dict will never remove assets)
    updated_simulator_config[commons_constants.CONFIG_STARTING_PORTFOLIO] = updated_portfolio
    dict_util.nested_update_dict(updated_simulator_config, simulator_config_update)

    # real trader
    updated_trader_config = copy.deepcopy(current_edited_config.config[commons_constants.CONFIG_TRADER])
    # only update the "enabled" state
    updated_trader_config[commons_constants.CONFIG_ENABLED_OPTION] = not simulated_enabled

    # trading
    updated_trading_config = copy.deepcopy(current_edited_config.config[commons_constants.CONFIG_TRADING])
    if trading_pair:
        # only update the reference market
        updated_trading_config[commons_constants.CONFIG_TRADER_REFERENCE_MARKET] = (
            symbol_utils.parse_symbol(trading_pair).quote
        )

    update = {
        commons_constants.CONFIG_CRYPTO_CURRENCIES: updated_currencies_config,
        commons_constants.CONFIG_EXCHANGES: updated_exchange_config,
        commons_constants.CONFIG_TRADING: updated_trading_config,
        commons_constants.CONFIG_TRADER: updated_trader_config,
        commons_constants.CONFIG_SIMULATOR: updated_simulator_config,
    }
    # apply & save changes
    current_edited_config.config.update(update)
    current_edited_config.save()
    _get_distribution_logger().info(
        f"Configuration updated. Current profile: {current_edited_config.profile.name}"
    )
    if changed_portfolio:
        _get_distribution_logger().info("Simulated portfolio changed: resetting simulated portfolio content.")
        models_trading.clear_exchanges_portfolio_history(simulated_only=True)


def _save_distribution_tentacle_config(
    trading_mode_name: str,
    trading_mode_configuration: dict,
) -> None:
    tentacle_class = tentacles_manager_api.get_tentacle_class_from_string(trading_mode_name)
    tentacles_manager_api.update_tentacle_config(
        interfaces_util.get_edited_tentacles_config(),
        tentacle_class,
        trading_mode_configuration,
        keep_existing=False,
    )
    _get_distribution_logger().info(
        f"{trading_mode_name} configuration updated."
    )


def _filter_distribution_0_values(elements: dict) -> dict:
    return {
        key: val
        for key, val in elements.items()
        if val
    }


def _get_distribution_logger():
    return bot_logging.get_logger("DistributionConfigurationModel")
