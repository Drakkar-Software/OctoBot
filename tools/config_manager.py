import json
import logging
import os
import shutil

from config.config import load_config
from config.cst import CONFIG_DEBUG_OPTION, CONFIG_EVALUATOR_FILE_PATH


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
                    cg_file.write(json.dumps(config))

            # check if the new config file is correct
            ConfigManager.check_config(config_file)

            # remove temp file
            ConfigManager.restore_config(temp_config_file, config_file, remove_old_file=True, restore=False)

        # when fail restore the old config
        except Exception as e:
            logging.getLogger("ConfigManager").error("Save config failed : {}".format(e))
            ConfigManager.restore_config(config_file, temp_config_file)
            raise e

    @staticmethod
    def restore_config(new_config_file, old_config_file, remove_old_file=True, restore=True):
        try:
            if restore:
                shutil.copy(old_config_file, new_config_file)

            if remove_old_file:
                os.remove(old_config_file)
        except OSError:
            pass

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
                    logging.getLogger("ConfigManager").info("evaluator_config.json updated: {0} {1}".
                                                            format(evaluator_name,
                                                                   "activated" if active else "deactivated"))
                    current_config[evaluator_name] = active
                    something_changed = True
        if something_changed:
            with open(CONFIG_EVALUATOR_FILE_PATH, "w+") as evaluator_config_file_w:
                evaluator_config_file_w.write(json.dumps(current_config, indent=4, sort_keys=True))
