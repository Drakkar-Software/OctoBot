#  Drakkar-Software OctoBot-Tentacles-Manager
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
import contextlib
import os
import os.path as path
import shutil

import octobot_tentacles_manager.configuration as configuration
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.loaders as loaders



def _get_config_from_file_system(tentacles_setup_config, klass):
    config_path = _get_config_file_path(tentacles_setup_config, klass)
    if not config_path:
        return {}
    return configuration.read_config(config_path)


_GET_CONFIG_PROXY = _get_config_from_file_system


def set_get_config_proxy(new_proxy):
    # todo handle concurrency
    global _GET_CONFIG_PROXY
    _GET_CONFIG_PROXY = new_proxy


@contextlib.contextmanager
def local_get_config_proxy(new_proxy):
    previous_proxy = _GET_CONFIG_PROXY
    try:
        set_get_config_proxy(new_proxy)
        yield
    finally:
        set_get_config_proxy(previous_proxy)


def get_config(tentacles_setup_config, klass) -> dict:
    return _GET_CONFIG_PROXY(tentacles_setup_config, klass)


def update_config(tentacles_setup_config, klass, config_update, keep_existing=True) -> None:
    config_file = _get_config_file_path(tentacles_setup_config, klass)
    current_config = configuration.read_config(config_file)
    # only update values in config update not to erase values in root config (might not be editable)
    if keep_existing:
        # keep inactive settings in nested dicts
        current_config = _recursive_config_update(current_config, config_update)
    else:
        current_config.update(config_update)
    config_file = _get_config_file_path(tentacles_setup_config, klass, updated_config=True)
    configuration.write_config(config_file, current_config)

def _recursive_config_update(current_config: dict, config_update: dict)-> dict:
    for key, values in config_update.items():
        if isinstance(values, dict) and isinstance(current_config.get(key), dict):
            current_config[key] = _recursive_config_update(current_config[key], values)
            continue
        current_config[key] = values     
    return current_config

def factory_reset_config(tentacles_setup_config, klass) -> None:
    shutil.copy(_get_reference_config_file_path(klass), _get_config_file_path(tentacles_setup_config, klass))


def get_config_schema_path(klass) -> str:
    return path.join(_get_reference_config_path(klass), f"{klass.get_name()}{constants.CONFIG_SCHEMA_EXT}")


def get_user_tentacles_config_folder(tentacles_setup_config) -> str:
    return path.join(tentacles_setup_config.get_config_folder(), constants.TENTACLES_SPECIFIC_CONFIG_FOLDER)


def get_profile_config_specific_file_path(tentacles_setup_config, klass) -> str:
    return path.join(get_user_tentacles_config_folder(tentacles_setup_config), _get_config_file_name(klass))


def _get_reference_config_path(klass) -> str:
    return path.join(loaders.get_tentacle_module_path(klass), constants.TENTACLE_CONFIG)


def _get_reference_config_file_path(klass):
    return path.join(_get_reference_config_path(klass), _get_config_file_name(klass))


def _get_config_file_path(tentacles_setup_config, klass, updated_config=False) -> str:
    """
    Get tentacle config file path : specific if exists else reference
    :param tentacles_setup_config: the tentacles_setup_config instance
    :param klass: the tentacle class
    :param updated_config: True when called during tentacle config update
    :return: the path to the specific or reference tentacle config file
    """
    specific_config_path = get_profile_config_specific_file_path(tentacles_setup_config, klass)
    if os.path.exists(specific_config_path) or updated_config:
        return specific_config_path
    try:
        return _get_reference_config_file_path(klass)
    except TypeError:
        return ""


def _get_config_file_name(klass) -> str:
    try:
        return f"{klass.get_name()}{constants.CONFIG_EXT}"
    except AttributeError:
        return f"{klass}{constants.CONFIG_EXT}"
