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
    def update_symbol_candles(self, time_frame, new_symbol_candles_data):
        if time_frame not in self.symbol_candles:
            self.symbol_candles[time_frame] = CandleData(new_symbol_candles_data)

        # else check if we should edit the last candle or move to a new one
        elif self._has_candle_changed():
            pass

        # only need to edit the last candle
        else:
            pass

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
    def _has_candle_changed(self):
        pass

    def _edit_last_candle(self, time_frame, new_last_candle_data):
        pass


class CandleData:
    def __init__(self, all_candles_data):
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

    # getters
    def get_symbol_close_candles(self, limit=None, return_list=False):
        if return_list:
            return self.close_candles_list
        else:
            return self.close_candles_array

    def get_symbol_open_candles(self, limit=None, return_list=False):
        if return_list:
            return self.open_candles_list
        else:
            return self.open_candles_array

    def get_symbol_high_candles(self, limit=None, return_list=False):
        if return_list:
            return self.high_candles_list
        else:
            return self.high_candles_array

    def get_symbol_low_candles(self, limit=None, return_list=False):
        if return_list:
            return self.low_candles_list
        else:
            return self.low_candles_array

    def get_symbol_time_candles(self, limit=None, return_list=False):
        if return_list:
            return self.time_candles_list
        else:
            return self.time_candles_array

    def get_symbol_volume_candles(self, limit=None, return_list=False):
        if return_list:
            return self.volume_candles_list
        else:
            return self.volume_candles_array

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
        self.create_all_arrays()

    def create_all_arrays(self):
        self.close_candles_array = self.convert_list_to_array(self.close_candles_list)
        self.open_candles_array = self.convert_list_to_array(self.open_candles_list)
        self.high_candles_array = self.convert_list_to_array(self.high_candles_list)
        self.low_candles_array = self.convert_list_to_array(self.low_candles_list)
        self.time_candles_array = self.convert_list_to_array(self.time_candles_list)
        self.volume_candles_array = self.convert_list_to_array(self.volume_candles_list)

    @staticmethod
    def convert_list_to_array(list_to_convert):
        return np.array(list_to_convert)

    def add_price(self, symbol, time_frame, start_candle_time, candle_data):
        # add price only if candles have been initialized by rest exchange
        if symbol in self.symbol_prices and time_frame in self.symbol_prices[symbol]:
            time_frame_data = self.symbol_prices[symbol][time_frame]

            # add new candle if previous candle is done
            if time_frame_data[self.CANDLE_LIST][-1][PriceIndexes.IND_PRICE_TIME.value] < start_candle_time:

                # remove most ancient candle if max candle count reached
                if time_frame_data[self.TIME_FRAME_HAS_REACH_MAX_CANDLE_COUNT]:
                    time_frame_data[self.CANDLE_LIST].pop(0)
                    time_frame_data[self.CANDLE_DATAFRAME].drop(0, inplace=True)
                    time_frame_data[self.CANDLE_DATAFRAME].reset_index(drop=True, inplace=True)
                elif len(time_frame_data[self.CANDLE_LIST]) + 1 >= self._MAX_STORED_CANDLE_COUNT:
                    time_frame_data[self.TIME_FRAME_HAS_REACH_MAX_CANDLE_COUNT] = True

                # add new candle
                time_frame_data[self.CANDLE_LIST].append(candle_data)

                # refresh dataframe
                time_frame_data[self.CANDLE_DATAFRAME] = pandas.concat(
                    [time_frame_data[self.CANDLE_DATAFRAME], DataFrameUtil.candles_array_to_data_frame([candle_data])],
                    ignore_index=True)
