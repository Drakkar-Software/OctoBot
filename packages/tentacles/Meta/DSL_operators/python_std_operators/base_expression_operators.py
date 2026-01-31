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

import octobot_commons.dsl_interpreter.operators.expression_operator as dsl_interpreter_expression_operator
import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator


class IfExpOperator(dsl_interpreter_expression_operator.ExpressionOperator):
    """
    Base class for if expression operators: a if b else c
    If expression operators have three operands: condition, true expression, false expression.
    """
    NAME = "if ... else"
    DESCRIPTION = "Conditional expression operator. Returns the body expression if the test condition is True, otherwise returns the orelse expression."
    EXAMPLE = "5 if True else 3"

    def __init__(
        self,
        test: dsl_interpreter_operator.OperatorParameterType,
        body: dsl_interpreter_operator.OperatorParameterType,
        orelse: dsl_interpreter_operator.OperatorParameterType,
    ):
        super().__init__(test, body, orelse)
        self.test = test
        self.body = body
        self.orelse = orelse

    @staticmethod
    def get_name() -> str:
        return ast.IfExp.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        # Compute the test condition
        test_value = (
            self.test.compute()
            if isinstance(self.test, dsl_interpreter_operator.Operator)
            else self.test
        )
        # Evaluate the condition (truthy check)
        if test_value:
            # Return body if condition is True
            return (
                self.body.compute()
                if isinstance(self.body, dsl_interpreter_operator.Operator)
                else self.body
            )
        # Return orelse if condition is False
        return (
            self.orelse.compute()
            if isinstance(self.orelse, dsl_interpreter_operator.Operator)
            else self.orelse
        )
