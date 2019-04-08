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
import time

from tools import get_logger


class CryptoFeedCallBack:
    def __init__(self, parent):
        self.parent = parent

        self.logger = get_logger(f"WebSocket"
                                 f" - {self.parent.exchange_manager.exchange.get_name()}"
                                 f" - {self.__class__.__name__}")


class OrderBookCallBack(CryptoFeedCallBack):
    async def l2_order_book_callback(self, _, pair, book, timestamp):
        symbol_data = self.parent.get_symbol_data_from_pair(pair)
        if symbol_data and symbol_data.order_book_is_initialized():
            symbol_data.update_order_book(self.parent.convert_into_ccxt_full_order_book(symbol_data.symbol,
                                                                                        book,
                                                                                        timestamp))


class RecentTradesCallBack(CryptoFeedCallBack):
    async def recent_trades_callback(self, _, pair, order_id, timestamp, side, amount, price):
        symbol_data = self.parent.get_symbol_data_from_pair(pair)
        if symbol_data and symbol_data.recent_trades_are_initialized():
            symbol_data.add_new_recent_trades(self.parent.convert_into_ccxt_recent_trade(symbol_data.symbol,
                                                                                         side,
                                                                                         amount,
                                                                                         price,
                                                                                         timestamp))


class TickersCallBack(CryptoFeedCallBack):
    async def tickers_callback(self, _, pair, bid, ask):
        symbol_data = self.parent.get_symbol_data_from_pair(pair)
        if symbol_data:
            symbol_data.update_symbol_price_ticker(
                self.parent.convert_into_ccxt_price_ticker(symbol_data.symbol, bid, ask, time.time()))


class OHLCVCallBack(CryptoFeedCallBack):
    def __init__(self, parent, time_frame):
        super().__init__(parent)

        self.time_frame = time_frame

    async def ohlcv_callback(self, data=None):
        timestamp = time.time()  # TODO
        for symbol in data:
            symbol_data = self.parent.get_symbol_data_from_pair(symbol)
            if symbol_data:
                if self.time_frame > 0 and symbol_data.candles_are_initialized(self.time_frame):
                    candle = self.parent.convert_into_ccxt_ohlcv(data, symbol, timestamp)
                    self.parent.exchange_manager.uniformize_candles_if_necessary(candle)
                    symbol_data.update_symbol_candles(self.time_frame, candle, replace_all=False)
                else:
                    # real time data
                    symbol_data.update_symbol_ticker(
                        self.parent.convert_into_ccxt_ticker(symbol, data, timestamp))


class FundingCallBack(CryptoFeedCallBack):
    async def funding_callback(self, **kwargs):
        # Not implemented
        timestamp = time.time()
        feed = kwargs['feed']
