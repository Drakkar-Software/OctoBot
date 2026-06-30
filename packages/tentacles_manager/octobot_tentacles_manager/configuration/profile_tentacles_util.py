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
import os
import typing

import octobot_commons.constants as commons_constants
import octobot_commons.json_util as json_util
import octobot_commons.profiles.profile_types.profile as profile_module
import octobot_commons.profiles.profile_data as profile_data_module

import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_tentacles_manager.constants as tentacles_manager_constants
import octobot_tentacles_manager.configuration.tentacle_configuration as tentacle_configuration


def build_setup_config_from_profile_data(
    profile_data: profile_data_module.ProfileData,
    output_path: typing.Optional[str] = None,
    import_registered_tentacles: bool = False,
):
    tentacle_classes = []
    for tentacle_data in profile_data.tentacles:
        tentacle_name = tentacle_data.name
        if (
            not tentacle_name
            or tentacle_name
            in tentacles_manager_constants.IGNORED_TENTACLES_NAMES_IN_TENTACLES_SETUP_CONFIG
        ):
            continue
        try:
            tentacle_class = tentacles_manager_api.get_tentacle_class_from_string(
                tentacle_name
            )
        except RuntimeError:
            continue
        tentacle_classes.append(tentacle_class.__name__)
    config_path = None
    if output_path is not None:
        config_path = os.path.join(output_path, commons_constants.CONFIG_TENTACLES_FILE)
    tentacles_setup_config = (
        tentacles_manager_api.create_tentacles_setup_config_with_tentacles(
            *tentacle_classes, config_path=config_path
        )
    )
    use_reference_registered_tentacles = not tentacles_setup_config.registered_tentacles
    tentacles_manager_api.fill_with_installed_tentacles(
        tentacles_setup_config,
        import_registered_tentacles=import_registered_tentacles,
        use_reference_registered_tentacles=use_reference_registered_tentacles,
    )
    return tentacles_setup_config


def write_specific_configs_to_profile_folder(
    profile_data: profile_data_module.ProfileData,
    output_path: str,
    is_config_update: bool,
) -> bool:
    changed = False
    specific_config_dir = os.path.join(
        output_path,
        tentacles_manager_constants.TENTACLES_SPECIFIC_CONFIG_FOLDER,
    )
    if not os.path.exists(specific_config_dir):
        os.mkdir(specific_config_dir)
    for tentacle_config in profile_data.tentacles:
        file_path = os.path.join(
            specific_config_dir,
            f"{tentacle_config.name}{tentacles_manager_constants.CONFIG_EXT}",
        )
        if is_config_update and json_util.has_same_content(
            file_path, tentacle_config.config
        ):
            continue
        changed = True
        json_util.safe_dump(
            tentacle_config.config,
            file_path,
        )
    return changed


def load_setup_config_from_profile_path(tentacles_config_path: str):
    return tentacles_manager_api.get_tentacles_setup_config(tentacles_config_path)


def read_specific_configs_by_tentacle_name(profile_folder_path: str) -> dict[str, dict]:
    specific_config_dir = os.path.join(
        profile_folder_path,
        tentacles_manager_constants.TENTACLES_SPECIFIC_CONFIG_FOLDER,
    )
    config_by_tentacle = {}
    if not os.path.isdir(specific_config_dir):
        return config_by_tentacle
    for config_file_name in os.listdir(specific_config_dir):
        if not config_file_name.endswith(tentacles_manager_constants.CONFIG_EXT):
            continue
        tentacle_name = config_file_name[
            : -len(tentacles_manager_constants.CONFIG_EXT)
        ]
        config_by_tentacle[tentacle_name] = json_util.read_file(
            os.path.join(specific_config_dir, config_file_name)
        )
    return config_by_tentacle


def collect_tentacles_data_from_setup(
    tentacles_setup_config,
    specific_configs_by_tentacle_name: typing.Optional[dict[str, dict]] = None,
) -> list[profile_data_module.TentaclesData]:
    tentacles_data = []
    preloaded_configs = specific_configs_by_tentacle_name or {}
    for (
        tentacle_type,
        tentacle_names,
    ) in tentacles_setup_config.tentacles_activation.items():
        for tentacle_class_name, is_activated in tentacle_names.items():
            if not is_activated:
                continue
            try:
                tentacle_class = tentacles_manager_api.get_tentacle_class_from_string(
                    tentacle_class_name
                )
            except Exception:
                continue
            tentacle_name = tentacle_class.get_name()
            tentacle_config = preloaded_configs.get(tentacle_name)
            if tentacle_config is None:
                tentacle_config = tentacle_configuration.get_config(
                    tentacles_setup_config, tentacle_class
                )
            tentacles_data.append(
                profile_data_module.TentaclesData(
                    name=tentacle_name,
                    config=tentacle_config or {},
                )
            )
    return tentacles_data


def collect_tentacles_data_from_filesystem_profile(
    profile: profile_module.Profile,
) -> typing.Optional[list[profile_data_module.TentaclesData]]:
    tentacles_config_path = profile.get_tentacles_config_path()
    if not os.path.isfile(tentacles_config_path):
        return None
    tentacles_setup_config = load_setup_config_from_profile_path(
        tentacles_config_path
    )
    specific_configs_by_tentacle_name = read_specific_configs_by_tentacle_name(
        profile.path
    )
    return collect_tentacles_data_from_setup(
        tentacles_setup_config,
        specific_configs_by_tentacle_name=specific_configs_by_tentacle_name,
    )
