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

import pytest

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.errors


class AddOperator(dsl_interpreter.BinaryOperator):
    @staticmethod
    def get_name() -> str:
        return ast.Add.__name__

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left + right


class NestedEchoOperator(
    dsl_interpreter.CallOperator,
    dsl_interpreter.NestedInterpretationMixin,
):
    @staticmethod
    def get_name() -> str:
        return "nested_echo"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        return "unused"


@pytest.fixture
def interpreter():
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators() + [AddOperator]
    )


def test_operator_receives_interpreter_on_instantiation(interpreter):
    interpreter.prepare("1 + (2 + 3)")
    top_operator = interpreter.get_top_operator()
    assert isinstance(top_operator, AddOperator)
    assert top_operator.interpreter is interpreter
    inner_add = top_operator.parameters[1]
    assert isinstance(inner_add, AddOperator)
    assert inner_add.interpreter is interpreter


def test_create_nested_reuses_operator_classes(interpreter):
    interpreter.extend([NestedEchoOperator])
    nested_interpreter = interpreter.create_nested()
    assert set(nested_interpreter.operators_by_name.keys()) == set(
        interpreter.operators_by_name.keys()
    )
    assert nested_interpreter is not interpreter


@pytest.mark.asyncio
async def test_interprete_nested_raises_without_interpreter():
    operator = NestedEchoOperator()
    with pytest.raises(octobot_commons.errors.DSLInterpreterError, match="no parent interpreter"):
        await operator.interprete_in_nested_interpreter("1 + 1")
