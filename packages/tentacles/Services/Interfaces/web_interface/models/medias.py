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

import octobot_commons.constants as commons_constants
import octobot_tentacles_manager.constants as tentacles_manager_constants
import octobot_commons.user_root_folder_provider as user_root_folder_provider

ALLOWED_IMAGE_FORMATS = ["png", "jpg", "jpeg", "gif", "svg"]
ALLOWED_SOUNDS_FORMATS = ["mp3"]


def _is_valid_path(path, header):
    return path.startswith(header) and ".." not in path


def _profile_image_allowed_roots():
    # Local profiles under the process user root, plus master profiles when this
    # process is an automation child (OCTOBOT_SYNC_DATA_ROOT points at the executor user/).
    allowed_roots = [user_root_folder_provider.get_user_profiles_folder()]
    sync_profiles_root = os.path.join(
        user_root_folder_provider.get_sync_data_root(),
        commons_constants.PROFILES_FOLDER,
    )
    normalized_roots = {os.path.normcase(os.path.normpath(root)) for root in allowed_roots}
    if os.path.normcase(os.path.normpath(sync_profiles_root)) not in normalized_roots:
        allowed_roots.append(sync_profiles_root)
    return allowed_roots


def _is_path_under_root(path, root):
    # Reject traversal before normalization; commonpath handles absolute vs relative
    # paths on Windows (avatar_path is often an absolute master profiles path in URLs).
    if ".." in path:
        return False
    normalized_path = os.path.normcase(os.path.normpath(path))
    normalized_root = os.path.normcase(os.path.normpath(root))
    try:
        common_path = os.path.commonpath([normalized_path, normalized_root])
    except ValueError:
        return False
    return common_path == normalized_root


def is_valid_tentacle_image_path(path):
    path_ending = path.split(".")[-1].lower()
    return path_ending in ALLOWED_IMAGE_FORMATS and _is_valid_path(path, tentacles_manager_constants.TENTACLES_PATH)


def is_valid_profile_image_path(path):
    """True when path is a supported image under local or sync-data profiles."""
    path_ending = path.split(".")[-1].lower()
    if path_ending not in ALLOWED_IMAGE_FORMATS:
        return False
    return any(
        _is_path_under_root(path, allowed_root)
        for allowed_root in _profile_image_allowed_roots()
    )


def is_valid_audio_path(path):
    path_ending = path.split(".")[-1].lower()
    return path_ending in ALLOWED_SOUNDS_FORMATS and _is_valid_path(path, "")
