#  Drakkar-Software OctoBot-Services
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
from octobot_commons.logging.logging_util import get_logger

from octobot_services.interfaces.bots import abstract_bot_interface

from octobot_services.interfaces.bots.abstract_bot_interface import (
    AbstractBotInterface,
)

LOGGER = get_logger(__name__)
EOL = "\n"
NO_TRADER_MESSAGE = """OctoBot is either starting or there is no trader is activated in my config/config.json file.
See https://github.com/Drakkar-Software/OctoBot/wiki if you need help with my configuration."""
NO_CURRENCIES_MESSAGE = "No cryptocurrencies are in my activated profile.\n" \
                        "See https://github.com/Drakkar-Software/OctoBot/wiki/Configuration#cryptocurrencies " \
                        "if you need help with my cryptocurrencies configuration."""
UNAUTHORIZED_USER_MESSAGE = "Hello, I dont talk to strangers."

__all__ = [
    "AbstractBotInterface",
    "LOGGER",
    "EOL",
    "NO_TRADER_MESSAGE",
    "NO_CURRENCIES_MESSAGE"
]
