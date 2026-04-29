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
import octobot_commons.logging as logging
import octobot_commons.constants as commons_constants


DELETE_ELEMENT_VALUE = ""


def filter_to_update_data(to_update_data, in_backtesting):
    """
    Filter data to update
    :param to_update_data: the data to be updated
    :param in_backtesting: if backtesting is enabled
    :return: the updated data
    """
    if in_backtesting:
        for key in set(to_update_data.keys()):
            # remove changes to currency config when in backtesting
            if commons_constants.CONFIG_CRYPTO_CURRENCIES in key:
                to_update_data.pop(key)


def parse_and_update(key, new_data, config_separator):
    """
    Parse and update key
    :param key: the key to update
    :param new_data: the new data
    :param config_separator: the config separator
    :return: the key updated
    """
    parsed_data_array = key.split(config_separator)
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


def merge_dictionaries_by_appending_keys(
    dict_dest, dict_src, merge_sub_array=False
) -> dict:
    """
    Merge dictionnaries by appending keys
    :param dict_dest: the destination dictionnary
    :param dict_src: the source dictionnary
    :return: the merged dictionnary
    """
    for key in dict_src:
        src_val = dict_src[key]
        if key in dict_dest:
            dest_val = dict_dest[key]
            if isinstance(dest_val, dict) and isinstance(src_val, dict):
                dict_dest[key] = merge_dictionaries_by_appending_keys(dest_val, src_val)
            elif dest_val == src_val:
                pass  # same leaf value
            elif _are_of_compatible_type(dest_val, src_val):
                # simple type: update value
                dict_dest[key] = src_val
            elif isinstance(dest_val, list) and isinstance(src_val, list):
                if merge_sub_array:
                    dict_dest[key] += src_val
                    dict_dest[key] = list(set(dict_dest[key]))
                else:
                    dict_dest[key] = src_val
            else:
                logging.get_logger("ConfigOperations").error(
                    f"Conflict when merging dict with key : {key}"
                )
        else:
            dict_dest[key] = src_val

    return dict_dest


def clear_dictionaries_by_keys(dict_dest, dict_src):
    """
    Clear dictionnaries by keys
    :param dict_dest: the destination dictionnary
    :param dict_src: the source dictionnary
    :return: the cleaned dictionnary
    """
    for key in dict_src:
        src_val = dict_src[key]
        if key in dict_dest:
            dest_val = dict_dest[key]
            if src_val == DELETE_ELEMENT_VALUE:
                dict_dest.pop(key)
            elif isinstance(dest_val, dict) and isinstance(src_val, dict):
                dict_dest[key] = clear_dictionaries_by_keys(dest_val, src_val)
            else:
                logging.get_logger("ConfigOperations").error(
                    f"Conflict when deleting dict element with key : {key}"
                )

    return dict_dest


def _are_of_compatible_type(val1, val2) -> bool:
    """
    Check if types are compatibles
    :param val1: the first value
    :param val2: the second value
    :return: True if types are compatible
    """
    return (
        isinstance(val1, val2.__class__)
        or (isinstance(val1, (float, int)) and isinstance(val2, (float, int)))
    ) and isinstance(val1, (bool, str, float, int))
