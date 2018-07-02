import json
import logging
import os
import shutil

from config.config import load_config
from config.cst import CONFIG_DEBUG_OPTION


class ConfigManager:
    @staticmethod
    def save_config(config_file, config, temp_config_file):
        logger = logging.getLogger("ConfigManager")
        try:
            # prepare a restoration config file
            ConfigManager.restore_config(temp_config_file, config_file, remove_old_file=False)

            # edit the config file
            with open(config_file, "w") as cg_file:
                cg_file.write(json.dumps(config))

            # check if the new config file is correct
            ConfigManager.check_config(config_file)

        # when fail restore the old config
        except Exception as e:
            logger.error("Save config failed : {}".format(e))
            ConfigManager.restore_config(config_file, temp_config_file)
            raise e

    @staticmethod
    def restore_config(new_config_file, old_config_file, remove_old_file=True):
        try:
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
