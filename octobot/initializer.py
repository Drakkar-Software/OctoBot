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
from octobot_backtesting.api.backtesting import is_backtesting_enabled
from octobot_tentacles_manager.api.configurator import get_tentacles_setup_config
from octobot.community.community_manager import CommunityManager


class Initializer:
    """Initializer class:
    - Initialize services, constants and tools
    """

    def __init__(self, octobot):
        self.octobot = octobot

    async def create(self):
        # initialize tentacle configuration
        self.octobot.tentacles_setup_config = await get_tentacles_setup_config()
        # initialize tools
        self._init_metrics()

    def _init_metrics(self):
        if not is_backtesting_enabled(self.octobot.config):
            self.octobot.community_handler = CommunityManager(self.octobot.octobot_api)
