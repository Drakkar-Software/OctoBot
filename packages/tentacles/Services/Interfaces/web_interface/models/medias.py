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
import octobot_tentacles_manager.constants as tentacles_manager_constants
import octobot_commons.constants as commons_constants

ALLOWED_IMAGE_FORMATS = ["png", "jpg", "jpeg", "gif", "svg"]
ALLOWED_SOUNDS_FORMATS = ["mp3"]


def _is_valid_path(path, header):
    return path.startswith(header) and ".." not in path


def is_valid_tentacle_image_path(path):
    path_ending = path.split(".")[-1].lower()
    return path_ending in ALLOWED_IMAGE_FORMATS and _is_valid_path(path, tentacles_manager_constants.TENTACLES_PATH)


def is_valid_profile_image_path(path):
    path_ending = path.split(".")[-1].lower()
    return path_ending in ALLOWED_IMAGE_FORMATS and _is_valid_path(path, commons_constants.USER_PROFILES_FOLDER)


def is_valid_audio_path(path):
    path_ending = path.split(".")[-1].lower()
    return path_ending in ALLOWED_SOUNDS_FORMATS and _is_valid_path(path, "")
