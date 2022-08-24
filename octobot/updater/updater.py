#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
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
import packaging.version as packaging_version

import octobot.constants as constants
import octobot.configuration_manager as configuration_manager
import octobot.commands as commands
import octobot_commons.logging as logging


class Updater:
    def __init__(self):
        self.logger = logging.get_logger(self.__class__.__name__)

    async def should_be_updated(self):
        """
        :return: True if the updater version is greater than current bot version
        """
        try:
            latest_version = await self.get_latest_version()
            if latest_version is None:
                return False
            return packaging_version.parse(latest_version) > packaging_version.parse(constants.VERSION)
        except TypeError as e:
            self.logger.debug(f"Error when comparing latest with current OctoBot version: {e}")

    async def get_latest_version(self):
        raise NotImplementedError("get_latest_version is not implemented")

    async def update_impl(self) -> bool:
        raise NotImplementedError("update_impl is not implemented")

    async def update_tentacles(self):
        await commands.install_all_tentacles(
            tentacles_url=configuration_manager.get_default_tentacles_url(version=await self.get_latest_version()))

    async def post_update(self):
        await self.update_tentacles()
        commands.restart_bot()

    async def update(self):
        """
        Call updater update_impl and updates tentacles on update success
        """
        if await self.update_impl():
            await self.post_update()
