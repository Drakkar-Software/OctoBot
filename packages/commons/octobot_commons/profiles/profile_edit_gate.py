# pylint: disable=C0116
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

import enum
import os
import typing

import octobot_commons.constants as constants
import octobot_commons.enums as enums
import octobot_commons.errors as errors
import octobot_commons.logging as logging

if typing.TYPE_CHECKING:
    import octobot_commons.profiles.profile_storage as profile_storage_module
    import octobot_commons.profiles.profile_types.profile as profile_module

_PROFILE_EDIT_LOGGER = "ProfileEdit"


class ProfileEditType(enum.Enum):
    PROFILE_CONFIG = "profile_config"
    TENTACLE_CONFIG = "tentacle_config"
    TENTACLE_ACTIVATION = "tentacle_activation"


class ProfilePersistenceTarget(enum.Enum):
    CHILD_OVERRIDE = "child_override"
    STANDARD_FILESYSTEM = "standard_filesystem"
    MASTER_OVERLAY = "master_overlay"
    SYNC_PROFILE = "sync_profile"


class ProfileEditGate:
    """
    Policy-only gate for profile edit persistence.
    Callers perform disk I/O after consulting assert_edit_allowed and resolve_writable_path.
    """

    def __init__(self, profile_storage: profile_storage_module.ProfileStorage) -> None:
        self._profile_storage = profile_storage

    def assert_edit_allowed(
        self,
        profile: profile_module.Profile,
        edit_type: ProfileEditType,
    ) -> None:
        if profile.get_storage_source() == enums.ProfileSource.EPHEMERAL:
            reason = "Ephemeral profiles cannot be persisted"
            self.log_edit_blocked(profile, edit_type, reason)
            raise errors.ProfileDataError(reason)
        if (
            edit_type is ProfileEditType.TENTACLE_ACTIVATION
            and self.is_strategy_locked(profile)
            and not profile.is_sync_backed()
        ):
            reason = (
                f"{profile.name} profile strategy is read-only; "
                f"tentacle activation cannot be changed"
            )
            self.log_edit_blocked(profile, edit_type, reason)
            raise errors.ProfileDataError(reason)

    def resolve_writable_path(
        self,
        profile: profile_module.Profile,
        edit_type: ProfileEditType,
    ) -> str:
        del edit_type
        if profile.is_sync_backed():
            if profile.path is None:
                raise errors.ProfileDataError(
                    f"Sync-backed profile {profile.name} has no writable path"
                )
            return profile.path
        if self._profile_storage.is_readonly_master_overlay_profile(profile):
            return self._child_overlay_profile_path(profile)
        return profile.path

    def resolve_activation_read_path(self, profile: profile_module.Profile) -> str:
        strategy_source_path = self.resolve_strategy_source_path(profile)
        return os.path.join(strategy_source_path, constants.CONFIG_TENTACLES_FILE)

    def resolve_strategy_source_path(self, profile: profile_module.Profile) -> str:
        return profile.path

    def resolve_persistence_target(
        self,
        profile: profile_module.Profile,
        edit_type: ProfileEditType,
    ) -> ProfilePersistenceTarget:
        del edit_type
        if profile.is_sync_backed():
            return ProfilePersistenceTarget.SYNC_PROFILE
        if self._profile_storage.is_readonly_master_overlay_profile(profile):
            return ProfilePersistenceTarget.CHILD_OVERRIDE
        if self._profile_storage.is_master_overlay_profile(profile):
            return ProfilePersistenceTarget.MASTER_OVERLAY
        return ProfilePersistenceTarget.STANDARD_FILESYSTEM

    def is_strategy_locked(self, profile: profile_module.Profile) -> bool:
        return bool(profile.read_only)

    def should_skip_tentacles_setup_config_write(
        self,
        profile: profile_module.Profile,
    ) -> bool:
        return self.is_strategy_locked(profile) and not profile.is_sync_backed()

    def log_edit_saved(
        self,
        profile: profile_module.Profile,
        edit_type: ProfileEditType,
        target_path: str,
        **context,
    ) -> None:
        persistence_target = self.resolve_persistence_target(profile, edit_type)
        context_suffix = ""
        if context:
            context_suffix = " " + " ".join(
                f"{key}={value}" for key, value in context.items()
            )
        logging.get_logger(_PROFILE_EDIT_LOGGER).info(
            "Saved profile edit: edit_type=%s persistence_target=%s profile=%r "
            "profile_id=%s path=%s%s",
            edit_type.value,
            persistence_target.value,
            profile.name,
            profile.profile_id,
            target_path,
            context_suffix,
        )

    def log_edit_blocked(
        self,
        profile: profile_module.Profile,
        edit_type: ProfileEditType,
        reason: str,
    ) -> None:
        logging.get_logger(_PROFILE_EDIT_LOGGER).error(
            "Blocked profile edit: edit_type=%s profile=%r profile_id=%s reason=%s",
            edit_type.value,
            profile.name,
            profile.profile_id,
            reason,
        )

    def _child_overlay_profile_path(self, profile: profile_module.Profile) -> str:
        if not profile.profile_id:
            raise errors.ProfileDataError(
                f"Profile {profile.name} has no profile_id for child overlay path"
            )
        profiles_path = self._profile_storage.profiles_path
        if not profiles_path:
            raise errors.ProfileDataError(
                "profiles_path is required for child overlay writes"
            )
        return os.path.join(profiles_path, profile.profile_id)
