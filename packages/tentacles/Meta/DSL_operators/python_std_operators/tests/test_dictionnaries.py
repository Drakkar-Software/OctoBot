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


@pytest.mark.parametrize(
    "libraries", 
    [tuple(), (octobot_commons.constants.BASE_OPERATORS_LIBRARY, )]
)
def test_get_all_operators(libraries):
    assert octobot_commons.dsl_interpreter.get_all_operators(*libraries) is not None
    assert len(octobot_commons.dsl_interpreter.get_all_operators(*libraries)) > 0
    operators = octobot_commons.dsl_interpreter.get_all_operators(*libraries)
    operator_types = [
        octobot_commons.dsl_interpreter.BinaryOperator,
        octobot_commons.dsl_interpreter.UnaryOperator,
        octobot_commons.dsl_interpreter.CompareOperator,
        octobot_commons.dsl_interpreter.NaryOperator,
        octobot_commons.dsl_interpreter.CallOperator,
        octobot_commons.dsl_interpreter.NameOperator,
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
