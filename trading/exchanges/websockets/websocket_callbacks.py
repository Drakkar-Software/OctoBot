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
from core.channels.exchange.ohlcv import OHLCVProducer
from core.channels.exchange.order_book import OrderBookProducer
from core.channels.exchange.recent_trade import RecentTradeProducer
from core.channels.exchange.ticker import TickerProducer
from tools import get_logger


class WebsocketCallBack:
    def __init__(self, parent):
        self.parent = parent
        self.logger = get_logger(f"WebSocket"
                                 f" - {self.parent.exchange_manager.exchange.get_name()}"
                                 f" - {self.__class__.__name__}")


class OrderBookCallBack(WebsocketCallBack, OrderBookProducer):
    async def l2_order_book_callback(self, _, pair, book, timestamp):
        await self.receive(symbol=pair,
                           order_book=self.parent.convert_into_ccxt_full_order_book(
                               pair,
                               book,
                               timestamp))


class RecentTradesCallBack(WebsocketCallBack, RecentTradeProducer):
    async def recent_trades_callback(self, _, pair, order_id, timestamp, side, amount, price):
        await self.receive(symbol=pair,
                           recent_trade=self.parent.convert_into_ccxt_recent_trade(
                               pair,
                               side,
                               amount,
                               price,
                               timestamp))


class TickersCallBack(WebsocketCallBack, TickerProducer):
    async def tickers_callback(self, _, pair, bid, ask, timestamp):
        await self.receive(symbol=pair,
                           ticker=self.parent.convert_into_ccxt_price_ticker(
                               pair,
                               bid,
                               ask,
                               timestamp))


class OHLCVCallBack(WebsocketCallBack, OHLCVProducer):
    def __init__(self, parent, time_frame):
        super().__init__(parent)

        self.time_frame = time_frame

    async def ohlcv_callback(self, data=None):
        for symbol in data:
            await self.receive(symbol=symbol,
                               time_frame=self.time_frame,
                               candle=self.parent.convert_into_ccxt_ohlcv(data[symbol]))
