#  Drakkar-Software OctoBot-Tentacles-Manager
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
import octobot_commons.profiles as profiles
import octobot_tentacles_manager.constants as constants


def get_profile_folders(package_root) -> list:
    profiles_source_path = os.path.join(package_root, constants.TENTACLES_PACKAGE_PROFILES_PATH)
    if os.path.isdir(profiles_source_path):
        return [
            profile.path
            for profile in os.scandir(profiles_source_path)
        ]
    return []


def import_profile(profile_path, bot_install_root_folder, quite=False) -> None:
    profile_name = os.path.split(profile_path)[-1]
    profiles.install_profile(profile_path,
                             profile_name,
                             bot_install_root_folder,
                             True,
                             False,
                             quite=quite
                             )
