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
import time

import octobot_commons.errors
import octobot_commons.dsl_interpreter as dsl_interpreter


class MinOperator(dsl_interpreter.CallOperator):
    MIN_PARAMS = 1
    NAME = "min"
    DESCRIPTION = "Returns the minimum value from the given operands."
    EXAMPLE = "min(1, 2, 3)"

    @staticmethod
    def get_name() -> str:
        return "min"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        operands = self.get_computed_parameters()
        return min(operands)


class MaxOperator(dsl_interpreter.CallOperator):
    MIN_PARAMS = 1
    NAME = "max"
    DESCRIPTION = "Returns the maximum value from the given operands."
    EXAMPLE = "max(1, 2, 3)"

    @staticmethod
    def get_name() -> str:
        return "max"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        operands = self.get_computed_parameters()
        return max(operands)


class MeanOperator(dsl_interpreter.CallOperator):
    MIN_PARAMS = 1
    NAME = "mean"
    DESCRIPTION = "Returns the arithmetic mean (average) of the given numeric operands."
    EXAMPLE = "mean(1, 2, 3, 4)"

    @staticmethod
    def get_name() -> str:
        return "mean"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        operands = self.get_computed_parameters()
        # Ensure all operands are numeric
        numeric_operands = []
        for operand in operands:
            if isinstance(operand, (int, float)):
                numeric_operands.append(operand)
            else:
                raise octobot_commons.errors.InvalidParametersError(
                    f"mean() requires numeric arguments, got {type(operand).__name__}"
                )
        return sum(numeric_operands) / len(numeric_operands)


class SqrtOperator(dsl_interpreter.CallOperator):
    MIN_PARAMS = 1
    MAX_PARAMS = 1
    NAME = "sqrt"
    DESCRIPTION = "Returns the square root of the given numeric operand."
    EXAMPLE = "sqrt(16)"

    @staticmethod
    def get_name() -> str:
        return "sqrt"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        computed_parameters = self.get_computed_parameters()
        operand = computed_parameters[0]
        if isinstance(operand, (int, float)):
            return math.sqrt(operand)
        raise octobot_commons.errors.InvalidParametersError(
            f"sqrt() requires a numeric argument, got {type(operand).__name__}"
        )


class AbsOperator(dsl_interpreter.CallOperator):
    MIN_PARAMS = 1
    MAX_PARAMS = 1
    NAME = "abs"
    DESCRIPTION = "Returns the absolute value of the given operand."
    EXAMPLE = "abs(-5)"

    @staticmethod
    def get_name() -> str:
        return "abs"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        computed_parameters = self.get_computed_parameters()
        operand = computed_parameters[0]
        return abs(operand)


class RoundOperator(dsl_interpreter.CallOperator):
    NAME = "round"
    DESCRIPTION = "Rounds the given numeric value to the specified number of decimal digits. If digits is not provided, rounds to the nearest integer."
    EXAMPLE = "round(3.14159, 2)"

    @staticmethod
    def get_name() -> str:
        return "round"

    @staticmethod
    def get_parameters() -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="value", description="the value to round", required=True, type=list),
            dsl_interpreter.OperatorParameter(name="digits", description="the number of digits to round to", required=False, type=int),
        ]

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        computed_parameters = self.get_computed_parameters()
        operand = computed_parameters[0]
        digits = int(computed_parameters[1]) if len(computed_parameters) == 2 else 0
        if isinstance(operand, (int, float)):
            return round(operand, digits)
        raise octobot_commons.errors.InvalidParametersError(
            f"round() requires a numeric argument, got {type(operand).__name__}"
        )


class FloorOperator(dsl_interpreter.CallOperator):
    MIN_PARAMS = 1
    MAX_PARAMS = 1
    NAME = "floor"
    DESCRIPTION = "Returns the floor of the given numeric operand (largest integer less than or equal to the value)."
    EXAMPLE = "floor(3.7)"

    @staticmethod
    def get_name() -> str:
        return "floor"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        computed_parameters = self.get_computed_parameters()
        operand = computed_parameters[0]
        if isinstance(operand, (int, float)):
            return math.floor(operand)
        raise octobot_commons.errors.InvalidParametersError(
            f"floor() requires a numeric argument, got {type(operand).__name__}"
        )


class CeilOperator(dsl_interpreter.CallOperator):
    MIN_PARAMS = 1
    MAX_PARAMS = 1
    NAME = "ceil"
    DESCRIPTION = "Returns the ceiling of the given numeric operand (smallest integer greater than or equal to the value)."
    EXAMPLE = "ceil(3.2)"

    @staticmethod
    def get_name() -> str:
        return "ceil"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        computed_parameters = self.get_computed_parameters()
        operand = computed_parameters[0]
        if isinstance(operand, (int, float)):
            return math.ceil(operand)
        raise octobot_commons.errors.InvalidParametersError(
            f"ceil() requires a numeric argument, got {type(operand).__name__}"
        )


class SinOperator(dsl_interpreter.CallOperator):
    MIN_PARAMS = 1
    MAX_PARAMS = 1
    NAME = "sin"
    DESCRIPTION = "Returns the sine of the given numeric operand (in radians)."
    EXAMPLE = "sin(1.23)"

    @staticmethod
    def get_name() -> str:
        return "sin"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        computed_parameters = self.get_computed_parameters()
        operand = computed_parameters[0]
        if isinstance(operand, (int, float)):
            return math.sin(operand)
        raise octobot_commons.errors.InvalidParametersError(
            f"sin() requires a numeric argument, got {type(operand).__name__}"
        )


class CosOperator(dsl_interpreter.CallOperator):
    MIN_PARAMS = 1
    MAX_PARAMS = 1
    NAME = "cos"
    DESCRIPTION = "Returns the cosine of the given numeric operand (in radians)."
    EXAMPLE = "cos(1.23)"

    @staticmethod
    def get_name() -> str:
        return "cos"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        computed_parameters = self.get_computed_parameters()
        operand = computed_parameters[0]
        if isinstance(operand, (int, float)):
            return math.cos(operand)
        raise octobot_commons.errors.InvalidParametersError(
            f"cos() requires a numeric argument, got {type(operand).__name__}"
        )


class OscillatorOperator(dsl_interpreter.CallOperator):
    MIN_PARAMS = 3
    MAX_PARAMS = 3
    NAME = "oscillate"
    DESCRIPTION = "Returns the base value with a time-based oscillating component added. The oscillation uses a sine wave with the specified maximum percentage of the base value and period in minutes."
    EXAMPLE = "oscillate(100, 10, 60)"

    @staticmethod
    def get_name() -> str:
        return "oscillate"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        computed_parameters = self.get_computed_parameters()
        base_value = computed_parameters[0]
        max_oscillating_percent = computed_parameters[1]
        period_minutes = computed_parameters[2]

        # Validate all parameters are numeric
        if not isinstance(base_value, (int, float)):
            raise octobot_commons.errors.InvalidParametersError(
                f"oscillate() requires a numeric base value, got {type(base_value).__name__}"
            )
        if not isinstance(max_oscillating_percent, (int, float)):
            raise octobot_commons.errors.InvalidParametersError(
                f"oscillate() requires a numeric max oscillating percent, got {type(max_oscillating_percent).__name__}"
            )
        if not isinstance(period_minutes, (int, float)) or period_minutes <= 0:
            raise octobot_commons.errors.InvalidParametersError(
                f"oscillate() requires a positive numeric period in minutes, got {type(period_minutes).__name__}"
            )

        oscillation_range = base_value * (max_oscillating_percent / 100)
        period_seconds = period_minutes * 60
        phase = 2 * math.pi * (time.time() / period_seconds)
        oscillation = math.sin(phase)
        oscillation_value = oscillation_range * oscillation

        return base_value + oscillation_value
