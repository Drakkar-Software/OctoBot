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
from tentacles_manager.tentacle_manager import TentacleManager
from tentacles_manager.tentacle_package_manager import TentaclePackageManager
from tentacles_manager.tentacle_package_util import get_octobot_tentacle_public_repo, get_is_url, get_package_name, \
    get_package_description_with_adaptation

from tools.logging.logging_util import get_logger


from config import CONFIG_TENTACLES_KEY, TENTACLE_PACKAGE_DESCRIPTION, TENTACLES_DEFAULT_BRANCH
from interfaces import get_bot

logger = get_logger("TentaclesModel")


def get_tentacles_packages():
    default_tentacles_repo_desc_file = get_octobot_tentacle_public_repo()
    default_tentacles_repo = get_octobot_tentacle_public_repo(False)
    packages = {
        default_tentacles_repo: get_package_name(default_tentacles_repo_desc_file,
                                                 get_is_url(default_tentacles_repo_desc_file))
    }
    if CONFIG_TENTACLES_KEY in get_bot().get_config():
        for tentacle_package in get_bot().get_config()[CONFIG_TENTACLES_KEY]:
            packages[tentacle_package] = get_package_name(tentacle_package, get_is_url(tentacle_package))
    return packages


def get_tentacles_package_description(path_or_url):
    try:
        return get_package_description_with_adaptation(path_or_url)[TENTACLE_PACKAGE_DESCRIPTION]
    except Exception:
        return None


def _get_tentacles_manager(config):
    tentacles_manager = TentacleManager(config)
    tentacles_manager.git_branch = TENTACLES_DEFAULT_BRANCH
    return tentacles_manager


def register_and_install(path_or_url):
    config = get_bot().get_config()
    config[CONFIG_TENTACLES_KEY].append(path_or_url)
    # TODO update config.json

    tentacles_manager = _get_tentacles_manager(config)
    tentacles_manager.install_tentacle_package(path_or_url, True)
    return True


def install_packages():
    try:
        tentacles_manager = _get_tentacles_manager(get_bot().get_config())
        tentacles_manager.update_list()
        tentacles_manager.set_force_actions(True)
        return f"{tentacles_manager.install_parser(None, True)} installed tentacles"
    except Exception as e:
        logger.error(f"Error when installing packages: {e}")
        logger.exception(e)
        return False


def update_packages():
    try:
        tentacles_manager = _get_tentacles_manager(get_bot().get_config())
        tentacles_manager.update_list()
        tentacles_manager.set_force_actions(True)
        return f"{tentacles_manager.update_parser(None, True)} tentacles up to date"
    except Exception as e:
        logger.error(f"Error when updating packages: {e}")
        logger.exception(e)
        return None


def reset_packages():
    try:
        tentacles_manager = _get_tentacles_manager(get_bot().get_config())
        tentacles_manager.reset_tentacles()
        return "reset successful"
    except Exception as e:
        logger.error(f"Error when resetting packages: {e}")
        logger.exception(e)
        return None


def update_modules(modules):
    try:
        tentacles_manager = _get_tentacles_manager(get_bot().get_config())
        tentacles_manager.update_list()
        tentacles_manager.set_force_actions(True)
        nb_updated = tentacles_manager.update_parser(modules, False)
        return f"{nb_updated} up to date module(s)" if nb_updated > 1 else f"{modules[0]} up to date"
    except Exception as e:
        logger.error(f"Error when updating modules: {e}")
        logger.exception(e)
        return None


def uninstall_modules(modules):
    try:
        tentacles_manager = _get_tentacles_manager(get_bot().get_config())
        tentacles_manager.update_list()
        nb_uninstalled = tentacles_manager.uninstall_parser(modules, False)
        return f"{nb_uninstalled} uninstalled module(s)" if nb_uninstalled > 1 else f"{modules[0]} uninstalled"
    except Exception as e:
        logger.error(f"Error when uninstalling modules: {e}")
        logger.exception(e)
        return None


def get_tentacles():
    return TentaclePackageManager.get_installed_modules()
