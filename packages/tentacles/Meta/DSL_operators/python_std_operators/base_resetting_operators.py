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
        return self.build_re_callable_result(
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
