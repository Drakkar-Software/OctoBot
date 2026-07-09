# pylint: disable=R0913,W0718,W0706,C0415,R0914
#  Drakkar-Software OctoBot-Commons
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
import copy
import os
import uuid

import octobot_commons.profiles.profile_data as profile_data_import
import octobot_commons.profiles.profile_types.profile as profile_import
import octobot_commons.profiles.backends as profile_backends_module
import octobot_commons.logging as bot_logging
import octobot_commons.constants as constants
import octobot_commons.aiohttp_util as aiohttp_util
import octobot_commons.enums as enums

IMPORTED_AVATAR = "avatar"
IMPORTED_PROFILES_DEFAULT_EXTRA_BACKTESTING_TIMEFRAME = (
    enums.TimeFrames.FIFTEEN_MINUTES.value
)


def init_profile_directory(
    output_path: str,
):
    """
    :param output_path: profile folder path
    """
    if os.path.exists(output_path):
        raise OSError(f"{output_path} already exists")
    os.mkdir(output_path)


async def convert_profile_data_to_profile_directory(
    profile_data: profile_data_import.ProfileData,
    output_path: str,
    description: str = None,
    risk: enums.ProfileRisk = enums.ProfileRisk.MODERATE,
    auto_update: bool = False,
    slug: str = None,
    avatar_url: str = None,
    force_simulator: bool = False,
    aiohttp_session=None,
    profile_to_update: profile_import.Profile = None,
    changed: bool = False,
) -> bool:
    """
    Creates a profile folder from the given ProfileData
    :param profile_data: path to the profile zipped archive
    :param description: profile description
    :param risk: profile risk
    :param slug: slug of the associated strategy
    :param auto_update: True if the profile should be kept up-to-date
    :param avatar_url: profile avatar_url
    :param output_path: profile folder path
    :param force_simulator: True if trader simulator should be forced in config
    :param aiohttp_session: session to use
    :param profile_to_update: profile to update instead of creating a new one
    :param changed: if True, profile will be saved even if no change are identified
    """
    profile = (
        profile_to_update
        if profile_to_update
        else _get_profile(
            profile_data,
            description,
            risk,
            output_path,
            auto_update,
            slug,
            force_simulator,
        )
    )
    # when updating profile, keep existing registered tentacles
    import_registered_tentacles = profile_to_update is not None
    # tentacles_config.json
    try:
        import octobot_tentacles_manager.configuration.profile_tentacles_util as profile_tentacles_util

        tentacles_setup_config = profile_tentacles_util.build_setup_config_from_profile_data(
            profile_data, output_path, import_registered_tentacles
        )
        if tentacles_setup_config.save_config(is_config_update=True):
            changed = True
        # specific_config
        if profile_tentacles_util.write_specific_configs_to_profile_folder(
            profile_data, output_path, bool(profile_to_update)
        ):
            changed = True
    except ImportError:
        raise
    # avatar file
    if avatar_url:
        try:
            await _download_and_set_avatar(
                profile, avatar_url, output_path, aiohttp_session
            )
        except Exception as err:
            bot_logging.get_logger(__name__).exception(
                err, True, f"Error when downloading profile avatar: {err}"
            )
    # finish with profile.json to include edits from previous methods
    if changed:
        profile_storage = profile.get_profile_storage()
        if profile_storage is not None:
            profile.save()
        else:
            profile_backends_module.FilesystemProfileBackend().write_profile_config(profile)
    return changed


def _get_profile(
    profile_data: profile_data_import.ProfileData,
    description: str,
    risk: enums.ProfileRisk,
    output_path: str,
    auto_update: bool,
    slug: str,
    force_simulator: bool,
):
    profile = profile_import.Profile.from_profile_data(profile_data, output_path)
    if force_simulator:
        profile.config[constants.CONFIG_TRADER][constants.CONFIG_ENABLED_OPTION] = False
        profile.config[constants.CONFIG_SIMULATOR][
            constants.CONFIG_ENABLED_OPTION
        ] = True
    profile.description = description
    profile.risk = risk
    profile.auto_update = auto_update
    profile.slug = slug
    profile.profile_id = str(uuid.uuid4().hex)
    profile.read_only = True
    profile.extra_backtesting_time_frames = [
        IMPORTED_PROFILES_DEFAULT_EXTRA_BACKTESTING_TIMEFRAME
    ]
    return profile


def get_updated_profile(
    profile_to_update: profile_import.Profile,
    profile_data: profile_data_import.ProfileData,
) -> bool:
    """
    :param profile_to_update: the profile to be updated
    :param profile_data: the profile_data to get the update from
    :return: True if something changed in the updated profile
    """
    updated_profile = profile_import.Profile.from_profile_data(profile_data, "")
    changed = False
    # update traded currencies (add new currencies)
    origin_currencies = copy.deepcopy(
        profile_to_update.config[constants.CONFIG_CRYPTO_CURRENCIES]
    )
    profile_to_update.config[constants.CONFIG_CRYPTO_CURRENCIES] = {
        **origin_currencies,
        **updated_profile.config[constants.CONFIG_CRYPTO_CURRENCIES],
    }
    if (
        origin_currencies
        != profile_to_update.config[constants.CONFIG_CRYPTO_CURRENCIES]
    ):
        changed = True
    # update ref market
    origin_ref_market = profile_to_update.config[constants.CONFIG_TRADING][
        constants.CONFIG_TRADER_REFERENCE_MARKET
    ]
    profile_to_update.config[constants.CONFIG_TRADING][
        constants.CONFIG_TRADER_REFERENCE_MARKET
    ] = profile_data.trading.reference_market
    if (
        origin_ref_market
        != profile_to_update.config[constants.CONFIG_TRADING][
            constants.CONFIG_TRADER_REFERENCE_MARKET
        ]
    ):
        changed = True
    # leave other fields as is (tentacles config will be updated)
    return changed


async def _download_and_set_avatar(
    profile, avatar_url, output_path: str, aiohttp_session
):
    profile.avatar = _get_avatar_name(avatar_url)
    try:
        import aiofiles

        async with aiofiles.open(
            os.path.join(output_path, profile.avatar), "wb+"
        ) as downloaded_file:
            await aiohttp_util.download_stream_file(
                downloaded_file,
                avatar_url,
                aiohttp_session,
                is_aiofiles_output_file=True,
            )
    except ImportError:
        raise


def _get_avatar_name(avatar_url: str):
    # remove params and get file name with ext
    return avatar_url.split("?")[0].split("/")[-1]
