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

from core.consumers_producers.producers import Producer
from core.exchange.ohlcv import OHLCVConsumer
from core.exchange.order_book import OrderBookConsumer
from core.exchange.recent_trade import RecentTradeConsumer
from core.exchange.ticker import TickerConsumer
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
        await self.send(
            OrderBookConsumer.create_feed(pair,
                                          self.parent.convert_into_ccxt_full_order_book(
                                              pair,
                                              book,
                                              timestamp)))


class RecentTradesCallBack(WebsocketCallBack):
    async def recent_trades_callback(self, _, pair, order_id, timestamp, side, amount, price):
        await self.send(RecentTradeConsumer.create_feed(pair,
                                                        self.parent.convert_into_ccxt_recent_trade(
                                                            pair,
                                                            side,
                                                            amount,
                                                            price,
                                                            timestamp)))


class TickersCallBack(WebsocketCallBack):
    async def tickers_callback(self, _, pair, bid, ask, timestamp):
        await self.send(TickerConsumer.create_feed(pair,
                                                   self.parent.convert_into_ccxt_price_ticker(
                                                       pair,
                                                       bid,
                                                       ask,
                                                       timestamp)))


class OHLCVCallBack(WebsocketCallBack):
    def __init__(self, parent, consumer, time_frame):
        super().__init__(parent, consumer)

        self.time_frame = time_frame

    async def ohlcv_callback(self, data=None):
        for symbol in data:
            await self.send(OHLCVConsumer.create_feed(self.time_frame,
                                                      symbol,
                                                      self.parent.convert_into_ccxt_ohlcv(
                                                          data,
                                                          symbol)))
