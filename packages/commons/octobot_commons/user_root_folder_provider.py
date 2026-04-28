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
import os
import typing

import octobot_commons.constants as commons_constants
import octobot_commons.singleton.singleton_class as singleton_class

# Matches historical layout under the user root; "specific_config" matches
# octobot_tentacles_manager.constants.TENTACLES_SPECIFIC_CONFIG_FOLDER (commons cannot import tentacles_manager).
_REFERENCE_TENTACLES_CONFIG_DIR = "reference_tentacles_config"
_TENTACLES_SPECIFIC_CONFIG_DIR = "specific_config"


class UserRootFolderProvider(singleton_class.Singleton):
    """
    Singleton: effective user data root (config, profiles, reference_tentacles_config, etc.).
    Default matches commons_constants.USER_FOLDER when unset.
    """

    def __init__(self) -> None:
        """Initialize with no explicit root (``get_root`` falls back to ``USER_FOLDER``)."""
        self._root: typing.Optional[str] = None

    def get_root(self) -> str:
        """Return the configured user data root, or ``commons_constants.USER_FOLDER`` if unset."""
        if self._root is None:
            return commons_constants.USER_FOLDER
        return self._root

    def set_root(self, root: str) -> None:
        """Set the user data root directory path."""
        self._root = root

    def get_user_profiles_folder(self) -> str:
        """Return the profiles folder path under the user root."""
        return os.path.join(self.get_root(), commons_constants.PROFILES_FOLDER)

    def get_user_reference_tentacle_config_path(self) -> str:
        """Return the reference tentacles config directory under the user root."""
        return os.path.join(self.get_root(), _REFERENCE_TENTACLES_CONFIG_DIR)

    def get_user_reference_tentacle_config_file_path(self) -> str:
        """Return the path to the main tentacles config file under reference config."""
        return os.path.join(
            self.get_user_reference_tentacle_config_path(),
            commons_constants.CONFIG_TENTACLES_FILE,
        )

    def get_user_reference_tentacle_specific_config_path(self) -> str:
        """Return the tentacles-specific config directory under reference config."""
        return os.path.join(
            self.get_user_reference_tentacle_config_path(),
            _TENTACLES_SPECIFIC_CONFIG_DIR,
        )


def instance() -> UserRootFolderProvider:
    """Module alias for the singleton (same as ``UserRootFolderProvider.instance()``)."""
    return UserRootFolderProvider.instance()


def get_user_root_folder() -> str:
    """Return the effective user data root from the singleton provider."""
    return UserRootFolderProvider.instance().get_root()


def get_user_profiles_folder() -> str:
    """Module-level helper: profiles folder under the user root."""
    return UserRootFolderProvider.instance().get_user_profiles_folder()


def get_user_reference_tentacle_config_path() -> str:
    """Module-level helper: reference tentacles config directory under the user root."""
    return UserRootFolderProvider.instance().get_user_reference_tentacle_config_path()


def get_user_reference_tentacle_config_file_path() -> str:
    """Module-level helper: main tentacles config file path under reference config."""
    return UserRootFolderProvider.instance().get_user_reference_tentacle_config_file_path()


def get_user_reference_tentacle_specific_config_path() -> str:
    """Module-level helper: tentacles-specific config directory under reference config."""
    return UserRootFolderProvider.instance().get_user_reference_tentacle_specific_config_path()
