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
import os.path as path
import sys
from typing import TYPE_CHECKING

import octobot_commons.tentacles_management as tentacles_management

import octobot_tentacles_manager.api as api
import octobot_tentacles_manager.configuration as configuration
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.util as util
import octobot_tentacles_manager.managers as managers

if TYPE_CHECKING:
    from octobot_tentacles_manager.configuration import TentaclesSetupConfiguration


async def ensure_setup_configuration(tentacle_path=constants.TENTACLES_PATH, bot_path=constants.DEFAULT_BOT_PATH,
                                     bot_install_dir=constants.DEFAULT_BOT_INSTALL_DIR) -> None:
    if not path.exists(path.join(bot_path, constants.USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH)):
        await api.repair_installation(tentacle_path, bot_path, bot_install_dir, verbose=False)


def refresh_profile_tentacles_setup_config(
        profile_folder,
        tentacle_path=constants.TENTACLES_PATH,
        bot_installation_path=constants.DEFAULT_BOT_PATH,
        bot_install_dir=constants.DEFAULT_BOT_INSTALL_DIR
):
    tentacles_setup_manager = managers.TentaclesSetupManager(path.join(bot_installation_path, tentacle_path),
                                                             bot_installation_path,
                                                             path.join(bot_install_dir,
                                                                       constants.DEFAULT_TENTACLE_CONFIG))
    tentacles_setup_manager.refresh_profile_tentacles_config(profile_folder)


def refresh_all_tentacles_setup_configs(
    tentacle_path=constants.TENTACLES_PATH,
    bot_installation_path=constants.DEFAULT_BOT_PATH,
    bot_install_dir=constants.DEFAULT_BOT_INSTALL_DIR
):
    tentacles_setup_manager = managers.TentaclesSetupManager(path.join(bot_installation_path, tentacle_path),
                                                             bot_installation_path,
                                                             path.join(bot_install_dir,
                                                                       constants.DEFAULT_TENTACLE_CONFIG))
    tentacles_setup_manager.refresh_user_tentacles_setup_config_file(force_update_registered_tentacles=True)


def get_tentacles_setup_config(
    config_path=constants.USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH
) -> "TentaclesSetupConfiguration":
    setup_config = configuration.TentaclesSetupConfiguration(config_path=config_path)
    setup_config.read_config()
    return setup_config


def create_tentacles_setup_config_with_tentacles(
    *tentacles_classes, config_path=constants.USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH
) -> "TentaclesSetupConfiguration":
    setup_config = configuration.TentaclesSetupConfiguration(config_path=config_path)
    setup_config.from_activated_tentacles_classes(*tentacles_classes)
    return setup_config


def is_tentacle_activated_in_tentacles_setup_config(tentacles_setup_config: "TentaclesSetupConfiguration",
                                                    klass_name: str, default_value=False, raise_errors=False) -> bool:
    try:
        return tentacles_setup_config.is_tentacle_activated(klass_name)
    except KeyError as e:
        if raise_errors:
            raise e
        return default_value


def fill_with_installed_tentacles(
    tentacles_setup_config: "TentaclesSetupConfiguration",
    tentacles_folder: str = constants.TENTACLES_PATH,
    import_registered_tentacles: bool = False,
    use_reference_registered_tentacles: bool = False,
):
    available_tentacle = util.load_tentacle_with_metadata(tentacles_folder)
    # fill overall tentacles setup config data
    tentacles_setup_config.fill_tentacle_config(available_tentacle)
    if import_registered_tentacles and path.isfile(tentacles_setup_config.config_path):
        # reuse existing registered tentacles to avoid loosing their url
        origin_tentacles_setup_config = get_tentacles_setup_config(tentacles_setup_config.config_path)
        tentacles_setup_config.registered_tentacles = origin_tentacles_setup_config.registered_tentacles
    elif use_reference_registered_tentacles:
        _apply_reference_tentacles_config_registered_tentacles(tentacles_setup_config)


def _apply_reference_tentacles_config_registered_tentacles(
    tentacles_setup_config: "TentaclesSetupConfiguration"
):
    reference_tentacles_setup_config = get_tentacles_setup_config(
        constants.USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH
    )
    tentacles_setup_config.registered_tentacles = reference_tentacles_setup_config.registered_tentacles


def get_class_from_name_with_activated_required_tentacles(name: str,
                                                          parent_class,
                                                          tentacles_setup_config: "TentaclesSetupConfiguration",
                                                          with_class_method=None):
    for subclass in tentacles_management.get_all_classes_from_parent(parent_class):
        # Filter sub classes to only use the one that is appropriate to the given name and that has its
        # tentacles requirements activated (identified by REQUIRED_ACTIVATED_TENTACLES iterable class attribute).
        if subclass.get_name() == name and \
                tentacles_setup_config is not None and \
                all(is_tentacle_activated_in_tentacles_setup_config(tentacles_setup_config, required_tentacle.__name__)
                    for required_tentacle in subclass.REQUIRED_ACTIVATED_TENTACLES):
            if with_class_method is None or getattr(subclass, with_class_method)():
                return subclass
    return None


def get_tentacles_activation(tentacles_setup_config: "TentaclesSetupConfiguration") -> dict:
    return tentacles_setup_config.tentacles_activation


def get_tentacles_config_folder(tentacles_setup_config: "TentaclesSetupConfiguration") -> str:
    return tentacles_setup_config.get_config_folder()


def get_registered_tentacle_packages(tentacles_setup_config: "TentaclesSetupConfiguration") -> dict:
    return tentacles_setup_config.registered_tentacles


def unregister_tentacle_packages(tentacles_setup_config: "TentaclesSetupConfiguration",
                                 package_name: str) -> dict:
    return tentacles_setup_config.unregister_tentacles_package(package_name)


def update_activation_configuration(tentacles_setup_config: "TentaclesSetupConfiguration",
                                    new_config: dict, deactivate_others: bool, add_missing_elements=False) \
        -> bool:
    return tentacles_setup_config.update_activation_configuration(new_config, deactivate_others, add_missing_elements)


def deactivate_all_tentacles(tentacles_setup_config: "TentaclesSetupConfiguration",
                             trading_modes: bool, strategies: bool, evaluators: bool):
    tentacles_setup_config.deactivate_all(trading_modes, strategies, evaluators)


def save_tentacles_setup_configuration(tentacles_setup_config: "TentaclesSetupConfiguration") -> None:
    tentacles_setup_config.save_config()


def has_profile_local_configuration(tentacles_setup_config: "TentaclesSetupConfiguration", tentacle_class):
    return path.exists(configuration.get_profile_config_specific_file_path(tentacles_setup_config, tentacle_class))


def get_activated_tentacles(tentacles_setup_config: "TentaclesSetupConfiguration") -> list:
    return [tentacle_class
            for tentacle_classes in get_tentacles_activation(tentacles_setup_config).values()
            for tentacle_class, activated in tentacle_classes.items()
            if activated]


def update_tentacle_config(tentacles_setup_config: "TentaclesSetupConfiguration",
                           tentacle_class: object, config_data: dict, keep_existing: bool=True) -> None:
    configuration.update_config(tentacles_setup_config, tentacle_class, config_data, keep_existing)


def import_user_tentacles_config_folder(tentacles_setup_config: "TentaclesSetupConfiguration"):
    # WARNING: this code should only be called on profiles that are safe to import (might be a security break otherwise)
    # => careful with downloaded profiles
    user_tentacles_config_folder = configuration.get_user_tentacles_config_folder(tentacles_setup_config)
    if path.isdir(user_tentacles_config_folder) and user_tentacles_config_folder not in sys.path:
        sys.path.append(user_tentacles_config_folder)


def get_tentacle_config(tentacles_setup_config: "TentaclesSetupConfiguration", klass) -> dict:
    return configuration.get_config(tentacles_setup_config, klass)


def set_tentacle_config_proxy(new_proxy) -> dict:
    return configuration.set_get_config_proxy(new_proxy)


def local_tentacle_config_proxy(new_proxy):
    return configuration.local_get_config_proxy(new_proxy)


def factory_tentacle_reset_config(tentacles_setup_config: "TentaclesSetupConfiguration", klass) -> None:
    return configuration.factory_reset_config(tentacles_setup_config, klass)


def get_tentacle_config_schema_path(klass) -> str:
    return configuration.get_config_schema_path(klass)


def get_compiled_tentacles_url(base_url, version) -> str:
    return f"{base_url}{util.get_local_arch_download_path()}/{version}.zip"


def set_tentacles_setup_configuration_path(tentacles_setup_config: "TentaclesSetupConfiguration", new_path):
    tentacles_setup_config.config_path = new_path


def get_code_hash(tentacles: list) -> str:
    return util.get_tentacles_code_hash(tentacles)


def get_config_hash(tentacles: list,
                    tentacles_setup_config: "TentaclesSetupConfiguration") -> str:
    return util.get_tentacles_config_hash(tentacles, tentacles_setup_config)
