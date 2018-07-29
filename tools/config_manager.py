import json
import logging
import os
import shutil
from copy import copy, deepcopy
from functools import reduce

from config.config import load_config, decrypt, encrypt
from config.cst import CONFIG_DEBUG_OPTION, CONFIG_EVALUATOR_FILE_PATH, UPDATED_CONFIG_SEPARATOR, CONFIG_FILE, \
    TEMP_RESTORE_CONFIG_FILE, CONFIG_NOTIFICATION_INSTANCE, CONFIG_EVALUATOR, CONFIG_INTERFACES, CONFIG_ADVANCED_CLASSES, \
    CONFIG_ADVANCED_INSTANCES, CONFIG_TIME_FRAME, CONFIG_SERVICE_INSTANCE, CONFIG_CATEGORY_SERVICES, CONFIG_EXCHANGES, \
    CONFIG_EXCHANGE_SECRET, CONFIG_EXCHANGE_KEY


def get_logger():
    return logging.getLogger(ConfigManager.__name__)


class ConfigManager:

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
    def restore_config(restore_file, target_file):
        shutil.copy(restore_file, target_file)

    @staticmethod
    def prepare_restore_file(restore_file, current_config_file):
        shutil.copy(current_config_file, restore_file)

    @staticmethod
    def remove_restore_file(restore_file):
        os.remove(restore_file)

    @staticmethod
    def jsonify_config(config):
        # check exchange keys encryption
        for exchange in config[CONFIG_EXCHANGES]:
            try:
                decrypt(config[CONFIG_EXCHANGES][exchange][CONFIG_EXCHANGE_KEY], silent_on_invalid_token=True)
            except Exception:
                config[CONFIG_EXCHANGES][exchange][CONFIG_EXCHANGE_KEY] = encrypt(config[CONFIG_EXCHANGES][exchange][CONFIG_EXCHANGE_KEY]).decode()
            try:
                decrypt(config[CONFIG_EXCHANGES][exchange][CONFIG_EXCHANGE_SECRET], silent_on_invalid_token=True)
            except Exception:
                config[CONFIG_EXCHANGES][exchange][CONFIG_EXCHANGE_SECRET] = encrypt(config[CONFIG_EXCHANGES][exchange][CONFIG_EXCHANGE_SECRET]).decode()

        return json.dumps(config, indent=4, sort_keys=True)

    @staticmethod
    def check_config(config_file):
        try:
            load_config(config_file=config_file, error=True)
        except Exception as e:
            raise e

    @staticmethod
    def is_in_dev_mode(config):
        if CONFIG_DEBUG_OPTION in config and config[CONFIG_DEBUG_OPTION]:
            return True
        return False

    @staticmethod
    def update_evaluator_config(to_update_data, current_config):
        something_changed = False
        for evaluator_name, activated in to_update_data.items():
            if evaluator_name in current_config:
                active = activated if isinstance(activated, bool) else activated.lower() == "true"
                current_activation = current_config[evaluator_name]
                if current_activation != active:
                    get_logger().info(f"evaluator_config.json updated: {evaluator_name} "
                                      f"{'activated' if active else 'deactivated'}")
                    current_config[evaluator_name] = active
                    something_changed = True
        if something_changed:
            with open(CONFIG_EVALUATOR_FILE_PATH, "w+") as evaluator_config_file_w:
                evaluator_config_file_w.write(json.dumps(current_config, indent=4, sort_keys=True))

    @staticmethod
    def update_global_config(to_update_data, current_config):
        new_current_config = copy(current_config)

        # remove service instances
        for service in new_current_config[CONFIG_CATEGORY_SERVICES]:
            new_current_config[CONFIG_CATEGORY_SERVICES][service].pop(CONFIG_SERVICE_INSTANCE, None)

        # remove non config keys
        new_current_config.pop(CONFIG_EVALUATOR, None)
        new_current_config.pop(CONFIG_INTERFACES, None)
        new_current_config.pop(CONFIG_ADVANCED_CLASSES, None)
        new_current_config.pop(CONFIG_TIME_FRAME, None)
        new_current_config.pop(CONFIG_NOTIFICATION_INSTANCE, None)
        new_current_config.pop(CONFIG_ADVANCED_INSTANCES, None)

        # now can make a deep copy
        new_current_config = deepcopy(new_current_config)

        updated_configs = [
            ConfigManager.parse_and_update(data_key, data_value)
            for data_key, data_value in to_update_data.items()
        ]

        # merge configs
        reduce(ConfigManager.merge_dictionaries_by_appending_keys, [new_current_config] + updated_configs)

        # save config
        ConfigManager.save_config(CONFIG_FILE, new_current_config, TEMP_RESTORE_CONFIG_FILE)

    @staticmethod
    def parse_and_update(key, new_data):
        parsed_data_array = key.split(UPDATED_CONFIG_SEPARATOR)
        new_config = {}
        current_dict = new_config

        for i in range(len(parsed_data_array)):
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
        return \
            (
                type(val1) == type(val2) or
                    ((type(val1) is float or type(val1) is int) and
                     (type(val2) is float or type(val2) is int))) \
            and \
            (
                    isinstance(val1, bool) or isinstance(val1, str) or
                    isinstance(val1, float) or isinstance(val1, int)
            )

    @staticmethod
    def merge_dictionaries_by_appending_keys(dict_dest, dict_src):
        for key in dict_src:
            src_val = dict_src[key]
            if key in dict_dest:
                dest_val = dict_dest[key]
                if not key == "notification-type":
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
                    get_logger().warning(f"{key} configuration editing ignored because not implemented yet")
            else:
                dict_dest[key] = src_val

        return dict_dest
