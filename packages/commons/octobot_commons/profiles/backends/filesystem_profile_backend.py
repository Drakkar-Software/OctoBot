# pylint: disable=C0116,W0718
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
import shutil
import typing

import octobot_commons.constants as constants
import octobot_commons.errors as errors
import octobot_commons.enums as enums
import octobot_commons.json_util as json_util
import octobot_commons.logging as commons_logging
import octobot_commons.profiles.backends.abstract_profile_backend as abstract_profile_backend_module
import octobot_commons.profiles.profile_types.profile as profile_module


class FilesystemProfileBackend(abstract_profile_backend_module.AbstractProfileBackend):
    @property
    def source(self) -> enums.ProfileSource:
        return enums.ProfileSource.FILESYSTEM

    @staticmethod
    def config_file_path(profile_path: str) -> str:
        return os.path.join(profile_path, constants.PROFILE_CONFIG_FILE)

    @staticmethod
    def tentacles_config_path(profile_path: str) -> str:
        return os.path.join(profile_path, constants.CONFIG_TENTACLES_FILE)

    def list_profiles(
        self,
        schema_path: str = None,
    ) -> dict[str, profile_module.Profile]:
        resolved_schema_path = self._resolve_schema_path(schema_path)
        profiles = {}
        for profile in self._scan_profiles(self._profiles_path, resolved_schema_path):
            profiles[profile.profile_id] = profile
        return profiles

    def get_profile(
        self,
        profile_id: str,
        schema_path: str = None,
    ) -> typing.Optional[profile_module.Profile]:
        resolved_schema_path = self._resolve_schema_path(schema_path)
        for profile in self._scan_profiles(self._profiles_path, resolved_schema_path):
            if profile.profile_id == profile_id:
                return profile
        return None

    def load_profile(
        self,
        profile_id: str,
        schema_path: str = None,
    ) -> profile_module.Profile:
        profile = self.get_profile(profile_id, schema_path)
        if profile is None:
            raise errors.NoProfileError(f"No profile with id: {profile_id}")
        return profile

    def list_profile_ids(
        self,
        ignore: str = None,
        schema_path: str = None,
    ) -> list[str]:
        resolved_schema_path = self._resolve_schema_path(schema_path)
        return [
            profile.profile_id
            for profile in self._scan_profiles(
                self._profiles_path, resolved_schema_path, ignore=ignore
            )
        ]

    def filesystem_profile_ids(self) -> set[str]:
        if not os.path.isdir(self._profiles_path):
            return set()
        return {
            entry
            for entry in os.listdir(self._profiles_path)
            if os.path.isdir(os.path.join(self._profiles_path, entry))
        }

    def read_profile_from_path(
        self,
        profile_path: str,
        schema_path: str = None,
    ) -> profile_module.Profile:
        profile = self._load_profile_from_folder(profile_path, schema_path)
        if profile is None:
            raise errors.ProfileDataError(
                f"No profile configuration found at '{profile_path}'"
            )
        return profile

    def write_profile_config(self, profile: profile_module.Profile) -> None:
        if profile.is_sync_backed():
            raise errors.ProfileDataError(
                "FilesystemProfileBackend cannot write sync-backed profiles"
            )
        json_util.safe_dump(profile.as_dict(), self.config_file_path(profile.path))

    def resolve_avatar_path(self, profile: profile_module.Profile) -> None:
        if profile.avatar and profile.path:
            avatar_path = os.path.join(profile.path, profile.avatar)
            if os.path.isfile(avatar_path):
                profile.avatar_path = avatar_path

    def save_profile(
        self,
        profile: profile_module.Profile,
        global_config: dict,
    ) -> None:
        self.write_profile_config(profile)

    def duplicate_profile(
        self,
        profile: profile_module.Profile,
        name: str = None,
        description: str = None,
        schema_path: str = None,
    ) -> profile_module.Profile:
        raise NotImplementedError("FilesystemProfileBackend cannot duplicate profiles")

    def delete_profile(
        self,
        profile_id: str,
        profile: typing.Optional[profile_module.Profile] = None,
    ) -> None:
        if profile is not None and not profile.is_sync_backed():
            shutil.rmtree(profile.path)
            return
        profile_path = os.path.join(self._profiles_path, profile_id)
        if os.path.isdir(profile_path):
            shutil.rmtree(profile_path)

    def _scan_profiles(
        self,
        profiles_path: str,
        schema_path: str = None,
        ignore: str = None,
    ) -> list[profile_module.Profile]:
        profiles = []
        if not os.path.isdir(profiles_path):
            return profiles
        ignored_path = None if ignore is None else os.path.normpath(ignore)
        for profile_entry in os.scandir(profiles_path):
            if (
                ignored_path is not None
                and os.path.normpath(profile_entry.path) == ignored_path
            ):
                continue
            profile = self._load_profile_from_folder(profile_entry.path, schema_path)
            if profile is not None:
                profiles.append(profile)
        return profiles

    def _load_profile_from_folder(
        self,
        profile_path: str,
        schema_path: str = None,
    ) -> typing.Optional[profile_module.Profile]:
        logger = commons_logging.get_logger("ProfileExplorer")
        config_path = self.config_file_path(profile_path)
        if not os.path.isfile(config_path):
            logger.debug(
                f"Ignored {profile_path} as it does not contain a profile configuration"
            )
            return None
        profile = profile_module.Profile(profile_path, schema_path=schema_path)
        try:
            profile.from_dict(json_util.read_file(config_path))
            self.resolve_avatar_path(profile)
            return profile
        except Exception as err:
            logger.exception(
                err,
                True,
                f"Ignored profile due to an error upon reading '{profile_path}': {err}",
            )
        return None
