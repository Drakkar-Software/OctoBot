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
import copy
import os
import shutil

import octobot_commons.config as config
import octobot_commons.config_manager as config_manager
import octobot_commons.constants as common_constants
import octobot_commons.logging as logging

import octobot_trading.api as trading_api
import octobot_trading.constants as trading_constants

LOGGER_NAME = "Configuration"


class ConfigurationManager:
    def __init__(self):
        self.configuration_elements = {}

    def add_element(self, key, element):
        self.configuration_elements[key] = ConfigurationElement(element)

    def get_edited_config(self, key):
        return self.configuration_elements[key].edited_config

    def get_startup_config(self, key):
        return self.configuration_elements[key].startup_config


class ConfigurationElement:
    def __init__(self, element):
        self.config = element
        self.startup_config = copy.deepcopy(element)
        self.edited_config = copy.deepcopy(element)


def config_health_check(config):
    # 1 ensure api key encryption
    should_replace_config = False
    if trading_constants.CONFIG_EXCHANGES in config:
        for exchange, exchange_config in config[trading_constants.CONFIG_EXCHANGES].items():
            for key in trading_constants.CONFIG_EXCHANGE_ENCRYPTED_VALUES:
                try:
                    if not config_manager._handle_encrypted_value(key, exchange_config, verbose=True):
                        should_replace_config = True
                except Exception as e:
                    logging.get_logger(LOGGER_NAME).exception(e, True,
                                                              f"Exception when checking exchange config encryption: {e}")

    # 2 ensure single trader activated
    try:
        trader_enabled = trading_api.is_trader_enabled_in_config(config)
        if trader_enabled:
            simulator_enabled = trading_api.is_trader_simulator_enabled_in_config(config)
            if simulator_enabled:
                logging.get_logger(LOGGER_NAME).error(f"Impossible to activate a trader simulator additionally to a "
                                                      f"real trader, simulator deactivated.")
                config[trading_constants.CONFIG_SIMULATOR][common_constants.CONFIG_ENABLED_OPTION] = False
                should_replace_config = True
    except KeyError as e:
        logging.get_logger(LOGGER_NAME).exception(e, True,
                                                  f"KeyError when checking traders activation: {e}. "
                                                  f"Activating trader simulator.")
        config[trading_constants.CONFIG_SIMULATOR][common_constants.CONFIG_ENABLED_OPTION] = True
        config[trading_constants.CONFIG_TRADER][common_constants.CONFIG_ENABLED_OPTION] = False
        should_replace_config = True

    # 3 save fixed config if necessary
    if should_replace_config:
        try:
            config_manager.save_config(config.get_user_config(),
                                       config,
                                       common_constants.TEMP_RESTORE_CONFIG_FILE,
                                       common_constants.CONFIG_FILE_SCHEMA,
                                       json_data=config_manager.dump_json(config))
            return config
        except Exception as e:
            logging.get_logger(LOGGER_NAME).error(f"Save of the health checked config failed : {e}, "
                                                  f"will use the initial config")
            return config.load_config(error=False, fill_missing_fields=True)


def init_config(
        config_file=config.get_user_config(), from_config_file=common_constants.DEFAULT_CONFIG_FILE
):
    """
    Initialize default config
    :param config_file: the config file path
    :param from_config_file: the default config file path
    """
    try:
        if not os.path.exists(common_constants.USER_FOLDER):
            os.makedirs(common_constants.USER_FOLDER)

        shutil.copyfile(from_config_file, config_file)
    except Exception as global_exception:
        raise Exception(f"Can't init config file {global_exception}")
