#  Drakkar-Software OctoBot-Tentacles
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
from ..hollaex_autofilled.hollaex_autofilled_exchange import HollaexAutofilled
from ..hollaex_websocket_feed.hollaex_websocket import HollaexCCXTWebsocketConnector


class HollaexAutofilledCCXTWebsocketConnector(HollaexCCXTWebsocketConnector):
    def _get_logger_name(self):
        return f"WebSocket - {self._get_visible_name()}"

    def _get_visible_name(self):
        return self.exchange_manager.exchange_name

    @classmethod
    def get_name(cls):
        return HollaexAutofilled.get_name()

    def get_feed_name(self):
        return HollaexCCXTWebsocketConnector.get_name()
