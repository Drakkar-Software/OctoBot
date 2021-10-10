#  Drakkar-Software OctoBot
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
import aiofiles

import octobot.constants as constants
import octobot.community.configuration.community_configuration as community_configuration


class ConfigurationSynchronizer:
    def __init__(self, authenticator):
        self.authenticator = authenticator

    async def get_account_configurations(self) -> list:
        async with self.authenticator.get_aiohttp_session().get(constants.OCTOBOT_COMMUNITY_CONFIGURATION_URL) as resp:
            if resp.status == 200:
                return self._parse_configurations(await resp.json())
            else:
                self._handle_resp_error(resp, "fetching")

    async def download_account_configurations(self,
                                              configuration: community_configuration.CommunityConfiguration,
                                              target_path: str) -> None:
        async with self.authenticator.get_aiohttp_session().get(
                f"{constants.OCTOBOT_COMMUNITY_CONFIGURATION_URL}{configuration.identifier}/download"
        ) as resp:
            if resp.status == 200:
                async with aiofiles.open(target_path, mode="wb") as f:
                    await f.write(await resp.read())
            else:
                self._handle_resp_error(resp, "fetching")

    async def create_account_configuration(self, configuration: community_configuration.CommunityConfiguration) \
            -> community_configuration.CommunityConfiguration:
        async with self.authenticator.get_aiohttp_session().post(
                constants.OCTOBOT_COMMUNITY_CONFIGURATION_URL,
                {"user_configuration": configuration.to_dict()}
        ) as resp:
            if resp.status == 200:
                return community_configuration.CommunityConfiguration.from_community_dict(await resp.json())
            else:
                self._handle_resp_error(resp, "creating")

    async def update_account_configuration(self,
                                           configuration: community_configuration.CommunityConfiguration,
                                           upload_archive=True) \
            -> community_configuration.CommunityConfiguration:
        async with self.authenticator.get_aiohttp_session().put(
                f"{constants.OCTOBOT_COMMUNITY_CONFIGURATION_URL}{configuration.identifier}",
                {"user_configuration": configuration.to_dict(with_archive=upload_archive)}
        ) as resp:
            if resp.status == 200:
                return community_configuration.CommunityConfiguration.from_community_dict(await resp.json())
            else:
                self._handle_resp_error(resp, "updating")

    async def delete_account_configuration(self, configuration: community_configuration.CommunityConfiguration) -> None:
        async with self.authenticator.get_aiohttp_session().delete(
                f"{constants.OCTOBOT_COMMUNITY_CONFIGURATION_URL}{configuration.identifier}"
        ) as resp:
            self._handle_resp_error(resp, "updating")

    def apply_configuration(self, configuration: community_configuration.CommunityConfiguration) -> None:
        pass
        #TODO

    def create_archive(self, configuration: community_configuration.CommunityConfiguration, config_dir: str) -> None:
        pass
        #TODO

    @staticmethod
    async def _handle_resp_error(resp, action):
        if resp.status != 200:
            raise RuntimeError(f"Error when {action} configurations, "
                               f"code: {resp.status}, text: {await resp.text}")

    @staticmethod
    def _parse_configurations(configurations):
        return [
            community_configuration.CommunityConfiguration.from_community_dict(data)
            for data in configurations
        ]
