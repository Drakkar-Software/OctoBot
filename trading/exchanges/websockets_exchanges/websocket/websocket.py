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
from trading.exchanges.websockets_exchanges import AbstractWebSocket


class WebSocket(AbstractWebSocket):

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)

    # Abstract methods
    @classmethod
    def get_name(cls):
        raise NotImplementedError("get_name not implemented")

    @classmethod
    def has_name(cls, name: str) -> bool:
        raise NotImplementedError("has_name not implemented")

    def start_sockets(self):
        raise NotImplementedError("start_sockets not implemented")

    def stop_sockets(self):
        raise NotImplementedError("stop_sockets not implemented")

    @staticmethod
    def get_websocket_client(config, exchange_manager):
        raise NotImplementedError("get_websocket_client not implemented")

    def init_web_sockets(self, time_frames, trader_pairs):
        raise NotImplementedError("init_web_sockets not implemented")

    def close_and_restart_sockets(self):
        raise NotImplementedError("close_and_restart_sockets not implemented")

    def handles_recent_trades(self) -> bool:
        raise NotImplementedError("handles_recent_trades not implemented")

    def handles_order_book(self) -> bool:
        raise NotImplementedError("handles_order_book not implemented")

    def handles_price_ticker(self) -> bool:
        raise NotImplementedError("handles_price_ticker not implemented")

    def handles_ohlcv(self) -> bool:
        raise NotImplementedError("handles_ohlcv not implemented")

    def handles_funding(self) -> bool:
        raise NotImplementedError("handles_funding not implemented")

    # Converters
    def convert_into_ccxt_ticker(self, **kwargs):
        raise NotImplementedError("convert_into_ccxt_ticker not implemented")

    def convert_into_ccxt_order_book(self, **kwargs):
        raise NotImplementedError("convert_into_ccxt_order_book not implemented")

    def convert_into_ccxt_recent_trades(self, **kwargs):
        raise NotImplementedError("convert_into_ccxt_recent_trades not implemented")

    def convert_into_ccxt_ohlcv(self, **kwargs):
        raise NotImplementedError("convert_into_ccxt_ohlcv not implemented")

    def convert_into_ccxt_funding(self, **kwargs):
        raise NotImplementedError("convert_into_ccxt_funding not implemented")
