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
from tools.logging.logging_util import get_logger as get_util_logger
import os
import shutil
from copy import copy, deepcopy
from functools import reduce
import jsonschema

from config.config import load_config, decrypt, encrypt
from config import CONFIG_DEBUG_OPTION, CONFIG_EVALUATOR_FILE_PATH, UPDATED_CONFIG_SEPARATOR, CONFIG_FILE, \
    TEMP_RESTORE_CONFIG_FILE, CONFIG_NOTIFICATION_INSTANCE, CONFIG_EVALUATOR, CONFIG_INTERFACES, CONFIG_TRADING_FILE, \
    CONFIG_ADVANCED_INSTANCES, CONFIG_TIME_FRAME, CONFIG_SERVICE_INSTANCE, CONFIG_CATEGORY_SERVICES, CONFIG_EXCHANGES, \
    CONFIG_EVALUATOR_FILE, CONFIG_TRADING_FILE_PATH, CONFIG_TRADING_TENTACLES, CONFIG_ADVANCED_CLASSES, \
    DEFAULT_CONFIG_VALUES, CONFIG_TRADER_REFERENCE_MARKET, CONFIG_CRYPTO_CURRENCIES, CONFIG_CRYPTO_PAIRS, \
    DEFAULT_REFERENCE_MARKET, CONFIG_BACKTESTING, CONFIG_ANALYSIS_ENABLED_OPTION, CONFIG_ENABLED_OPTION, \
    CONFIG_METRICS, CONFIG_TRADER, CONFIG_SIMULATOR, CONFIG_FILE_SCHEMA, CONFIG_TRADING, CONFIG_ACCEPTED_TERMS, \
    TENTACLE_DEFAULT_FOLDER, CONFIG_EXCHANGE_ENCRYPTED_VALUES
from tools.symbol_util import split_symbol
from tools.dict_util import get_value_or_default
from backtesting import backtesting_enabled
from tools.errors import ConfigEvaluatorError, ConfigTradingError


def get_logger():
    return get_util_logger(ConfigManager.__name__)


class ConfigManager:

    DELETE_ELEMENT_VALUE = ""

    @staticmethod
    def save_config(config_file, config, temp_restore_config_file, json_data=None):
        try:

            # prepare a restoration config file
            ConfigManager.prepare_restore_file(temp_restore_config_file, config_file)

            new_content = ConfigManager.jsonify_config(config) if json_data is None else json_data

            # edit the config file
            with open(config_file, "w") as cg_file:
                cg_file.write(new_content)

            # check if the new config file is correct
            ConfigManager.check_config(config_file)

            # remove temp file
            ConfigManager.remove_restore_file(temp_restore_config_file)

        # when fail restore the old config
        except Exception as e:
            get_logger().error(f"Save config failed : {e}")
            ConfigManager.restore_config(temp_restore_config_file, config_file)
            raise e

    @staticmethod
    def validate_config_file(config=None, schema_file=CONFIG_FILE_SCHEMA):
        try:
            with open(schema_file) as json_schema:
                loaded_schema = json.load(json_schema)
            jsonschema.validate(instance=config, schema=loaded_schema)
        except Exception as e:
            return False, e
        return True, None

    @staticmethod
    def config_health_check(config):
        # 1 ensure api key encryption
        should_replace_config = False
        if CONFIG_EXCHANGES in config:
            for exchange, exchange_config in config[CONFIG_EXCHANGES].items():
                for key in CONFIG_EXCHANGE_ENCRYPTED_VALUES:
                    try:
                        if not ConfigManager._handle_encrypted_value(key, exchange_config, verbose=True):
                            should_replace_config = True
                    except Exception as e:
                        get_logger().error(f"Exception when checking exchange config encryption: {e}")
                        get_logger().exception(e)

        # 2 ensure single trader activated
        try:
            trader_enabled = ConfigManager.get_trader_enabled(config)
            if trader_enabled:
                simulator_enabled = ConfigManager.get_trader_simulator_enabled(config)
                if simulator_enabled:
                    get_logger().error(f"Impossible to activate a trader simulator additionally to a real trader, "
                                       f"simulator deactivated.")
                    config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION] = False
                    should_replace_config = True
        except KeyError as e:
            get_logger().error(f"KeyError when checking traders activation: {e}. Activating trader simulator.")
            get_logger().exception(e)
            config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION] = True
            config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = False
            should_replace_config = True

        # 3 save fixed config if necessary
        if should_replace_config:
            try:
                ConfigManager.save_config(CONFIG_FILE,
                                          config,
                                          TEMP_RESTORE_CONFIG_FILE,
                                          json_data=ConfigManager.dump_json(config))
                return config
            except Exception as e:
                get_logger().error(f"Save of the health checked config failed : {e}, will use the initial config")
                return load_config(error=False, fill_missing_fields=True)

    @staticmethod
    def restore_config(restore_file, target_file):
        shutil.copy(restore_file, target_file)

    @staticmethod
    def prepare_restore_file(restore_file, current_config_file):
        shutil.copy(current_config_file, restore_file)

    @staticmethod
    def remove_restore_file(restore_file):
        os.remove(restore_file)

    @staticmethod
    def _handle_encrypted_value(value_key, config_element, verbose=False):
        if value_key in config_element:
            key = config_element[value_key]
            if not ConfigManager.has_invalid_default_config_value(key):
                try:
                    decrypt(key, silent_on_invalid_token=True)
                    return True
                except Exception:
                    config_element[value_key] = encrypt(key).decode()
                    if verbose:
                        get_logger().warning(f"Non encrypted secret info found in config ({value_key}): replaced "
                                             f"value with encrypted equivalent.")
                    return False
        return True

    @staticmethod
    def jsonify_config(config):
        # check exchange keys encryption
        for exchange, exchange_config in config[CONFIG_EXCHANGES].items():
            try:
                for key in CONFIG_EXCHANGE_ENCRYPTED_VALUES:
                    ConfigManager._handle_encrypted_value(key, exchange_config)
            except Exception:
                config[CONFIG_EXCHANGES][exchange] = {key: "" for key in CONFIG_EXCHANGE_ENCRYPTED_VALUES}

        return ConfigManager.dump_json(config)

    @staticmethod
    def dump_json(json_data):
        return json.dumps(json_data, indent=4, sort_keys=True)

    @staticmethod
    def check_config(config_file):
        try:
            valid, e = ConfigManager.validate_config_file(load_config(config_file=config_file, error=True))
            if not valid:
                raise e
        except Exception as e:
            raise e

    @staticmethod
    def is_in_dev_mode(config):
        # return True if "DEV-MODE": true in config.json
        return CONFIG_DEBUG_OPTION in config and config[CONFIG_DEBUG_OPTION]

    @staticmethod
    def update_evaluator_config(to_update_data, current_config, deactivate_others):
        ConfigManager._update_activation_config(to_update_data, current_config,
                                                CONFIG_EVALUATOR_FILE_PATH, CONFIG_EVALUATOR_FILE,
                                                deactivate_others)

    @staticmethod
    def update_trading_config(to_update_data, current_config):
        ConfigManager._update_activation_config(to_update_data, current_config,
                                                CONFIG_TRADING_FILE_PATH, CONFIG_TRADING_FILE,
                                                False)

    @staticmethod
    def remove_loaded_only_element(config):

        # remove service instances
        for service in config[CONFIG_CATEGORY_SERVICES]:
            config[CONFIG_CATEGORY_SERVICES][service].pop(CONFIG_SERVICE_INSTANCE, None)

        # remove non config keys
        config.pop(CONFIG_EVALUATOR, None)
        config.pop(CONFIG_TRADING_TENTACLES, None)
        config.pop(CONFIG_INTERFACES, None)
        config.pop(CONFIG_ADVANCED_CLASSES, None)
        config.pop(CONFIG_TIME_FRAME, None)
        config.pop(CONFIG_NOTIFICATION_INSTANCE, None)
        config.pop(CONFIG_ADVANCED_INSTANCES, None)

        # remove backtesting specific differences
        if backtesting_enabled(config):
            if CONFIG_BACKTESTING in config:
                config[CONFIG_BACKTESTING].pop(CONFIG_ENABLED_OPTION, None)
                config[CONFIG_BACKTESTING].pop(CONFIG_ANALYSIS_ENABLED_OPTION, None)

    @staticmethod
    def filter_to_update_data(to_update_data, current_config):
        if backtesting_enabled(current_config):
            for key in set(to_update_data.keys()):
                # remove changes to currency config when in backtesting
                if CONFIG_CRYPTO_CURRENCIES in key:
                    to_update_data.pop(key)

    @staticmethod
    def update_global_config(to_update_data, current_config, update_input=False, delete=False):
        new_current_config = copy(current_config)

        ConfigManager.filter_to_update_data(to_update_data, current_config)

        ConfigManager.remove_loaded_only_element(new_current_config)

        # now can make a deep copy
        new_current_config = deepcopy(new_current_config)

        if delete:
            removed_configs = [ConfigManager.parse_and_update(data_key, ConfigManager.DELETE_ELEMENT_VALUE)
                               for data_key in to_update_data]
            reduce(ConfigManager.clear_dictionaries_by_keys, [new_current_config] + removed_configs)
            if update_input:
                reduce(ConfigManager.clear_dictionaries_by_keys, [current_config] + removed_configs)
        else:
            updated_configs = [
                ConfigManager.parse_and_update(data_key, data_value)
                for data_key, data_value in to_update_data.items()
            ]
            # merge configs
            reduce(ConfigManager.merge_dictionaries_by_appending_keys, [new_current_config] + updated_configs)
            if update_input:
                reduce(ConfigManager.merge_dictionaries_by_appending_keys, [current_config] + updated_configs)

        # save config
        ConfigManager.save_config(CONFIG_FILE, new_current_config, TEMP_RESTORE_CONFIG_FILE)

    @staticmethod
    def simple_save_config_update(updated_config):
        to_save_config = copy(updated_config)
        ConfigManager.remove_loaded_only_element(to_save_config)
        ConfigManager.save_config(CONFIG_FILE, to_save_config, TEMP_RESTORE_CONFIG_FILE)
        return True

    @staticmethod
    def parse_and_update(key, new_data):
        parsed_data_array = key.split(UPDATED_CONFIG_SEPARATOR)
        new_config = {}
        current_dict = new_config

        for i, _ in enumerate(parsed_data_array):
            if i > 0:
                if i == len(parsed_data_array) - 1:
                    current_dict[parsed_data_array[i]] = new_data
                else:
                    current_dict[parsed_data_array[i]] = {}
            else:
                new_config[parsed_data_array[i]] = {}

            current_dict = current_dict[parsed_data_array[i]]

        return new_config

    @staticmethod
    def are_of_compatible_type(val1, val2):
        return (
                (
                    isinstance(val1, val2.__class__) or
                    (isinstance(val1, (float, int)) and isinstance(val2, (float, int)))
                ) and isinstance(val1, (bool, str, float, int))
        )

    @staticmethod
    def merge_dictionaries_by_appending_keys(dict_dest, dict_src):
        for key in dict_src:
            src_val = dict_src[key]
            if key in dict_dest:
                dest_val = dict_dest[key]
                if isinstance(dest_val, dict) and isinstance(src_val, dict):
                    dict_dest[key] = ConfigManager.merge_dictionaries_by_appending_keys(dest_val, src_val)
                elif dest_val == src_val:
                    pass  # same leaf value
                elif ConfigManager.are_of_compatible_type(dest_val, src_val):
                    # simple type: update value
                    dict_dest[key] = src_val
                elif isinstance(dest_val, list) and isinstance(src_val, list):
                    dict_dest[key] = src_val
                else:
                    get_logger().error(f"Conflict when merging dict with key : {key}")
            else:
                dict_dest[key] = src_val

        return dict_dest

    @staticmethod
    def clear_dictionaries_by_keys(dict_dest, dict_src):
        for key in dict_src:
            src_val = dict_src[key]
            if key in dict_dest:
                dest_val = dict_dest[key]
                if src_val == ConfigManager.DELETE_ELEMENT_VALUE:
                    dict_dest.pop(key)
                elif isinstance(dest_val, dict) and isinstance(src_val, dict):
                    dict_dest[key] = ConfigManager.clear_dictionaries_by_keys(dest_val, src_val)
                else:
                    get_logger().error(f"Conflict when deleting dict element with key : {key}")

        return dict_dest

    @staticmethod
    def _update_activation_config(to_update_data, current_config, config_file_path, config_file, deactivate_others):
        from tentacles_management.class_inspector import get_class_from_string, evaluator_parent_inspection
        something_changed = False
        for element_name, activated in to_update_data.items():
            if element_name in current_config:
                active = activated if isinstance(activated, bool) else activated.lower() == "true"
                current_activation = current_config[element_name]
                if current_activation != active:
                    get_logger().info(f"{config_file} updated: {element_name} "
                                      f"{'activated' if active else 'deactivated'}")
                    current_config[element_name] = active
                    something_changed = True
        if deactivate_others:
            import evaluator.Strategies as strategies
            for element_name, activated in current_config.items():
                if element_name not in to_update_data:
                    if current_config[element_name]:
                        # do not deactivate strategies
                        config_class = get_class_from_string(element_name, strategies.StrategiesEvaluator,
                                                             strategies, evaluator_parent_inspection)
                        if config_class is None:
                            get_logger().info(f"{config_file} updated: {element_name} "
                                              f"{'deactivated'}")
                            current_config[element_name] = False
                            something_changed = True
        if something_changed:
            with open(config_file_path, "w+") as config_file_w:
                config_file_w.write(ConfigManager.dump_json(current_config))

    @staticmethod
    def update_tentacle_config(klass, config_update):
        current_config = klass.get_specific_config()
        # only update values in config update not to erase values in root config (might not be editable)
        for key, val in config_update.items():
            current_config[key] = val
        with open(klass.get_config_file_name(), "w+") as config_file_w:
            config_file_w.write(ConfigManager.dump_json(current_config))

    @staticmethod
    def factory_reset_tentacle_config(klass):
        config_file = klass.get_config_file_name()
        config_folder = klass.get_config_folder()
        config_file_name = config_file.split(config_folder)[1]
        factory_config = f"{config_folder}/{TENTACLE_DEFAULT_FOLDER}/{config_file_name}"
        shutil.copy(factory_config, config_file)

    @staticmethod
    def reload_tentacle_config(config):
        config[CONFIG_EVALUATOR] = load_config(CONFIG_EVALUATOR_FILE_PATH, False)
        if config[CONFIG_EVALUATOR] is None:
            raise ConfigEvaluatorError

        config[CONFIG_TRADING_TENTACLES] = load_config(CONFIG_TRADING_FILE_PATH, False)
        if config[CONFIG_TRADING_TENTACLES] is None:
            raise ConfigTradingError

        return config

    @staticmethod
    def has_invalid_default_config_value(*config_values):
        return any(value in DEFAULT_CONFIG_VALUES for value in config_values)

    @staticmethod
    def get_symbols(config):
        if CONFIG_CRYPTO_CURRENCIES in config and isinstance(config[CONFIG_CRYPTO_CURRENCIES], dict):
            for crypto_currency_data in config[CONFIG_CRYPTO_CURRENCIES].values():
                for symbol in crypto_currency_data[CONFIG_CRYPTO_PAIRS]:
                    yield symbol

    @staticmethod
    def get_all_currencies(config):
        currencies = set()
        for symbol in ConfigManager.get_symbols(config):
            quote, base = split_symbol(symbol)
            currencies.add(quote)
            currencies.add(base)
        return currencies

    @staticmethod
    def get_pairs(config, currency) -> []:
        pairs = []
        for symbol in ConfigManager.get_symbols(config):
            if currency in split_symbol(symbol):
                pairs.append(symbol)
        return pairs

    @staticmethod
    def get_market_pair(config, currency) -> (str, bool):
        if CONFIG_TRADING in config:
            reference_market = ConfigManager.get_reference_market(config)
            for symbol in ConfigManager.get_symbols(config):
                symbol_currency, symbol_market = split_symbol(symbol)
                if currency == symbol_currency and reference_market == symbol_market:
                    return symbol, False
                elif reference_market == symbol_currency and currency == symbol_market:
                    return symbol, True
        return "", False

    @staticmethod
    def get_reference_market(config) -> str:
        # The reference market is the currency unit of the calculated quantity value
        return get_value_or_default(config[CONFIG_TRADING], CONFIG_TRADER_REFERENCE_MARKET, DEFAULT_REFERENCE_MARKET)

    @staticmethod
    def get_metrics_enabled(config):
        if CONFIG_METRICS in config and config[CONFIG_METRICS] and \
                CONFIG_ENABLED_OPTION in config[CONFIG_METRICS]:
            return bool(config[CONFIG_METRICS][CONFIG_ENABLED_OPTION])
        else:
            return True

    @staticmethod
    def get_trader_enabled(config):
        return config[CONFIG_TRADER][CONFIG_ENABLED_OPTION]

    @staticmethod
    def get_trader_simulator_enabled(config):
        return config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION]

    @staticmethod
    def accepted_terms(config):
        if CONFIG_ACCEPTED_TERMS in config:
            return config[CONFIG_ACCEPTED_TERMS]
        return False

    @staticmethod
    def accept_terms(config, accepted):
        config[CONFIG_ACCEPTED_TERMS] = accepted
        ConfigManager.simple_save_config_update(config)
