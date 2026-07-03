# pylint: disable=W0212,C0415,R0401
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

from __future__ import annotations

import os
import shutil

import octobot_commons.constants as constants
import octobot_commons.errors as errors
import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.profile_storage as profile_storage_module


def migrate_user_profiles_to_sync(
    profile_storage: profile_storage_module.ProfileStorage,
) -> list[str]:
    """Migrate local filesystem profiles into the sync backend for the configured wallet."""
    if not profile_storage.is_sync_available():
        raise errors.ProfileDataError(
            "Profile migration requires a configured wallet user id"
        )
    migrated_profile_ids = []
    sync_backend = profile_storage._sync_backend
    filesystem_ids = profile_storage.filesystem_profile_ids()
    for profile_id in list(filesystem_ids):
        profile = profile_storage.find_profile(profile_id)
        if profile is None or profile.is_sync_backed():
            continue
        if profile.read_only and not profile.imported:
            continue
        profile_data = profile_data_module.ProfileData.from_filesystem_profile(profile)
        profile_data.profile_details.id = profile.profile_id
        sync_backend.import_profile_data(
            profile_data, schema_path=profile_storage.profile_schema_path
        )
        _archive_filesystem_profile(profile_storage.profiles_path, profile_id)
        migrated_profile_ids.append(profile_id)
    return migrated_profile_ids


def _archive_filesystem_profile(
    profiles_path: str,
    profile_id: str,
) -> None:
    source_path = os.path.join(profiles_path, profile_id)
    if not os.path.isdir(source_path):
        return
    import octobot_commons.user_root_folder_provider as user_root_folder_provider

    user_root = user_root_folder_provider.get_sync_data_root()
    migrated_root = os.path.join(user_root, constants.PROFILES_MIGRATED_FOLDER)
    os.makedirs(migrated_root, exist_ok=True)
    destination_path = os.path.join(migrated_root, profile_id)
    if os.path.exists(destination_path):
        shutil.rmtree(destination_path)
    shutil.move(source_path, destination_path)
