# pylint: disable=W1203
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
import logging
import hashlib
import cryptography.fernet as fernet

import octobot_commons
import octobot_commons.constants as commons_constants


def has_invalid_default_config_value(*config_values):
    """
    Check if config has invalid values
    :param config_values: the config values to check
    :return: the check result
    """
    return any(
        value in commons_constants.DEFAULT_CONFIG_VALUES for value in config_values
    )


def encrypt(data):
    """
    Basic encryption
    :param data: the data to encrypt
    :return: the encrypted data
    """
    try:
        return fernet.Fernet(octobot_commons.OCTOBOT_KEY).encrypt(data.encode())
    except Exception as global_exception:
        logging.getLogger().error(f"Failed to encrypt : {data}")
        raise global_exception


def decrypt(data, silent_on_invalid_token=False):
    """
    Basic decryption method
    :param data: the data to decrypt
    :param silent_on_invalid_token: if an error should be raised if a token is invalid
    :return: the decrypted data
    """
    try:
        return (
            fernet.Fernet(octobot_commons.OCTOBOT_KEY).decrypt(data.encode()).decode()
        )
    except fernet.InvalidToken as invalid_token_error:
        if not silent_on_invalid_token:
            logging.getLogger().error(
                f"Failed to decrypt : {data} ({invalid_token_error})"
            )
        raise invalid_token_error
    except Exception as global_exception:
        logging.getLogger().error(f"Failed to decrypt : {data} ({global_exception})")
        raise global_exception


def decrypt_element_if_possible(value_key, config_element, default="") -> str:
    """
    Return decrypted values, handles placeholder values
    :param value_key: the value key
    :param config_element: the config element
    :param default: the default value if no decrypt possible
    :return: True if the value can be decrypted
    """
    element = config_element.get(value_key, "")
    if element and not has_invalid_default_config_value(element):
        return decrypt(element)
    return default


def get_password_hash(password):
    """
    Returns the password's hex digest
    :param password: the password to hash
    :return: the hash digest
    """
    return hashlib.sha256(password.encode()).hexdigest()
