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
import os

import octobot_services.interfaces.util as interfaces_util
import octobot_commons.profiles as profiles
import octobot_commons.errors as errors
import octobot_commons.enums as commons_enums
import octobot_commons.authentication as authentication
import octobot_trading.util as trading_util
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot.constants as constants
import octobot.community as community
import octobot.community.errors as community_errors


ACTIVATION = "activation"
VERSION = "version"
IMPORTED = "imported"
REQUIRE_EXACT_VERSION = "require_exact_version"
READ_ERROR = "read_error"

_PROFILE_TENTACLES_CONFIG_CACHE = {}


def get_current_profile():
    return interfaces_util.get_edited_config(dict_only=False).profile


def duplicate_profile(profile_id):
    to_duplicate = get_profile(profile_id)
    new_profile = to_duplicate.duplicate(name=f"{to_duplicate.name}_(copy)", description=to_duplicate.description)
    tentacles_manager_api.refresh_profile_tentacles_setup_config(new_profile.path)
    interfaces_util.get_edited_config(dict_only=False).load_profiles()
    return get_profile(new_profile.profile_id)


def convert_to_live_profile(profile_id):
    profile = get_profile(profile_id)
    profile.profile_type = commons_enums.ProfileType.LIVE
    profile.validate_and_save_config()


def select_profile(profile_id):
    _select_and_save(interfaces_util.get_edited_config(dict_only=False), profile_id)


def _select_and_save(config, profile_id):
    config.select_profile(profile_id)
    _update_edited_tentacles_config(config)
    config.save()


def _update_edited_tentacles_config(config):
    updated_tentacles_config = tentacles_manager_api.get_tentacles_setup_config(config.get_tentacles_config_path())
    interfaces_util.set_edited_tentacles_config(updated_tentacles_config)


def get_profile(profile_id):
    return interfaces_util.get_edited_config(dict_only=False).profile_by_id[profile_id]


def get_tentacles_setup_config_from_profile_id(profile_id):
    return get_tentacles_setup_config_from_profile(get_profile(profile_id))


def get_tentacles_setup_config_from_profile(profile):
    return tentacles_manager_api.get_tentacles_setup_config(
        profile.get_tentacles_config_path()
    )


def get_profiles(profile_type: commons_enums.ProfileType = None):
    return {
        identifier: profile
        for identifier, profile in interfaces_util.get_edited_config(dict_only=False).profile_by_id.items()
        if profile_type is None or profile.profile_type is profile_type
    }


def _get_profile_setup_config(profile, reloading_profile):
    if profile.profile_id == reloading_profile:
        _PROFILE_TENTACLES_CONFIG_CACHE.pop(reloading_profile, None)
        return tentacles_manager_api.get_tentacles_setup_config(
            profile.get_tentacles_config_path()
        )
    try:
        _PROFILE_TENTACLES_CONFIG_CACHE[profile.profile_id]
    except KeyError:
        _PROFILE_TENTACLES_CONFIG_CACHE[profile.profile_id] = \
            tentacles_manager_api.get_tentacles_setup_config(
                profile.get_tentacles_config_path()
            )
    return _PROFILE_TENTACLES_CONFIG_CACHE[profile.profile_id]


def get_profiles_tentacles_details(profiles_list):
    tentacles_by_profile_id = {}
    current_profile_id = get_current_profile().profile_id
    for profile in profiles_list.values():
        try:
            # force reload for current profile as tentacles setup config can change
            tentacles_setup_config = _get_profile_setup_config(profile, current_profile_id)
            tentacles_by_profile_id[profile.profile_id] = {
                ACTIVATION: tentacles_manager_api.get_activated_tentacles(tentacles_setup_config),
                VERSION: tentacles_manager_api.get_tentacles_installation_version(tentacles_setup_config),
                IMPORTED: profile.imported,
                REQUIRE_EXACT_VERSION: False,  # implement if exact version is required in profiles
                READ_ERROR:
                    not tentacles_manager_api.is_tentacles_setup_config_successfully_loaded(tentacles_setup_config),
            }
        except Exception:
            # do not raise here to prevent avoid config display
            pass
    return tentacles_by_profile_id


def update_profile(profile_id, json_profile_desc, json_profile_content=None):
    profile = get_profile(profile_id)
    new_name = json_profile_desc.get("name", profile.name)
    renamed = profile.name != new_name
    if renamed and get_current_profile().profile_id == profile_id:
        return False, "Can't rename the active profile"
    profile.name = new_name
    profile.description = json_profile_desc.get("description", profile.description)
    profile.avatar = json_profile_desc.get("avatar", profile.avatar)
    profile.complexity = commons_enums.ProfileComplexity(int(json_profile_desc.get("complexity", profile.complexity.value)))
    profile.risk = commons_enums.ProfileRisk(int(json_profile_desc.get("risk", profile.risk.value)))
    if json_profile_content is not None:
        profile.config = json_profile_content
    profile.validate_and_save_config()
    if renamed:
        profile.rename_folder(new_name, False)
    return True, "Profile updated"


def remove_profile(profile_id):
    profile = None
    if get_current_profile().profile_id == profile_id:
        return profile, "Can't remove the active profile"
    try:
        profile = get_profile(profile_id)
        interfaces_util.get_edited_config(dict_only=False).remove_profile(profile_id)
    except errors.ProfileRemovalError as err:
        return profile, err
    return profile, None


def export_profile(profile_id, export_path) -> str:
    return profiles.export_profile(get_profile(profile_id), export_path)


def import_profile(profile_path, name, profile_url=None):
    profile = profiles.import_profile(profile_path, constants.PROFILE_FILE_SCHEMA, name=name, origin_url=profile_url)
    interfaces_util.get_edited_config(dict_only=False).load_profiles()
    return profile


def import_strategy_as_profile(authenticator, strategy: community.StrategyData, name: str, description: str):
    if strategy.is_extension_only() and not authenticator.has_open_source_package():
        raise community_errors.ExtensionRequiredError(
            f"The {constants.OCTOBOT_EXTENSION_PACKAGE_1_NAME} is required to install this strategy"
        )
    profile_data = interfaces_util.run_in_bot_main_loop(authenticator.get_strategy_profile_data(strategy.id))

    profile = interfaces_util.run_in_bot_main_loop(
        profiles.import_profile_data_as_profile(
            profile_data,
            constants.PROFILE_FILE_SCHEMA,
            interfaces_util.get_bot_api().get_aiohttp_session(),
            name=name,
            description=description,
            risk=strategy.get_risk(),
            origin_url=strategy.get_product_url(),
            logo_url=strategy.logo_url,
            auto_update=strategy.is_auto_updated(),
            force_simulator=True
        )
    )
    interfaces_util.get_edited_config(dict_only=False).load_profiles()
    return profile


def download_and_import_profile(profile_url):
    name = profile_url.split('/')[-1]
    if "?" in name:
        # remove parameter
        name = name.split("?")[0]
    file_path = profiles.download_profile(profile_url, name)
    profile = import_profile(file_path, name, profile_url=profile_url)
    if os.path.isfile(file_path):
        os.remove(file_path)
    return profile


def get_profile_name(profile_id) -> str:
    return get_profile(profile_id).name


def get_forced_profile() -> profiles.Profile:
    if constants.FORCED_PROFILE:
        # env variables are priority 1
        return get_current_profile()
    try:
        startup_info = interfaces_util.run_in_bot_main_loop(
            authentication.Authenticator.instance().get_startup_info(),
            log_exceptions=False
        )
        if startup_info.forced_profile_url:
            return get_current_profile()
    except community.BotError:
        pass
    return None


def is_real_trading(profile):
    if trading_util.is_trader_enabled(profile.config):
        return True
    return False
