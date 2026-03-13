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
import asyncio
import time

import pytest
import mock

import tentacles.Meta.DSL_operators.python_std_operators.base_resetting_operators as base_resetting_operators
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.errors


@pytest.fixture
def interpreter():
    return dsl_interpreter.Interpreter(dsl_interpreter.get_all_operators())


class TestWaitOperator:
    @pytest.mark.asyncio
    async def test_wait_operator(self, interpreter):
        assert "wait" in interpreter.operators_by_name

        # wait(0) returns None after 0 seconds (instant)
        assert await interpreter.interprete("wait(0)") is None

        with mock.patch.object(asyncio, "sleep", new=mock.AsyncMock()) as mock_sleep:
            await interpreter.interprete("wait(1)")
            mock_sleep.assert_awaited_once_with(1)

            mock_sleep.reset_mock()

            # wait with return_remaining_time=True returns ReCallingOperatorResult dict
            with mock.patch.object(time, "time", return_value=1000.0):
                result = await interpreter.interprete("wait(5, return_remaining_time=True)")
                assert result == {
                    "last_execution_result": {
                        dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 1000.0,
                        dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value: 5,
                    },
                }
                mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_wait_operator_unit(self):
        operator = base_resetting_operators.WaitOperator(1)

        # _compute_sleep_time with min_seconds only
        assert operator._compute_sleep_time({"min_seconds": 1, "max_seconds": None}) == 1
        assert operator._compute_sleep_time({"min_seconds": 0, "max_seconds": None}) == 0

        # _compute_sleep_time with negative raises
        with pytest.raises(octobot_commons.errors.InvalidParametersError, match="non-negative"):
            operator._compute_sleep_time({"min_seconds": -1, "max_seconds": None})

        # _compute_sleep_time with min and max - returns value in range (mock random)
        with mock.patch.object(base_resetting_operators.random, "randrange", return_value=1500):
            assert operator._compute_sleep_time({"min_seconds": 1, "max_seconds": 2}) == 1.5

        # _compute_remaining_time with no previous
        with mock.patch.object(base_resetting_operators.time, "time", return_value=1000.0):
            with mock.patch.object(base_resetting_operators.random, "randrange", return_value=3000):
                result = operator._compute_remaining_time({
                    "min_seconds": 1, "max_seconds": 4,
                    dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: None,
                })
        assert result is not None
        assert result["last_execution_result"][dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value] == 1000.0
        assert result["last_execution_result"][dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value] == 3.0

        # _compute_remaining_time with previous (ReCallingOperatorResult format)
        with mock.patch.object(base_resetting_operators.time, "time", return_value=1002.0):
            result = operator._compute_remaining_time({
                "min_seconds": 1, "max_seconds": None,
                dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: {
                    "last_execution_result": {
                        dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 1000.0,
                        dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value: 5.0,
                    },
                },
            })
        assert result is not None
        assert result["last_execution_result"][dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value] == 1002.0
        assert result["last_execution_result"][dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value] == 3.0  # 5 - (1002 - 1000)

        # No mock: ensure random and time are actually called and return valid values
        min_sec, max_sec = 1, 3
        sleep_times = [
            operator._compute_sleep_time({"min_seconds": min_sec, "max_seconds": max_sec})
            for _ in range(20)
        ]
        for sleep_time in sleep_times:
            assert min_sec <= sleep_time < max_sec
        assert len(set(sleep_times)) > 1  # random produces varying values

        result = operator._compute_remaining_time({
            "min_seconds": 2, "max_seconds": 5,
            dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: None,
        })
        assert result is not None
        assert "last_execution_result" in result
        assert dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value in result["last_execution_result"]
        assert dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value in result["last_execution_result"]
        assert 2 <= result["last_execution_result"][dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value] < 5
        assert result["last_execution_result"][dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value] > 0

        previous = {
            "last_execution_result": {
                dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: time.time() - 1.0,
                dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value: 5.0,
            },
        }
        result = operator._compute_remaining_time({
            "min_seconds": 1, "max_seconds": None,
            dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: previous,
        })
        assert result is not None
        assert result["last_execution_result"][dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value] <= 5.0  # time has passed
        assert result["last_execution_result"][dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value] >= previous["last_execution_result"][dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value]

    @pytest.mark.asyncio
    async def test_wait_operator_pre_compute(self):
        operator = base_resetting_operators.WaitOperator(0)
        with mock.patch.object(asyncio, "sleep", new=mock.AsyncMock()) as mock_sleep:
            await operator.pre_compute()
            mock_sleep.assert_awaited_once_with(0)

        operator_with_return = base_resetting_operators.WaitOperator(2, return_remaining_time=True)
        with mock.patch.object(asyncio, "sleep", new=mock.AsyncMock()) as mock_sleep:
            await operator_with_return.pre_compute()
            mock_sleep.assert_not_awaited()
            assert operator_with_return.value is not None
            assert isinstance(operator_with_return.value, dict)
            assert operator_with_return.value["last_execution_result"][dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value] == 2

    @pytest.mark.asyncio
    async def test_wait_operator_invalid_parameters(self, interpreter):
        with pytest.raises(octobot_commons.errors.InvalidParametersError, match="non-negative"):
            await interpreter.interprete("wait(-1)")
