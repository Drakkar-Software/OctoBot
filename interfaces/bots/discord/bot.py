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
from config import CONFIG_INTERFACES_DISCORD
from interfaces.bots.interface_bot import InterfaceBot


class DiscordApp(InterfaceBot):
    def __init__(self, config):
        super().__init__(config)

    @staticmethod
    def enable(config, is_enabled, associated_config=CONFIG_INTERFACES_DISCORD):
        super().enable(config, is_enabled, associated_config=associated_config)

    @staticmethod
    def is_enabled(config, associated_config=CONFIG_INTERFACES_DISCORD):
        return super().is_enabled(config, associated_config=associated_config)
