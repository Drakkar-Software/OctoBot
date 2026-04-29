#  Drakkar-Software OctoBot-Trading
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
import numpy as np

import octobot_commons.enums as enums
import octobot_commons.constants as commons_constants

import octobot_trading.exchange_data.ohlcv.candles_manager as candles_manager


class PreloadedCandlesManager(candles_manager.CandlesManager):

    def get_preloaded_symbol_candles_count(self):
        return len(self.time_candles)

    def get_preloaded_symbol_close_candles(self):
        return self.close_candles

    def get_preloaded_symbol_open_candles(self):
        return self.open_candles

    def get_preloaded_symbol_high_candles(self):
        return self.high_candles

    def get_preloaded_symbol_low_candles(self):
        return self.low_candles

    def get_preloaded_symbol_time_candles(self):
        return self.time_candles

    def get_preloaded_symbol_volume_candles(self):
        return self.volume_candles

    def _set_all_candles(self, new_candles_data):
        self.close_candles = self._get_candle_values_array(new_candles_data, enums.PriceIndexes.IND_PRICE_CLOSE.value)
        self.open_candles = self._get_candle_values_array(new_candles_data, enums.PriceIndexes.IND_PRICE_OPEN.value)
        self.high_candles = self._get_candle_values_array(new_candles_data, enums.PriceIndexes.IND_PRICE_HIGH.value)
        self.low_candles = self._get_candle_values_array(new_candles_data, enums.PriceIndexes.IND_PRICE_LOW.value)
        self.time_candles = self._get_candle_values_array(new_candles_data, enums.PriceIndexes.IND_PRICE_TIME.value)
        self.volume_candles = self._get_candle_values_array(new_candles_data, enums.PriceIndexes.IND_PRICE_VOL.value)

    def _get_candle_values_array(self, candles, key):
        return np.array([candle[key] for candle in candles], dtype=np.float64)

    def _get_candle_index(self, candle):
        # Uses the given candle to find the index on the associated candle in preloaded candles.
        # The goal of this method is to quickly identify where the limit between past and future candles
        # should be when handling preloaded candles.

        # return actual index + 1 as it is used as a select length
        select_index = 0 if self.time_candles_index == 0 else self.time_candles_index - 1
        for delta_index, time_value in enumerate(self.time_candles[select_index:]):
            if time_value == candle[enums.PriceIndexes.IND_PRICE_TIME.value]:
                return self.time_candles_index + delta_index
        # candle in past candles
        for index, time_value in enumerate(self.time_candles[:select_index]):
            if time_value == candle[enums.PriceIndexes.IND_PRICE_TIME.value]:
                return index
        return commons_constants.DEFAULT_IGNORED_VALUE

    def add_old_and_new_candles(self, candles_data):
        # candles are already loaded, just set indexes to the new candle
        current_index = self._get_candle_index(candles_data[-1])
        if current_index == commons_constants.DEFAULT_IGNORED_VALUE:
            self.logger.error(
                f"Can't find candle at time: {candles_data[-1][enums.PriceIndexes.IND_PRICE_TIME.value]}"
            )
            return
        self.close_candles_index = current_index
        self.open_candles_index = current_index
        self.high_candles_index = current_index
        self.low_candles_index = current_index
        self.time_candles_index = current_index
        self.volume_candles_index = current_index

    def _extract_limited_data(self, data, limit=-1, max_limit=-1):
        if limit == -1:
            if max_limit == -1:
                return data
            return np.array(data[:max_limit], dtype=np.float64)

        if max_limit == -1:
            return np.array(data[-min(limit, len(data)):], dtype=np.float64)
        else:
            return np.array(data[max(0, max_limit - limit): max_limit], dtype=np.float64)

    def add_new_candle(self, new_candle_data):
        self.logger.error("add_new_candle should not be called")

    def _reset_candles(self):
        self.candles_initialized = False

        self.close_candles_index = 0
        self.open_candles_index = 0
        self.high_candles_index = 0
        self.low_candles_index = 0
        self.time_candles_index = 0
        self.volume_candles_index = 0

        self.close_candles = np.ndarray((0,))
        self.open_candles = np.ndarray((0,))
        self.high_candles = np.ndarray((0,))
        self.low_candles = np.ndarray((0,))
        self.time_candles = np.ndarray((0,))
        self.volume_candles = np.ndarray((0,))
