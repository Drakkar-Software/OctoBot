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
from __future__ import annotations

import contextlib
import contextvars
import os
import os.path as path
import shutil
import typing

import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.profile_edit_gate as profile_edit_gate_module
import octobot_commons.constants as commons_constants
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_tentacles_manager.configuration as configuration
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.loaders as loaders

if typing.TYPE_CHECKING:
    import octobot_tentacles_manager.configuration.tentacles_setup_configuration as tentacles_setup_configuration


_LOCAL_GET_CONFIG_OVERRIDE: contextvars.ContextVar = contextvars.ContextVar(
    "local_get_config_override", default=None
)


def _get_config_from_file_system(tentacles_setup_config, klass):
    config_path = _get_config_file_path(tentacles_setup_config, klass)
    if not config_path:
        return {}
    return configuration.read_config(config_path)


def _update_config_from_file_system(tentacles_setup_config, klass, config_update, keep_existing=True) -> None:
    profile = tentacles_setup_config.profile
    edit_gate = None
    if profile is not None:
        profile_storage = profile.get_profile_storage()
        if profile_storage is not None:
            edit_gate = profile_storage.edit_gate
            edit_gate.assert_edit_allowed(
                profile,
                profile_edit_gate_module.ProfileEditType.TENTACLE_CONFIG,
            )
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
    if edit_gate is not None and profile is not None:
        edit_gate.log_edit_saved(
            profile,
            profile_edit_gate_module.ProfileEditType.TENTACLE_CONFIG,
            config_file,
            tentacle=klass.get_name(),
        )


def _recursive_config_update(current_config: dict, config_update: dict)-> dict:
    for key, values in config_update.items():
        if isinstance(values, dict) and isinstance(current_config.get(key), dict):
            current_config[key] = _recursive_config_update(current_config[key], values)
            continue
        current_config[key] = values
    return current_config


def _factory_reset_config_from_file_system(tentacles_setup_config, klass) -> None:
    shutil.copy(_get_reference_config_file_path(klass), _get_config_file_path(tentacles_setup_config, klass))


def _get_config_for_profile(tentacles_setup_config, klass) -> dict:
    profile = tentacles_setup_config.profile
    file_or_factory_config = _get_config_from_file_system(tentacles_setup_config, klass)
    if profile is None or not profile.is_profile_data_tentacle_backed():
        return file_or_factory_config
    tentacle_name = klass.get_name()
    for tentacle_data in profile.get_profile_data().tentacles:
        if tentacle_data.name == tentacle_name:
            if tentacle_data.config:
                return _recursive_config_update(dict(file_or_factory_config), tentacle_data.config)
            return file_or_factory_config
    return file_or_factory_config


def _update_config_for_profile(
    tentacles_setup_config, klass, config_update, keep_existing=True
) -> None:
    profile = tentacles_setup_config.profile
    if profile is None or not profile.is_profile_data_tentacle_backed():
        _update_config_from_file_system(
            tentacles_setup_config, klass, config_update, keep_existing=keep_existing
        )
        return
    tentacle_name = klass.get_name()
    profile_data = profile.get_profile_data()
    updated_tentacle = None
    for tentacle_data in profile_data.tentacles:
        if tentacle_data.name == tentacle_name:
            updated_tentacle = tentacle_data
            break
    if updated_tentacle is None:
        updated_tentacle = profile_data_module.TentaclesData(
            name=tentacle_name, config={}
        )
        profile_data.tentacles.append(updated_tentacle)
    updated_tentacle.activated = tentacles_manager_api.is_tentacle_activated_in_tentacles_setup_config(
        tentacles_setup_config,
        tentacle_name,
        default_value=False,
    )
    if keep_existing:
        merged_config = dict(updated_tentacle.config or {})
        merged_config.update(config_update)
        updated_tentacle.config = merged_config
    else:
        updated_tentacle.config = config_update


def _factory_reset_config_for_profile(tentacles_setup_config, klass) -> None:
    profile = tentacles_setup_config.profile
    if profile is None or not profile.is_profile_data_tentacle_backed():
        _factory_reset_config_from_file_system(tentacles_setup_config, klass)
        return
    tentacle_name = klass.get_name()
    profile_data = profile.get_profile_data()
    profile_data.tentacles = [
        tentacle_data
        for tentacle_data in profile_data.tentacles
        if tentacle_data.name != tentacle_name
    ]


@contextlib.contextmanager
def local_get_config_proxy(new_proxy):
    override_token = _LOCAL_GET_CONFIG_OVERRIDE.set(new_proxy)
    try:
        yield
    finally:
        _LOCAL_GET_CONFIG_OVERRIDE.reset(override_token)


def get_config(
    tentacles_setup_config: tentacles_setup_configuration.TentaclesSetupConfiguration,
    klass,
) -> dict:
    local_override = _LOCAL_GET_CONFIG_OVERRIDE.get()
    if local_override is not None:
        return local_override(tentacles_setup_config, klass)
    if tentacles_setup_config.profile:
        return _get_config_for_profile(tentacles_setup_config, klass)
    return _get_config_from_file_system(tentacles_setup_config, klass)


def update_config(
    tentacles_setup_config: tentacles_setup_configuration.TentaclesSetupConfiguration,
    klass,
    config_update,
    keep_existing=True,
) -> None:
    if tentacles_setup_config.profile:
        return _update_config_for_profile(
            tentacles_setup_config, klass, config_update, keep_existing=keep_existing
        )
    return _update_config_from_file_system(
        tentacles_setup_config, klass, config_update, keep_existing=keep_existing
    )


def factory_reset_config(
    tentacles_setup_config: tentacles_setup_configuration.TentaclesSetupConfiguration,
    klass,
) -> None:
    if tentacles_setup_config.profile:
        return _factory_reset_config_for_profile(tentacles_setup_config, klass)
    return _factory_reset_config_from_file_system(tentacles_setup_config, klass)


def get_config_schema_path(klass) -> str:
    return path.join(_get_reference_config_path(klass), f"{klass.get_name()}{constants.CONFIG_SCHEMA_EXT}")


def get_user_tentacles_config_folder(tentacles_setup_config) -> str:
    profile = tentacles_setup_config.profile
    config_folder = tentacles_setup_config.get_config_folder()
    if profile is not None:
        profile_storage = profile.get_profile_storage()
        if profile_storage is not None:
            config_folder = profile_storage.edit_gate.resolve_writable_path(
                profile,
                profile_edit_gate_module.ProfileEditType.TENTACLE_CONFIG,
            )
    return path.join(config_folder, commons_constants.TENTACLES_SPECIFIC_CONFIG_FOLDER)


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
