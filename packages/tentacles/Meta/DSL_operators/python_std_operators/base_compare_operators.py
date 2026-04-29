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

import octobot_commons.dsl_interpreter.operators.compare_operator as dsl_interpreter_compare_operator
import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator


class EqOperator(dsl_interpreter_compare_operator.CompareOperator):
    NAME = "=="
    DESCRIPTION = "Equality operator. Returns True if the left operand equals the right operand."
    EXAMPLE = "5 == 5"

    @staticmethod
    def get_name() -> str:
        return ast.Eq.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left == right


class NotEqOperator(dsl_interpreter_compare_operator.CompareOperator):
    NAME = "!="
    DESCRIPTION = "Inequality operator. Returns True if the left operand does not equal the right operand."
    EXAMPLE = "5 != 3"

    @staticmethod
    def get_name() -> str:
        return ast.NotEq.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left != right


class LtOperator(dsl_interpreter_compare_operator.CompareOperator):
    NAME = "<"
    DESCRIPTION = "Less than operator. Returns True if the left operand is less than the right operand."
    EXAMPLE = "3 < 5"

    @staticmethod
    def get_name() -> str:
        return ast.Lt.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left < right


class LtEOperator(dsl_interpreter_compare_operator.CompareOperator):
    NAME = "<="
    DESCRIPTION = "Less than or equal operator. Returns True if the left operand is less than or equal to the right operand."
    EXAMPLE = "5 <= 5"

    @staticmethod
    def get_name() -> str:
        return ast.LtE.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left <= right


class GtOperator(dsl_interpreter_compare_operator.CompareOperator):
    NAME = ">"
    DESCRIPTION = "Greater than operator. Returns True if the left operand is greater than the right operand."
    EXAMPLE = "5 > 3"

    @staticmethod
    def get_name() -> str:
        return ast.Gt.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left > right


class GtEOperator(dsl_interpreter_compare_operator.CompareOperator):
    NAME = ">="
    DESCRIPTION = "Greater than or equal operator. Returns True if the left operand is greater than or equal to the right operand."
    EXAMPLE = "5 >= 5"

    @staticmethod
    def get_name() -> str:
        return ast.GtE.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left >= right


class IsOperator(dsl_interpreter_compare_operator.CompareOperator):
    NAME = "is"
    DESCRIPTION = "Identity operator. Returns True if the left operand is the same object as the right operand."
    EXAMPLE = "x is None"

    @staticmethod
    def get_name() -> str:
        return ast.Is.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left is right


class IsNotOperator(dsl_interpreter_compare_operator.CompareOperator):
    NAME = "is not"
    DESCRIPTION = "Negated identity operator. Returns True if the left operand is not the same object as the right operand."
    EXAMPLE = "x is not None"

    @staticmethod
    def get_name() -> str:
        return ast.IsNot.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left is not right


class InOperator(dsl_interpreter_compare_operator.CompareOperator):
    NAME = "in"
    DESCRIPTION = "Membership operator. Returns True if the left operand is found in the right operand (container)."
    EXAMPLE = "3 in [1, 2, 3]"

    @staticmethod
    def get_name() -> str:
        return ast.In.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left in right


class NotInOperator(dsl_interpreter_compare_operator.CompareOperator):
    NAME = "not in"
    DESCRIPTION = "Negated membership operator. Returns True if the left operand is not found in the right operand (container)."
    EXAMPLE = "4 not in [1, 2, 3]"

    @staticmethod
    def get_name() -> str:
        return ast.NotIn.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left not in right
