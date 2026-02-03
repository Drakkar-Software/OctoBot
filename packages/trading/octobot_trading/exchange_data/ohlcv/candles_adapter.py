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

import octobot_commons.data_util as data_util
import octobot_commons.enums as enums


def get_symbol_close_candles(symbol_data, time_frame, limit, include_in_construction):
    tf = enums.TimeFrames(time_frame)
    if include_in_construction:
        return _add_in_construction_data(
            symbol_data.symbol_candles[tf].get_symbol_close_candles(limit),
            symbol_data,
            tf,
            enums.PriceIndexes.IND_PRICE_CLOSE.value)
    return symbol_data.symbol_candles[tf].get_symbol_close_candles(limit)


def get_symbol_open_candles(symbol_data, time_frame, limit, include_in_construction):
    tf = enums.TimeFrames(time_frame)
    if include_in_construction:
        return _add_in_construction_data(
            symbol_data.symbol_candles[tf].get_symbol_open_candles(limit),
            symbol_data,
            tf,
            enums.PriceIndexes.IND_PRICE_OPEN.value)
    return symbol_data.symbol_candles[tf].get_symbol_open_candles(limit)


def get_symbol_high_candles(symbol_data, time_frame, limit, include_in_construction):
    tf = enums.TimeFrames(time_frame)
    if include_in_construction:
        return _add_in_construction_data(
            symbol_data.symbol_candles[tf].get_symbol_high_candles(limit),
            symbol_data,
            tf,
            enums.PriceIndexes.IND_PRICE_HIGH.value)
    return symbol_data.symbol_candles[tf].get_symbol_high_candles(limit)


def get_symbol_low_candles(symbol_data, time_frame, limit, include_in_construction):
    tf = enums.TimeFrames(time_frame)
    if include_in_construction:
        return _add_in_construction_data(
            symbol_data.symbol_candles[tf].get_symbol_low_candles(limit),
            symbol_data,
            tf,
            enums.PriceIndexes.IND_PRICE_LOW.value)
    return symbol_data.symbol_candles[tf].get_symbol_low_candles(limit)


def get_symbol_volume_candles(symbol_data, time_frame, limit, include_in_construction):
    tf = enums.TimeFrames(time_frame)
    if include_in_construction:
        return _add_in_construction_data(
            symbol_data.symbol_candles[tf].get_symbol_volume_candles(limit),
            symbol_data,
            tf,
            enums.PriceIndexes.IND_PRICE_VOL.value)
    return symbol_data.symbol_candles[tf].get_symbol_volume_candles(limit)


def get_symbol_time_candles(symbol_data, time_frame, limit, include_in_construction):
    tf = enums.TimeFrames(time_frame)
    if include_in_construction:
        return _add_in_construction_data(
            symbol_data.symbol_candles[tf].get_symbol_time_candles(limit),
            symbol_data,
            tf,
            enums.PriceIndexes.IND_PRICE_TIME.value)
    return symbol_data.symbol_candles[tf].get_symbol_time_candles(limit)


def get_candle_as_list(candle_arrays_dict: dict, candle_index: int) -> list:
    candle = [None] * len(enums.PriceIndexes)
    candle[enums.PriceIndexes.IND_PRICE_TIME.value] = candle_arrays_dict[enums.PriceIndexes.IND_PRICE_TIME.value][candle_index]
    candle[enums.PriceIndexes.IND_PRICE_OPEN.value] = candle_arrays_dict[enums.PriceIndexes.IND_PRICE_OPEN.value][candle_index]
    candle[enums.PriceIndexes.IND_PRICE_HIGH.value] = candle_arrays_dict[enums.PriceIndexes.IND_PRICE_HIGH.value][candle_index]
    candle[enums.PriceIndexes.IND_PRICE_LOW.value] = candle_arrays_dict[enums.PriceIndexes.IND_PRICE_LOW.value][candle_index]
    candle[enums.PriceIndexes.IND_PRICE_CLOSE.value] = candle_arrays_dict[enums.PriceIndexes.IND_PRICE_CLOSE.value][candle_index]
    candle[enums.PriceIndexes.IND_PRICE_VOL.value] = candle_arrays_dict[enums.PriceIndexes.IND_PRICE_VOL.value][candle_index]
    return candle


def _add_in_construction_data(candles, symbol_data, time_frame, data_type):
    try:
        return np.array(data_util.shift_value_array(candles,
                                                    fill_value=symbol_data.symbol_klines[time_frame].kline[data_type]),
                        dtype=np.float64)
    except KeyError:
        return candles
