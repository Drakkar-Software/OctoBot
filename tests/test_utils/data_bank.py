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
from copy import deepcopy

from octobot_backtesting.importers.exchanges.exchange_importer import ExchangeDataImporter
from octobot_commons.enums import TimeFrames
from octobot_commons.enums import PriceIndexes
import octobot_trading.exchange_data as exchange_data
from octobot_trading.api.symbol_data import create_new_candles_manager
from octobot_trading.exchanges.exchange_manager import ExchangeManager
from octobot_trading.util.initializable import Initializable

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

    def __init__(self, data_file=None):
        super().__init__()
        self.data_file = data_file if data_file else "tests/static/AbstractExchangeHistoryCollector_1586017993.616272.data"
        self.exchange_name = None
        self.data_importer = ExchangeDataImporter({}, self.data_file)
        self.default_symbol = "BTC/USDT"

        self.origin_ohlcv_by_symbol = {}
        self.candles_managers_by_time_frame = {}
        self.current_init_indexes_by_time_frame = {}
        self.current_data = None
        self.data_by_symbol_by_data_frame = None
        self.manager = ExchangeManager({}, "binance")
        self.symbol_data = exchange_data.ExchangeSymbolData(self.manager, self.default_symbol)
        self.symbol_data.symbol_candles = self.candles_managers_by_time_frame

    async def initialize_impl(self):
        await self.data_importer.initialize()
        self.exchange_name = self.data_importer.exchange_name
        for time_frame in self.data_importer.time_frames:
            for symbol in self.data_importer.symbols:
                if symbol not in self.origin_ohlcv_by_symbol:
                    self.origin_ohlcv_by_symbol[symbol] = {}
                db_data = await self.data_importer.get_ohlcv_from_timestamps(
                    exchange_name=self.exchange_name,
                    symbol=symbol,
                    time_frame=time_frame
                )
                # store ohlcv only
                self.origin_ohlcv_by_symbol[symbol][time_frame] = sorted(
                    [data[-1] for data in db_data],
                    key=lambda x: x[PriceIndexes.IND_PRICE_TIME.value]
                )

    async def stop(self):
        await self.data_importer.stop()
        await self.manager.stop()

    def get_time_frames(self):
        return self.data_importer.time_frames

    def get_last_candle_for_default_symbol(self, time_frame):
        return [val[0] for val in self.candles_managers_by_time_frame[time_frame].get_symbol_prices(1).values()]

    def set_data_for_default_symbol(self, time_frame, end_index):
        self._set_candle_manager(time_frame, end_index, use_current_data=True)

    def increment_data_for_default_symbol(self, time_frame):
        current_index = self.current_init_indexes_by_time_frame[time_frame]
        candle = self.origin_ohlcv_by_symbol[self.default_symbol][time_frame][current_index]
        self.candles_managers_by_time_frame[time_frame].add_new_candle(candle)
        self.current_init_indexes_by_time_frame[time_frame] += 1

    # use default data with full data range
    def standard_mode(self, initial_candles):
        for time_frame in self.get_time_frames():
            self._set_candle_manager(time_frame, initial_candles)

    # works only with default data file
    # not started, selling started, selling maxed, buying starting, max: back normal:
    def rise_after_over_sold_mode(self):
        self.current_data = self._merge_candles(
            self.origin_ohlcv_by_symbol[self.default_symbol][TimeFrames.FOUR_HOURS][35:61],
            self.origin_ohlcv_by_symbol[self.default_symbol][TimeFrames.FOUR_HOURS][0:49]
        )
        return TimeFrames.FOUR_HOURS, 35, 43, 46, 47, 75

    # works only with default data file
    # not started, buying started, buying maxed, start dipping, super dip, max: back normal:
    def dip_after_over_bought_mode(self):
        self.current_data = self.origin_ohlcv_by_symbol[self.default_symbol][TimeFrames.ONE_DAY]
        return TimeFrames.ONE_DAY, 72, 76, 80, 81, 88, 90

    # works only with default data file
    # not started, started, heavy dump, very light dump, max: stopped dump:
    def sudden_dump_mode(self):
        self.current_data = self.origin_ohlcv_by_symbol[self.default_symbol][TimeFrames.ONE_HOUR]
        return TimeFrames.ONE_HOUR, 42, 43, 44, 45, 46

    # works only with default data file
    # not started, started, heavy pump, max pump, change trend, dipping, max: dipped:
    def sudden_pump_mode(self):
        self.current_data = self.origin_ohlcv_by_symbol[self.default_symbol][TimeFrames.HEIGHT_HOURS]
        return TimeFrames.HEIGHT_HOURS, 71, 74, 76, 77, 78, 79, 83

    # works only with default data file
    # long data_frame with flat then sudden big rise and then mostly flat for 120 values
    # start move ending up in a rise, reaches flat trend, first micro up p1, first mirco up p2, micro down, micro up,
    # micro down, micro up, micro down, back normal, micro down, back normal, micro down, back up, micro up, back down,
    # back normal, micro down, back up, micro down, back up, micro down, back up
    def overall_flat_trend_mode(self):
        cheap_prices = [
            [data * 0.9 for data in candle]
            for candle in self.origin_ohlcv_by_symbol[self.default_symbol][TimeFrames.FIFTEEN_MINUTES][6:72]
        ]
        self.current_data = self._merge_candles(
            cheap_prices,
            self.origin_ohlcv_by_symbol[self.default_symbol][TimeFrames.HEIGHT_HOURS][25:43],
            self.origin_ohlcv_by_symbol[self.default_symbol][TimeFrames.FIFTEEN_MINUTES][6:72],
            self.origin_ohlcv_by_symbol[self.default_symbol][TimeFrames.FIFTEEN_MINUTES][6:72]
        )
        return TimeFrames.FIFTEEN_MINUTES, 67, 85, 87, 90, 95, 107, 116, 123, 138, 141, 151, 153, 161, 163, 173, \
            174, 175, 180, 183, 193, 198, 203, 207

    def _set_candle_manager(self, time_frame, initial_candles_max_index, use_current_data=False):
        self.candles_managers_by_time_frame[time_frame] = create_new_candles_manager(
            self.current_data[:initial_candles_max_index] if use_current_data else
            self.origin_ohlcv_by_symbol[self.default_symbol][time_frame][:initial_candles_max_index]
        )
        self.current_init_indexes_by_time_frame[time_frame] = initial_candles_max_index

    @staticmethod
    def _merge_candles(*candles_list):
        result_list = deepcopy(candles_list[0])
        timestamp_list = [candle[PriceIndexes.IND_PRICE_TIME.value] for candle in result_list]
        for candle_list in candles_list[1:]:
            # ensure no timestamp is present in 2 candles
            while any(candle[PriceIndexes.IND_PRICE_TIME.value] in timestamp_list for candle in candle_list):
                for candle in candle_list:
                    candle[PriceIndexes.IND_PRICE_TIME.value] = candle[PriceIndexes.IND_PRICE_TIME.value] + 1
            result_list += deepcopy(candle_list)
            timestamp_list = [candle[PriceIndexes.IND_PRICE_TIME.value] for candle in result_list]
        return result_list
