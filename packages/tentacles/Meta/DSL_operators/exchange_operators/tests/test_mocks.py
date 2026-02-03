#  Drakkar-Software OctoBot-Commons
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

import numpy as np

import octobot_commons.enums
import octobot_commons.constants

from tentacles.Meta.DSL_operators.exchange_operators.tests import (
    historical_prices,
    historical_volume,
    historical_times,
    KLINE_SIGNATURE,
    TIME_FRAME,
    exchange_manager_with_candles,
    exchange_manager_with_candles_and_klines,
    exchange_manager_with_candles_and_new_candle_klines,
    candle_manager_by_time_frame_by_symbol,
    interpreter,
    interpreter_with_candle_manager_by_time_frame_by_symbol,
    interpreter_with_exchange_manager_and_new_candle_klines,
    interpreter_with_exchange_manager_and_klines
)


@pytest.mark.asyncio
async def test_interpreter_mock(interpreter, historical_prices, historical_volume, historical_times):
    assert np.array_equal(await interpreter.interprete("open"), historical_prices)
    assert await interpreter.interprete("open[-1]") == historical_prices[-1] == 92.22
    assert np.array_equal(await interpreter.interprete("high"), historical_prices)
    assert await interpreter.interprete("high[-1]") == historical_prices[-1] == 92.22
    assert np.array_equal(await interpreter.interprete("low"), historical_prices)
    assert await interpreter.interprete("low[-1]") == historical_prices[-1] == 92.22
    assert np.array_equal(await interpreter.interprete("close"), historical_prices)
    assert await interpreter.interprete("close[-1]") == historical_prices[-1] == 92.22
    assert np.array_equal(await interpreter.interprete("volume"), historical_volume)
    assert await interpreter.interprete("volume[-1]") == historical_volume[-1] == 1113
    assert np.array_equal(await interpreter.interprete("time"), historical_times)
    assert await interpreter.interprete("time[-1]") == historical_times[-1] == 41


@pytest.mark.asyncio
async def test_interpreter_with_exchange_manager_and_klines_mock(
    interpreter_with_exchange_manager_and_klines, historical_prices, historical_volume, historical_times
):
    kline_adapted_historical_prices = historical_prices.copy()
    kline_adapted_historical_prices[-1] += KLINE_SIGNATURE
    assert np.array_equal(await interpreter_with_exchange_manager_and_klines.interprete("open"), kline_adapted_historical_prices)
    assert await interpreter_with_exchange_manager_and_klines.interprete("open[-1]") == kline_adapted_historical_prices[-1] == 92.22 + KLINE_SIGNATURE
    assert np.array_equal(await interpreter_with_exchange_manager_and_klines.interprete("high"), kline_adapted_historical_prices)
    assert await interpreter_with_exchange_manager_and_klines.interprete("high[-1]") == kline_adapted_historical_prices[-1] == 92.22 + KLINE_SIGNATURE
    assert np.array_equal(await interpreter_with_exchange_manager_and_klines.interprete("low"), kline_adapted_historical_prices)
    assert await interpreter_with_exchange_manager_and_klines.interprete("low[-1]") == kline_adapted_historical_prices[-1] == 92.22 + KLINE_SIGNATURE
    assert np.array_equal(await interpreter_with_exchange_manager_and_klines.interprete("close"), kline_adapted_historical_prices)
    assert await interpreter_with_exchange_manager_and_klines.interprete("close[-1]") == kline_adapted_historical_prices[-1] == 92.22 + KLINE_SIGNATURE
    kline_adapted_historical_volume = historical_volume.copy()
    kline_adapted_historical_volume[-1] += KLINE_SIGNATURE
    assert np.array_equal(await interpreter_with_exchange_manager_and_klines.interprete("volume"), 
    kline_adapted_historical_volume)
    assert await interpreter_with_exchange_manager_and_klines.interprete("volume[-1]") == historical_volume[-1] + KLINE_SIGNATURE == 1113 + KLINE_SIGNATURE
    assert np.array_equal(await interpreter_with_exchange_manager_and_klines.interprete("time"), historical_times)
    assert await interpreter_with_exchange_manager_and_klines.interprete("time[-1]") == historical_times[-1] == 41


@pytest.mark.asyncio
async def test_interpreter_with_exchange_manager_and_new_candle_klines_mock(
    interpreter_with_exchange_manager_and_new_candle_klines, historical_prices, historical_volume, historical_times
):
    kline_adapted_historical_prices = np.append(historical_prices[1:], historical_prices[-1] + KLINE_SIGNATURE)
    assert len(historical_prices) == len(kline_adapted_historical_prices)
    assert np.array_equal(await interpreter_with_exchange_manager_and_new_candle_klines.interprete("open"), kline_adapted_historical_prices)
    assert await interpreter_with_exchange_manager_and_new_candle_klines.interprete("open[-1]") == kline_adapted_historical_prices[-1] == 92.22 + KLINE_SIGNATURE
    assert np.array_equal(await interpreter_with_exchange_manager_and_new_candle_klines.interprete("high"), kline_adapted_historical_prices)
    assert await interpreter_with_exchange_manager_and_new_candle_klines.interprete("high[-1]") == kline_adapted_historical_prices[-1] == 92.22 + KLINE_SIGNATURE
    assert np.array_equal(await interpreter_with_exchange_manager_and_new_candle_klines.interprete("low"), kline_adapted_historical_prices)
    assert await interpreter_with_exchange_manager_and_new_candle_klines.interprete("low[-1]") == kline_adapted_historical_prices[-1] == 92.22 + KLINE_SIGNATURE
    assert np.array_equal(await interpreter_with_exchange_manager_and_new_candle_klines.interprete("close"), kline_adapted_historical_prices)
    assert await interpreter_with_exchange_manager_and_new_candle_klines.interprete("close[-1]") == kline_adapted_historical_prices[-1] == 92.22 + KLINE_SIGNATURE
    kline_adapted_historical_volume = np.append(historical_volume[1:], historical_volume[-1] + KLINE_SIGNATURE)
    assert np.array_equal(await interpreter_with_exchange_manager_and_new_candle_klines.interprete("volume"), 
    kline_adapted_historical_volume)
    assert await interpreter_with_exchange_manager_and_new_candle_klines.interprete("volume[-1]") == historical_volume[-1] + KLINE_SIGNATURE == 1113 + KLINE_SIGNATURE
    new_kline_time = historical_times[-1] + octobot_commons.enums.TimeFramesMinutes[octobot_commons.enums.TimeFrames(TIME_FRAME)] * octobot_commons.constants.MINUTE_TO_SECONDS
    kline_adapted_historical_times = np.append(historical_times[1:], new_kline_time)
    assert np.array_equal(await interpreter_with_exchange_manager_and_new_candle_klines.interprete("time"), kline_adapted_historical_times)
    assert await interpreter_with_exchange_manager_and_new_candle_klines.interprete("time[-1]") == kline_adapted_historical_times[-1] == new_kline_time


@pytest.mark.asyncio
async def test_interpreter_with_candle_manager_by_time_frame_by_symbol_mock(
    interpreter_with_candle_manager_by_time_frame_by_symbol, historical_prices, historical_volume, historical_times
):
    assert np.array_equal(await interpreter_with_candle_manager_by_time_frame_by_symbol.interprete("open"), historical_prices)
    assert await interpreter_with_candle_manager_by_time_frame_by_symbol.interprete("open[-1]") == historical_prices[-1] == 92.22
    assert np.array_equal(await interpreter_with_candle_manager_by_time_frame_by_symbol.interprete("high"), historical_prices)
    assert await interpreter_with_candle_manager_by_time_frame_by_symbol.interprete("high[-1]") == historical_prices[-1] == 92.22
    assert np.array_equal(await interpreter_with_candle_manager_by_time_frame_by_symbol.interprete("low"), historical_prices)
    assert await interpreter_with_candle_manager_by_time_frame_by_symbol.interprete("low[-1]") == historical_prices[-1] == 92.22
    assert np.array_equal(await interpreter_with_candle_manager_by_time_frame_by_symbol.interprete("close"), historical_prices)
    assert await interpreter_with_candle_manager_by_time_frame_by_symbol.interprete("close[-1]") == historical_prices[-1] == 92.22
    assert np.array_equal(await interpreter_with_candle_manager_by_time_frame_by_symbol.interprete("volume"), historical_volume)
    assert await interpreter_with_candle_manager_by_time_frame_by_symbol.interprete("volume[-1]") == historical_volume[-1] == 1113
    assert np.array_equal(await interpreter_with_candle_manager_by_time_frame_by_symbol.interprete("time"), historical_times)
    assert await interpreter_with_candle_manager_by_time_frame_by_symbol.interprete("time[-1]") == historical_times[-1] == 41
