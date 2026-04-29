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
import typing

import octobot_commons.profiles.profile_data as profile_data_import
import octobot_commons.profiles.exchange_auth_data as exchange_auth_data_import


class TentaclesProfileDataAdapter:
    """
    Used to adapt the content of a ProfileData using the given TentaclesData
    """

    def __init__(
        self,
        tentacles_data: list[profile_data_import.TentaclesData],
        additional_data: dict,
        authenticator,
        auth_key: typing.Optional[str],
    ):
        self.tentacles_data: list[profile_data_import.TentaclesData] = tentacles_data
        self.additional_data: dict = additional_data
        self.authenticator = authenticator
        self.auth_key = auth_key

    async def adapt(
        self,
        profile_data: profile_data_import.ProfileData,
        auth_data: list[exchange_auth_data_import.ExchangeAuthData],
    ) -> None:
        """
        Use self.tentacles_data to adapt the given profile_data
        """
        raise NotImplementedError("adapt is not implemented")

    @classmethod
    def get_tentacle_name(cls) -> str:
        """
        :return: the name of the adapter
        """
        raise NotImplementedError("get_tentacle_name is not implemented")
