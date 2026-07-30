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
import math

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.dsl_interpreter.operators.name_operator as dsl_interpreter_name_operator
import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator


class PiOperator(dsl_interpreter_name_operator.NameOperator):
    MAX_PARAMS = 0
    NAME = "pi"
    DESCRIPTION = "Mathematical constant pi (π), approximately 3.14159."
    EXAMPLE = "pi"
    CATEGORY = commons_enums.DslKeywordCategory.SOURCE.value

    @staticmethod
    def get_name() -> str:
        return "pi"

    @classmethod
    def get_return_values(cls) -> list[dsl_interpreter.OperatorParameter]:
        return cls.result_return_value(
            commons_enums.DslValueType.NUMBER.value,
            description="Mathematical constant pi",
        )

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        return math.pi


class NaNOperator(dsl_interpreter_name_operator.NameOperator):
    MAX_PARAMS = 0
    NAME = "nan"
    DESCRIPTION = "Not a Number constant. Represents an undefined or unrepresentable numeric value."
    EXAMPLE = "nan"
    CATEGORY = commons_enums.DslKeywordCategory.SOURCE.value

    @staticmethod
    def get_name() -> str:
        return "nan"

    @classmethod
    def get_return_values(cls) -> list[dsl_interpreter.OperatorParameter]:
        return cls.result_return_value(
            commons_enums.DslValueType.NUMBER.value,
            description="Not a Number (NaN)",
        )

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        return float("nan")
