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

import octobot_commons.enums as enums
import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.profile_types.profile_data_backed_profile as profile_data_backed_profile_module


class SyncProfile(profile_data_backed_profile_module.ProfileDataBackedProfile):
    """
    Profile facade backed by StrategyProvider profile_data.
    """

    def __init__(
        self,
        profile_data: profile_data_module.ProfileData,
        runtime_path: str,
        schema_path: str = None,
        strategy_version: str = "1",
    ):
        super().__init__(profile_data, profile_path=runtime_path, schema_path=schema_path)
        self._strategy_version = strategy_version

    def is_sync_backed(self) -> bool:
        return True

    def get_storage_source(self) -> enums.ProfileSource:
        return enums.ProfileSource.SYNC

    def get_strategy_version(self) -> str:
        return self._strategy_version

    def set_profile_data(self, profile_data: profile_data_module.ProfileData) -> None:
        self._profile_data = profile_data
        self.from_dict(profile_data._to_profile_dict())
        if profile_data.profile_details.id:
            self.profile_id = profile_data.profile_details.id
