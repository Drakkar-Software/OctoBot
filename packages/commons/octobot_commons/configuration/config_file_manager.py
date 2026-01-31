# pylint: disable=W0613, W0703, W0719
#  Drakkar-Software OctoBot-Commons
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
import os
import octobot_commons.logging as logging
import octobot_commons.constants as commons_constants
import octobot_commons.configuration.fields_utils as fields_utils
import octobot_commons.json_util as json_util


LOGGER_NAME = "ConfigFileManager"


def get_user_config() -> str:
    """
    Return user config path
    :return: user config path
    """
    return os.path.join(commons_constants.USER_FOLDER, commons_constants.CONFIG_FILE)


def load(config_file, should_raise=True, fill_missing_fields=False) -> dict:
    """
    Load a config from a config_file
    :param config_file: the config file path
    :param should_raise: if error should be raised
    :param fill_missing_fields: if missing fields should be filled
    :return: the loaded config
    """
    logger = logging.get_logger(LOGGER_NAME)
    basic_error = "Error when load config file {0}".format(config_file)
    try:
        config = json_util.read_file(config_file)
        return config
    except ValueError as value_error:
        error_str = f"{basic_error} : json decoding failed ({value_error})"
        if should_raise:
            raise Exception(error_str)
        logger.error(error_str)
    except IOError as io_error:
        error_str = f"{basic_error} : file opening failed ({io_error})"
        if should_raise:
            raise Exception(error_str)
        logger.error(error_str)
    except Exception as global_exception:
        error_str = f"{basic_error} : {global_exception}"
        if should_raise:
            raise Exception(error_str)
        logger.error(error_str)
    return None


def dump(
    config_file,
    config,
    schema_file=None,
) -> None:
    """
    Save a json config
    :param config_file: the config file path
    :param config: the json config
    :param schema_file: path to the json schema to validate the updated config
    """
    try:
        encrypt_values_if_necessary(config)
        if schema_file is not None:
            # check if the new config file is correct
            _check_config(config, schema_file)
    except Exception as global_exception:
        logging.get_logger(LOGGER_NAME).error(
            f"Failed to validate configuration to save : {global_exception}"
        )
        raise global_exception

    json_util.safe_dump(config, config_file)


def _check_config(content, schema_file) -> None:
    """
    Check a config file
    :param content: the config content
    :param schema_file: path to the json schema to validate the updated config
    """
    try:
        json_util.validate(content, schema_file=schema_file)
    except Exception as global_exception:
        raise global_exception


def encrypt_values_if_necessary(config) -> None:
    """
    check exchange keys encryption
    """
    if commons_constants.CONFIG_EXCHANGES not in config:
        return
    # check exchange keys encryption
    for exchange, exchange_config in config[commons_constants.CONFIG_EXCHANGES].items():
        try:
            for key in commons_constants.CONFIG_EXCHANGE_ENCRYPTED_VALUES:
                handle_encrypted_value(key, exchange_config)
        except Exception:
            config[commons_constants.CONFIG_EXCHANGES][exchange] = {
                key: "" for key in commons_constants.CONFIG_EXCHANGE_ENCRYPTED_VALUES
            }


def handle_encrypted_value(value_key, config_element, verbose=False) -> bool:
    """
    Handle encrypted value
    :param value_key: the value key
    :param config_element: the config element
    :param verbose: if verbosity is enabled
    :return: True if the value can be decrypted
    """
    if value_key in config_element:
        key = config_element[value_key]
        if not fields_utils.has_invalid_default_config_value(key):
            try:
                fields_utils.decrypt(key, silent_on_invalid_token=True)
                return True
            except Exception:
                config_element[value_key] = fields_utils.encrypt(key).decode()
                if verbose:
                    logging.get_logger(LOGGER_NAME).warning(
                        f"Non encrypted secret info found in config ({value_key}): replaced "
                        f"value with encrypted equivalent."
                    )
                return False
    return True
