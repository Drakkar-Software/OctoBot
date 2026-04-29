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
import mock
import time
import pytest

import octobot_commons.dsl_interpreter as dsl_interpreter
import tentacles.Meta.DSL_operators.python_std_operators.base_time_operators as base_time_operators


@pytest.fixture
def interpreter():
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators() + [base_time_operators.NowMsOperator]
    )


@pytest.mark.asyncio
async def test_now_ms_returns_current_time(interpreter):
    fixed_time = 1700000000.123
    with mock.patch.object(time, "time", return_value=fixed_time):
        result = await interpreter.interprete("now_ms()")
    assert result == 1700000000123


@pytest.mark.asyncio
async def test_now_ms_in_expression(interpreter):
    fixed_time = 1700000000.0
    with mock.patch.object(time, "time", return_value=fixed_time):
        result = await interpreter.interprete("now_ms() > 0")
    assert result is True
