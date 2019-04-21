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
from typing import Dict

from core.channels.channel import Channel

"""
Channels ***
"""


class Channels:
    def __init__(self):
        self.channels: Dict[Channel] = {}

    async def start(self):
        for channel in [channel.values() for channel in self.channels.values()]:
            await channel.start()

    async def stop(self):
        for channel in [channel.values() for channel in self.channels.values()]:
            await channel.stop()

    async def run(self):
        for channel in [channel.values() for channel in self.channels.values()]:
            await channel.run()
