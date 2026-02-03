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
import pytest

import octobot_commons.constants
import octobot_commons.dsl_interpreter




class BinOperator1(octobot_commons.dsl_interpreter.BinaryOperator):
    @staticmethod
    def get_name() -> str:
        return "b1"

    def compute(self) -> octobot_commons.dsl_interpreter.ComputedOperatorParameterType:
        return 0


class BinOperator2(octobot_commons.dsl_interpreter.BinaryOperator):
    @staticmethod
    def get_name() -> str:
        return "b2"

    def compute(self) -> octobot_commons.dsl_interpreter.ComputedOperatorParameterType:
        return 0


class BinOperator3(octobot_commons.dsl_interpreter.BinaryOperator):
    @staticmethod
    def get_name() -> str:
        return "b3"

    def compute(self) -> octobot_commons.dsl_interpreter.ComputedOperatorParameterType:
        return 0


class UnaryOperator1(octobot_commons.dsl_interpreter.UnaryOperator):
    @staticmethod
    def get_name() -> str:
        return "u1"

    def compute(self) -> octobot_commons.dsl_interpreter.ComputedOperatorParameterType:
        return 0


class UnaryOperator2(octobot_commons.dsl_interpreter.UnaryOperator):
    @staticmethod
    def get_name() -> str:
        return "u2"

    def compute(self) -> octobot_commons.dsl_interpreter.ComputedOperatorParameterType:
        return 0


class ContextualOperator(octobot_commons.dsl_interpreter.CallOperator):
    @staticmethod
    def get_name() -> str:
        return "c1"
    
    @staticmethod
    def get_library() -> str:
        return octobot_commons.constants.CONTEXTUAL_OPERATORS_LIBRARY

    def compute(self) -> octobot_commons.dsl_interpreter.ComputedOperatorParameterType:
        return 0


@pytest.mark.parametrize(
    "libraries", 
    [tuple(), (octobot_commons.constants.BASE_OPERATORS_LIBRARY, )]
)
def test_get_all_operators(libraries):
    assert octobot_commons.dsl_interpreter.get_all_operators(*libraries) is not None
    assert len(octobot_commons.dsl_interpreter.get_all_operators(*libraries)) > 0
    operators = octobot_commons.dsl_interpreter.get_all_operators(*libraries)
    assert ContextualOperator not in operators
    operator_types = [
        octobot_commons.dsl_interpreter.BinaryOperator,
        octobot_commons.dsl_interpreter.UnaryOperator,
    ]
    operator_by_type = {
        operator_type.__name__: [] for operator_type in operator_types
    }
    for operator in operators:
        name = operator.get_name()
        assert len(name) > 0
        for operator_type in operator_types:
            if issubclass(operator, operator_type):
                operator_by_type[operator_type.__name__].append(operator)
                break
    for operator_type, operators in operator_by_type.items():
        assert len(operators) > 1, f"Expected at least 2 {operator_type} operators. {operator_by_type=}"


def test_get_all_operators_unknown_library():
    assert octobot_commons.dsl_interpreter.get_all_operators("unknown_library") == []
    # now include base library as well
    operators = octobot_commons.dsl_interpreter.get_all_operators("base", "unknown_library")
    assert len(operators) > 4
    assert ContextualOperator not in operators


def test_clear_get_all_operators_cache():

    def create_new_operator():
        class NewOperator(octobot_commons.dsl_interpreter.Operator):
            @staticmethod
            def get_name() -> str:
                return "new_operator"
            def compute(self) -> octobot_commons.dsl_interpreter.ComputedOperatorParameterType:
                return 0
        return NewOperator

    first_get_all_operators = octobot_commons.dsl_interpreter.get_all_operators()
    assert len(first_get_all_operators) > 0
    assert octobot_commons.dsl_interpreter.get_all_operators() == first_get_all_operators
    new_operator_class = create_new_operator()
    assert octobot_commons.dsl_interpreter.get_all_operators() == first_get_all_operators
    # new operator should not be in the list: list was cached before the new operator was created
    assert new_operator_class not in first_get_all_operators
    assert ContextualOperator not in first_get_all_operators
    # now clear the cache and check that the new operator is in the list
    octobot_commons.dsl_interpreter.clear_get_all_operators_cache()
    second_get_all_operators = octobot_commons.dsl_interpreter.get_all_operators()
    assert len(second_get_all_operators) == len(first_get_all_operators) + 1
    assert new_operator_class in second_get_all_operators
    assert ContextualOperator not in second_get_all_operators
