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

import octobot_commons.authentication as authentication_module
import octobot_commons.enums as enums
import octobot_commons.errors as errors
import octobot_commons.logging as logging
import octobot_commons.profiles.backends as profile_backends_module
import octobot_commons.profiles.profile_types.profile as profile_module
import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.profile_migration as profile_migration
import octobot_commons.profiles.profile_sharing as profile_sharing


class ProfileStorage:
    def __init__(
        self,
        profiles_path: str,
        profile_schema_path: str = None,
        filesystem_backend: profile_backends_module.FilesystemProfileBackend = None,
        sync_backend: profile_backends_module.SyncProfileBackend = None,
    ) -> None:
        self._profiles_path = profiles_path
        self._profile_schema_path = profile_schema_path
        self._sync_user_id: typing.Optional[str] = None
        self._readonly_profiles_path: typing.Optional[str] = None
        self._readonly_filesystem_backend: typing.Optional[
            profile_backends_module.FilesystemProfileBackend
        ] = None
        self._filesystem_backend = (
            filesystem_backend
            or profile_backends_module.FilesystemProfileBackend(
                profiles_path, profile_schema_path
            )
        )
        self._sync_backend = sync_backend or profile_backends_module.SyncProfileBackend(
            profiles_path, profile_schema_path, sync_user_id=None
        )

    @property
    def profiles_path(self) -> str:
        return self._profiles_path

    @property
    def profile_schema_path(self) -> str:
        return self._profile_schema_path

    def configure_sync_user(self, user_id: str) -> None:
        try:
            authentication_module.Authenticator.instance().get_wallet_by_user_id(user_id)
        except Exception as error:
            raise errors.ProfileDataError(
                f"Unknown sync user id: {user_id}"
            ) from error
        self._sync_user_id = user_id
        self._sync_backend._sync_user_id = user_id

    def bind_process_child_sync_user_id(self, user_id: str) -> None:
        if not user_id or not str(user_id).strip():
            raise errors.ProfileDataError("Process child sync user id must be non-empty")
        self._sync_user_id = str(user_id)
        self._sync_backend._sync_user_id = self._sync_user_id

    def is_master_overlay_profile(self, profile: profile_module.Profile) -> bool:
        if not self._readonly_profiles_path or profile.path is None:
            return False
        normalized_profile_path = os.path.normpath(profile.path)
        readonly_prefix = self._readonly_profiles_path
        if not readonly_prefix.endswith(os.sep):
            readonly_prefix = f"{readonly_prefix}{os.sep}"
        return normalized_profile_path == self._readonly_profiles_path or normalized_profile_path.startswith(
            readonly_prefix
        )

    def is_readonly_master_overlay_profile(self, profile: profile_module.Profile) -> bool:
        return self.is_master_overlay_profile(profile) and profile.read_only

    def configure_readonly_profiles_path(self, path: str) -> None:
        normalized_path = os.path.normpath(path)
        self._readonly_profiles_path = normalized_path
        self._readonly_filesystem_backend = profile_backends_module.FilesystemProfileBackend(
            normalized_path, self._profile_schema_path
        )

    def configure_paths(
        self,
        profiles_path: str,
        profile_schema_path: str = None,
    ) -> None:
        self._profiles_path = profiles_path
        if profile_schema_path is not None:
            self._profile_schema_path = profile_schema_path
        self._filesystem_backend._profiles_path = profiles_path
        self._sync_backend._profiles_path = profiles_path
        if profile_schema_path is not None:
            self._filesystem_backend._profile_schema_path = profile_schema_path
            self._sync_backend._profile_schema_path = profile_schema_path
            if self._readonly_filesystem_backend is not None:
                self._readonly_filesystem_backend._profile_schema_path = profile_schema_path

    def is_sync_available(self) -> bool:
        return bool(self._sync_user_id and str(self._sync_user_id).strip())

    def load_all_profiles(self) -> dict[str, profile_module.Profile]:
        if self._profiles_path is None:
            raise errors.ProfileDataError("profiles_path is required to load profiles")
        loaded_profiles = self._list_profiles()
        for profile in loaded_profiles.values():
            profile.bind_profile_storage(self)
        return loaded_profiles

    def list_sync_profiles(self) -> dict[str, profile_module.Profile]:
        profiles = self._sync_backend.list_profiles(self._profile_schema_path)
        for profile in profiles.values():
            profile.bind_profile_storage(self)
        return profiles

    def find_profile(
        self,
        profile_id: str,
    ) -> typing.Optional[profile_module.Profile]:
        return self._resolve_profile(profile_id)

    def get_profile(
        self,
        profile_id: str,
    ) -> typing.Optional[profile_module.Profile]:
        profile = self.find_profile(profile_id)
        if profile is not None:
            profile.bind_profile_storage(self)
        return profile

    def load_profile_by_id(self, profile_id: str) -> profile_module.Profile:
        profile = self.get_profile(profile_id)
        if profile is None:
            raise errors.NoProfileError(f"No profile with id: {profile_id}")
        return profile

    def filesystem_profile_ids(self) -> set[str]:
        return self._filesystem_backend.filesystem_profile_ids()

    def list_profile_ids(self, ignore: str = None) -> list[str]:
        filesystem_ids = self._filesystem_backend.list_profile_ids(ignore=ignore)
        overlay_ids = self._master_overlay_profile_ids(ignore=ignore)
        sync_ids = self._sync_backend.list_profile_ids(ignore=ignore)
        return list(dict.fromkeys(filesystem_ids + overlay_ids + sync_ids))

    def duplicate_profile(
        self,
        profile: profile_module.Profile,
        name: str = None,
        description: str = None,
    ) -> profile_module.Profile:
        if not self.is_sync_available():
            raise errors.ProfileDataError(
                "Profile duplicate requires a configured wallet user id"
            )
        clone = self._sync_backend.duplicate_profile(
            profile,
            name=name,
            description=description,
        )
        clone.bind_profile_storage(self)
        return clone

    def activate_profile(self, profile: profile_module.Profile) -> None:
        profile.bind_profile_storage(self)
        profile.init_tentacles_setup_config()

    def save_active_profile(
        self,
        profile: profile_module.Profile,
        global_config: dict,
    ) -> None:
        if self.is_readonly_master_overlay_profile(profile):
            raise errors.ProfileDataError(
                f"{profile.name} profile is shared from the master and can't be saved"
            )
        backend = self._get_backend_for_profile(profile)
        logging.get_logger(self.__class__.__name__).info(
            f"Saving {profile.name} {profile.__class__.__name__} with "
            f"{backend.__class__.__name__}"
        )
        backend.save_profile(profile, global_config)
        if profile.get_storage_source() == enums.ProfileSource.FILESYSTEM:
            tentacles_setup_config = profile.tentacles_setup_config
            if tentacles_setup_config is not None:
                tentacles_setup_config.save_config(is_config_update=True)

    def delete_profile(
        self,
        profile_id: str,
        profile: profile_module.Profile = None,
    ) -> None:
        if profile is None:
            profile = self.find_profile(profile_id)
        if profile is None:
            raise errors.ProfileRemovalError(f"Profile {profile_id} not found")
        if self.is_readonly_master_overlay_profile(profile):
            raise errors.ProfileRemovalError(
                f"{profile.name} profile is shared from the master and can't be removed"
            )
        backend = self._get_backend_for_profile(profile)
        if profile.read_only and not profile.imported:
            raise errors.ProfileRemovalError(f"{profile.name} profile can't be removed")
        backend.delete_profile(profile_id, profile=profile)

    def has_any_profiles(self) -> bool:
        if self._profiles_path is None:
            return False
        return self._has_any_profiles()

    async def import_profile_data(
        self,
        profile_data: profile_data_module.ProfileData,
        profile_schema: str,
        bot_install_path: str,
        name: str = None,
        description: str = None,
        risk=None,
        auto_update: bool = False,
        slug: str = None,
        logo_url: str = None,
        force_simulator: bool = False,
        aiohttp_session=None,
        origin_url: str = None,
    ) -> profile_module.Profile:
        if self.is_sync_available():
            profile = self._sync_backend.import_profile_data(
                profile_data,
                schema_path=profile_schema,
                name=name,
                description=description,
                risk=risk,
                auto_update=auto_update,
                slug=slug,
                force_simulator=force_simulator,
            )
            profile.bind_profile_storage(self)
            return profile
        return await profile_sharing.import_profile_data_as_profile(
            profile_data,
            profile_schema,
            aiohttp_session,
            name=name,
            description=description,
            risk=risk,
            bot_install_path=bot_install_path,
            origin_url=origin_url,
            logo_url=logo_url,
            auto_update=auto_update,
            force_simulator=force_simulator,
            profile_storage=self,
        )

    def migrate_filesystem_profiles_to_sync(self) -> list[str]:
        return profile_migration.migrate_user_profiles_to_sync(self)

    def _master_overlay_profiles(self) -> dict[str, profile_module.Profile]:
        if self._readonly_filesystem_backend is None:
            return {}
        return self._readonly_filesystem_backend.list_profiles()

    def _master_overlay_profile_ids(self, ignore: str = None) -> list[str]:
        overlay_ids = []
        for profile_id in self._master_overlay_profiles():
            if ignore is not None and profile_id == ignore:
                continue
            overlay_ids.append(profile_id)
        return overlay_ids

    def _list_profiles(self) -> dict[str, profile_module.Profile]:
        profiles = self._sync_backend.list_profiles()
        for profile_id, profile in self._master_overlay_profiles().items():
            if profile_id not in profiles:
                profiles[profile_id] = profile
        profiles.update(self._filesystem_backend.list_profiles())
        return profiles

    def _resolve_profile(
        self,
        profile_id: str,
    ) -> typing.Optional[profile_module.Profile]:
        filesystem_profile = self._filesystem_backend.get_profile(profile_id)
        if filesystem_profile is not None:
            return filesystem_profile
        sync_profile = self._sync_backend.get_profile(profile_id)
        if sync_profile is not None:
            return sync_profile
        if self._readonly_filesystem_backend is None:
            return None
        return self._readonly_filesystem_backend.get_profile(profile_id)

    def _ensure_profile_persistable(self, profile: profile_module.Profile) -> None:
        if profile.get_storage_source() == enums.ProfileSource.EPHEMERAL:
            raise errors.ProfileDataError("Ephemeral profiles cannot be persisted")

    def _get_backend_for_profile(
        self, profile: profile_module.Profile
    ) -> profile_backends_module.AbstractProfileBackend:
        self._ensure_profile_persistable(profile)
        if profile.is_sync_backed():
            return self._sync_backend
        if self.is_master_overlay_profile(profile) and self._readonly_filesystem_backend is not None:
            return self._readonly_filesystem_backend
        return self._filesystem_backend

    def _has_any_profiles(self) -> bool:
        return bool(self._list_profiles())
