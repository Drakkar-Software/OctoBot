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

import octobot_commons.logging as logging
import octobot_services.interfaces.util as interfaces_util
import octobot_commons.profiles as profiles
import octobot_commons.errors as errors
import octobot_commons.enums as commons_enums
import octobot_commons.authentication as authentication
import octobot_trading.util as trading_util
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_tentacles_manager.constants as tentacles_manager_constants
import octobot.constants as constants
import octobot.community as community
import octobot.community.errors as community_errors

import tentacles.Services.Interfaces.web_interface.models.configuration as configuration_model


ACTIVATION = "activation"
VERSION = "version"
IMPORTED = "imported"
REQUIRE_EXACT_VERSION = "require_exact_version"
READ_ERROR = "read_error"

_PROFILE_TENTACLES_CONFIG_CACHE = {}

def _get_logger():
    return logging.get_logger("WebProfileModel")


def _fallback_tentacles_details(profile, *, read_error: bool = True) -> dict:
    return {
        ACTIVATION: [],
        VERSION: tentacles_manager_constants.TENTACLE_INSTALLATION_CONTEXT_OCTOBOT_VERSION_UNKNOWN,
        IMPORTED: profile.imported,
        REQUIRE_EXACT_VERSION: False,
        READ_ERROR: read_error,
    }


def _resolve_profile_tentacles_setup_config(profile, *, force_reload: bool = False):
    if profile.is_profile_data_tentacle_backed():
        if force_reload or profile.tentacles_setup_config is None:
            profile.init_tentacles_setup_config()
        tentacles_setup_config = profile.tentacles_setup_config
        return profile.bind_tentacles_setup_config(tentacles_setup_config)
    return tentacles_manager_api.get_tentacles_setup_config(
        profile.get_tentacles_config_path(),
        profile=profile,
    )


def _ensure_profile_in_config(config, profile_id):
    if profile_id in config.profile_by_id:
        return config.profile_by_id[profile_id]
    config.load_profiles()
    if profile_id in config.profile_by_id:
        return config.profile_by_id[profile_id]
    profile = config.profile_storage.load_profile_by_id(profile_id)
    config.profile_by_id[profile_id] = profile
    return profile


def get_current_profile():
    return interfaces_util.get_edited_config(dict_only=False).profile


def duplicate_profile(profile_id):
    to_duplicate = get_profile(profile_id)
    new_profile = to_duplicate.duplicate(name=f"{to_duplicate.name}_(copy)", description=to_duplicate.description)
    if not new_profile.is_profile_data_tentacle_backed():
        tentacles_manager_api.refresh_profile_tentacles_setup_config(new_profile.path)
    interfaces_util.get_edited_config(dict_only=False).load_profiles()
    new_profile = get_profile(new_profile.profile_id)
    if new_profile.is_profile_data_tentacle_backed():
        new_profile.init_tentacles_setup_config()
    return new_profile

def convert_to_live_profile(profile_id):
    profile = get_profile(profile_id)
    profile.profile_type = commons_enums.ProfileType.LIVE
    profile.validate_and_save_config()


def select_profile(profile_id):
    config = interfaces_util.get_edited_config(dict_only=False)
    _ensure_profile_in_config(config, profile_id)
    _select_and_save(config, profile_id)


def _select_and_save(config, profile_id):
    config.select_profile(profile_id)
    _update_edited_tentacles_config(config)
    config.save()


def _update_edited_tentacles_config(config, *, force_reload: bool = False):
    updated_tentacles_config = _resolve_profile_tentacles_setup_config(
        config.profile,
        force_reload=force_reload,
    )
    interfaces_util.set_edited_tentacles_config(updated_tentacles_config)


def refresh_sync_profiles_for_display(config=None):
    if config is None:
        config = interfaces_util.get_edited_config(dict_only=False)
    config.refresh_sync_profiles()
    force_reload = config.profile is not None and config.profile.is_sync_backed()
    if force_reload:
        _PROFILE_TENTACLES_CONFIG_CACHE.pop(config.profile.profile_id, None)
    _update_edited_tentacles_config(config, force_reload=force_reload)

    configuration_model.clear_tentacle_config_cache()
    return config


def get_profile(profile_id):
    config = interfaces_util.get_edited_config(dict_only=False)
    return _ensure_profile_in_config(config, profile_id)


def get_tentacles_setup_config_from_profile_id(profile_id):
    return get_tentacles_setup_config_from_profile(get_profile(profile_id))


def get_tentacles_setup_config_from_profile(profile):
    return _resolve_profile_tentacles_setup_config(profile)


def get_profiles(profile_type: commons_enums.ProfileType = None):
    config = refresh_sync_profiles_for_display()
    return {
        identifier: profile
        for identifier, profile in config.profile_by_id.items()
        if profile_type is None or profile.profile_type is profile_type
    }


def _get_profile_setup_config(profile, reloading_profile):
    force_reload = profile.profile_id == reloading_profile
    if force_reload:
        _PROFILE_TENTACLES_CONFIG_CACHE.pop(profile.profile_id, None)
    if profile.is_profile_data_tentacle_backed():
        return _resolve_profile_tentacles_setup_config(profile, force_reload=force_reload)
    if profile.profile_id not in _PROFILE_TENTACLES_CONFIG_CACHE or force_reload:
        _PROFILE_TENTACLES_CONFIG_CACHE[profile.profile_id] = _resolve_profile_tentacles_setup_config(
            profile,
            force_reload=force_reload,
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
        except Exception as err:
            _get_logger().warning(
                "Failed to load tentacles details for profile %r: %s",
                profile.profile_id,
                err,
            )
            tentacles_by_profile_id[profile.profile_id] = _fallback_tentacles_details(profile)
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
    if renamed and not profile.is_sync_backed():
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
