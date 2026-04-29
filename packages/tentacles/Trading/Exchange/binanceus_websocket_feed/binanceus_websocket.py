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
import tentacles.Trading.Exchange.binanceus.binanceus_exchange as binanceus_exchange
import tentacles.Trading.Exchange.binance_websocket_feed.binance_websocket as binance_websocket


class BinanceUSCCXTFeedConnector(binance_websocket.BinanceCCXTWebsocketConnector):
    @classmethod
    def get_name(cls):
        return binanceus_exchange.BinanceUS.get_name()
