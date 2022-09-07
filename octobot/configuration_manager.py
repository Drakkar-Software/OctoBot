#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import copy
import os
import shutil
import json

import octobot.constants as constants
import octobot_commons.configuration as configuration
import octobot_commons.constants as common_constants
import octobot_commons.logging as logging
import octobot_commons.errors as common_errors
import octobot_tentacles_manager.constants as tentacles_manager_constants

import octobot_trading.api as trading_api

LOGGER_NAME = "Configuration"


class ConfigurationManager:
    def __init__(self):
        self.configuration_elements = {}

    def add_element(self, key, element, has_dict=False):
        self.configuration_elements[key] = ConfigurationElement(element, has_dict)

    def get_edited_config(self, key, dict_only):
        config_element = self.configuration_elements[key]
        if dict_only and config_element.has_dict:
            return config_element.edited_config.config
        return self.configuration_elements[key].edited_config

    def set_edited_config(self, key, config):
        self.configuration_elements[key].edited_config = config

    def get_startup_config(self, key, dict_only):
        config_element = self.configuration_elements[key]
        if dict_only and config_element.has_dict:
            return config_element.startup_config.config
        return self.configuration_elements[key].startup_config


class ConfigurationElement:
    def __init__(self, element, has_dict):
        self.config = element
        self.has_dict = has_dict
        self.startup_config = copy.deepcopy(element)
        self.edited_config = copy.deepcopy(element)


def config_health_check(config: configuration.Configuration, in_backtesting: bool) -> configuration.Configuration:
    logger = logging.get_logger(LOGGER_NAME)
    # 1 ensure api key encryption
    should_replace_config = False
    if common_constants.CONFIG_EXCHANGES in config.config:
        for exchange, exchange_config in config.config[common_constants.CONFIG_EXCHANGES].items():
            for key in common_constants.CONFIG_EXCHANGE_ENCRYPTED_VALUES:
                try:
                    if not configuration.handle_encrypted_value(key, exchange_config, verbose=True):
                        should_replace_config = True
                except Exception as e:
                    logger.exception(e, True,
                                     f"Exception when checking exchange config encryption: {e}")

    # 2 ensure single trader activated
    try:
        trader_enabled = trading_api.is_trader_enabled_in_config(config.config)
        if trader_enabled:
            simulator_enabled = trading_api.is_trader_simulator_enabled_in_config(config.config)
            if simulator_enabled:
                logger.error(f"Impossible to activate a trader simulator additionally to a "
                             f"real trader, simulator deactivated.")
                config.config[common_constants.CONFIG_SIMULATOR][common_constants.CONFIG_ENABLED_OPTION] = False
                should_replace_config = True
    except KeyError as e:
        logger.exception(e, True,
                         f"KeyError when checking traders activation: {e}. "
                         f"Activating trader simulator.")
        config.config[common_constants.CONFIG_SIMULATOR][common_constants.CONFIG_ENABLED_OPTION] = True
        config.config[common_constants.CONFIG_TRADER][common_constants.CONFIG_ENABLED_OPTION] = False
        should_replace_config = True

    # 3 inform about configuration issues
    if not (in_backtesting or
            trading_api.is_trader_enabled_in_config(config.config) or
            trading_api.is_trader_simulator_enabled_in_config(config.config)):
        logger.error(f"Real trader and trader simulator are deactivated in configuration. This will prevent OctoBot "
                     f"from creating any new order.")

    # 4 save fixed config if necessary
    if should_replace_config:
        try:
            config.save()
            return config
        except Exception as e:
            logger.error(f"Save of the health checked config failed : {e}, "
                         f"will use the initial config")
            config.read(should_raise=False, fill_missing_fields=True)
            return config


def init_config(
        config_file=configuration.get_user_config(),
        from_config_file=constants.DEFAULT_CONFIG_FILE
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


def set_default_profile(config, from_default_config_file=constants.DEFAULT_CONFIG_FILE):
    """
    Set current selected profile to default one based on :from_default_config_file: file content
    :param config: the current configuration
    :param from_default_config_file: the config file containing the default profile id to use
    :return: None
    """
    with open(from_default_config_file, "r") as default_config_file:
        default_config = json.loads(default_config_file.read())
    default_profile_id = default_config.get(common_constants.CONFIG_PROFILE)
    config.select_profile(default_profile_id)
    config.save()


def get_default_tentacles_url(version=None):
    beta_tentacle_bundle = os.getenv(constants.ENV_BETA_TENTACLES_PACKAGE_NAME, constants.BETA_TENTACLE_PACKAGE_NAME)
    # use beta tentacles repository for beta tentacles
    tentacles_repository = \
        os.getenv(constants.ENV_BETA_TENTACLES_REPOSITORY, constants.BETA_TENTACLES_REPOSITORY) \
        if version == beta_tentacle_bundle else \
        os.getenv(constants.ENV_TENTACLES_REPOSITORY, constants.TENTACLES_REPOSITORY)
    if version is None:
        version = constants.TENTACLES_REQUIRED_VERSION \
            if constants.TENTACLES_REQUIRED_VERSION else constants.LONG_VERSION
    return os.getenv(
        constants.ENV_TENTACLES_URL,
        f"{constants.OCTOBOT_ONLINE}/"
        f"{tentacles_repository}/"
        f"{os.getenv(constants.ENV_TENTACLES_PACKAGES_SOURCE, constants.OFFICIALS)}/"
        f"{os.getenv(constants.ENV_TENTACLES_PACKAGES_TYPE, constants.TENTACLE_PACKAGES)}/"
        f"{os.getenv(constants.ENV_TENTACLE_CATEGORY, constants.TENTACLE_CATEGORY)}/"
        f"{os.getenv(constants.ENV_TENTACLE_PACKAGE_NAME, constants.TENTACLE_PACKAGE_NAME)}/"
        f"{version}/"
        f"{tentacles_manager_constants.ANY_PLATFORM_FILE_NAME}.{tentacles_manager_constants.TENTACLES_PACKAGE_FORMAT}"
    )


def get_default_compiled_tentacles_url():
    return os.getenv(
        constants.ENV_COMPILED_TENTACLES_URL,
        f"{constants.OCTOBOT_ONLINE}/{constants.TENTACLES_REPOSITORY}/"
        f"{os.getenv(constants.ENV_TENTACLES_PACKAGES_SOURCE, constants.OFFICIALS)}/"
        f"{os.getenv(constants.ENV_COMPILED_TENTACLES_PACKAGES_TYPE, constants.TENTACLE_PACKAGES)}/"
        f"{os.getenv(constants.ENV_COMPILED_TENTACLES_CATEGORY, constants.COMPILED_TENTACLE_CATEGORY)}/"
        f"{os.getenv(constants.ENV_COMPILED_TENTACLES_SUBCATEGORY, '')}"
    )


def get_user_local_config_file():
    try:
        import octobot_commons.constants as commons_constants
        return f"{commons_constants.USER_FOLDER}/logging_config.ini"
    except ImportError:
        return None


def load_default_tentacles_config(profile_folder):
    if os.path.isdir(tentacles_manager_constants.USER_REFERENCE_TENTACLE_CONFIG_PATH):
        shutil.copyfile(tentacles_manager_constants.USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH,
                        os.path.join(profile_folder, tentacles_manager_constants.constants.CONFIG_TENTACLES_FILE))
        shutil.copytree(tentacles_manager_constants.USER_REFERENCE_TENTACLE_SPECIFIC_CONFIG_PATH,
                        os.path.join(profile_folder, tentacles_manager_constants.TENTACLES_SPECIFIC_CONFIG_FOLDER))


def migrate_from_previous_config(config):
    logger = logging.get_logger(LOGGER_NAME)
    # migrate tentacles configuration if necessary
    previous_tentacles_config = os.path.join(common_constants.USER_FOLDER, "tentacles_config")
    previous_tentacles_config_save = os.path.join(common_constants.USER_FOLDER, "tentacles_config.back")
    if os.path.isdir(previous_tentacles_config) and \
            not os.path.isdir(tentacles_manager_constants.USER_REFERENCE_TENTACLE_CONFIG_PATH):
        logger.info(
            f"Updating your tentacles configuration located in {previous_tentacles_config} into the new format. "
            f"A save of your previous tentacles config is available in {previous_tentacles_config_save}")
        shutil.copytree(previous_tentacles_config,
                        tentacles_manager_constants.USER_REFERENCE_TENTACLE_CONFIG_PATH)
        shutil.move(previous_tentacles_config, previous_tentacles_config_save)
        load_default_tentacles_config(
            os.path.join(common_constants.USER_PROFILES_FOLDER, common_constants.DEFAULT_PROFILE)
        )
    # migrate global configuration if necessary
    config_path = configuration.get_user_config()
    previous_config_save_path = f"{config_path}.back"
    logger.info(f"Updating your {config_path} into the new format. A save of your previous config is available in "
                f"{previous_config_save_path}")
    # save the current config file in case some data should be kept
    shutil.copyfile(config_path, previous_config_save_path)
    if common_constants.CONFIG_CRYPTO_CURRENCIES in config.config:
        # config migration required
        # add missing exchange enabled config
        for exchange_config in config.config[common_constants.CONFIG_EXCHANGES].values():
            exchange_config[common_constants.CONFIG_ENABLED_OPTION] = \
                exchange_config.get(common_constants.CONFIG_ENABLED_OPTION, True)
        for key in ("tentacles-packages", "performance-analyser", "PERF", "SAVE_EVALUATIONS"):
            config.config.pop(key, None)
        config.save()
        return True
    else:
        # real config issue
        return False
