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
import octobot_commons.dsl_interpreter as dsl_interpreter
import tentacles.Meta.DSL_operators.exchange_operators as exchange_operators


SYMBOL = "BTC/USDT"
TICKERS = {
    SYMBOL: {
        "close": 50000.0,
        "open": 49000.0,
        "high": 51000.0,
        "low": 48000.0,
        "baseVolume": 1234.5,
        "last": 50100.0,
    },
    "ETH/USDT": {
        "close": 3000.0,
        "open": 2900.0,
        "high": 3100.0,
        "low": 2800.0,
        "baseVolume": 5678.9,
        "last": 3050.0,
    },
}


@pytest.fixture
def interpreter():
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + exchange_operators.create_ticker_operators(TICKERS)
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("operator, field", [
    ("ticker_close", "close"),
    ("ticker_open", "open"),
    ("ticker_high", "high"),
    ("ticker_low", "low"),
    ("ticker_volume", "baseVolume"),
    ("ticker_last", "last"),
])
async def test_ticker_operators(interpreter, operator, field):
    assert await interpreter.interprete(f"{operator}('{SYMBOL}')") == TICKERS[SYMBOL][field]
    assert await interpreter.interprete(f"{operator}('ETH/USDT')") == TICKERS["ETH/USDT"][field]


@pytest.mark.asyncio
async def test_ticker_unknown_symbol(interpreter):
    with pytest.raises(octobot_commons.errors.DSLInterpreterError, match="No ticker data"):
        await interpreter.interprete("ticker_close('UNKNOWN/PAIR')")


@pytest.mark.asyncio
async def test_ticker_none_field():
    tickers_with_none = {SYMBOL: {"close": None}}
    interp = dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + exchange_operators.create_ticker_operators(tickers_with_none)
    )
    with pytest.raises(octobot_commons.errors.DSLInterpreterError, match="is None"):
        await interp.interprete(f"ticker_close('{SYMBOL}')")
