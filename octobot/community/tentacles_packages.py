#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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
import octobot_commons.logging as logging
import octobot_tentacles_manager.api as tentacles_manager_api


async def has_tentacles_to_install_and_uninstall_tentacles_if_necessary(community_auth):
    tentacles_setup_config = tentacles_manager_api.get_tentacles_setup_config(
        community_auth.config.get_tentacles_config_path()
    )
    to_install, to_remove_tentacles, force_refresh_tentacles_setup_config = get_to_install_and_remove_tentacles(
        community_auth, tentacles_setup_config, constants.LONG_VERSION
    )
    if to_remove_tentacles:
        logging.get_logger(__name__).debug(
            f"Uninstalling {len(to_remove_tentacles)} tentacles: those are not available to the current OctoBot. "
            f"Tentacles: {to_remove_tentacles}"
        )
        await uninstall_tentacles(to_remove_tentacles)
    elif force_refresh_tentacles_setup_config:
        refresh_tentacles_setup_config()
    return bool(to_install)


def adapt_url_to_bot_version(package_url: str, bot_version: str) -> str:
    if constants.VERSION_PLACEHOLDER in package_url:
        package_url = package_url.replace(constants.VERSION_PLACEHOLDER, bot_version)
    return package_url


def get_to_install_and_remove_tentacles(
    community_auth, selected_profile_tentacles_setup_config, bot_version: str
):
    installed_community_package_urls = [
        adapt_url_to_bot_version(package_url, bot_version)
        for package_url in tentacles_manager_api.get_all_installed_package_urls(
            selected_profile_tentacles_setup_config
        )
        if is_community_tentacle_url(package_url)
    ]
    additional_tentacles_package_urls = [
        adapt_url_to_bot_version(package_url, bot_version)
        for package_url in community_auth.get_saved_package_urls()
    ] if community_auth.is_logged_in() else []
    to_keep_tentacles = set(
        additional_tentacles_package_urls + [
            adapt_url_to_bot_version(package_url, bot_version)
            for package_url in get_env_variable_tentacles_urls()
        ] + get_env_variable_tentacles_urls()
    )
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
        if package_url not in to_keep_tentacles
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
    force_refresh_tentacles_setup_config = False
    if to_remove_urls and not to_remove_tentacles:
        # True when no tentacle to uninstall but still registered tentacles should be refreshed
        force_refresh_tentacles_setup_config = True

    # install missing
    to_install_urls = [
        package_url
        for package_url in additional_tentacles_package_urls
        if package_url not in installed_community_package_urls
    ]
    return list(set(to_install_urls)), list(set(to_remove_tentacles)), force_refresh_tentacles_setup_config


def get_env_variable_tentacles_urls() -> list[str]:
    return constants.ADDITIONAL_TENTACLES_PACKAGE_URL.split(constants.URL_SEPARATOR) \
        if constants.ADDITIONAL_TENTACLES_PACKAGE_URL else []


def is_community_tentacle_url(url: str) -> bool:
    return constants.COMMUNITY_EXTENSIONS_PACKAGES_IDENTIFIER in url


def refresh_tentacles_setup_config():
    tentacles_manager_api.refresh_all_tentacles_setup_configs()


async def uninstall_tentacles(tentacles: list[str]):
    await tentacles_manager_api.uninstall_tentacles(tentacles)

