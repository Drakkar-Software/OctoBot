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
import numpy as np

from octobot_commons.enums import PriceIndexes
from octobot_trading.exchange_data.ohlcv.candles_manager import CandlesManager


def test_constructor():
    candles_manager = CandlesManager()
    assert candles_manager.candles_initialized is False
    assert candles_manager.close_candles_index == 0
    assert len(candles_manager.close_candles) == CandlesManager.MAX_CANDLES_COUNT
    assert all(np.isnan(value) for value in candles_manager.close_candles)


def test_add_new_candle():
    candles_manager = CandlesManager()
    candle = _gen_candles(1)[0]
    candles_manager.add_new_candle(candle)
    assert candles_manager.close_candles_index == 1
    assert len(candles_manager.close_candles) == CandlesManager.MAX_CANDLES_COUNT
    assert candles_manager.close_candles[0] == candle[PriceIndexes.IND_PRICE_CLOSE.value]


def test_add_old_and_new_candles():
    candles_manager = CandlesManager()

    # with one candle
    single_candle = _gen_candles(1)
    candles_manager.add_old_and_new_candles(single_candle)
    assert candles_manager.reached_max is False
    assert candles_manager.close_candles_index == 1
    assert len(candles_manager.close_candles) == CandlesManager.MAX_CANDLES_COUNT
    assert candles_manager.close_candles[0] == single_candle[0][PriceIndexes.IND_PRICE_CLOSE.value]

    # with many candles including first one
    many_candles = _gen_candles(10)
    candles_manager.add_old_and_new_candles(many_candles)
    assert candles_manager.reached_max is False
    assert candles_manager.close_candles_index == 10
    assert len(candles_manager.close_candles) == CandlesManager.MAX_CANDLES_COUNT
    assert candles_manager.close_candles[0] == many_candles[0][PriceIndexes.IND_PRICE_CLOSE.value]
    assert candles_manager.close_candles[9] == many_candles[9][PriceIndexes.IND_PRICE_CLOSE.value]


def test_replace_all_candles():
    candles_manager = CandlesManager()
    many_candles = _gen_candles(20)[10:]
    candles_manager.add_old_and_new_candles(many_candles)
    assert candles_manager.close_candles[0] == many_candles[0][PriceIndexes.IND_PRICE_CLOSE.value]
    assert candles_manager.close_candles[9] == many_candles[9][PriceIndexes.IND_PRICE_CLOSE.value]
    new_candles = _gen_candles(10)
    candles_manager.replace_all_candles(new_candles)
    assert candles_manager.close_candles[0] == new_candles[0][PriceIndexes.IND_PRICE_CLOSE.value]
    assert candles_manager.close_candles[9] == new_candles[9][PriceIndexes.IND_PRICE_CLOSE.value]


def test_get_symbol_prices():
    candles_manager = CandlesManager()
    candle = _gen_candles(1)[0]
    candles_manager.add_new_candle(candle)
    symbol_price = candles_manager.get_symbol_prices()
    assert symbol_price[PriceIndexes.IND_PRICE_CLOSE.value][-1] == candle[PriceIndexes.IND_PRICE_CLOSE.value]
    assert symbol_price[PriceIndexes.IND_PRICE_OPEN.value][-1] == candle[PriceIndexes.IND_PRICE_OPEN.value]
    assert symbol_price[PriceIndexes.IND_PRICE_HIGH.value][-1] == candle[PriceIndexes.IND_PRICE_HIGH.value]
    assert symbol_price[PriceIndexes.IND_PRICE_LOW.value][-1] == candle[PriceIndexes.IND_PRICE_LOW.value]
    assert symbol_price[PriceIndexes.IND_PRICE_VOL.value][-1] == candle[PriceIndexes.IND_PRICE_VOL.value]
    assert symbol_price[PriceIndexes.IND_PRICE_TIME.value][-1] == candle[PriceIndexes.IND_PRICE_TIME.value]

    second_candle = _gen_candles(2)[1]
    candles_manager.add_new_candle(second_candle)
    second_sym_price = candles_manager.get_symbol_prices(1)
    assert second_sym_price[PriceIndexes.IND_PRICE_CLOSE.value][-1] == second_candle[PriceIndexes.IND_PRICE_CLOSE.value]
    assert second_sym_price[PriceIndexes.IND_PRICE_OPEN.value][-1] == second_candle[PriceIndexes.IND_PRICE_OPEN.value]
    assert second_sym_price[PriceIndexes.IND_PRICE_HIGH.value][-1] == second_candle[PriceIndexes.IND_PRICE_HIGH.value]
    assert second_sym_price[PriceIndexes.IND_PRICE_LOW.value][-1] == second_candle[PriceIndexes.IND_PRICE_LOW.value]
    assert second_sym_price[PriceIndexes.IND_PRICE_VOL.value][-1] == second_candle[PriceIndexes.IND_PRICE_VOL.value]
    assert second_sym_price[PriceIndexes.IND_PRICE_TIME.value][-1] == second_candle[PriceIndexes.IND_PRICE_TIME.value]


def test_get_symbol_candles_data():
    candles_manager = CandlesManager()
    _test_data(candles_manager.get_symbol_close_candles(), 0, np.nan)
    _test_data(candles_manager.get_symbol_open_candles(), 0, np.nan)
    _test_data(candles_manager.get_symbol_high_candles(), 0, np.nan)
    _test_data(candles_manager.get_symbol_low_candles(), 0, np.nan)
    _test_data(candles_manager.get_symbol_time_candles(), 0, np.nan)
    _test_data(candles_manager.get_symbol_volume_candles(), 0, np.nan)

    new_candles = _gen_candles(2)
    candles_manager.add_old_and_new_candles(new_candles)
    _test_data(candles_manager.get_symbol_close_candles(), 2, new_candles[-1][PriceIndexes.IND_PRICE_CLOSE.value])
    _test_data(candles_manager.get_symbol_open_candles(), 2, new_candles[-1][PriceIndexes.IND_PRICE_OPEN.value])
    _test_data(candles_manager.get_symbol_high_candles(), 2, new_candles[-1][PriceIndexes.IND_PRICE_HIGH.value])
    _test_data(candles_manager.get_symbol_low_candles(), 2, new_candles[-1][PriceIndexes.IND_PRICE_LOW.value])
    _test_data(candles_manager.get_symbol_volume_candles(), 2, new_candles[-1][PriceIndexes.IND_PRICE_VOL.value])
    _test_data(candles_manager.get_symbol_time_candles(), 2, new_candles[-1][PriceIndexes.IND_PRICE_TIME.value])


def test_reach_max_candles_count():
    candles_manager = CandlesManager()
    all_candles = _gen_candles(candles_manager.MAX_CANDLES_COUNT + 3)
    max_candles = all_candles[0:candles_manager.MAX_CANDLES_COUNT]
    other_candles = all_candles[candles_manager.MAX_CANDLES_COUNT:]

    assert candles_manager.reached_max is False
    candles_manager.add_old_and_new_candles(max_candles)
    assert candles_manager.reached_max is True
    _test_data(candles_manager.get_symbol_close_candles(), candles_manager.MAX_CANDLES_COUNT,
               max_candles[-1][PriceIndexes.IND_PRICE_CLOSE.value])
    assert candles_manager.close_candles_index == candles_manager.MAX_CANDLES_COUNT - 1

    # should remove oldest (first) candles and insert new ones instead
    candles_manager.add_old_and_new_candles(other_candles)
    _test_data(candles_manager.get_symbol_close_candles(), candles_manager.MAX_CANDLES_COUNT,
               other_candles[-1][PriceIndexes.IND_PRICE_CLOSE.value])


def test_reach_max_candles_count_with_custom_candles_count():
    # negative value: use default MAX_CANDLES_COUNT
    candles_manager = CandlesManager(max_candles_count=-1)
    assert candles_manager.max_candles_count == candles_manager.MAX_CANDLES_COUNT

    candles_manager = CandlesManager(max_candles_count=CandlesManager.MAX_CANDLES_COUNT + 21)
    assert candles_manager.max_candles_count != candles_manager.MAX_CANDLES_COUNT
    assert candles_manager.MAX_CANDLES_COUNT == CandlesManager.MAX_CANDLES_COUNT
    all_candles = _gen_candles(candles_manager.max_candles_count + 3)
    max_candles = all_candles[0:candles_manager.max_candles_count]
    other_candles = all_candles[candles_manager.max_candles_count:]

    assert candles_manager.reached_max is False
    candles_manager.add_old_and_new_candles(max_candles)
    assert candles_manager.reached_max is True
    _test_data(candles_manager.get_symbol_close_candles(), candles_manager.max_candles_count,
               max_candles[-1][PriceIndexes.IND_PRICE_CLOSE.value])
    assert candles_manager.close_candles_index == candles_manager.max_candles_count - 1

    # should remove oldest (first) candles and insert new ones instead
    candles_manager.add_old_and_new_candles(other_candles)
    _test_data(candles_manager.get_symbol_close_candles(), candles_manager.max_candles_count,
               other_candles[-1][PriceIndexes.IND_PRICE_CLOSE.value])


def _test_data(candles_data, expected_len, expected_last_val):
    assert len(candles_data) == expected_len
    if expected_len > 0:
        assert candles_data[-1] == expected_last_val


def _gen_candles(size) -> list:
    return [_get_candle(seed) for seed in range(1, size + 1)]


def _get_candle(seed):
    return [int(seed), seed * 10, seed * 100, seed * 1000, seed * 10000, seed * 100000]
