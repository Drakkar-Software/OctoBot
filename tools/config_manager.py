import json
import logging
import os
import shutil
from copy import copy
from functools import reduce

from config.config import load_config
from config.cst import CONFIG_DEBUG_OPTION, CONFIG_EVALUATOR_FILE_PATH, UPDATED_CONFIG_SEPARATOR, CONFIG_FILE, \
    TEMP_CONFIG_FILE, CONFIG_NOTIFICATION_INSTANCE, CONFIG_EVALUATOR, CONFIG_INTERFACES, CONFIG_ADVANCED_CLASSES, \
    CONFIG_ADVANCED_INSTANCES, CONFIG_TIME_FRAME, CONFIG_SERVICE_INSTANCE, CONFIG_CATEGORY_SERVICES


class ConfigManager:
    @staticmethod
    def save_config(config_file, config, temp_config_file, json_data=None):
        try:
            # prepare a restoration config file
            ConfigManager.restore_config(temp_config_file, config_file, remove_old_file=False)

            # edit the config file
            with open(config_file, "w") as cg_file:
                if json_data is not None:
                    cg_file.write(json_data)
                else:
                    cg_file.write(ConfigManager.jsonify_config(config))

            # check if the new config file is correct
            ConfigManager.check_config(config_file)

            # remove temp file
            ConfigManager.restore_config(temp_config_file, config_file, remove_old_file=True, restore=False)

        # when fail restore the old config
        except Exception as e:
            logging.getLogger("ConfigManager").error("Save config failed : {}".format(e))
            ConfigManager.restore_config(temp_config_file, config_file)
            raise e

    @staticmethod
    def restore_config(new_config_file, old_config_file, remove_old_file=True, restore=True):
        try:
            if restore:
                shutil.copy(new_config_file, old_config_file)

            if remove_old_file:
                os.remove(new_config_file)
        except OSError:
            pass

    @staticmethod
    def jsonify_config(config):
        # remove service instances
        for service in config[CONFIG_CATEGORY_SERVICES]:
            config[CONFIG_CATEGORY_SERVICES][service].pop(CONFIG_SERVICE_INSTANCE, None)

        # remove non config keys
        # TODO
        config.pop(CONFIG_EVALUATOR, None)
        config.pop(CONFIG_INTERFACES, None)
        config.pop(CONFIG_ADVANCED_CLASSES, None)
        config.pop(CONFIG_TIME_FRAME, None)
        config.pop(CONFIG_NOTIFICATION_INSTANCE, None)
        config.pop(CONFIG_ADVANCED_INSTANCES, None)

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
                    logging.getLogger("ConfigManager").info(f"evaluator_config.json updated: {evaluator_name} "
                                                            f"{'activated' if active else 'deactivated'}")
                    current_config[evaluator_name] = active
                    something_changed = True
        if something_changed:
            with open(CONFIG_EVALUATOR_FILE_PATH, "w+") as evaluator_config_file_w:
                evaluator_config_file_w.write(json.dumps(current_config, indent=4, sort_keys=True))

    @staticmethod
    def update_global_config(to_update_data, current_config):
        new_current_config = copy(current_config)
        updated_configs = [
            ConfigManager.parse_and_update(data_key, data_value)
            for data_key, data_value in to_update_data.items()
        ]

        # merge configs
        reduce(ConfigManager.merge_dictionaries_by_appending_keys, [new_current_config] + updated_configs)

        # save config
        ConfigManager.save_config(CONFIG_FILE, new_current_config, TEMP_CONFIG_FILE)

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
    def merge_dictionaries_by_appending_keys(dict_src, dict_dest):
        for key in dict_src:
            if key in dict_dest:
                if isinstance(dict_dest[key], dict) and isinstance(dict_src[key], dict):
                    dict_dest[key] = ConfigManager.merge_dictionaries_by_appending_keys(dict_dest[key], dict_src[key])
                elif dict_dest[key] == dict_src[key]:
                    pass  # same leaf value
                else:
                    # config
                    logging.getLogger().error(f"Conflict when merging dict with key : {key}")
            else:
                dict_dest[key] = dict_src[key]

        return dict_dest

