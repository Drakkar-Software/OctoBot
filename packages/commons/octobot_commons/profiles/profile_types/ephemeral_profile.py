# pylint: disable=W0237
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

import octobot_commons.enums as enums
import octobot_commons.errors as errors
import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.profile_types.profile_data_backed_profile as profile_data_backed_profile_module


class EphemeralProfile(profile_data_backed_profile_module.ProfileDataBackedProfile):
    """
    Short-lived RAM-only profile backed by ProfileData.
    """

    @classmethod
    def from_profile_data(
        cls,
        profile_data: profile_data_module.ProfileData,
        schema_path: str = None,
    ) -> EphemeralProfile:
        return cls(profile_data, schema_path=schema_path)

    def __init__(
        self,
        profile_data: profile_data_module.ProfileData,
        schema_path: str = None,
    ):
        super().__init__(profile_data, profile_path=None, schema_path=schema_path)

    def is_sync_backed(self) -> bool:
        return False

    def get_storage_source(self) -> enums.ProfileSource:
        return enums.ProfileSource.EPHEMERAL

    def validate_and_save_config(self) -> None:
        raise errors.ProfileDataError("Ephemeral profiles cannot be saved")

    def save(self) -> None:
        raise errors.ProfileDataError("Ephemeral profiles cannot be saved")

    def delete(self) -> None:
        raise errors.ProfileDataError("Ephemeral profiles cannot be deleted")

    def duplicate(self, name: str = None, description: str = None):
        raise errors.ProfileDataError("Ephemeral profiles cannot be duplicated")
