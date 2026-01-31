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
import math
import pytest
import mock
import time
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.errors


@pytest.fixture
def interpreter():
    return dsl_interpreter.Interpreter(dsl_interpreter.get_all_operators())


@pytest.mark.asyncio
async def test_interpreter_basic_operations(interpreter):
    # constants
    assert await interpreter.interprete("True") is True
    assert await interpreter.interprete("'test'") == "test"
    assert await interpreter.interprete('"test"') == "test"

    # unary operators
    assert await interpreter.interprete("1") == 1
    assert await interpreter.interprete("-11") == -11
    assert await interpreter.interprete("+11") == +11
    assert await interpreter.interprete("not True") is False
    assert await interpreter.interprete("~ False") is True

    # binary operators
    assert await interpreter.interprete("1 + 2") == 3
    assert await interpreter.interprete("1 - 2") == -1
    assert await interpreter.interprete("4 * 2") == 8
    assert await interpreter.interprete("1 / 2") == 0.5
    assert await interpreter.interprete("1 % 3") == 1
    assert await interpreter.interprete("1 // 2") == 0
    assert await interpreter.interprete("3 ** 2") == 9

    # compare operators
    assert await interpreter.interprete("1 < 2") is True
    assert await interpreter.interprete("1 <= 2") is True
    assert await interpreter.interprete("2 <= 2") is True
    assert await interpreter.interprete("1 > 2") is False
    assert await interpreter.interprete("2 >= 2") is True
    assert await interpreter.interprete("1 == 2") is False
    assert await interpreter.interprete("1 != 2") is True
    assert await interpreter.interprete("1 is 2") is False
    assert await interpreter.interprete("1 is not 2") is True
    assert await interpreter.interprete("'1' in '123'") is True
    assert await interpreter.interprete("'4' in '123'") is False
    assert await interpreter.interprete("1 in [1, 2, 3]") is True
    assert await interpreter.interprete("4 in [1, 2, 3]") is False
    assert await interpreter.interprete("1 not in [1, 2, 3]") is False
    assert await interpreter.interprete("4 not in [1, 2, 3]") is True

    # variables
    assert await interpreter.interprete("pi") == math.pi
    assert await interpreter.interprete("pi + 1") == math.pi + 1
    assert math.isnan(await interpreter.interprete("nan"))
    assert math.isnan(await interpreter.interprete("nan + 1"))

    # expressions
    assert await interpreter.interprete("1 if True else 2") == 1
    assert await interpreter.interprete("1 if False else 2") == 2
    assert await interpreter.interprete("1 if 1 < 2 else 2") == 1
    assert await interpreter.interprete("1 if 1 > 2 else 2") == 2
    assert await interpreter.interprete("1 if 1 == 1 else 2") == 1
    assert await interpreter.interprete("1 if 1 != 2 else 2") == 1
    assert await interpreter.interprete("1 if 1 is 1 else 2") == 1
    assert await interpreter.interprete("1 if 1 is not 2 else 2") == 1

    # subscripting operators
    assert await interpreter.interprete("[1, 2, 3][:]") == [1, 2, 3]
    assert await interpreter.interprete("[1, 2, 3][0]") == 1
    assert await interpreter.interprete("[1, 2, 3][0:2]") == [1, 2]
    assert await interpreter.interprete("[1, 2, 3][2:]") == [3]
    assert await interpreter.interprete("[1, 2, 3][:1]") == [1]
    assert await interpreter.interprete("[1, 2, 3][:-1]") == [1, 2]
    assert await interpreter.interprete("[1, 2, 3][-1]") == 3
    assert await interpreter.interprete("[1, 2, 3, 4, 5, 6][0:6:2]") == [1, 3, 5]


@pytest.mark.asyncio
async def test_interpreter_mixed_basic_operations(interpreter):
    assert await interpreter.interprete("1 + 2 * 3") == 7
    assert await interpreter.interprete("(1 + 2) * 3") == 9
    assert await interpreter.interprete("(1 + 2) * 3 + 5 / 2 + 10") == 21.5
    assert await interpreter.interprete("(1 + 2) * 3 if 1 < 2 else 10 + pi") == 9
    assert await interpreter.interprete("(1 + 2) * 3 if 1 > 2 else 10 + pi") == 10 + math.pi
    assert await interpreter.interprete("1 < 2 and 2 < 3") is True
    assert await interpreter.interprete("1 < 2 and 2 < 3 and True and 1") is True
    assert await interpreter.interprete("1 < 2 and 2 > 3") is False
    assert await interpreter.interprete("1 < 2 or 2 > 3") is True
    assert await interpreter.interprete("1 < 2 or 2 > 3 or True or False or 0") is True
    assert await interpreter.interprete("1 > 2 or 2 > 3") is False
    assert await interpreter.interprete("not (1 < 2 and 2 < 3)") is False
    assert await interpreter.interprete("not (1 < 2 and 2 > 3)") is True
    assert await interpreter.interprete("not (1 > 2 or 2 > 3)") is True
    assert await interpreter.interprete("not (1 > 2 or 2 < 3)") is False


@pytest.mark.asyncio
async def test_interpreter_call_operations(interpreter):
    assert await interpreter.interprete("max(1, 2, 3)") == 3
    assert await interpreter.interprete("min(1, 2, 3)") == 1
    assert await interpreter.interprete("abs(-1)") == 1
    assert await interpreter.interprete("abs(1)") == 1
    assert await interpreter.interprete("sqrt(4)") == 2
    assert await interpreter.interprete("mean(1, 2, 3)") == 2
    assert await interpreter.interprete("mean(50, 110.2)") == 80.1
    assert await interpreter.interprete("mean(3)") == 3
    assert await interpreter.interprete("round(1.23456789, 2)") == 1.23
    assert await interpreter.interprete("round(1.23456789, 2.22)") == 1.23
    assert await interpreter.interprete("round(1.23456789)") == 1
    assert await interpreter.interprete("floor(1.23456789)") == 1
    assert await interpreter.interprete("ceil(1.23456789)") == 2
    assert await interpreter.interprete("sin(0)") == 0
    assert abs(await interpreter.interprete("sin(pi/2)") - 1) < 1e-10
    assert abs(await interpreter.interprete("sin(pi)") - 0) < 1e-10
    assert await interpreter.interprete("cos(0)") == 1
    assert abs(await interpreter.interprete("cos(pi/2)") - 0) < 1e-10
    assert abs(await interpreter.interprete("cos(pi)") - (-1)) < 1e-10
    assert 90 <= await interpreter.interprete("oscillate(100, 10, 60)") <= 110  # 100 ± 10%
    assert 40 <= await interpreter.interprete("oscillate(50, 20, 30)") <= 60  # 50 ± 20%
    assert 190 <= await interpreter.interprete("oscillate(200, 5, 120)") <= 210  # 200 ± 5%
    assert 185 <= await interpreter.interprete("oscillate(150 + oscillate(50, 10, 60), 5, 120)") <= 215  # 200 ± 5%


@pytest.mark.asyncio
async def test_interpreter_oscillate_operations(interpreter):
    for time_mock in range(int(time.time()), int(time.time()) + 3600, 1):
        with mock.patch.object(time, 'time', return_value=time_mock * 0.1241):
            # always returns a value between 90 and 110
            assert 90 <= await interpreter.interprete("oscillate(100, 10, 60.221)") <= 110


@pytest.mark.asyncio
async def test_interpreter_mixed_call_and_basic_operations(interpreter):
    assert await interpreter.interprete("max(sqrt(9), abs(-4), 3 + 6)") == 9
    assert await interpreter.interprete("min(sqrt(9), abs(-4), 3 + 6)") == 3
    assert await interpreter.interprete("abs(min(sqrt(9), abs(-4), 3 + 6))") == 3
    assert await interpreter.interprete("sqrt(max(1, 2, 3, 4))") == 2
    assert await interpreter.interprete("sqrt(2**2)") == 2
    assert await interpreter.interprete("sqrt(min(1, 2, 3))") == 1
    assert await interpreter.interprete("abs(sqrt(max(1, 2, 4)))") == 2
    assert await interpreter.interprete("abs(sqrt(min(1, 2, 4)))") == 1
    assert await interpreter.interprete("mean(4, 5) + 1 + mean(1, 1 + 1, 3)") == 7.5
    assert abs(await interpreter.interprete("sin(pi/2) + cos(0)") - 2) < 1e-10
    assert abs(await interpreter.interprete("sin(pi/4) * cos(pi/4)") - 0.5) < 1e-10
    assert abs(await interpreter.interprete("sqrt(sin(pi/2)**2 + cos(pi/2)**2)") - 1) < 1e-10


@pytest.mark.asyncio
async def test_interpreter_insupported_operations(interpreter):
    with pytest.raises(octobot_commons.errors.UnsupportedOperatorError):
        await interpreter.interprete("1 & 2")
    with pytest.raises(octobot_commons.errors.UnsupportedOperatorError):
        await interpreter.interprete("1 | 2")
    with pytest.raises(octobot_commons.errors.UnsupportedOperatorError):
        await interpreter.interprete("3 ^ 2")
    with pytest.raises(octobot_commons.errors.UnsupportedOperatorError):
        await interpreter.interprete("1 << 2")
    with pytest.raises(octobot_commons.errors.UnsupportedOperatorError):
        await interpreter.interprete("1 >> 2")
    with pytest.raises(octobot_commons.errors.UnsupportedOperatorError):
        await interpreter.interprete("my_variable")
    with pytest.raises(octobot_commons.errors.UnsupportedOperatorError):
        await interpreter.interprete("unknown_operator(1)")
    with pytest.raises(octobot_commons.errors.InvalidParametersError):
        await interpreter.interprete("mean(1, 'a')")
    with pytest.raises(octobot_commons.errors.InvalidParametersError):
        await interpreter.interprete("mean()")
    with pytest.raises(octobot_commons.errors.InvalidParametersError):
        await interpreter.interprete("sin('a')")
    with pytest.raises(octobot_commons.errors.InvalidParametersError):
        await interpreter.interprete("cos('a')")
    with pytest.raises(octobot_commons.errors.InvalidParametersError):
        await interpreter.interprete("oscillate('a', 10, 60)")
    with pytest.raises(octobot_commons.errors.InvalidParametersError):
        await interpreter.interprete("oscillate(100, 'b', 60)")
    with pytest.raises(octobot_commons.errors.InvalidParametersError):
        await interpreter.interprete("oscillate(100, 10, 'c')")
    with pytest.raises(octobot_commons.errors.InvalidParametersError):
        await interpreter.interprete("oscillate(100)")
    with pytest.raises(octobot_commons.errors.InvalidParametersError):
        await interpreter.interprete("oscillate(100, 10)")
    with pytest.raises(octobot_commons.errors.InvalidParametersError):
        await interpreter.interprete("oscillate(100, 10, 60, 70)")
    with pytest.raises(octobot_commons.errors.InvalidParametersError):
        await interpreter.interprete("oscillate(100, 10, -1)")
    with pytest.raises(octobot_commons.errors.InvalidParametersError):
        await interpreter.interprete("oscillate(100, 10, 0)")
