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

import octobot_commons.errors
from tentacles.Meta.DSL_operators.exchange_operators.tests import (
    historical_prices,
    historical_volume,
    historical_times,
    exchange_manager_with_candles,
    interpreter,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("operator, static_parameters", [
    # list all operator and "possible" invalid parameters
    ("rsi", ["", "(close)", "(close, 14, 20)"]),
    ("macd", ["", "(close)", "(close, 'a')", "(close, 'a', 26)", "('a', 14, 26, 9, 0)"]),
    ("ma", ["", "(close)", "(close, 14, 20)"]),
    ("ema", ["", "(close)", "(close, 14, 20)"]),
    ("vwma", ["", "(close)", "('a', 14)", "(close, 'a')", "(close, 14, 11, 20)"]),
])
async def test_operator_invalid_static_parameters(interpreter, operator, static_parameters):
    for param in static_parameters:
        with pytest.raises(octobot_commons.errors.InvalidParametersError, match=f"{operator} "):
            # static validation
            interpreter.prepare(f"{operator}{param}")
        with pytest.raises(octobot_commons.errors.InvalidParametersError):
            # dynamic validation
            await interpreter.interprete(f"{operator}{param}")


@pytest.mark.asyncio
@pytest.mark.parametrize("operator, dynamic_parameters", [
    # list all operator and "possible" invalid parameters
    ("rsi", ["('a', 14)", "(close, 'a')"]),
    ("macd", ["('a', 14, 26, 9)", "(close, 'a', 26, 9)", "(close, 14, 'a', 9)", "(close, 14, 26, 'a')"]),
    ("ma", ["('a', 14)", "(close, 'a')"]),
    ("ema", ["('a', 14)", "(close, 'a')"]),
    ("vwma", ["(close, volume, 'a')", "(close, 14, 20)"]),
])
async def test_operator_invalid_dynamic_parameters(interpreter, operator, dynamic_parameters):
    for param in dynamic_parameters:
        # static validation: do not raise
        interpreter.prepare(f"{operator}{param}")
        with pytest.raises(octobot_commons.errors.InvalidParametersError):
            # dynamic validation
            await interpreter.interprete(f"{operator}{param}")


@pytest.mark.asyncio
@pytest.mark.parametrize("operator, dynamic_parameters", [
    # list all operator and invalid parameters that should raise a tulipy error that will be converted to a TypeError
    ("rsi", ["(close, 999999)", "(close, 0)", "(close, -1)"]),
    ("macd", ["(close, 14, 99999, 2)", "(close, 99999, 12, 2)", "(close, 0, 12, 2)", "(close, 7, 12, -1)"]),
    ("ma", ["(close, 999999)", "(close, 0)", "(close, -1)"]),
    ("ema", ["(close, -1)"]),
    ("vwma", ["(close, volume, 999999)", "(close, volume, 0)", "(close, volume, -1)"]),
])
async def test_operator_converted_tulipy_error(interpreter, operator, dynamic_parameters):
    for param in dynamic_parameters:
        # static validation: do not raise
        interpreter.prepare(f"{operator}{param}")
        with pytest.raises(TypeError):
            # dynamic validation
            await interpreter.interprete(f"{operator}{param}")


@pytest.mark.asyncio
async def test_operator_operations(interpreter):
    # ensure the output is a list and can be used in arithmetic operations
    assert isinstance(await interpreter.interprete("rsi(close, 14)"), list)
    assert await interpreter.interprete("round(rsi(close, 26)[-1], 2)") == 74.3
    assert await interpreter.interprete("round(rsi(close, 14)[-1], 2)") == 67.55
    assert await interpreter.interprete("round(rsi(close, 26)[-1] - rsi(close, 14)[-1], 2)") == 6.74

    # combine ma & vwma
    ma = await interpreter.interprete("ma(close, 14)")
    vwma = await interpreter.interprete("vwma(close, volume, 14)")
    assert round(ma[-1], 2) == 92.53
    assert round(vwma[-1], 2) == 92.37
    assert round(ma[-1]*0.7 + vwma[-1]*0.3, 2) == 92.48
    assert await interpreter.interprete("round(ma(close, 14)[-1]*0.7 + vwma(close, volume, 14)[-1]*0.3, 2)") == 92.48


@pytest.mark.asyncio
async def test_rsi_operator(interpreter):
    rsi = await interpreter.interprete("rsi(close, 14)")
    rounded_rsi = [round(v, 2) for v in rsi]
    assert rounded_rsi == [
        79.56, 78.6, 77.04, 81.67, 82.88, 84.06, 87.44, 88.03, 85.21, 85.81, 86.73, 
        78.58, 78.71, 70.4, 72.5, 72.78, 67.78, 67.55
    ]
    # different periods, different result
    rsi = await interpreter.interprete("rsi(close, 20)")
    rounded_rsi = [round(v, 2) for v in rsi]
    assert rounded_rsi == [
        85.71, 86.2, 84.2, 84.66, 85.37, 79.61, 79.7, 73.72, 75.04, 75.22, 71.62, 71.46
    ]

    assert await interpreter.interprete("round(rsi(close, 26)[-1], 2)") == 74.3
    assert await interpreter.interprete("round(rsi(close, 14)[-1], 2)") == 67.55
    assert await interpreter.interprete("round(rsi(close, 26)[-1] - rsi(close, 14)[-1], 2)") == 6.74


@pytest.mark.asyncio
async def test_macd_operator(interpreter):
    macd = await interpreter.interprete("macd(close, 12, 26, 9)")
    rounded_macd = [round(v, 2) for v in macd]
    assert rounded_macd == [0.0, -0.03, -0.14, -0.18, -0.22, -0.29, -0.34]

    # different parameters, different result
    macd = await interpreter.interprete("macd(close, 9, 26, 9)")
    rounded_macd = [round(v, 2) for v in macd]
    assert rounded_macd == [
        0.0, -0.09, -0.29, -0.36, -0.41, -0.52, -0.59
    ]

    macd = await interpreter.interprete("macd(close, 9, 20, 9)")
    rounded_macd = [round(v, 2) for v in macd]
    assert rounded_macd == [
        0.0, 0.26, 0.41, 0.41, 0.38, 0.36, 0.21, 0.07, -0.14, -0.23, -0.29, -0.4, -0.46
    ]

    macd = await interpreter.interprete("macd(close, 9, 20, 6)")
    rounded_macd = [round(v, 2) for v in macd]
    assert rounded_macd == [
        0.0, 0.23, 0.35, 0.32, 0.28, 0.25, 0.1, -0.01, -0.19, -0.24, -0.26, -0.33, -0.37
    ]


@pytest.mark.asyncio
async def test_ma_operator(interpreter):
    ma = await interpreter.interprete("ma(close, 14)")
    rounded_ma = [round(v, 2) for v in ma]
    assert rounded_ma == [
        84.12, 84.53, 84.97, 85.26, 85.7, 86.13, 86.64, 87.36, 88.03, 88.63, 
        89.28, 89.9, 90.37, 90.82, 91.12, 91.52, 91.93, 92.3, 92.53
    ]

    # different periods, different result
    ma = await interpreter.interprete("ma(close, 20)")
    rounded_ma = [round(v, 2) for v in ma]
    assert rounded_ma == [
        85.41, 85.98, 86.59, 87.1, 87.62, 88.15, 88.65, 89.16, 89.57, 89.98, 
        90.41, 90.75, 91.03
    ]


@pytest.mark.asyncio
async def test_vwma_operator(interpreter):
    vwma = await interpreter.interprete("vwma(close, volume, 14)")
    rounded_vwma = [round(v, 2) for v in vwma]
    assert rounded_vwma == [
        # different results from ma(close, 14)
        84.15, 84.51, 84.87, 85.29, 85.66, 86.3, 86.76, 87.37, 88.02, 88.55, 
        89.1, 89.9, 90.31, 90.87, 91.16, 91.53, 91.91, 92.19, 92.37
    ]
    # different periods, different result
    vwma = await interpreter.interprete("vwma(close, volume, 20)")
    rounded_vwma = [round(v, 2) for v in vwma]
    assert rounded_vwma == [
        85.52, 85.93, 86.5, 87.19, 87.66, 88.06, 88.53, 89.24, 89.6, 89.9, 
        90.27, 90.84, 91.08
    ]


@pytest.mark.asyncio
async def test_ema_operator(interpreter):
    ema = await interpreter.interprete("ema(close, 14)")
    rounded_ema = [round(v, 2) for v in ema]
    assert rounded_ema == [
        # different results from ma(close, 14)
        81.59, 81.52, 81.7, 81.87, 82.1, 82.24, 82.32, 82.55, 82.81, 83.02, 
        83.35, 83.78, 84.19, 84.67, 85.02, 85.31, 85.53, 86.0, 86.49, 87.01, 
        87.78, 88.53, 89.13, 89.7, 90.29, 90.67, 91.0, 91.15, 91.37, 91.58, 
        91.67, 91.74
    ]

    # different periods, different result
    ema = await interpreter.interprete("ema(close, 20)")
    rounded_ema = [round(v, 2) for v in ema]
    assert rounded_ema == [
        81.59, 81.54, 81.67, 81.79, 81.97, 82.08, 82.15, 82.33, 82.54, 82.71, 
        82.98, 83.32, 83.66, 84.05, 84.36, 84.63, 84.85, 85.25, 85.67, 86.12, 
        86.76, 87.39, 87.92, 88.45, 88.99, 89.38, 89.75, 89.97, 90.24, 90.5, 
        90.66, 90.81
    ]
