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
import packaging.version as packaging_version

import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.loaders as loaders
import octobot_tentacles_manager.managers as managers
import octobot_tentacles_manager.util as util


def load_tentacles(verbose=True) -> bool:
    return managers.TentaclesSetupManager.is_tentacles_arch_valid(verbose=verbose)


def is_tentacles_architecture_valid() -> bool:
    return managers.TentaclesSetupManager.is_tentacles_arch_valid(verbose=False, import_tentacles=False)


def are_tentacles_up_to_date(tentacles_setup_config, bot_version):
    installation_version = get_tentacles_installation_version(tentacles_setup_config)
    if installation_version == constants.TENTACLE_INSTALLATION_CONTEXT_OCTOBOT_VERSION_UNKNOWN:
        return False
    return packaging_version.parse(bot_version) <= packaging_version.parse(installation_version)


def get_tentacles_installation_version(tentacles_setup_config):
    return tentacles_setup_config.installation_context.get(
        constants.TENTACLE_INSTALLATION_CONTEXT_OCTOBOT_VERSION,
        constants.TENTACLE_INSTALLATION_CONTEXT_OCTOBOT_VERSION_UNKNOWN)


def is_tentacles_setup_config_successfully_loaded(tentacles_setup_config):
    return tentacles_setup_config.is_successfully_loaded


def reload_tentacle_info() -> None:
    loaders.reload_tentacle_by_tentacle_class()


def ensure_tentacle_info(tentacles_path=constants.TENTACLES_PATH) -> None:
    loaders.ensure_tentacles_metadata(tentacles_path)


def register_extra_tentacle_data(tentacle_class, tentacle_type_path: str):
    """
    :param tentacle_class: class of the tentacle
    :param tentacle_type_path: path of the tentacle, ex "Trading/mode"
    """
    return util.register_extra_tentacle_data(tentacle_class.get_name(), tentacle_type_path, tentacle_class)
