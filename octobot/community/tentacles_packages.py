#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import octobot.constants as constants
import octobot_tentacles_manager.api as tentacles_manager_api


async def has_tentacles_to_install_and_uninstall_tentacles_if_necessary(community_auth):
    tentacles_setup_config = tentacles_manager_api.get_tentacles_setup_config(
        community_auth.config.get_tentacles_config_path()
    )
    to_install, to_remove_tentacles = get_to_install_and_remove_tentacles(
        community_auth, tentacles_setup_config
    )
    if to_remove_tentacles:
        await uninstall_tentacles(to_remove_tentacles)
    return bool(to_install)


def get_to_install_and_remove_tentacles(
    community_auth, selected_profile_tentacles_setup_config
):
    installed_community_package_urls = [
        package_url
        for package_url in tentacles_manager_api.get_all_installed_package_urls(
            selected_profile_tentacles_setup_config
        )
        if is_community_tentacle_url(package_url)
    ]
    additional_tentacles_package_urls = community_auth.get_saved_package_urls() if community_auth.is_logged_in() else []
    was_connected_with_remote_packages = community_auth.was_connected_with_remote_packages()

    # do not remove tentacles:
    #   - if account has already been authenticated with valid extensions but is currently unauthenticated
    #   - if tentacles packages urls have not been fetched
    # remove if: is authenticated and doesn't have access to these tentacles or has never been authenticated
    can_remove_tentacles = True
    if was_connected_with_remote_packages and not community_auth.is_logged_in():
        # currently unauthenticated
        can_remove_tentacles = False
    if not community_auth.successfully_fetched_tentacles_package_urls:
        # did not fetch tentacles packages
        can_remove_tentacles = False
    to_remove_urls = [
        package_url
        for package_url in installed_community_package_urls
        if package_url not in additional_tentacles_package_urls
    ] if can_remove_tentacles else []
    if to_remove_urls:
        tentacles_manager_api.reload_tentacle_info()
    to_remove_tentacles = []
    for to_remove_url in to_remove_urls:
        installed_packages = tentacles_manager_api.get_installed_packages_from_url(
            selected_profile_tentacles_setup_config,
            to_remove_url
        )
        for installed_package in installed_packages:
            to_remove_tentacles += tentacles_manager_api.get_tentacles_from_package_name(installed_package)

    # install missing
    to_install_urls = [
        package_url
        for package_url in additional_tentacles_package_urls
        if package_url not in installed_community_package_urls
    ]
    return list(set(to_install_urls)), list(set(to_remove_tentacles))


def is_community_tentacle_url(url: str) -> bool:
    return constants.COMMUNITY_EXTENSIONS_PACKAGES_IDENTIFIER in url


async def uninstall_tentacles(tentacles: list[str]):
    await tentacles_manager_api.uninstall_tentacles(tentacles)

