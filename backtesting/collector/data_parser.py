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

import os

from config import CONFIG_DATA_COLLECTOR_PATH, PriceIndexes, BacktestingDataFormats, BACKTESTING_DATA_OHLCV, \
    BACKTESTING_DATA_TRADES
from backtesting import BacktestingDataFileException
from backtesting.collector.data_file_manager import read_data_file, get_data_type


class DataCollectorParser:
    @staticmethod
    def parse(file):
        if os.path.isfile(CONFIG_DATA_COLLECTOR_PATH + file):
            file_content = DataCollectorParser.get_file_content(CONFIG_DATA_COLLECTOR_PATH + file)
        else:
            file_content = DataCollectorParser.get_file_content(file)
        return file_content

    @staticmethod
    def get_file_content(file_name):
        file_content = read_data_file(file_name)
        data_type = get_data_type(file_name)
        if data_type == BacktestingDataFormats.REGULAR_COLLECTOR_DATA:
            return DataCollectorParser.merge_arrays(file_content)
        else:
            raise BacktestingDataFileException(file_name)

    @staticmethod
    def merge_arrays(arrays):
        parsed_data = DataCollectorParser.get_empty_parsed_data()
        ohlcv_data = parsed_data[BACKTESTING_DATA_OHLCV]
        for time_frame in arrays:
            data = arrays[time_frame]
            ohlcv_data[time_frame] = []
            for i in range(len(data[PriceIndexes.IND_PRICE_TIME.value])):
                ohlcv_data[time_frame].insert(i, [None]*len(PriceIndexes))
                ohlcv_data[time_frame][i][PriceIndexes.IND_PRICE_CLOSE.value] = \
                    data[PriceIndexes.IND_PRICE_CLOSE.value][i]
                ohlcv_data[time_frame][i][PriceIndexes.IND_PRICE_OPEN.value] = \
                    data[PriceIndexes.IND_PRICE_OPEN.value][i]
                ohlcv_data[time_frame][i][PriceIndexes.IND_PRICE_HIGH.value] = \
                    data[PriceIndexes.IND_PRICE_HIGH.value][i]
                ohlcv_data[time_frame][i][PriceIndexes.IND_PRICE_LOW.value] = \
                    data[PriceIndexes.IND_PRICE_LOW.value][i]
                ohlcv_data[time_frame][i][PriceIndexes.IND_PRICE_TIME.value] = \
                    data[PriceIndexes.IND_PRICE_TIME.value][i]
                ohlcv_data[time_frame][i][PriceIndexes.IND_PRICE_VOL.value] = \
                    data[PriceIndexes.IND_PRICE_VOL.value][i]

        return parsed_data

    @staticmethod
    def get_empty_parsed_data():
        return {
            BACKTESTING_DATA_OHLCV: {},
            BACKTESTING_DATA_TRADES: {}
        }
