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
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot.constants as constants
import octobot_commons.databases as databases
import octobot.databases_util as databases_util


class Initializer:
    """Initializer class:
    - Initialize services, constants and tools
    """

    def __init__(self, octobot):
        self.octobot = octobot

    async def create(self, init_bot_storage):
        # initialize tentacle configuration
        tentacles_config_path = self.octobot.get_startup_config(constants.CONFIG_KEY, dict_only=False).\
            get_tentacles_config_path()
        self.octobot.tentacles_setup_config = tentacles_manager_api.get_tentacles_setup_config(tentacles_config_path)

        if init_bot_storage:
            # init bot storage
            await databases.init_bot_storage(
                self.octobot.bot_id,
                databases_util.get_run_databases_identifier(
                    self.octobot.config,
                    self.octobot.tentacles_setup_config
                ),
                True
            )

        # create OctoBot channel
        await self.octobot.global_consumer.initialize()
