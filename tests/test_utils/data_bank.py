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

import ccxt
import numpy as np

from config import TimeFrames, PriceIndexes
from trading.exchanges.exchange_manager import ExchangeManager
from tools.initializable import Initializable

"""
Class containing data with known moves
Moves are in the middle of the return data_frame

TimeFrames.FIVE_MINUTES: 2018-04-26 17:00:00 -> 2018-04-27 02:00:00
TimeFrames.FIFTEEN_MINUTES: 2018-04-23 06:15:00 -> 2018-04-24 07:00:00
TimeFrames.ONE_HOUR: 2018-04-07 16:00:00 -> 2018-04-11 20:00:00
TimeFrames.FOUR_HOURS: 2018-02-03 00:00:00 -> 2018-02-20 16:00:00
TimeFrames.HEIGHT_HOURS: 2017-11-12 04:00:00 -> 2017-12-11 16:00:00
TimeFrames.ONE_DAY: 2017-08-17 00:00:00 -> 2017-11-12 00:00:00

"""


class DataBank(Initializable):

    def __init__(self, config, data_file=None, symbols=None):
        super().__init__()
        self.config = config
        self.data_file = data_file if data_file else "tests/static/binance_BTC_USDT_20180428_121156.data"
        self.symbols = symbols if symbols else ["BTC"]

        self.exchange_manager = ExchangeManager(self.config, ccxt.binance, is_simulated=True)
        self.exchange_simulator_inst = None

        self.data_by_symbol_by_data_frame = None

    async def initialize_impl(self):
        await self.exchange_manager.initialize()
        self.exchange_simulator_inst = self.exchange_manager.get_exchange().get_exchange()
        self._init_data()

    def get_all_data_for_all_available_time_frames_for_symbol(self, symbol):
        return self.data_by_symbol_by_data_frame[symbol]

    # works only with default data file
    # not started, selling started, selling maxed, buying starting, max: back normal:
    def get_rise_after_over_sold(self):
        return np.concatenate((self._get_bank_time_frame_data(TimeFrames.FOUR_HOURS, 35, 61),
                              self._get_bank_time_frame_data(TimeFrames.FOUR_HOURS, 0, 49)), axis=1), \
            35, 43, 46, 47

    # works only with default data file
    # not started, buying started, buying maxed, start dipping, super dip, max: back normal:
    def get_dip_after_over_bought(self):
        return self._get_bank_time_frame_data(TimeFrames.ONE_DAY, 0, 90), \
            -18, -14, -10, -9, -2

    # works only with default data file
    # not started, started, heavy dump, very light dump, max: stopped dump:
    def get_sudden_dump(self):
        return self._get_bank_time_frame_data(TimeFrames.ONE_HOUR, 0, 46), \
            -4, -3, -2, -1

    # works only with default data file
    # not started, started, heavy pump, max pump, change trend, dipping, max: dipped:
    def get_sudden_pump(self):
        return self._get_bank_time_frame_data(TimeFrames.HEIGHT_HOURS, 0, 83), \
            71, 74, 76, 77, 78, 79

    # works only with default data file
    # long data_frame with flat then sudden big rise and then mostly flat for 120 values
    # start move ending up in a rise, reaches flat trend, first micro up p1, first mirco up p2, micro down, micro up,
    # micro down, micro up, micro down, back normal, micro down, back normal, micro down, back up, micro up, back down,
    # back normal, micro down, back up, micro down, back up, micro down, back up
    def get_overall_flat_trend(self):
        return np.concatenate((self._get_bank_time_frame_data(TimeFrames.FIFTEEN_MINUTES, 6, 72)*0.9,
                              self._get_bank_time_frame_data(TimeFrames.HEIGHT_HOURS, 25, 43),
                              self._get_bank_time_frame_data(TimeFrames.FIFTEEN_MINUTES, 6, 72),
                              self._get_bank_time_frame_data(TimeFrames.FIFTEEN_MINUTES, 6, 72)), axis=1), \
            67, 85, 87, 90, 95, 107, 116, 123, 138, 141, 151, 153, 161, 163, 173, 174, 175, 180, 183, 193, 198, 203, 207

    def _get_bank_time_frame_data(self, time_frame, min_index=None, max_index=None):
        if max_index is None and min_index is None:
            return self.data_by_symbol_by_data_frame[self.symbols[0]][time_frame]
        else:
            min_i = min_index if min_index is not None else 0
            max_i = max_index if max_index is not None else \
                len(self.data_by_symbol_by_data_frame[self.symbols[0]][time_frame][0])-1
            return self.reduce_data(self.data_by_symbol_by_data_frame[self.symbols[0]][time_frame], min_i, max_i)

    def _init_data(self):
        self.data_by_symbol_by_data_frame = {symbol: self._get_symbol_data(symbol) for symbol in self.symbols}

    def _get_symbol_data(self, symbol):
        min_index = 0
        max_index = min_index + 100
        return {time_frame: self.exchange_simulator_inst.get_candles_exact(
            symbol,
            time_frame,
            min_index,
            max_index,
            return_list=False)
            for time_frame in TimeFrames
            if self.exchange_simulator_inst.has_data_for_time_frame(symbol, time_frame.value)}

    @staticmethod
    def reduce_data(time_frame_data, min_index, max_index):
        symbol_prices = [None]*len(PriceIndexes)
        symbol_prices[PriceIndexes.IND_PRICE_CLOSE.value] = \
            time_frame_data[PriceIndexes.IND_PRICE_CLOSE.value][min_index:max_index]
        symbol_prices[PriceIndexes.IND_PRICE_OPEN.value] = \
            time_frame_data[PriceIndexes.IND_PRICE_OPEN.value][min_index:max_index]
        symbol_prices[PriceIndexes.IND_PRICE_HIGH.value] = \
            time_frame_data[PriceIndexes.IND_PRICE_HIGH.value][min_index:max_index]
        symbol_prices[PriceIndexes.IND_PRICE_LOW.value] = \
            time_frame_data[PriceIndexes.IND_PRICE_LOW.value][min_index:max_index]
        symbol_prices[PriceIndexes.IND_PRICE_TIME.value] = \
            time_frame_data[PriceIndexes.IND_PRICE_TIME.value][min_index:max_index]
        symbol_prices[PriceIndexes.IND_PRICE_VOL.value] = \
            time_frame_data[PriceIndexes.IND_PRICE_VOL.value][min_index:max_index]
        return np.array(symbol_prices)
