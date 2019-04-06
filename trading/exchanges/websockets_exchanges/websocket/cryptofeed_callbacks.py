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

from tools import get_logger


class CryptoFeedCallBack:
    def __init__(self, parent):
        self.parent = parent

        self.logger = get_logger(f"WebSocket"
                                 f" - {self.parent.exchange_manager.exchange.get_name()}"
                                 f" - {self.__class__.__name__}")


class OrderBookCallBack(CryptoFeedCallBack):
    def __init__(self, parent):
        super().__init__(parent)

    async def order_book_callback(self, feed, pair, update, timestamp):
        # self.logger.info(f'ORDERBOOK / Timestamp: {timestamp} Feed: {feed} Pair: {pair}')
        # symbol_data = self._get_symbol_data_from_pair(pair)
        # if symbol_data:
        #     symbol_data.update_order_book(self.convert_into_ccxt_order_book(update))
        pass  # TODO


class RecentTradesCallBack(CryptoFeedCallBack):
    def __init__(self, parent):
        super().__init__(parent)

    async def recent_trades_callback(self, feed, pair, order_id, timestamp, side, amount, price):
        # self.logger.info(
        #     f"RECENT / Timestamp: {timestamp} Feed: {feed} Pair: {pair} ID: {order_id} Side: {side} Amount: {amount} Price: {price}")
        # symbol_data = self._get_symbol_data_from_pair(pair) if symbol_data:
        # symbol_data.update_recent_trades(self.convert_into_ccxt_recent_trades(side, amount, price))
        pass  # TODO


class TickersCallBack(CryptoFeedCallBack):
    def __init__(self, parent):
        super().__init__(parent)

    async def tickers_callback(self, feed, pair, bid, ask):
        # self.logger.info(f'TICKER / Pair: {pair} Bid: {bid} Ask: {ask}')
        # symbol_data = self._get_symbol_data_from_pair(pair)
        # if symbol_data:
        #     symbol_data.update_symbol_ticker(self.convert_into_ccxt_ticker(bid, ask))
        pass  # TODO


class OHLCVCallBack(CryptoFeedCallBack):
    def __init__(self, parent, time_frame):
        super().__init__(parent)

        self.time_frame = time_frame

    async def ohlcv_callback(self, data=None):
        self.logger.info("OHLCV callback")
        for symbol in data:
            symbol_data = self.parent.get_symbol_data_from_pair(symbol)
            if symbol_data.candles_are_initialized(self.time_frame):
                candle = self.parent.convert_into_ccxt_ohlcv(data, symbol)
                self.parent.exchange_manager.uniformize_candles_if_necessary(candle)
                symbol_data.update_symbol_candles(self.time_frame, candle, replace_all=False)


class FundingCallBack(CryptoFeedCallBack):
    def __init__(self, parent):
        super().__init__(parent)

    async def funding_callback(self, **kwargs):
        pass  # TODO
