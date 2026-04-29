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

import octobot_commons.tentacles_management.class_inspector as class_inspector
import octobot_commons.profiles.profile_data as profile_data_import
import octobot_commons.profiles.exchange_auth_data as exchange_auth_data_import
import octobot_commons.profiles.tentacles_profile_data_adapter as tentacles_profile_data_adapter


class TentaclesProfileDataTranslator:
    """
    Translates a tentacle-specific configuration into a ProfileData
    """

    def __init__(
        self,
        profile_data: profile_data_import.ProfileData,
        auth_data: list[exchange_auth_data_import.ExchangeAuthData],
    ):
        self.profile_data: profile_data_import.ProfileData = profile_data
        self.auth_data: list[exchange_auth_data_import.ExchangeAuthData] = auth_data

    async def translate(
        self,
        tentacles_data: list[profile_data_import.TentaclesData],
        additional_data: dict,
        authenticator,
        auth_key: typing.Optional[str],
    ) -> None:
        """
        updates self.profile_data by applying the given tentacles_data and
        additional_data configuration
        :param tentacles_data: the tentacles data to use
        :param additional_data: other data that can be useful in translation
        :param authenticator: authenticator to fetch data from if necessary
        :param auth_key: auth key to used if necessary
        :return:
        """
        adapter = self._get_adapter(tentacles_data)
        await adapter(tentacles_data, additional_data, authenticator, auth_key).adapt(
            self.profile_data, self.auth_data
        )

    @classmethod
    def _get_adapter(cls, tentacles_data: list[profile_data_import.TentaclesData]):
        """
        :return: the first adapter matching a TentaclesData name
        """
        adapters = cls._get_adapters()
        for tentacles_data_element in tentacles_data:
            if adapter := adapters.get(tentacles_data_element.name):
                return adapter
        raise KeyError("TentaclesData adapter not found")

    @classmethod
    def _get_adapters(cls) -> dict:
        return {
            adapter.get_tentacle_name(): adapter
            for adapter in class_inspector.get_all_classes_from_parent(
                tentacles_profile_data_adapter.TentaclesProfileDataAdapter
            )
        }
