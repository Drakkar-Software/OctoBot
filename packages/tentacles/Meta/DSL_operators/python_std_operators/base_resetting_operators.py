# pylint: disable=missing-class-docstring,missing-function-docstring
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
import typing
import time
import asyncio
import random

import octobot_commons.errors
import octobot_commons.dsl_interpreter as dsl_interpreter


"""
Resetting operators are ReCallableOperatorMixin that can be called multiple times
in order to execute a long lasting operation that can take several steps to complete.
"""


class WaitOperator(dsl_interpreter.PreComputingCallOperator, dsl_interpreter.ReCallableOperatorMixin):
    NAME = "wait"
    DESCRIPTION = "Pauses execution for the specified number of seconds. If return_remaining_time is True, instantly returns the remaining time to wait."
    EXAMPLE = "wait(5)"

    @staticmethod
    def get_name() -> str:
        return "wait"

    @classmethod
    def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="min_seconds", description="minimum number of seconds to wait", required=True, type=float),
            dsl_interpreter.OperatorParameter(name="max_seconds", description="maximum number of seconds to wait", required=False, type=float, default=None),
            dsl_interpreter.OperatorParameter(name="return_remaining_time", description="if True, instantly returns the remaining time to wait", required=False, type=bool, default=False),
        ] + cls.get_re_callable_parameters()

    async def pre_compute(self) -> None:
        await super().pre_compute()
        param_by_name = self.get_computed_value_by_parameter()
        if param_by_name["return_remaining_time"]:
            self.value = self._compute_remaining_time(param_by_name)
        else:
            await asyncio.sleep(self._compute_sleep_time(param_by_name))
            self.value = None

    def _compute_remaining_time(
        self, param_by_name: dict[str, typing.Any]
    ) -> typing.Optional[dict[str, typing.Any]]:
        current_time = time.time()
        if last_execution_result := self.get_last_execution_result(param_by_name):
            last_execution_time = last_execution_result[
                dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value
            ]
            waiting_time = (
                last_execution_result[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value]
                - (current_time - last_execution_time)
            )
        else:
            waiting_time = self._compute_sleep_time(param_by_name)
        if waiting_time <= 0:
            # done waiting
            return None
        return self.create_re_callable_result_dict(
            keyword=self.get_name(),
            last_execution_time=current_time,
            waiting_time=waiting_time,
        )

    def _compute_sleep_time(self, param_by_name: dict[str, typing.Any]) -> float:
        min_seconds = param_by_name["min_seconds"]
        if min_seconds < 0:
            raise octobot_commons.errors.InvalidParametersError(
                f"wait() requires a non-negative numeric argument (seconds), got {min_seconds}"
            )
        max_seconds = param_by_name["max_seconds"]
        if max_seconds is None:
            return min_seconds
        return random.randrange(int(min_seconds) * 1000, int(max_seconds) * 1000) / 1000


class LoopUntilOperator(dsl_interpreter.PreComputingCallOperator, dsl_interpreter.ReCallableOperatorMixin):
    NAME = "loop_until"
    DESCRIPTION = (
        "Re-evaluates a condition after retry_interval until it is true. "
        "Optional timeout and max_attempts stop the loop with ErrorStatementEncountered; "
        "if both are omitted, loops until the condition is true. "
        "Returns the condition value when it becomes true."
    )
    EXAMPLE = "loop_until(x > 0, 1, timeout=30, max_attempts=10)"

    LOOP_START_TIME_KEY = "loop_until_start_time"
    ATTEMPT_COUNT_KEY = "loop_until_attempt_count"

    @staticmethod
    def get_name() -> str:
        return "loop_until"

    @classmethod
    def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(
                name="condition",
                description="expression that must become true",
                required=True,
                type=bool,
            ),
            dsl_interpreter.OperatorParameter(
                name="retry_interval",
                description="seconds to wait between condition checks",
                required=True,
                type=float,
            ),
            dsl_interpreter.OperatorParameter(
                name="timeout",
                description="if set, maximum total seconds; if still false, raises ErrorStatementEncountered",
                required=False,
                type=float,
                default=None,
            ),
            dsl_interpreter.OperatorParameter(
                name="max_attempts",
                description="if set, maximum condition evaluations; if still false, raises ErrorStatementEncountered",
                required=False,
                type=int,
                default=None,
            ),
            dsl_interpreter.OperatorParameter(
                name="return_remaining_time",
                description="if True, instantly returns the remaining time until the next check",
                required=False,
                type=bool,
                default=False,
            ),
        ] + cls.get_re_callable_parameters()

    async def pre_compute(self) -> None:
        await super().pre_compute()
        param_by_name = self.get_computed_value_by_parameter()
        self._validate_loop_until_params(param_by_name)
        if param_by_name["return_remaining_time"]:
            self.value = await self._compute_return_remaining(param_by_name)
        else:
            self.value = await self._run_blocking_loop(param_by_name)

    def _validate_loop_until_params(self, param_by_name: dict[str, typing.Any]) -> None:
        timeout_value = param_by_name["timeout"]
        max_attempts_value = param_by_name["max_attempts"]
        retry_interval = param_by_name["retry_interval"]
        if retry_interval < 0:
            raise octobot_commons.errors.InvalidParametersError(
                f"loop_until() requires a non-negative retry_interval, got {retry_interval}"
            )
        if timeout_value is not None and timeout_value < 0:
            raise octobot_commons.errors.InvalidParametersError(
                f"loop_until() requires a non-negative timeout, got {timeout_value}"
            )
        if max_attempts_value is not None and max_attempts_value < 1:
            raise octobot_commons.errors.InvalidParametersError(
                f"loop_until() requires max_attempts >= 1 when set, got {max_attempts_value}"
            )

    def _extra_loop_state(self, last_execution_result: typing.Optional[dict]) -> dict[str, typing.Any]:
        if not last_execution_result:
            return {}
        skip_keys = {
            dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value,
            dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value,
        }
        return {
            key: value
            for key, value in last_execution_result.items()
            if key not in skip_keys
        }

    def _compute_remaining_retry_wait(
        self, current_time: float, last_execution_result: typing.Optional[dict]
    ) -> typing.Optional[float]:
        if not last_execution_result:
            return None
        last_execution_time = last_execution_result[
            dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value
        ]
        base_waiting_time = last_execution_result[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value]
        waiting_time = base_waiting_time - (current_time - last_execution_time)
        if waiting_time <= 0:
            # reset waiting timee
            return base_waiting_time
        return waiting_time

    def _read_loop_start_and_attempts(
        self,
        last_execution_result: typing.Optional[dict],
        current_time: float,
    ) -> tuple[float, int]:
        if not last_execution_result:
            return current_time, 0
        loop_start = last_execution_result.get(self.LOOP_START_TIME_KEY, current_time)
        attempt_count = last_execution_result.get(self.ATTEMPT_COUNT_KEY, 0)
        return loop_start, attempt_count

    async def _compute_return_remaining(
        self, param_by_name: dict[str, typing.Any]
    ) -> typing.Any:
        current_time = time.time()

        if condition_result := param_by_name.get("condition"):
            return condition_result

        last_execution_result = self.get_last_execution_result(param_by_name)
        loop_start_time, previous_attempt_count = self._read_loop_start_and_attempts(
            last_execution_result, current_time
        )
        attempt_count = previous_attempt_count + 1
        max_attempts = param_by_name.get("max_attempts")
        timeout = param_by_name.get("timeout")

        try:
            remaining_wait = self._compute_remaining_retry_wait(current_time, last_execution_result)
        except KeyError:
            remaining_wait = None
        if remaining_wait is None:
            # this is the first execution: validate the timeout and max_attempts values
            if timeout is not None and (
                current_time - loop_start_time >= timeout
            ):
                raise octobot_commons.errors.MaxAttemptsExceededError(
                    "loop_until: timeout exceeded before condition became true"
                )
            if max_attempts is not None and attempt_count >= max_attempts:
                raise octobot_commons.errors.MaxAttemptsExceededError(
                    "loop_until: max_attempts exceeded before condition became true"
                )
            remaining_wait = float(param_by_name["retry_interval"])
        else:
            # this is not the first execution: check exit conditions
            if timeout is not None and (
                current_time - loop_start_time >= timeout
            ):
                raise octobot_commons.errors.MaxAttemptsExceededError(
                    "loop_until: timeout exceeded before condition became true"
                )
            if (
                max_attempts is not None
                and attempt_count >= max_attempts
            ):
                raise octobot_commons.errors.MaxAttemptsExceededError(
                    "loop_until: max_attempts exceeded before condition became true"
                )

        return self.create_re_callable_result_dict(
            keyword=self.get_name(),
            last_execution_time=current_time,
            waiting_time=remaining_wait,
            **{
                self.LOOP_START_TIME_KEY: loop_start_time,
                self.ATTEMPT_COUNT_KEY: attempt_count,
            },
        )

    async def _evaluate_condition_async(self) -> typing.Any:
        condition_arg = self.get_input_value_by_parameter()["condition"]
        if isinstance(condition_arg, dsl_interpreter.Operator):
            await condition_arg.pre_compute()
            return condition_arg.compute()
        return self._get_computed_parameter(condition_arg)

    async def _run_blocking_loop(
        self, param_by_name: dict[str, typing.Any]
    ) -> typing.Any:
        retry_interval = float(param_by_name["retry_interval"])
        loop_start_time = time.time()
        attempt_count = 0
        while True:
            attempt_count += 1
            condition_result = await self._evaluate_condition_async()
            if bool(condition_result):
                return condition_result
            current_time = time.time()
            if param_by_name["timeout"] is not None and (
                current_time - loop_start_time >= param_by_name["timeout"]
            ):
                raise octobot_commons.errors.ErrorStatementEncountered(
                    "loop_until: timeout exceeded before condition became true"
                )
            if param_by_name["max_attempts"] is not None and attempt_count >= param_by_name["max_attempts"]:
                raise octobot_commons.errors.ErrorStatementEncountered(
                    "loop_until: max_attempts exceeded before condition became true"
                )
            await asyncio.sleep(retry_interval)
