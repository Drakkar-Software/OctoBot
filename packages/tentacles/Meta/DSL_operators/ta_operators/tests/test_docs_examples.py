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

from tentacles.Meta.DSL_operators.exchange_operators.tests import (
    historical_prices,
    historical_volume,
    historical_times,
    exchange_manager_with_candles,
    interpreter,
)


@pytest.mark.asyncio
async def test_mm_formulas_docs_examples(interpreter):
    # ensure examples in the docs are working (meaning returning a parsable number)
    assert round(await interpreter.interprete("close[-1]"), 2) == 92.22
    assert round(await interpreter.interprete("open[-1]"), 2) == 92.22
    assert round(await interpreter.interprete("high[-3]"), 2) == 92.92
    assert round(await interpreter.interprete("low[-1]"), 2) == 92.22
    assert round(await interpreter.interprete("volume[-2]"), 2) == 1211
    assert round(await interpreter.interprete("time[-1]"), 2) == 41
    assert round(await interpreter.interprete("ma(close, 12)[-1]"), 2) == 92.95
    assert round(await interpreter.interprete("ema(open, 24)[-1]"), 2) == 90.21
    assert round(await interpreter.interprete("vwma(close, volume, 4)[-1]"), 2) == 92.54
    assert round(await interpreter.interprete("rsi(close, 14)[-1]"), 2) == 67.55
    assert round(await interpreter.interprete("max(close[-1], open[-1])"), 2) == 92.22
    assert round(await interpreter.interprete("min(ma(close, 12)[-1], ema(open, 24)[-1])"), 2) == 90.21
    assert round(await interpreter.interprete("mean(close[-1], open[-1], high[-1], low[-1])"), 2) == 92.22
    assert round(await interpreter.interprete("round(ma(close, 12)[-1], 2)"), 2) == 92.95
    assert round(await interpreter.interprete("floor(close[-1])"), 2) == 92
    assert round(await interpreter.interprete("ceil(close[-1])"), 2) == 93
    assert round(await interpreter.interprete("abs(close[-1] - open[-1])"), 2) == 0
    assert 0 < await interpreter.interprete("sin(3.14)") < 0.01
    assert await interpreter.interprete("cos(3*pi)") == -1
    assert 900 <= await interpreter.interprete("oscillate(1000, 10, 60)") <= 1100
    assert round(await interpreter.interprete("100 if close[-1] > open[-1] else (90 + 1)"), 2) == 91
