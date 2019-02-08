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

import numpy as np

from config import PriceIndexes, TimeFramesMinutes, MINUTE_TO_SECONDS
from tools.logging.logging_util import get_logger


class SymbolData:
    MAX_ORDER_BOOK_ORDER_COUNT = 100
    MAX_RECENT_TRADES_COUNT = 100
    MAX_CANDLES_COUNT = 1000

    def __init__(self, symbol):
        self.symbol = symbol

        self.symbol_candles = {}
        self.order_book = []
        self.recent_trades = []
        self.symbol_ticker = None

        self.previous_candle_time = {}

        self.are_recent_trades_initialized = False
        self.is_order_book_initialized = False
        self.logger = get_logger(f"{self.__class__.__name__} - {self.symbol}")

    '''
    Called by exchange dispatcher
    '''

    # candle functions
    def update_symbol_candles(self, time_frame, new_symbol_candles_data, replace_all=False):
        current_time = time.time()
        if time_frame is not None and time_frame not in self.symbol_candles or replace_all:
            self.symbol_candles[time_frame] = CandleData(new_symbol_candles_data)
            self.previous_candle_time[time_frame] = current_time

        else:
            candle_data = self.symbol_candles[time_frame]
            # else check if we should edit the last candle or move to a new one
            if candle_data.should_add_new_candle(new_symbol_candles_data[PriceIndexes.IND_PRICE_TIME.value]):
                candle_data.change_current_candle(new_symbol_candles_data)
                self.previous_candle_time[time_frame] = current_time

            # only need to edit the last candle
            else:
                candle_data.set_last_candle(new_symbol_candles_data)

    def ensure_data_validity(self, time_frame):
        previous_candle_timestamp = self._get_previous_candle_timestamp(time_frame)
        error_allowance = 1.2
        current_time = time.time()
        if previous_candle_timestamp is not None:
            # if update time from the previous time frame is greater than this given time frame:
            # data did not get updated => data are invalid
            if current_time - previous_candle_timestamp > \
                    TimeFramesMinutes[time_frame] * MINUTE_TO_SECONDS * error_allowance:
                return False
        return True

    # ticker functions
    def update_symbol_ticker(self, new_symbol_ticker_data):
        self.symbol_ticker = new_symbol_ticker_data

    # order book functions
    def update_order_book(self, new_order_book_data):
        self.order_book = new_order_book_data

    # recent trade functions
    def update_recent_trades(self, new_recent_trades_data):
        self.recent_trades = new_recent_trades_data

    '''
    Called by non-trade classes
    '''

    # candle functions
    def get_candle_data(self, time_frame):
        if time_frame in self.symbol_candles:
            return self.symbol_candles[time_frame]
        elif time_frame is None:
            return self.symbol_candles[next(iter(self.symbol_candles))]
        return None

    def get_available_time_frames(self):
        return self.symbol_candles.keys()

    # ticker functions
    def get_symbol_ticker(self):
        return self.symbol_ticker

    # order book functions
    def get_symbol_order_book(self):
        return self.order_book

    # recent trade functions
    def get_symbol_recent_trades(self):
        return self.recent_trades

    # private functions
    @staticmethod
    def _has_candle_changed(candle_data, start_candle_time):
        return candle_data.time_candles_list[-1] < start_candle_time

    def _get_previous_candle_timestamp(self, time_frame):
        if time_frame in self.previous_candle_time:
            return self.previous_candle_time[time_frame]
        else:
            return None

    def candles_are_initialized(self, time_frame):
        if time_frame in self.symbol_candles and self.symbol_candles[time_frame].is_initialized:
            return True
        elif time_frame is None:
            return True
        return False

    def price_ticker_is_initialized(self) -> bool:
        return True if self.symbol_ticker is not None else False

    def get_symbol_prices(self, time_frame, limit=None, return_list=False):
        return self.get_candle_data(time_frame).get_symbol_prices(limit, return_list)

    def recent_trades_are_initialized(self):
        return self.are_recent_trades_initialized

    def init_recent_trades(self):
        self.are_recent_trades_initialized = True

    def order_book_is_initialized(self):
        return self.is_order_book_initialized

    def init_order_book(self):
        self.is_order_book_initialized = True


class CandleData:
    def __init__(self, all_candles_data):
        self.is_initialized = False
        self.close_candles_list = []
        self.open_candles_list = []
        self.high_candles_list = []
        self.low_candles_list = []
        self.time_candles_list = []
        self.volume_candles_list = []

        self.close_candles_array = None
        self.open_candles_array = None
        self.high_candles_array = None
        self.low_candles_array = None
        self.time_candles_array = None
        self.volume_candles_array = None

        self.set_all_candles(all_candles_data)

        self.is_initialized = True

    # getters
    def get_symbol_close_candles(self, limit=None, return_list=False):
        if return_list:
            return self.extract_limited_data(self.close_candles_list, limit)
        else:
            self.update_arrays()
            return self.extract_limited_data(self.close_candles_array, limit)

    def get_symbol_open_candles(self, limit=None, return_list=False):
        if return_list:
            return self.extract_limited_data(self.open_candles_list, limit)
        else:
            self.update_arrays()
            return self.extract_limited_data(self.open_candles_array, limit)

    def get_symbol_high_candles(self, limit=None, return_list=False):
        if return_list:
            return self.extract_limited_data(self.high_candles_list, limit)
        else:
            self.update_arrays()
            return self.extract_limited_data(self.high_candles_array, limit)

    def get_symbol_low_candles(self, limit=None, return_list=False):
        if return_list:
            return self.extract_limited_data(self.low_candles_list, limit)
        else:
            self.update_arrays()
            return self.extract_limited_data(self.low_candles_array, limit)

    def get_symbol_time_candles(self, limit=None, return_list=False):
        if return_list:
            return self.extract_limited_data(self.time_candles_list, limit)
        else:
            self.update_arrays()
            return self.extract_limited_data(self.time_candles_array, limit)

    def get_symbol_volume_candles(self, limit=None, return_list=False):
        if return_list:
            return self.extract_limited_data(self.volume_candles_list, limit)
        else:
            self.update_arrays()
            return self.extract_limited_data(self.volume_candles_array, limit)

    def get_symbol_prices(self, limit=None, return_list=False):
        symbol_prices = [None] * len(PriceIndexes)
        symbol_prices[PriceIndexes.IND_PRICE_CLOSE.value] = self.get_symbol_close_candles(limit, return_list)
        symbol_prices[PriceIndexes.IND_PRICE_OPEN.value] = self.get_symbol_open_candles(limit, return_list)
        symbol_prices[PriceIndexes.IND_PRICE_HIGH.value] = self.get_symbol_high_candles(limit, return_list)
        symbol_prices[PriceIndexes.IND_PRICE_LOW.value] = self.get_symbol_low_candles(limit, return_list)
        symbol_prices[PriceIndexes.IND_PRICE_TIME.value] = self.get_symbol_time_candles(limit, return_list)
        symbol_prices[PriceIndexes.IND_PRICE_VOL.value] = self.get_symbol_volume_candles(limit, return_list)

        if return_list:
            return symbol_prices
        else:
            return np.array(symbol_prices)

    # setters
    def set_last_candle(self, last_candle_data):
        self.close_candles_list[-1] = last_candle_data[PriceIndexes.IND_PRICE_CLOSE.value]
        self.high_candles_list[-1] = last_candle_data[PriceIndexes.IND_PRICE_HIGH.value]
        self.low_candles_list[-1] = last_candle_data[PriceIndexes.IND_PRICE_LOW.value]
        self.volume_candles_list[-1] = last_candle_data[PriceIndexes.IND_PRICE_VOL.value]

    def set_all_candles(self, new_candles_data):
        self.close_candles_list = []
        self.open_candles_list = []
        self.high_candles_list = []
        self.low_candles_list = []
        self.time_candles_list = []
        self.volume_candles_list = []

        if isinstance(new_candles_data[-1], list):
            for candle_data in new_candles_data:
                self.add_new_candle(candle_data)
        else:
            self.add_new_candle(new_candles_data)

    def change_current_candle(self, new_last_candle_data):
        if len(self.time_candles_list) >= SymbolData.MAX_CANDLES_COUNT:
            self.close_candles_list.pop(0)
            self.open_candles_list.pop(0)
            self.high_candles_list.pop(0)
            self.low_candles_list.pop(0)
            self.time_candles_list.pop(0)
            self.volume_candles_list.pop(0)
        self.add_new_candle(new_last_candle_data)

    def should_add_new_candle(self, new_open_time):
        return new_open_time not in self.time_candles_list

    def add_new_candle(self, new_candle_data):
        self.close_candles_list.append(new_candle_data[PriceIndexes.IND_PRICE_CLOSE.value])
        self.open_candles_list.append(new_candle_data[PriceIndexes.IND_PRICE_OPEN.value])
        self.high_candles_list.append(new_candle_data[PriceIndexes.IND_PRICE_HIGH.value])
        self.low_candles_list.append(new_candle_data[PriceIndexes.IND_PRICE_LOW.value])
        self.time_candles_list.append(new_candle_data[PriceIndexes.IND_PRICE_TIME.value])
        self.volume_candles_list.append(new_candle_data[PriceIndexes.IND_PRICE_VOL.value])

    def update_arrays(self):
        if self.time_candles_array is None or self.time_candles_array[-1] != self.time_candles_list[-1]:
            self.close_candles_array = self.convert_list_to_array(self.close_candles_list)
            self.open_candles_array = self.convert_list_to_array(self.open_candles_list)
            self.high_candles_array = self.convert_list_to_array(self.high_candles_list)
            self.low_candles_array = self.convert_list_to_array(self.low_candles_list)
            self.time_candles_array = self.convert_list_to_array(self.time_candles_list)
            self.volume_candles_array = self.convert_list_to_array(self.volume_candles_list)

            # used only when a new candle was created during the previous execution
            if self.time_candles_array[-1] != self.time_candles_list[-1]:
                self.update_arrays()
        else:
            self.set_last_candle_arrays(self.close_candles_list, self.close_candles_array)
            self.set_last_candle_arrays(self.high_candles_list, self.high_candles_array)
            self.set_last_candle_arrays(self.low_candles_list, self.low_candles_array)
            self.set_last_candle_arrays(self.volume_candles_list, self.volume_candles_array)

            # used only when a new update was preformed during the previous execution
            self.sanitize_last_candle(self.close_candles_array, self.high_candles_array, self.low_candles_array)

    @staticmethod
    def sanitize_last_candle(close_candle_data, high_candle_data, low_candle_data):
        close_last_candle = close_candle_data[-1]
        if low_candle_data[-1] > close_last_candle:
            low_candle_data[-1] = close_last_candle
        if high_candle_data[-1] < close_last_candle:
            high_candle_data[-1] = close_last_candle

    @staticmethod
    def set_last_candle_arrays(list_updated, array_to_update):
        if array_to_update is not None:
            array_to_update[-1] = list_updated[-1]

    @staticmethod
    def convert_list_to_array(list_to_convert):
        return np.array(list_to_convert)

    @staticmethod
    def extract_limited_data(data, limit=None):
        if limit is None:
            return data

        return data[-min(limit, len(data)):]
