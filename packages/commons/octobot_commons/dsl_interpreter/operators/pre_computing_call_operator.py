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
import octobot_commons.errors
import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator
import octobot_commons.dsl_interpreter.operator_parameter as dsl_interpreter_operator_parameter
import octobot_commons.dsl_interpreter.operators.call_operator as dsl_interpreter_call_operator


class PreComputingCallOperator(
    dsl_interpreter_call_operator.CallOperator
):  # pylint: disable=abstract-method
    """
    Base class for pre-computing call operators (function calls).
    Pre-computing call operators are call operators that must be pre-computed before being computed.
    """
    def __init__(self, *parameters: dsl_interpreter_operator.OperatorParameterType, **kwargs: typing.Any):
        super().__init__(*parameters, **kwargs)
        self.value: dsl_interpreter_operator.ComputedOperatorParameterType = dsl_interpreter_operator_parameter.UNINITIALIZED_VALUE # type: ignore
    
    async def pre_compute(self) -> None:
        await super().pre_compute()
        self.value = dsl_interpreter_operator_parameter.UNINITIALIZED_VALUE  # type: ignore

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        if self.value is dsl_interpreter_operator_parameter.UNINITIALIZED_VALUE:
            raise octobot_commons.errors.DSLInterpreterError("{self.__class__.__name__} has not been pre_computed")
        return self.value
