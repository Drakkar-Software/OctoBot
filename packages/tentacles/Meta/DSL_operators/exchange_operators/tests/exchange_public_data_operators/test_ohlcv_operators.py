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
import mock

import numpy as np

import octobot_commons.errors
import octobot_commons.enums
import octobot_commons.constants
import octobot_commons.logging
import octobot_trading.api
import octobot_trading.constants
import tentacles.Meta.DSL_operators.exchange_operators as exchange_operators
import tentacles.Meta.DSL_operators.exchange_operators.exchange_public_data_operators.ohlcv_operators as ohlcv_operators


from tentacles.Meta.DSL_operators.exchange_operators.tests import (
    SYMBOL,
    TIME_FRAME,
    KLINE_SIGNATURE,
    historical_prices,
    historical_volume,
    historical_times,
    exchange_manager_with_candles,
    exchange_manager_with_candles_and_klines,
    exchange_manager_with_candles_and_new_candle_klines,
    candle_manager_by_time_frame_by_symbol,
    interpreter_with_candle_manager_by_time_frame_by_symbol,
    interpreter_with_exchange_manager_and_klines,
    interpreter_with_exchange_manager_and_new_candle_klines,
    interpreter,
)


@pytest.fixture
def expected_values(request, historical_prices, historical_volume, historical_times):
    select_value = request.param
    if select_value == "price":
        return historical_prices
    elif select_value == "volume":
        return historical_volume
    elif select_value == "time":
        return historical_times
    raise octobot_commons.errors.InvalidParametersError(f"Invalid select_value: {select_value}")


@pytest.fixture
def operator(request):
    return request.param


@pytest.mark.asyncio
@pytest.mark.parametrize("operator, expected_values", [
    ("open", "price"),
    ("high", "price"),
    ("low", "price"),
    ("close", "price"), 
    ("volume", "volume"),
    ("time", "time")
], indirect=True) # use indirect=True to pass fixtures as a parameter
async def test_ohlcv_operators_basic_calls_without_klines(
    interpreter, interpreter_with_candle_manager_by_time_frame_by_symbol,
    operator, expected_values
):
    # test with both interpreter data sources
    for _interpreter in [interpreter, interpreter_with_candle_manager_by_time_frame_by_symbol]:
        # no param, use context values: SYMBOL, TIME_FRAME: BTC/USDT, 1h
        operator_value = await _interpreter.interprete(operator)
        assert np.array_equal(operator_value, expected_values)
        # ensure symbol parameters are used when provided
        assert np.array_equal(await _interpreter.interprete(f"{operator}('ETH/USDT')"), expected_values / 2) # 1h ETH
        assert np.array_equal(await _interpreter.interprete(f"{operator}('BTC/USDT')"), expected_values) # 1h BTC

        # ensure time frame is used when provided
        assert np.array_equal(await _interpreter.interprete(f"{operator}(None, '4h')"), expected_values * 2) # 4h BTC
        assert np.array_equal(await _interpreter.interprete(f"{operator}(None, '1h')"), expected_values) # 1h BTC

        # ensure symbol and time frame are used when provided
        assert np.array_equal(await _interpreter.interprete(f"{operator}('BTC/USDT', '1h')"), expected_values) # 4h BTC rsi value
        assert np.array_equal(await _interpreter.interprete(f"{operator}('BTC/USDT', '4h')"), expected_values * 2) # 4h BTC rsi value
        assert np.array_equal(await _interpreter.interprete(f"{operator}('ETH/USDT', '1h')"), expected_values / 2) # 1h ETH rsi value
        with pytest.raises(KeyError): # no 4h ETH candles
            await _interpreter.interprete(f"{operator}('ETH/USDT', '4h')")


def _adapted_for_kline(values: np.ndarray, operator: str, time_delay: float) -> np.ndarray:
    adapted = values.copy()
    if time_delay > 0:
        adapted = np.append(adapted[1:], adapted[-1] + (time_delay if operator == "time" else KLINE_SIGNATURE))
    else:
        adapted[-1] += (0 if operator == "time" else KLINE_SIGNATURE)
    return adapted


@pytest.mark.asyncio
@pytest.mark.parametrize("operator, expected_values", [
    ("open", "price"),
    ("high", "price"),
    ("low", "price"),
    ("close", "price"), 
    ("volume", "volume"),
    ("time", "time")
], indirect=True) # use indirect=True to pass fixtures as a parameter
async def test_ohlcv_operators_basic_calls_with_klines(
    interpreter_with_exchange_manager_and_klines, operator, expected_values
):
    # test with both interpreter data sources
    _interpreter = interpreter_with_exchange_manager_and_klines
    # no param, use context values: SYMBOL, TIME_FRAME: BTC/USDT, 1h
    operator_value = await _interpreter.interprete(operator)
    kline_adapted_value = _adapted_for_kline(expected_values, operator, 0)
    assert np.array_equal(operator_value, kline_adapted_value)
    # ensure symbol parameters are used when provided
    assert np.array_equal(await _interpreter.interprete(f"{operator}('ETH/USDT')"), _adapted_for_kline(expected_values / 2, operator, 0)) # 1h ETH
    assert np.array_equal(await _interpreter.interprete(f"{operator}('BTC/USDT')"), kline_adapted_value) # 1h BTC

    # ensure time frame is used when provided
    assert np.array_equal(await _interpreter.interprete(f"{operator}(None, '4h')"), _adapted_for_kline(expected_values * 2, operator, 0)) # 4h BTC
    assert np.array_equal(await _interpreter.interprete(f"{operator}(None, '1h')"), kline_adapted_value) # 1h BTC

    # ensure symbol and time frame are used when provided
    assert np.array_equal(await _interpreter.interprete(f"{operator}('BTC/USDT', '1h')"), kline_adapted_value) # 4h BTC rsi value
    assert np.array_equal(await _interpreter.interprete(f"{operator}('BTC/USDT', '4h')"), _adapted_for_kline(expected_values * 2, operator, 0)) # 4h BTC rsi value
    assert np.array_equal(await _interpreter.interprete(f"{operator}('ETH/USDT', '1h')"), _adapted_for_kline(expected_values / 2, operator, 0)) # 1h ETH rsi value
    with pytest.raises(KeyError): # no 4h ETH candles
        await _interpreter.interprete(f"{operator}('ETH/USDT', '4h')")


@pytest.mark.asyncio
@pytest.mark.parametrize("operator, expected_values", [
    ("open", "price"),
    ("high", "price"),
    ("low", "price"),
    ("close", "price"), 
    ("volume", "volume"),
    ("time", "time")
], indirect=True) # use indirect=True to pass fixtures as a parameter
async def test_ohlcv_operators_basic_calls_with_new_candle_klines(
    interpreter_with_exchange_manager_and_new_candle_klines, operator, expected_values
):
    # test with both interpreter data sources
    _interpreter = interpreter_with_exchange_manager_and_new_candle_klines
    # no param, use context values: SYMBOL, TIME_FRAME: BTC/USDT, 1h
    operator_value = await _interpreter.interprete(operator)
    one_hour_time_delay = octobot_commons.enums.TimeFramesMinutes[octobot_commons.enums.TimeFrames("1h")] * octobot_commons.constants.MINUTE_TO_SECONDS
    four_hours_time_delay = octobot_commons.enums.TimeFramesMinutes[octobot_commons.enums.TimeFrames("4h")] * octobot_commons.constants.MINUTE_TO_SECONDS
    kline_adapted_value = _adapted_for_kline(expected_values, operator, one_hour_time_delay)
    assert np.array_equal(operator_value, kline_adapted_value)
    # ensure symbol parameters are used when provided
    assert np.array_equal(await _interpreter.interprete(f"{operator}('ETH/USDT')"), _adapted_for_kline(expected_values / 2, operator, one_hour_time_delay)) # 1h ETH
    assert np.array_equal(await _interpreter.interprete(f"{operator}('BTC/USDT')"), kline_adapted_value) # 1h BTC

    # ensure time frame is used when provided
    assert np.array_equal(await _interpreter.interprete(f"{operator}(None, '4h')"), _adapted_for_kline(expected_values * 2, operator, four_hours_time_delay)) # 4h BTC
    assert np.array_equal(await _interpreter.interprete(f"{operator}(None, '1h')"), kline_adapted_value) # 1h BTC

    # ensure symbol and time frame are used when provided
    assert np.array_equal(await _interpreter.interprete(f"{operator}('BTC/USDT', '1h')"), kline_adapted_value) # 4h BTC rsi value
    assert np.array_equal(await _interpreter.interprete(f"{operator}('BTC/USDT', '4h')"), _adapted_for_kline(expected_values * 2, operator, four_hours_time_delay)) # 4h BTC rsi value
    assert np.array_equal(await _interpreter.interprete(f"{operator}('ETH/USDT', '1h')"), _adapted_for_kline(expected_values / 2, operator, one_hour_time_delay)) # 1h ETH rsi value
    with pytest.raises(KeyError): # no 4h ETH candles
        await _interpreter.interprete(f"{operator}('ETH/USDT', '4h')")

    # with unknown kline time: unknown kline is ignored
    def _get_kline(symbol_data, time_frame):
        kline = octobot_trading.api.get_symbol_klines(symbol_data, time_frame)
        kline[octobot_commons.enums.PriceIndexes.IND_PRICE_TIME.value] = 1000
        return kline

    bot_log_mock = mock.Mock(
        error=mock.Mock()
    )
    with mock.patch.object(
        ohlcv_operators, "_get_kline", side_effect=_get_kline
    ) as _get_kline_mock, mock.patch.object(
        octobot_commons.logging, "get_logger", mock.Mock(return_value=bot_log_mock)
    ):
        operator_value = await _interpreter.interprete(operator)
        _get_kline_mock.assert_called_once()
        # not == kline adapted value because unknown kline is ignored
        assert np.array_equal(operator_value, kline_adapted_value) is False
        assert np.array_equal(operator_value, expected_values)
        bot_log_mock.error.assert_called_once()
        assert "kline time (1000) is not equal to last candle time not the last time" in bot_log_mock.error.call_args[0][0]


@pytest.mark.asyncio
@pytest.mark.parametrize("operator", [
    ("open"),
    ("high"),
    ("low"),
    ("close"), 
    ("volume"),
    ("time")
])
async def test_ohlcv_operators_dependencies(interpreter, operator, exchange_manager_with_candles):
    interpreter.prepare(f"{operator}")
    assert interpreter.get_dependencies() == [
        exchange_operators.ExchangeDataDependency(
            exchange_manager_id=octobot_trading.api.get_exchange_manager_id(exchange_manager_with_candles),
            symbol=SYMBOL,
            time_frame=TIME_FRAME,
            data_source=octobot_trading.constants.OHLCV_CHANNEL
        )
    ]

    # same dependency for all operators
    interpreter.prepare(f"{operator} + close + volume")
    assert interpreter.get_dependencies() == [
        exchange_operators.ExchangeDataDependency(
            exchange_manager_id=octobot_trading.api.get_exchange_manager_id(exchange_manager_with_candles),
            symbol=SYMBOL,
            time_frame=TIME_FRAME,
            data_source=octobot_trading.constants.OHLCV_CHANNEL
        )
    ]

    # SYMBOL + ETH/USDT dependency
    # => dynamic dependencies are not yet supported. Update this test when supported.
    interpreter.prepare(f"{operator} + close('ETH/USDT') + volume")
    assert interpreter.get_dependencies() == [
        exchange_operators.ExchangeDataDependency(
            exchange_manager_id=octobot_trading.api.get_exchange_manager_id(exchange_manager_with_candles),
            symbol=SYMBOL,
            time_frame=TIME_FRAME,
            data_source=octobot_trading.constants.OHLCV_CHANNEL
        ),
        # not identified as a dependency
        # exchange_operators.ExchangeDataDependency(
        #     exchange_manager_id=octobot_trading.api.get_exchange_manager_id(exchange_manager_with_candles),
        #     symbol="ETH/USDT",
        #     time_frame=TIME_FRAME,
        #     data_source=octobot_trading.constants.OHLCV_CHANNEL
        # ),
    ]
