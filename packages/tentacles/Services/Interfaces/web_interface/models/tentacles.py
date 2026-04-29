#  Drakkar-Software OctoBot-Interfaces
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

import octobot.constants as octobot_constants
import octobot.configuration_manager as configuration_manager
import octobot_commons.logging as bot_logging
import octobot_services.interfaces.util as interfaces_util
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_tentacles_manager.constants as tentacles_manager_constants

logger = bot_logging.get_logger("TentaclesModel")


def get_tentacles_packages():
    return tentacles_manager_api.get_registered_tentacle_packages(
        interfaces_util.get_bot_api().get_edited_tentacles_config())


def call_tentacle_manager(coro, *args, **kwargs):
    return interfaces_util.run_in_bot_main_loop(coro(*args, **kwargs)) == 0


def _add_version_to_tentacles_package_path(path_or_url, version):
    return f"{path_or_url}/{version.replace('.', tentacles_manager_constants.ARTIFACT_VERSION_DOT_REPLACEMENT)}"


def get_official_tentacles_url(use_beta_tentacles) -> str:
    return configuration_manager.get_default_tentacles_url(
        version=octobot_constants.BETA_TENTACLE_PACKAGE_NAME if use_beta_tentacles else None
    )


def install_packages(path_or_url=None, version=None, authenticator=None):
    message = "Tentacles installed. Restart your OctoBot to load the new tentacles."
    success = True
    if path_or_url and version:
        path_or_url = _add_version_to_tentacles_package_path(path_or_url, version)
    for package_url in [path_or_url] if path_or_url else \
            tentacles_manager_api.get_registered_tentacle_packages(
                interfaces_util.get_bot_api().get_edited_tentacles_config()).values():
        if not package_url == tentacles_manager_constants.UNKNOWN_TENTACLES_PACKAGE_LOCATION:
            if not call_tentacle_manager(tentacles_manager_api.install_all_tentacles,
                                         package_url,
                                         setup_config=interfaces_util.get_bot_api().get_edited_tentacles_config(),
                                         aiohttp_session=interfaces_util.get_bot_api().get_aiohttp_session(),
                                         bot_install_dir=octobot_constants.OCTOBOT_FOLDER,
                                         authenticator=authenticator
                                         ):
                success = False
        else:
            message = "Tentacles installed however it is impossible to re-install tentacles with unknown package origin"
    # reload profiles to display newly installed ones if any
    interfaces_util.get_edited_config(dict_only=False).load_profiles()
    if success:
        return message
    return False


def update_packages(authenticator=None):
    message = "Tentacles updated"
    success = True
    for package_url in tentacles_manager_api.get_registered_tentacle_packages(
            interfaces_util.get_bot_api().get_edited_tentacles_config()).values():
        if package_url != tentacles_manager_constants.UNKNOWN_TENTACLES_PACKAGE_LOCATION:
            if not call_tentacle_manager(tentacles_manager_api.update_all_tentacles,
                                         package_url,
                                         aiohttp_session=interfaces_util.get_bot_api().get_aiohttp_session(),
                                         authenticator=authenticator):
                success = False
        else:
            message = "Tentacles updated however it is impossible to update tentacles with unknown package origin"
    if success:
        return message
    return False


def reset_packages():
    if call_tentacle_manager(tentacles_manager_api.uninstall_all_tentacles,
                             setup_config=interfaces_util.get_bot_api().get_edited_tentacles_config(),
                             use_confirm_prompt=False):
        return "Reset successful"
    else:
        return None


def update_modules(modules):
    success = True
    for url in [
        get_official_tentacles_url(False),
        # tentacles_manager_api.get_compiled_tentacles_url(
        #     octobot_constants.DEFAULT_COMPILED_TENTACLES_URL,
        #     octobot_constants.TENTACLES_REQUIRED_VERSION
        # )
    ]:
        try:
            call_tentacle_manager(tentacles_manager_api.update_tentacles,
                                  modules,
                                  url,
                                  aiohttp_session=interfaces_util.get_bot_api().get_aiohttp_session(),
                                  quite_mode=True)
        except Exception:
            success = False
    if success:
        return f"{len(modules)} Tentacles updated"
    return None


def uninstall_modules(modules):
    if call_tentacle_manager(tentacles_manager_api.uninstall_tentacles,
                             modules):
        return f"{len(modules)} Tentacles uninstalled"
    else:
        return None


def get_tentacles():
    return tentacles_manager_api.get_installed_tentacles_modules()
