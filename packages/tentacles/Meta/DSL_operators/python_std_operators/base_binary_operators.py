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
import ast

import octobot_commons.dsl_interpreter.operators.binary_operator as dsl_interpreter_binary_operator
import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator


class AddOperator(dsl_interpreter_binary_operator.BinaryOperator):
    NAME = "+"
    DESCRIPTION = "Addition operator. Adds two operands together."
    EXAMPLE = "5 + 3"

    @staticmethod
    def get_name() -> str:
        return ast.Add.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left + right


class SubOperator(dsl_interpreter_binary_operator.BinaryOperator):
    NAME = "-"
    DESCRIPTION = "Subtraction operator. Subtracts the right operand from the left operand."
    EXAMPLE = "5 - 3"

    @staticmethod
    def get_name() -> str:
        return ast.Sub.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left - right


class MultOperator(dsl_interpreter_binary_operator.BinaryOperator):
    NAME = "*"
    DESCRIPTION = "Multiplication operator. Multiplies two operands."
    EXAMPLE = "5 * 3"

    @staticmethod
    def get_name() -> str:
        return ast.Mult.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left * right


class DivOperator(dsl_interpreter_binary_operator.BinaryOperator):
    NAME = "/"
    DESCRIPTION = "Division operator. Divides the left operand by the right operand."
    EXAMPLE = "10 / 2"

    @staticmethod
    def get_name() -> str:
        return ast.Div.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left / right


class FloorDivOperator(dsl_interpreter_binary_operator.BinaryOperator):
    NAME = "//"
    DESCRIPTION = "Floor division operator. Divides the left operand by the right operand and returns the floor of the result."
    EXAMPLE = "10 // 3"

    @staticmethod
    def get_name() -> str:
        return ast.FloorDiv.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left // right


class ModOperator(dsl_interpreter_binary_operator.BinaryOperator):
    NAME = "%"
    DESCRIPTION = "Modulo operator. Returns the remainder after dividing the left operand by the right operand."
    EXAMPLE = "10 % 3"

    @staticmethod
    def get_name() -> str:
        return ast.Mod.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left % right


class PowOperator(dsl_interpreter_binary_operator.BinaryOperator):
    NAME = "**"
    DESCRIPTION = "Exponentiation operator. Raises the left operand to the power of the right operand."
    EXAMPLE = "2 ** 3"

    @staticmethod
    def get_name() -> str:
        return ast.Pow.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left**right
