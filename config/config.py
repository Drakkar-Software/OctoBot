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
import logging
import os
from shutil import copyfile

from cryptography.fernet import Fernet, InvalidToken

from config import CONFIG_FILE, OCTOBOT_KEY, DEFAULT_CONFIG_FILE, CONFIG_CRYPTO_CURRENCIES, CONFIG_CATEGORY_SERVICES, \
    CONFIG_STARTING_PORTFOLIO, CONFIG_EXCHANGES
from tools.dict_util import check_and_merge_values_from_reference


def load_config(config_file=CONFIG_FILE, error=True, fill_missing_fields=False):
    logger = logging.getLogger("CONFIG LOADER")
    basic_error = "Error when load config file {0}".format(config_file)
    try:
        with open(config_file) as json_data_file:
            config = json.load(json_data_file)
            if fill_missing_fields:
                _fill_missing_config_fields(config)
        return config
    except ValueError as e:
        error_str = "{0} : json decoding failed ({1})".format(basic_error, e)
        if error:
            raise Exception(error_str)
        else:
            logger.error(error_str)
    except IOError as e:
        error_str = "{0} : file opening failed ({1})".format(basic_error, e)
        if error:
            raise Exception(error_str)
        else:
            logger.error(error_str)
    except Exception as e:
        error_str = f"{basic_error} : {e}"
        if error:
            raise Exception(error_str)
        else:
            logger.error(error_str)
    return None


def init_config(config_file=CONFIG_FILE, from_config_file=DEFAULT_CONFIG_FILE):
    try:
        copyfile(from_config_file, config_file)
    except Exception as e:
        raise Exception(f"Can't init config file {e}")


def is_config_empty_or_missing(config_file=CONFIG_FILE):
    return (not os.path.isfile(config_file)) or os.stat(config_file).st_size == 0


def encrypt(data):
    try:
        return Fernet(OCTOBOT_KEY).encrypt(data.encode())
    except Exception as e:
        logging.getLogger().error(f"Failed to encrypt : {data}")
        raise e


def decrypt(data, silent_on_invalid_token=False):
    try:
        return Fernet(OCTOBOT_KEY).decrypt(data.encode()).decode()
    except InvalidToken as e:
        if not silent_on_invalid_token:
            logging.getLogger().error(f"Failed to decrypt : {data} ({e})")
        raise e
    except Exception as e:
        logging.getLogger().error(f"Failed to decrypt : {data} ({e})")
        raise e


def _fill_missing_config_fields(config, reference_config_file=DEFAULT_CONFIG_FILE):
    logger = logging.getLogger("CONFIG LOADER")
    try:
        default_config = load_config(reference_config_file, error=True)
        exception_list = [CONFIG_CRYPTO_CURRENCIES, CONFIG_STARTING_PORTFOLIO, CONFIG_EXCHANGES,
                          CONFIG_CATEGORY_SERVICES]
        check_and_merge_values_from_reference(config, default_config, exception_list, logger)
    except Exception as e:
        logger.warning(f"Impossible to check configuration file integrity ({e})")
