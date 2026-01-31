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

import octobot_commons.dsl_interpreter.operators.unary_operator as dsl_interpreter_unary_operator
import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator


class UAddOperator(dsl_interpreter_unary_operator.UnaryOperator):
    NAME = "+"
    DESCRIPTION = "Unary plus operator. Returns the operand unchanged (mainly for symmetry with unary minus)."
    EXAMPLE = "+5"

    @staticmethod
    def get_name() -> str:
        return ast.UAdd.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        operand = self.get_computed_operand()
        return +operand


class USubOperator(dsl_interpreter_unary_operator.UnaryOperator):
    NAME = "-"
    DESCRIPTION = "Unary minus operator. Negates the operand (multiplies by -1)."
    EXAMPLE = "-5"

    @staticmethod
    def get_name() -> str:
        return ast.USub.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        operand = self.get_computed_operand()
        return -operand


class NotOperator(dsl_interpreter_unary_operator.UnaryOperator):
    NAME = "not"
    DESCRIPTION = "Logical NOT operator. Returns True if the operand is falsy, False if it is truthy."
    EXAMPLE = "not True"

    @staticmethod
    def get_name() -> str:
        return ast.Not.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        operand = self.get_computed_operand()
        return not operand


class InvertOperator(dsl_interpreter_unary_operator.UnaryOperator):
    NAME = "~"
    DESCRIPTION = "Bitwise NOT operator. Inverts all bits of the operand. In this implementation, it behaves as logical NOT."
    EXAMPLE = "~True"

    @staticmethod
    def get_name() -> str:
        return ast.Invert.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        operand = self.get_computed_operand()
        return not operand  # ~operand has been deprecated in favor of "not"
        # return ~operand
