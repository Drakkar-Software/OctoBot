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


class _LoopUntilSingleEvalTestConditionOperator(dsl_interpreter.CallOperator):
    MIN_PARAMS = 0
    MAX_PARAMS = 0

    @staticmethod
    def get_name() -> str:
        return "test_loop_until_single_eval_condition"

    def compute(self):
        return True


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

            # wait with return_remaining_time=True returns ReCallingOperatorResult dict (wrapped format)
            with mock.patch.object(time, "time", return_value=1000.0):
                result = await interpreter.interprete("wait(5, return_remaining_time=True)")
                assert dsl_interpreter.ReCallingOperatorResult.__name__ in result
                inner = result[dsl_interpreter.ReCallingOperatorResult.__name__]
                assert inner == {
                    "last_execution_result": {
                        dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 1000.0,
                        dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value: 5,
                    },
                    "keyword": "wait",
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
        last_result = result[dsl_interpreter.ReCallingOperatorResult.__name__]["last_execution_result"]
        assert last_result[dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value] == 1000.0
        assert last_result[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value] == 3.0

        # _compute_remaining_time with previous (ReCallingOperatorResult wrapped format)
        with mock.patch.object(base_resetting_operators.time, "time", return_value=1002.0):
            result = operator._compute_remaining_time({
                "min_seconds": 1, "max_seconds": None,
                dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: {
                    dsl_interpreter.ReCallingOperatorResult.__name__: {
                        "last_execution_result": {
                            dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 1000.0,
                            dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value: 5.0,
                        },
                    },
                },
            })
        assert result is not None
        last_result = result[dsl_interpreter.ReCallingOperatorResult.__name__]["last_execution_result"]
        assert last_result[dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value] == 1002.0
        assert last_result[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value] == 3.0  # 5 - (1002 - 1000)

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
        last_result = result[dsl_interpreter.ReCallingOperatorResult.__name__]["last_execution_result"]
        assert dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value in last_result
        assert dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value in last_result
        assert 2 <= last_result[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value] < 5
        assert last_result[dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value] > 0

        previous = {
            dsl_interpreter.ReCallingOperatorResult.__name__: {
                "last_execution_result": {
                    dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: time.time() - 1.0,
                    dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value: 5.0,
                },
            },
        }
        result = operator._compute_remaining_time({
            "min_seconds": 1, "max_seconds": None,
            dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: previous,
        })
        assert result is not None
        last_result = result[dsl_interpreter.ReCallingOperatorResult.__name__]["last_execution_result"]
        prev_last_result = previous[dsl_interpreter.ReCallingOperatorResult.__name__]["last_execution_result"]
        assert last_result[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value] <= 5.0  # time has passed
        assert last_result[dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value] >= prev_last_result[dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value]

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
            last_result = operator_with_return.value[dsl_interpreter.ReCallingOperatorResult.__name__]["last_execution_result"]
            assert last_result[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value] == 2

    @pytest.mark.asyncio
    async def test_wait_operator_invalid_parameters(self, interpreter):
        with pytest.raises(octobot_commons.errors.InvalidParametersError, match="non-negative"):
            await interpreter.interprete("wait(-1)")


class TestLoopUntilOperator:
    @pytest.mark.asyncio
    async def test_loop_until_registered(self, interpreter):
        assert "loop_until" in interpreter.operators_by_name

    @pytest.mark.asyncio
    async def test_loop_until_blocking_immediate_true(self, interpreter):
        assert await interpreter.interprete("loop_until(1<2, 0, max_attempts=1)") is True

    @pytest.mark.asyncio
    async def test_loop_until_blocking_returns_condition_value(self, interpreter):
        assert await interpreter.interprete("loop_until(42, 0, max_attempts=1)") == 42

    @pytest.mark.asyncio
    async def test_loop_until_blocking_max_attempts_exceeded(self, interpreter):
        with pytest.raises(octobot_commons.errors.ErrorStatementEncountered, match="max_attempts"):
            await interpreter.interprete("loop_until(False, 0, max_attempts=1)")

    @pytest.mark.asyncio
    async def test_loop_until_blocking_max_attempts_after_retries(self, interpreter):
        with mock.patch.object(asyncio, "sleep", new=mock.AsyncMock()) as mock_sleep:
            with pytest.raises(octobot_commons.errors.ErrorStatementEncountered, match="max_attempts"):
                await interpreter.interprete("loop_until(False, 0, max_attempts=3)")
        assert mock_sleep.await_count == 2

    @pytest.mark.asyncio
    async def test_loop_until_blocking_condition_true_after_iterations(self, interpreter):
        with mock.patch.object(
            base_resetting_operators.LoopUntilOperator,
            "_evaluate_condition_async",
            new=mock.AsyncMock(side_effect=[False, False, "ready"]),
        ):
            with mock.patch.object(asyncio, "sleep", new=mock.AsyncMock()) as mock_sleep:
                final_value = await interpreter.interprete(
                    "loop_until(False, 1, max_attempts=10, timeout=60)"
                )
        assert final_value == "ready"
        assert mock_sleep.await_count == 2

    @pytest.mark.asyncio
    async def test_loop_until_blocking_timeout(self, interpreter):
        with mock.patch.object(
            base_resetting_operators.time,
            "time",
            side_effect=[0.0, 0.0, 100.0],
        ):
            with mock.patch.object(asyncio, "sleep", new=mock.AsyncMock()):
                with pytest.raises(octobot_commons.errors.ErrorStatementEncountered, match="timeout"):
                    await interpreter.interprete("loop_until(False, 1, timeout=10)")

    @pytest.mark.asyncio
    async def test_loop_until_invalid_retry_interval(self, interpreter):
        with pytest.raises(octobot_commons.errors.InvalidParametersError, match="retry_interval"):
            await interpreter.interprete("loop_until(True, -1, max_attempts=1)")

    @pytest.mark.asyncio
    async def test_loop_until_invalid_max_attempts(self, interpreter):
        with pytest.raises(octobot_commons.errors.InvalidParametersError, match="max_attempts"):
            await interpreter.interprete("loop_until(True, 1, max_attempts=0)")

    @pytest.mark.asyncio
    async def test_loop_until_return_remaining_first_failure_schedules_wait(self):
        operator = base_resetting_operators.LoopUntilOperator(
            False,
            5,
            max_attempts=10,
            return_remaining_time=True,
        )
        with mock.patch.object(base_resetting_operators.time, "time", return_value=1000.0):
            await operator.pre_compute()
        assert isinstance(operator.value, dict)
        last_result = operator.value[dsl_interpreter.ReCallingOperatorResult.__name__][
            "last_execution_result"
        ]
        assert last_result[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value] == 5.0
        assert last_result[dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value] == 1000.0
        assert last_result[base_resetting_operators.LoopUntilOperator.ATTEMPT_COUNT_KEY] == 1
        assert last_result[base_resetting_operators.LoopUntilOperator.LOOP_START_TIME_KEY] == 1000.0

    @pytest.mark.asyncio
    async def test_loop_until_return_remaining_condition_true_immediately(self):
        operator = base_resetting_operators.LoopUntilOperator(
            True,
            5,
            max_attempts=10,
            return_remaining_time=True,
        )
        await operator.pre_compute()
        assert operator.value is True

    @pytest.mark.asyncio
    async def test_loop_until_return_remaining_preserves_loop_state_while_waiting(self):
        wrapped_previous = {
            dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: {
                dsl_interpreter.ReCallingOperatorResult.__name__: {
                    "last_execution_result": {
                        dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 1000.0,
                        dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value: 5.0,
                        base_resetting_operators.LoopUntilOperator.LOOP_START_TIME_KEY: 999.0,
                        base_resetting_operators.LoopUntilOperator.ATTEMPT_COUNT_KEY: 1,
                    },
                },
            },
        }
        operator = base_resetting_operators.LoopUntilOperator(
            False,
            5,
            max_attempts=10,
            return_remaining_time=True,
            **wrapped_previous,
        )
        with mock.patch.object(base_resetting_operators.time, "time", return_value=1002.0):
            await operator.pre_compute()
        last_result = operator.value[dsl_interpreter.ReCallingOperatorResult.__name__][
            "last_execution_result"
        ]
        assert last_result[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value] == 3.0
        assert last_result[base_resetting_operators.LoopUntilOperator.ATTEMPT_COUNT_KEY] == 2
        assert last_result[base_resetting_operators.LoopUntilOperator.LOOP_START_TIME_KEY] == 999.0

    @pytest.mark.asyncio
    async def test_loop_until_return_remaining_max_attempts_while_still_waiting(self):
        wrapped_previous = {
            dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: {
                dsl_interpreter.ReCallingOperatorResult.__name__: {
                    "last_execution_result": {
                        dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 1000.0,
                        dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value: 5.0,
                        base_resetting_operators.LoopUntilOperator.LOOP_START_TIME_KEY: 999.0,
                        base_resetting_operators.LoopUntilOperator.ATTEMPT_COUNT_KEY: 1,
                    },
                },
            },
        }
        operator = base_resetting_operators.LoopUntilOperator(
            False,
            5,
            max_attempts=2,
            return_remaining_time=True,
            **wrapped_previous,
        )
        with mock.patch.object(base_resetting_operators.time, "time", return_value=1002.0):
            with pytest.raises(octobot_commons.errors.ErrorStatementEncountered, match="max_attempts"):
                await operator.pre_compute()

    @pytest.mark.asyncio
    async def test_loop_until_return_remaining_true_while_wait_incomplete_short_circuits_wait(self):
        wrapped_previous = {
            dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: {
                dsl_interpreter.ReCallingOperatorResult.__name__: {
                    "last_execution_result": {
                        dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 1000.0,
                        dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value: 5.0,
                        base_resetting_operators.LoopUntilOperator.LOOP_START_TIME_KEY: 998.0,
                        base_resetting_operators.LoopUntilOperator.ATTEMPT_COUNT_KEY: 1,
                    },
                },
            },
        }
        operator = base_resetting_operators.LoopUntilOperator(
            True,
            5,
            max_attempts=10,
            return_remaining_time=True,
            **wrapped_previous,
        )
        await operator.pre_compute()
        assert operator.value is True

    @pytest.mark.asyncio
    async def test_loop_until_return_remaining_true_branch_single_condition_eval_via_interpreter(
        self,
    ):
        operators = list(dsl_interpreter.get_all_operators())
        operators.append(_LoopUntilSingleEvalTestConditionOperator)
        interpreter_with_test_condition = dsl_interpreter.Interpreter(operators)
        with mock.patch.object(
            _LoopUntilSingleEvalTestConditionOperator,
            "compute",
            mock.Mock(return_value=True),
        ) as mock_condition_compute:
            result = await interpreter_with_test_condition.interprete(
                "loop_until(test_loop_until_single_eval_condition(), 0, max_attempts=10, "
                "return_remaining_time=True)"
            )
        assert result is True
        mock_condition_compute.assert_called_once()

    @pytest.mark.asyncio
    async def test_loop_until_return_remaining_max_attempts_after_wait(self):
        wrapped_previous = {
            dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: {
                dsl_interpreter.ReCallingOperatorResult.__name__: {
                    "last_execution_result": {
                        dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 1000.0,
                        dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value: 2.0,
                        base_resetting_operators.LoopUntilOperator.LOOP_START_TIME_KEY: 990.0,
                        base_resetting_operators.LoopUntilOperator.ATTEMPT_COUNT_KEY: 1,
                    },
                },
            },
        }
        operator = base_resetting_operators.LoopUntilOperator(
            False,
            1,
            max_attempts=2,
            return_remaining_time=True,
            **wrapped_previous,
        )
        with mock.patch.object(base_resetting_operators.time, "time", return_value=1005.0):
            with pytest.raises(octobot_commons.errors.ErrorStatementEncountered, match="max_attempts"):
                await operator.pre_compute()

    @pytest.mark.asyncio
    async def test_loop_until_compute_remaining_retry_wait_no_previous(self):
        operator = base_resetting_operators.LoopUntilOperator(False, 3, max_attempts=5)
        assert operator._compute_remaining_retry_wait(
            1000.0,
            None
        ) is None
