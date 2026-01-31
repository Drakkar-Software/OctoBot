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
import ast

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.errors as commons_errors


async def get_x_value_async() -> int:
    return 666


class SumPlusXOperatorWithoutInit(dsl_interpreter.NaryOperator):
    def __init__(self, *parameters: dsl_interpreter.OperatorParameterType, **kwargs: typing.Any):
        super().__init__(*parameters, **kwargs)
        self.x_value = 42
    
    @staticmethod
    def get_name() -> str:
        return "plus_42"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        computed_parameters = self.get_computed_parameters()
        return sum(computed_parameters) + self.x_value


class SumPlusXOperatorWithPreCompute(dsl_interpreter.NaryOperator):
    def __init__(self, *parameters: dsl_interpreter.OperatorParameterType, **kwargs: typing.Any):
        super().__init__(*parameters, **kwargs)
        self.x_value = 42
    
    @staticmethod
    def get_name() -> str:
        return "plus_x"

    @staticmethod
    def get_parameters() -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="data", description="the data to compute the sum of", required=True, type=int),
            dsl_interpreter.OperatorParameter(name="data2", description="the data to compute the sum of", required=False, type=int),
        ]

    async def pre_compute(self) -> None:
        await super().pre_compute()
        self.x_value = await get_x_value_async()

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        computed_parameters = self.get_computed_parameters()
        return sum(computed_parameters) + self.x_value


class TimeFrameToSecondsOperator(dsl_interpreter.CallOperator):
    MIN_PARAMS = 1
    MAX_PARAMS = 1

    def __init__(self, *params, **kwargs: typing.Any):
        super().__init__(*params, **kwargs)

    @staticmethod
    def get_name() -> str:
        return "time_frame_to_seconds"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        computed_parameters = self.get_computed_parameters()
        return commons_enums.TimeFramesMinutes[commons_enums.TimeFrames(computed_parameters[0])] * commons_constants.MINUTE_TO_SECONDS


class AddOperator(dsl_interpreter.BinaryOperator):
    @staticmethod
    def get_name() -> str:
        return ast.Add.__name__

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left + right

class Add2Operator(dsl_interpreter.CallOperator):
    @staticmethod
    def get_name() -> str:
        return "add2"

    @staticmethod
    def get_parameters() -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="left", description="the left operand", required=True, type=int),
            dsl_interpreter.OperatorParameter(name="right", description="the right operand", required=True, type=int),
        ]

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left + right


@pytest.fixture
def interpreter():
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators() + [
            SumPlusXOperatorWithoutInit, SumPlusXOperatorWithPreCompute, TimeFrameToSecondsOperator, AddOperator, Add2Operator
        ]
    )


@pytest.mark.asyncio
async def test_interpreter_basic_operations(interpreter):
    assert await interpreter.interprete("plus_42()") == 42
    assert await interpreter.interprete("plus_42(6)") == 48
    assert await interpreter.interprete("plus_42(1, 2, 3)") == 48
    assert await interpreter.interprete("plus_42(1, 1 + 1, 1.5 +1.5)") == 48
    assert await interpreter.interprete("plus_x(1, 1)") == 668
    assert await interpreter.interprete("10 + (plus_x(1, 1) + plus_x(1, 1))") == 10 + (668 + 668) == 1346
    assert await interpreter.interprete("time_frame_to_seconds('1m')") == 60
    assert await interpreter.interprete("time_frame_to_seconds('1d')") == 86400
    assert await interpreter.interprete("time_frame_to_seconds('1'+'h')") == 3600


@pytest.mark.asyncio
async def test_interpreter_invalid_parameters(interpreter):
    with pytest.raises(commons_errors.InvalidParametersError, match="plus_x requires at least 1 parameter\(s\): 1: data"):
        interpreter.prepare("plus_x()")
    with pytest.raises(commons_errors.InvalidParametersError, match="plus_x requires at least 1 parameter\(s\): 1: data"):
        await interpreter.interprete("plus_x()")
    with pytest.raises(commons_errors.InvalidParametersError, match="add2 requires at least 2 parameter\(s\): 1: left"):
        interpreter.prepare("add2()")
    with pytest.raises(commons_errors.InvalidParametersError, match="add2 requires at least 2 parameter\(s\): 1: left"):
        await interpreter.interprete("add2()")
    with pytest.raises(commons_errors.InvalidParametersError, match="add2 supports up to 2 parameters:"):
        interpreter.prepare("add2(1, 2, 3)")
    with pytest.raises(commons_errors.InvalidParametersError, match="add2 supports up to 2 parameters:"):
        await interpreter.interprete("add2(1, 2, 3)")
    with pytest.raises(commons_errors.InvalidParametersError, match="time_frame_to_seconds requires at least 1 parameter\(s\)"):
        interpreter.prepare("time_frame_to_seconds()")
    with pytest.raises(commons_errors.InvalidParametersError, match="time_frame_to_seconds requires at least 1 parameter\(s\)"):
        await interpreter.interprete("time_frame_to_seconds()")
    with pytest.raises(commons_errors.InvalidParametersError, match="time_frame_to_seconds supports up to 1 parameters"):
        interpreter.prepare("time_frame_to_seconds(1, 2, 3)")
    with pytest.raises(commons_errors.InvalidParametersError, match="time_frame_to_seconds supports up to 1 parameters"):
        await interpreter.interprete("time_frame_to_seconds(1, 2, 3)")


class OperatorWithName(dsl_interpreter.Operator):
    NAME = "custom_name"
    DESCRIPTION = "A custom operator with NAME set"
    EXAMPLE = "custom_name(1, 2)"
    
    @staticmethod
    def get_name() -> str:
        return "fallback_name"
    
    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        return sum(self.get_computed_parameters())


class OperatorWithoutName(dsl_interpreter.Operator):
    DESCRIPTION = "An operator without NAME, uses get_name()"
    EXAMPLE = "fallback_name(5)"
    
    @staticmethod
    def get_name() -> str:
        return "fallback_name"
    
    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        return sum(self.get_computed_parameters())


class OperatorWithParameters(dsl_interpreter.Operator):
    NAME = "param_op"
    DESCRIPTION = "Operator with parameters"
    EXAMPLE = "param_op(1, 2)"
    
    @staticmethod
    def get_name() -> str:
        return "param_op"
    
    @staticmethod
    def get_parameters() -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="x", description="first parameter", required=True, type=int),
            dsl_interpreter.OperatorParameter(name="y", description="second parameter", required=False, type=int),
        ]
    
    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        return sum(self.get_computed_parameters())


class OperatorWithoutParameters(dsl_interpreter.Operator):
    NAME = "no_param_op"
    DESCRIPTION = "Operator without parameters"
    EXAMPLE = "no_param_op()"
    
    @staticmethod
    def get_name() -> str:
        return "no_param_op"
    
    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        return 42


class OperatorWithCustomLibrary(dsl_interpreter.Operator):
    NAME = "custom_lib_op"
    DESCRIPTION = "Operator with custom library"
    EXAMPLE = "custom_lib_op()"
    
    @staticmethod
    def get_name() -> str:
        return "custom_lib_op"
    
    @staticmethod
    def get_library() -> str:
        return "custom_library"
    
    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        return 42


class OperatorWithEmptyFields(dsl_interpreter.Operator):
    # NAME, DESCRIPTION, EXAMPLE all empty/default
    @staticmethod
    def get_name() -> str:
        return "empty_fields_op"
    
    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        return 42


def test_get_docs_with_name_set():
    """Test get_docs() when NAME class attribute is set"""
    docs = OperatorWithName.get_docs()
    assert isinstance(docs, dsl_interpreter.OperatorDocs)
    assert docs.name == "custom_name"  # Should use NAME, not get_name()
    assert docs.description == "A custom operator with NAME set"
    assert docs.type == commons_constants.BASE_OPERATORS_LIBRARY
    assert docs.example == "custom_name(1, 2)"
    assert docs.parameters == []


def test_get_docs_without_name_uses_get_name():
    """Test get_docs() when NAME is not set, should use get_name()"""
    docs = OperatorWithoutName.get_docs()
    assert isinstance(docs, dsl_interpreter.OperatorDocs)
    assert docs.name == "fallback_name"  # Should use get_name() when NAME is empty
    assert docs.description == "An operator without NAME, uses get_name()"
    assert docs.type == commons_constants.BASE_OPERATORS_LIBRARY
    assert docs.example == "fallback_name(5)"
    assert docs.parameters == []


def test_get_docs_with_parameters():
    """Test get_docs() when operator has parameters"""
    docs = OperatorWithParameters.get_docs()
    assert isinstance(docs, dsl_interpreter.OperatorDocs)
    assert docs.name == "param_op"
    assert docs.description == "Operator with parameters"
    assert docs.type == commons_constants.BASE_OPERATORS_LIBRARY
    assert docs.example == "param_op(1, 2)"
    assert len(docs.parameters) == 2
    assert isinstance(docs.parameters[0], dsl_interpreter.OperatorParameter)
    assert docs.parameters[0].name == "x"
    assert docs.parameters[0].description == "first parameter"
    assert docs.parameters[0].required
    assert docs.parameters[0].type == int
    assert isinstance(docs.parameters[1], dsl_interpreter.OperatorParameter)
    assert docs.parameters[1].name == "y"
    assert docs.parameters[1].description == "second parameter"
    assert not docs.parameters[1].required
    assert docs.parameters[1].type == int


def test_get_docs_without_parameters():
    """Test get_docs() when operator has no parameters"""
    docs = OperatorWithoutParameters.get_docs()
    assert docs.name == "no_param_op"
    assert docs.description == "Operator without parameters"
    assert docs.type == commons_constants.BASE_OPERATORS_LIBRARY
    assert docs.example == "no_param_op()"
    assert docs.parameters == []


def test_get_docs_with_custom_library():
    """Test get_docs() when operator has custom library"""
    docs = OperatorWithCustomLibrary.get_docs()
    assert docs.name == "custom_lib_op"
    assert docs.description == "Operator with custom library"
    assert docs.type == "custom_library"  # Should use custom library, not default
    assert docs.example == "custom_lib_op()"
    assert docs.parameters == []


def test_get_docs_with_empty_fields():
    """Test get_docs() when NAME, DESCRIPTION, EXAMPLE are empty"""
    docs = OperatorWithEmptyFields.get_docs()
    assert docs.name == "empty_fields_op"  # Should use get_name()
    assert docs.description == ""  # Empty DESCRIPTION
    assert docs.type == commons_constants.BASE_OPERATORS_LIBRARY
    assert docs.example == ""  # Empty EXAMPLE
    assert docs.parameters == []


def test_get_docs_returns_operator_docs_instance():
    """Test that get_docs() returns an OperatorDocs instance"""
    docs = OperatorWithName.get_docs()
    assert isinstance(docs, dsl_interpreter.OperatorDocs)


def test_get_docs_to_json():
    """Test that the OperatorDocs returned by get_docs() can be serialized to JSON"""
    docs = OperatorWithParameters.get_docs()
    json_data = docs.to_json()
    assert isinstance(json_data, dict)
    assert json_data["name"] == "param_op"
    assert json_data["description"] == "Operator with parameters"
    assert json_data["type"] == commons_constants.BASE_OPERATORS_LIBRARY
    assert json_data["example"] == "param_op(1, 2)"
    assert len(json_data["parameters"]) == 2
    assert json_data["parameters"][0]["name"] == "x"
    assert json_data["parameters"][0]["description"] == "first parameter"
    assert json_data["parameters"][0]["required"] is True
    assert json_data["parameters"][0]["type"] == "int"
    assert json_data["parameters"][1]["name"] == "y"
    assert json_data["parameters"][1]["description"] == "second parameter"
    assert json_data["parameters"][1]["required"] is False
    assert json_data["parameters"][1]["type"] == "int"