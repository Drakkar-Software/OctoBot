# pylint: disable=missing-function-docstring
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

import octobot_commons.dsl_interpreter.operators.iterable_operator as dsl_interpreter_iterable_operator
import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator


class ListOperator(dsl_interpreter_iterable_operator.IterableOperator):
    """
    List operator: [1, 2, 3]
    List operator have one or more operands.
    """
    NAME = "[...]"
    DESCRIPTION = "List constructor operator. Creates a list from the given operands."
    EXAMPLE = "[1, 2, 3]"

    @staticmethod
    def get_name() -> str:
        return ast.List.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        # Compute the test condition
        return list(self.get_computed_parameters())
