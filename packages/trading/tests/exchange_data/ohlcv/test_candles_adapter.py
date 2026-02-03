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
import pytest
import pytest_asyncio
import numpy as np

from octobot_commons.enums import PriceIndexes, TimeFrames
from octobot_trading.api.symbol_data import get_symbol_candles_manager
from octobot_trading.exchange_data.ohlcv.candles_adapter import get_symbol_close_candles, get_symbol_open_candles, \
    get_symbol_low_candles, get_symbol_high_candles, get_symbol_time_candles, get_symbol_volume_candles, \
    get_candle_as_list
from octobot_trading.exchange_data.ohlcv.candles_manager import CandlesManager
from octobot_trading.exchange_data.kline.kline_manager import KlineManager
from octobot_trading.exchange_data.exchange_symbol_data import ExchangeSymbolData
from octobot_trading.exchanges.exchange_manager import ExchangeManager
from tests import event_loop


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def time_frame():
    return "1h"


@pytest_asyncio.fixture
async def symbol_data(time_frame):
    symbol_candles = CandlesManager()
    await symbol_candles.initialize()
    symbol_candles.replace_all_candles(_get_candles())
    symbol_kline = KlineManager()
    await symbol_kline.initialize()
    symbol_kline.kline_update(_get_candle(11))
    manager = ExchangeManager({}, "binanceus")
    symbol_data = ExchangeSymbolData(manager, "BTC/USDT")
    tf = TimeFrames(time_frame)
    symbol_data.symbol_candles[tf] = symbol_candles
    symbol_data.symbol_klines[tf] = symbol_kline
    return symbol_data


async def test_get_symbol_close_candles(symbol_data, time_frame):
    # default selector
    assert np.array_equal(get_symbol_close_candles(symbol_data, time_frame, 10, False),
                          np.array(_get_candles_extract(PriceIndexes.IND_PRICE_CLOSE.value), dtype=float))

    # selector with in construction candle
    assert np.array_equal(get_symbol_close_candles(symbol_data, time_frame, 10, True),
                          np.array(_get_candles_extract_with_extra_candle(PriceIndexes.IND_PRICE_CLOSE.value),
                                   dtype=float))


async def test_get_symbol_open_candles(symbol_data, time_frame):
    # default selector
    assert np.array_equal(get_symbol_open_candles(symbol_data, time_frame, 10, False),
                          np.array(_get_candles_extract(PriceIndexes.IND_PRICE_OPEN.value), dtype=float))

    # selector with in construction candle
    assert np.array_equal(get_symbol_open_candles(symbol_data, time_frame, 10, True),
                          np.array(_get_candles_extract_with_extra_candle(PriceIndexes.IND_PRICE_OPEN.value),
                                   dtype=float))


async def test_get_symbol_low_candles(symbol_data, time_frame):
    # default selector
    assert np.array_equal(get_symbol_low_candles(symbol_data, time_frame, 10, False),
                          np.array(_get_candles_extract(PriceIndexes.IND_PRICE_LOW.value), dtype=float))

    # selector with in construction candle
    assert np.array_equal(get_symbol_low_candles(symbol_data, time_frame, 10, True),
                          np.array(_get_candles_extract_with_extra_candle(PriceIndexes.IND_PRICE_LOW.value),
                                   dtype=float))


async def test_get_symbol_high_candles(symbol_data, time_frame):
    # default selector
    assert np.array_equal(get_symbol_high_candles(symbol_data, time_frame, 10, False),
                          np.array(_get_candles_extract(PriceIndexes.IND_PRICE_HIGH.value), dtype=float))

    # selector with in construction candle
    assert np.array_equal(get_symbol_high_candles(symbol_data, time_frame, 10, True),
                          np.array(_get_candles_extract_with_extra_candle(PriceIndexes.IND_PRICE_HIGH.value),
                                   dtype=float))


async def test_get_symbol_time_candles(symbol_data, time_frame):
    # default selector
    assert np.array_equal(get_symbol_time_candles(symbol_data, time_frame, 10, False),
                          np.array(_get_candles_extract(PriceIndexes.IND_PRICE_TIME.value), dtype=float))

    # selector with in construction candle
    assert np.array_equal(get_symbol_time_candles(symbol_data, time_frame, 10, True),
                          np.array(_get_candles_extract_with_extra_candle(PriceIndexes.IND_PRICE_TIME.value),
                                   dtype=float))


async def test_get_symbol_volume_candles(symbol_data, time_frame):
    # default selector
    assert np.array_equal(get_symbol_volume_candles(symbol_data, time_frame, 10, False),
                          np.array(_get_candles_extract(PriceIndexes.IND_PRICE_VOL.value), dtype=float))

    # selector with in construction candle
    assert np.array_equal(get_symbol_volume_candles(symbol_data, time_frame, 10, True),
                          np.array(_get_candles_extract_with_extra_candle(PriceIndexes.IND_PRICE_VOL.value),
                                   dtype=float))


async def test_get_candle_as_list(symbol_data, time_frame):
    row_candles = _get_candles()
    candles = get_symbol_candles_manager(symbol_data, time_frame).get_symbol_prices()
    candle_as_list = get_candle_as_list(candles, 0)
    assert candle_as_list == row_candles[0]

    candles_limit_1 = get_symbol_candles_manager(symbol_data, time_frame).get_symbol_prices(limit=1)
    candles_list_1 = get_candle_as_list(candles_limit_1, 0)
    assert candles_list_1 == row_candles[-1]

    candles_limit_2 = get_symbol_candles_manager(symbol_data, time_frame).get_symbol_prices(limit=2)
    candles_list_2 = get_candle_as_list(candles_limit_2, 0)
    assert candles_list_2 == row_candles[-2]

    candles_limit_2 = get_symbol_candles_manager(symbol_data, time_frame).get_symbol_prices(limit=2)
    candles_list_2 = get_candle_as_list(candles_limit_2, 1)
    assert candles_list_2 == row_candles[-1]


def _get_candles_extract(index, count=10):
    return [elem[index] for elem in _get_candles(count)]


def _get_candles_extract_with_extra_candle(index, count=10):
    return [elem[index] for elem in _get_candles(count=count+1)][1:]


def _get_candles(count=10):
    return [_get_candle(seed) for seed in range(1, count + 1)]


def _get_candle(seed):
    return [seed * (i + 1) * 1 / 3 for i, _ in enumerate(PriceIndexes)]
