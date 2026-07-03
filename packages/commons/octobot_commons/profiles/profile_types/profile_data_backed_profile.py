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

import typing

import octobot_commons.errors as errors
import octobot_commons.profiles.profile_types.profile as profile_module
import octobot_commons.profiles.profile_data as profile_data_module


class ProfileDataBackedProfile(profile_module.Profile):
    """
    Profile facade with tentacle config stored in profile_data (RAM only).
    """

    def __init__(
        self,
        profile_data: profile_data_module.ProfileData,
        profile_path: str = None,
        schema_path: str = None,
    ):
        super().__init__(profile_path, schema_path=schema_path)
        self._profile_data = profile_data
        self.from_dict(profile_data._to_profile_dict())
        if profile_data.profile_details.id:
            self.profile_id = profile_data.profile_details.id
        if profile_data.profile_details.name:
            self.name = profile_data.profile_details.name

    def is_profile_data_tentacle_backed(self) -> bool:
        return True

    def get_profile_data(self) -> profile_data_module.ProfileData:
        return self._profile_data

    def get_tentacles_config_path(self) -> str:
        raise errors.ProfileDataError(
            "Profile data backed profiles have no filesystem tentacles config path"
        )

    def _build_tentacles_setup_config(self):
        import octobot_tentacles_manager.configuration.profile_tentacles_util as profile_tentacles_util

        return profile_tentacles_util.build_setup_config_from_profile_data(
            self.get_profile_data(), output_path=None, import_registered_tentacles=False
        )

    def _get_tentacles_data_without_tentacles_manager(self) -> list:
        return list(self.get_profile_data().tentacles)

    def get_tentacles_data(self) -> typing.Optional[list]:
        tentacles_setup_config = self.tentacles_setup_config
        if tentacles_setup_config is None:
            return None
        import octobot_tentacles_manager.configuration.profile_tentacles_util as profile_tentacles_util

        specific_configs_by_tentacle_name = {
            tentacle_data.name: tentacle_data.config or {}
            for tentacle_data in self.get_profile_data().tentacles
        }
        return profile_tentacles_util.collect_tentacles_data_from_setup(
            tentacles_setup_config,
            specific_configs_by_tentacle_name=specific_configs_by_tentacle_name,
        )
