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

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.enums as trading_enums
import tentacles.Meta.DSL_operators.exchange_operators as exchange_operators


SYMBOL = "BTC/USDT"
EXPIRY_TIMESTAMP = 1700000000000


@pytest.fixture
def host():
    return mock.Mock(
        triggered_symbol=SYMBOL,
        exchange_manager=mock.Mock(
            exchange=mock.Mock(
                connector=mock.Mock(
                    client=mock.Mock(
                        markets={
                            SYMBOL: {
                                trading_enums.ExchangeConstantsMarketStatusColumns.EXPIRY.value: EXPIRY_TIMESTAMP,
                            },
                            "ETH/USDT": {},
                        }
                    )
                )
            )
        ),
    )


@pytest.fixture
def interpreter(host):
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + exchange_operators.create_symbol_operators(host)
    )


@pytest.mark.asyncio
async def test_triggered_symbol(interpreter):
    assert await interpreter.interprete("triggered_symbol()") == SYMBOL


@pytest.mark.asyncio
async def test_market_expiry_with_expiry(interpreter):
    assert await interpreter.interprete(f"market_expiry('{SYMBOL}')") == EXPIRY_TIMESTAMP


@pytest.mark.asyncio
async def test_market_expiry_without_expiry(interpreter):
    assert await interpreter.interprete("market_expiry('ETH/USDT')") is None


@pytest.mark.asyncio
async def test_market_expiry_unknown_symbol(interpreter):
    assert await interpreter.interprete("market_expiry('UNKNOWN/PAIR')") is None


@pytest.mark.asyncio
async def test_market_expiry_with_triggered_symbol(interpreter):
    assert await interpreter.interprete("market_expiry(triggered_symbol())") == EXPIRY_TIMESTAMP
