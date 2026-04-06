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
import dataclasses
import typing
import time
import enum

import octobot_commons.dataclasses
import octobot_commons.dsl_interpreter.operator_parameter as operator_parameter
import octobot_commons.dsl_interpreter.parameters_util as parameters_util


class ReCallingOperatorResultKeys(str, enum.Enum):
    WAITING_TIME = "waiting_time"
    LAST_EXECUTION_TIME = "last_execution_time"
    SCRIPT_OVERRIDE = "script_override"


@dataclasses.dataclass
class ReCallingOperatorResult(octobot_commons.dataclasses.MinimizableDataclass):
    keyword: typing.Optional[str] = None
    reset_to_id: typing.Optional[str] = None
    last_execution_result: typing.Optional[dict] = None

    @staticmethod
    def is_re_calling_operator_result(result: typing.Any) -> bool:
        """
        Check if the result is a re-calling operator result.
        """
        return isinstance(result, dict) and (
            ReCallingOperatorResult.__name__ in result
        )

    def get_next_call_time(self) -> typing.Optional[float]:
        """
        Returns the next call time based on the last execution result's 
        waiting time and last execution time.
        """
        if (
            self.last_execution_result
            and (waiting_time := self.last_execution_result.get(ReCallingOperatorResultKeys.WAITING_TIME.value))
        ):
            last_execution_time = self.last_execution_result.get(
                ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value
            ) or time.time()
            return last_execution_time + waiting_time
        return None

    @staticmethod
    def get_script_override(result: typing.Any) -> typing.Optional[str]:
        """
        Returns the script override from the last execution result.
        """
        if not ReCallingOperatorResult.is_re_calling_operator_result(result):
            return None
        return result[ReCallingOperatorResult.__name__].get("last_execution_result", {}).get(
            ReCallingOperatorResultKeys.SCRIPT_OVERRIDE.value
        )

    @staticmethod
    def get_keyword(result: typing.Any) -> typing.Optional[str]:
        """
        Returns the keyword from the re-calling operator result.
        """
        return result[ReCallingOperatorResult.__name__]["keyword"]


class ReCallableOperatorMixin:
    """
    Mixin for re-callable operators.
    """
    LAST_EXECUTION_RESULT_KEY = "last_execution_result"

    @classmethod
    def get_re_callable_parameters(cls) -> list[operator_parameter.OperatorParameter]:
        """
        Returns the parameters for the re-callable operator.
        """
        return [
            operator_parameter.OperatorParameter(
                name=cls.LAST_EXECUTION_RESULT_KEY,
                description="the return value of the previous call",
                required=False,
                type=dict,
                default=None,
            ),
        ]

    def get_last_execution_result(
        self, param_by_name: dict[str, typing.Any]
    ) -> typing.Optional[dict]:
        """
        Returns the potential last execution result from param_by_name.
        """
        if (
            (result_dict := param_by_name.get(self.LAST_EXECUTION_RESULT_KEY, None))
            and ReCallingOperatorResult.is_re_calling_operator_result(result_dict)
        ):
            return ReCallingOperatorResult.from_dict(result_dict[
                ReCallingOperatorResult.__name__
            ]).last_execution_result
        return None

    def create_re_callable_result( # pylint: disable=too-many-arguments
        self,
        keyword: str,
        reset_to_id: typing.Optional[str] = None,
        waiting_time: typing.Optional[float] = None,
        last_execution_time: typing.Optional[float] = None,
        script_override: typing.Optional[str] = None,
        **kwargs: typing.Any,
    ) -> ReCallingOperatorResult:
        """
        Builds a re-callable result from the given parameters.
        """
        return ReCallingOperatorResult(
            keyword=keyword,
            reset_to_id=reset_to_id,
            last_execution_result={
                ReCallingOperatorResultKeys.WAITING_TIME.value: waiting_time,
                ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: last_execution_time,
                ReCallingOperatorResultKeys.SCRIPT_OVERRIDE.value: script_override,
                **kwargs,
            },
        )

    def create_re_callable_result_dict( # pylint: disable=too-many-arguments
        self,
        keyword: str,
        reset_to_id: typing.Optional[str] = None,
        waiting_time: typing.Optional[float] = None,
        last_execution_time: typing.Optional[float] = None,
        script_override: typing.Optional[str] = None,
        **kwargs: typing.Any,
    ) -> dict:
        """
        Builds a dict formatted re-callable result from the given parameters.
        """
        return {
            ReCallingOperatorResult.__name__: self.create_re_callable_result(
                keyword=keyword,
                reset_to_id=reset_to_id,
                waiting_time=waiting_time,
                last_execution_time=last_execution_time,
                script_override=script_override,
                **kwargs,
            ).to_dict(include_default_values=False)
        }

    def re_create_script(self, param_by_name: dict[str, typing.Any]):
        """
        Returns the re-created script from the given parameters.
        """
        param_without_re_callable_operator_params = {
            k: v for k, v in param_by_name.items() if k != self.LAST_EXECUTION_RESULT_KEY
        }
        params = parameters_util.resove_operator_params(self, param_without_re_callable_operator_params)
        return f"{self.get_name()}({', '.join(params)})" # type: ignore
