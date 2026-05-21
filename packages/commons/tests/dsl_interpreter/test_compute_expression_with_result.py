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
import typing

import pytest

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.errors as commons_errors


class TestDSLCallResult:
    def test_error_message_defaults_to_none(self):
        call_result = dsl_interpreter.DSLCallResult(statement="ok", result=1)
        assert call_result.error_message is None
        assert call_result.succeeded()

    def test_success_has_no_error_fields(self):
        call_result = dsl_interpreter.DSLCallResult(statement="1 + 1", result=2)
        assert call_result.error is None
        assert call_result.error_message is None


class ErrorRaisingTestOperator(dsl_interpreter.CallOperator):
    @staticmethod
    def get_name() -> str:
        return "test_error"

    def compute(self):
        params = self.get_computed_parameters()
        raise commons_errors.ErrorStatementEncountered(*params)


class SumPlusFortyTwoOperator(dsl_interpreter.NaryOperator):
    def __init__(self, *parameters: dsl_interpreter.OperatorParameterType, **kwargs: typing.Any):
        super().__init__(*parameters, **kwargs)
        self.added_value = 42

    @staticmethod
    def get_name() -> str:
        return "plus_42"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        computed_parameters = self.get_computed_parameters()
        return sum(computed_parameters) + self.added_value


@pytest.fixture
def interpreter_with_test_error():
    interpreter = dsl_interpreter.Interpreter(dsl_interpreter.get_all_operators())
    interpreter.extend([ErrorRaisingTestOperator, SumPlusFortyTwoOperator])
    return interpreter


class TestComputeExpressionWithResult:
    @pytest.mark.asyncio
    async def test_single_argument_error(self, interpreter_with_test_error):
        interpreter_with_test_error.prepare("test_error('code-a')")
        call_result = await interpreter_with_test_error.compute_expression_with_result()
        assert not call_result.succeeded()
        assert call_result.error == "code-a"
        assert call_result.error_message == "code-a"

    @pytest.mark.asyncio
    async def test_status_and_detail_error(self, interpreter_with_test_error):
        interpreter_with_test_error.prepare("test_error('code-b', 'detail text')")
        call_result = await interpreter_with_test_error.compute_expression_with_result()
        assert not call_result.succeeded()
        assert call_result.error == "code-b"
        assert call_result.error_message == "detail text"

    @pytest.mark.asyncio
    async def test_multiple_detail_parts_joined(self, interpreter_with_test_error):
        interpreter_with_test_error.prepare("test_error('code-b', 'part1', 'part2')")
        call_result = await interpreter_with_test_error.compute_expression_with_result()
        assert call_result.error == "code-b"
        assert call_result.error_message == "part1, part2"

    @pytest.mark.asyncio
    async def test_success_has_no_error_message(self, interpreter_with_test_error):
        interpreter_with_test_error.prepare("plus_42()")
        call_result = await interpreter_with_test_error.compute_expression_with_result()
        assert call_result.succeeded()
        assert call_result.error_message is None
        assert call_result.result == 42
