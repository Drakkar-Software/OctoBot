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
import tentacles.Trading.Exchange.okxus.okxus_exchange as okxus_exchange
import tentacles.Trading.Exchange.okx_websocket_feed as okx_websocket_feed


class OkxUsCCXTWebsocketConnector(okx_websocket_feed.OKXCCXTWebsocketConnector):

    @classmethod
    def get_name(cls):
        return okxus_exchange.OkxUs.get_name()
