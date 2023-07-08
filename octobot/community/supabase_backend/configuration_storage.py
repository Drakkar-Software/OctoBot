#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import typing
import gotrue
import octobot_commons.configuration
import octobot_commons.logging
import octobot.constants


class SyncConfigurationStorage(gotrue.SyncSupportedStorage):
    """
    Used by gotrue client to save authenticated user session
    """
    def __init__(self, configuration: octobot_commons.configuration.Configuration):
        self.configuration: octobot_commons.configuration.Configuration = configuration

    def get_item(self, key: str) -> typing.Optional[str]:
        return self._get_value_in_config(key)

    def set_item(self, key: str, value: str) -> None:
        self._save_value_in_config(key, value)

    def remove_item(self, key: str) -> None:
        self._save_value_in_config(key, "")

    def _save_value_in_config(self, key, value):
        if self.configuration is not None:
            if octobot.constants.CONFIG_COMMUNITY not in self.configuration.config:
                self.configuration.config[octobot.constants.CONFIG_COMMUNITY] = {}
            self.configuration.config[octobot.constants.CONFIG_COMMUNITY][key] = value
            try:
                self.configuration.save()
            except Exception as err:
                octobot_commons.logging.get_logger(self.__class__.__name__).exception(
                    err, True, f"Error when saving configuration {err}"
                )

    def _get_value_in_config(self, key):
        if self.configuration is not None:
            try:
                return self.configuration.config[octobot.constants.CONFIG_COMMUNITY][key]
            except KeyError:
                return ""
        return None


class ASyncConfigurationStorage(gotrue.AsyncSupportedStorage):
    def __init__(self, configuration: octobot_commons.configuration.Configuration):
        self.sync_storage: SyncConfigurationStorage = SyncConfigurationStorage(configuration)

    async def get_item(self, key: str) -> typing.Optional[str]:
        return self.sync_storage.get_item(key)

    async def set_item(self, key: str, value: str) -> None:
        self.sync_storage.set_item(key, value)

    async def remove_item(self, key: str) -> None:
        self.sync_storage.remove_item(key)
