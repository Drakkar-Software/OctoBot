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

import octobot_commons.dsl_interpreter.operators.n_ary_operator as dsl_interpreter_n_ary_operator
import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator


class AndOperator(dsl_interpreter_n_ary_operator.NaryOperator):
    MIN_PARAMS = 1
    MAX_PARAMS = None
    NAME = "and"
    DESCRIPTION = "Logical AND operator. Returns True if all operands are truthy, otherwise returns False."
    EXAMPLE = "True and False"

    @staticmethod
    def get_name() -> str:
        return ast.And.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        operands = self.get_computed_parameters()
        return all(operands)


class OrOperator(dsl_interpreter_n_ary_operator.NaryOperator):
    MIN_PARAMS = 1
    MAX_PARAMS = None
    NAME = "or"
    DESCRIPTION = "Logical OR operator. Returns True if any operand is truthy, otherwise returns False."
    EXAMPLE = "True or False"

    @staticmethod
    def get_name() -> str:
        return ast.Or.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        operands = self.get_computed_parameters()
        return any(operands)
