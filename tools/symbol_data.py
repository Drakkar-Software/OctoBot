import numpy as np

from config.cst import PriceStrings


class SymbolData:
    MAX_ORDER_BOOK_ORDER_COUNT = 100
    MAX_RECENT_TRADES_COUNT = 100

    def __init__(self, symbol, time_frame):
        self.symbol = symbol
        self.time_frame = time_frame

        # candle attributes
        self.symbol_candles = {}

    '''
    Called by exchange dispatcher
    '''

    # candle functions
    def update_symbol_candles(self, time_frame, new_symbol_candles_data, start_candle_time=None, replace_all=False):
        if time_frame not in self.symbol_candles or replace_all:
            self.symbol_candles[time_frame] = CandleData(new_symbol_candles_data)

        # else check if we should edit the last candle or move to a new one
        elif start_candle_time is not None and self._has_candle_changed(time_frame, start_candle_time):
            self.symbol_candles[time_frame].change_current_candle(new_symbol_candles_data)

        # only need to edit the last candle
        else:
            self.symbol_candles[time_frame].set_last_candle(new_symbol_candles_data)

    # ticker functions
    def update_symbol_ticker(self, new_symbol_ticker_data):
        pass

    # order book functions
    def update_order_book(self, new_order_book_data):
        pass

    # recent trade functions
    def update_last_trades(self, new_recent_trades_data):
        pass

    '''
    Called by non-trade classes
    '''

    # candle functions
    def get_candle_data(self, time_frame):
        if time_frame in self.symbol_candles:
            return self.symbol_candles[time_frame]
        return None

    # ticker functions
    def get_symbol_ticker(self):
        pass

    # order book functions
    def get_symbol_order_book(self, limit=None):
        pass

    # recent trade functions
    def get_symbol_recent_trades(self, limit=None):
        pass

    # private functions
    def _has_candle_changed(self, time_frame, start_candle_time):
        if self.symbol_candles[time_frame].get_symbol_time_candles(1) < start_candle_time:
            return True
        else:
            return False


class CandleData:
    def __init__(self, all_candles_data, create_arrays=False):
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

        if create_arrays:
            self.create_all_arrays()

    # getters
    def get_symbol_close_candles(self, limit=None, return_list=False):
        if return_list:
            return self.extract_limited_data(self.close_candles_list, limit)
        else:
            if self.close_candles_array is None:
                self.close_candles_array = self.convert_list_to_array(self.close_candles_list)
            return self.extract_limited_data(self.close_candles_array, limit)

    def get_symbol_open_candles(self, limit=None, return_list=False):
        if return_list:
            return self.extract_limited_data(self.open_candles_list, limit)
        else:
            if self.open_candles_array is None:
                self.open_candles_array = self.convert_list_to_array(self.open_candles_list)
            return self.extract_limited_data(self.open_candles_array, limit)

    def get_symbol_high_candles(self, limit=None, return_list=False):
        if return_list:
            return self.extract_limited_data(self.high_candles_list, limit)
        else:
            if self.high_candles_array is None:
                self.high_candles_array = self.convert_list_to_array(self.high_candles_list)
            return self.extract_limited_data(self.high_candles_array, limit)

    def get_symbol_low_candles(self, limit=None, return_list=False):
        if return_list:
            return self.extract_limited_data(self.low_candles_list, limit)
        else:
            if self.low_candles_array is None:
                self.low_candles_array = self.convert_list_to_array(self.low_candles_list)
            return self.extract_limited_data(self.low_candles_array, limit)

    def get_symbol_time_candles(self, limit=None, return_list=False):
        if return_list:
            return self.extract_limited_data(self.time_candles_list, limit)
        else:
            if self.time_candles_array is None:
                self.time_candles_array = self.convert_list_to_array(self.time_candles_list)
            return self.extract_limited_data(self.time_candles_array, limit)

    def get_symbol_volume_candles(self, limit=None, return_list=False):
        if return_list:
            return self.extract_limited_data(self.volume_candles_list, limit)
        else:
            if self.volume_candles_array is None:
                self.volume_candles_array = self.convert_list_to_array(self.volume_candles_list)
            return self.extract_limited_data(self.volume_candles_array, limit)

    # setters
    def set_last_candle(self, last_candle_data):
        self.close_candles_list[-1] = last_candle_data[PriceStrings.STR_PRICE_CLOSE.value]
        self.open_candles_list[-1] = last_candle_data[PriceStrings.STR_PRICE_OPEN.value]
        self.high_candles_list[-1] = last_candle_data[PriceStrings.STR_PRICE_HIGH.value]
        self.low_candles_list[-1] = last_candle_data[PriceStrings.STR_PRICE_LOW.value]
        self.time_candles_list[-1] = last_candle_data[PriceStrings.STR_PRICE_TIME.value]
        self.volume_candles_list[-1] = last_candle_data[PriceStrings.STR_PRICE_VOL.value]

        self.set_last_candle_arrays(self.close_candles_list, self.close_candles_array)
        self.set_last_candle_arrays(self.open_candles_list, self.open_candles_array)
        self.set_last_candle_arrays(self.high_candles_list, self.high_candles_array)
        self.set_last_candle_arrays(self.low_candles_list, self.low_candles_array)
        self.set_last_candle_arrays(self.time_candles_list, self.time_candles_array)
        self.set_last_candle_arrays(self.volume_candles_list, self.volume_candles_array)

    @staticmethod
    def set_last_candle_arrays(array_to_update, list_updated):
        if array_to_update is not None:
            array_to_update[-1] = list_updated[-1]

    def set_all_candles(self, new_candles_data):
        for candle_data in new_candles_data:
            self.close_candles_list.append(candle_data[PriceStrings.STR_PRICE_CLOSE.value])
            self.open_candles_list.append(candle_data[PriceStrings.STR_PRICE_OPEN.value])
            self.high_candles_list.append(candle_data[PriceStrings.STR_PRICE_HIGH.value])
            self.low_candles_list.append(candle_data[PriceStrings.STR_PRICE_LOW.value])
            self.time_candles_list.append(candle_data[PriceStrings.STR_PRICE_TIME.value])
            self.volume_candles_list.append(candle_data[PriceStrings.STR_PRICE_VOL.value])

    def create_all_arrays(self):
        self.close_candles_array = self.convert_list_to_array(self.close_candles_list)
        self.open_candles_array = self.convert_list_to_array(self.open_candles_list)
        self.high_candles_array = self.convert_list_to_array(self.high_candles_list)
        self.low_candles_array = self.convert_list_to_array(self.low_candles_list)
        self.time_candles_array = self.convert_list_to_array(self.time_candles_list)
        self.volume_candles_array = self.convert_list_to_array(self.volume_candles_list)

    def change_current_candle(self, new_last_candle_data):
        self.close_candles_list.pop(0)
        self.open_candles_list.pop(0)
        self.high_candles_list.pop(0)
        self.low_candles_list.pop(0)
        self.time_candles_list.pop(0)
        self.volume_candles_list.pop(0)
        self.add_new_candle(new_last_candle_data)

    def add_new_candle(self, new_candle_data):
        self.close_candles_list.append(new_candle_data[PriceStrings.STR_PRICE_CLOSE.value])
        self.open_candles_list.append(new_candle_data[PriceStrings.STR_PRICE_OPEN.value])
        self.high_candles_list.append(new_candle_data[PriceStrings.STR_PRICE_HIGH.value])
        self.low_candles_list.append(new_candle_data[PriceStrings.STR_PRICE_LOW.value])
        self.time_candles_list.append(new_candle_data[PriceStrings.STR_PRICE_TIME.value])
        self.volume_candles_list.append(new_candle_data[PriceStrings.STR_PRICE_VOL.value])
        self.update_lists()

    def update_lists(self):
        if self.close_candles_array is None:
            self.close_candles_array = self.convert_list_to_array(self.close_candles_list)
        if self.open_candles_array is None:
            self.open_candles_array = self.convert_list_to_array(self.open_candles_list)
        if self.high_candles_array is None:
            self.high_candles_array = self.convert_list_to_array(self.high_candles_list)
        if self.low_candles_array is None:
            self.low_candles_array = self.convert_list_to_array(self.low_candles_list)
        if self.time_candles_array is None:
            self.time_candles_array = self.convert_list_to_array(self.time_candles_list)
        if self.volume_candles_array is None:
            self.volume_candles_array = self.convert_list_to_array(self.volume_candles_list)

    @staticmethod
    def convert_list_to_array(list_to_convert):
        return np.array(list_to_convert)

    @staticmethod
    def extract_limited_data(data, limit=None):
        if limit is None:
            return data

        return data[-min(limit, len(data)):]
