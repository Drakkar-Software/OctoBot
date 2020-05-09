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
from octobot_tentacles_manager.api.configurator import get_tentacles_setup_config


class Initializer:
    """Initializer class:
    - Initialize services, constants and tools
    """

    def __init__(self, octobot):
        self.octobot = octobot

    async def create(self):
        # initialize tentacle configuration
        self.octobot.tentacles_setup_config = get_tentacles_setup_config()

        # create OctoBot channel
        await self.octobot.global_consumer.initialize()
