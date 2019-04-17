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

from core.producers import Producer
from tools import get_logger


class WebsocketCallBack(Producer):
    def __init__(self, parent, consumer):
        super().__init__()
        self.parent = parent
        self.add_consumer(consumer)
        self.logger = get_logger(f"WebSocket"
                                 f" - {self.parent.exchange_manager.exchange.get_name()}"
                                 f" - {self.__class__.__name__}")


class OrderBookCallBack(WebsocketCallBack):
    async def l2_order_book_callback(self, _, pair, book, timestamp):
        await self.send(pair=pair,
                        order_book=self.parent.convert_into_ccxt_full_order_book(
                            pair,
                            book,
                            timestamp))


class RecentTradesCallBack(WebsocketCallBack):
    async def recent_trades_callback(self, _, pair, order_id, timestamp, side, amount, price):
        await self.send(pair=pair,
                        recent_trade=self.parent.convert_into_ccxt_recent_trade(
                            pair,
                            side,
                            amount,
                            price,
                            timestamp))


class TickersCallBack(WebsocketCallBack):
    async def tickers_callback(self, _, pair, bid, ask, timestamp):
        await self.send(pair=pair,
                        ticker=self.parent.convert_into_ccxt_price_ticker(
                            pair,
                            bid,
                            ask,
                            timestamp))


class OHLCVCallBack(WebsocketCallBack):
    def __init__(self, parent, consumer, time_frame):
        super().__init__(parent, consumer)

        self.time_frame = time_frame

    async def ohlcv_callback(self, data=None):
        for symbol in data:
            await self.send(pair=symbol,
                            time_frame=self.time_frame,
                            candle=self.parent.convert_into_ccxt_ohlcv(data[symbol]))
