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


from config import OctoBotTypes
from .abstract_websocket import AbstractWebSocket
from tools.os_util import get_octobot_type
from octobot_commons.logging.logging_util import get_logger

try:
    from trading.exchanges.websockets.octobot_websocket import OctoBotWebSocketClient
except ImportError as e:
    if get_octobot_type() != OctoBotTypes.BINARY.value:
        get_logger("websocket_exchanges").warning(f"Error when importing BinanceWebSocketClient: {e}")
