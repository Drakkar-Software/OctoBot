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
import re

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

    @classmethod
    def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
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


class SubOperator(dsl_interpreter.BinaryOperator):
    @staticmethod
    def get_name() -> str:
        return ast.Sub.__name__

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left - right


class LtOperator(dsl_interpreter.CompareOperator):
    @staticmethod
    def get_name() -> str:
        return ast.Lt.__name__

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left < right


class LtEOperator(dsl_interpreter.CompareOperator):
    @staticmethod
    def get_name() -> str:
        return ast.LtE.__name__

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left <= right


class GtOperator(dsl_interpreter.CompareOperator):
    @staticmethod
    def get_name() -> str:
        return ast.Gt.__name__

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left > right


class GtEOperator(dsl_interpreter.CompareOperator):
    @staticmethod
    def get_name() -> str:
        return ast.GtE.__name__

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left >= right


class EqOperator(dsl_interpreter.CompareOperator):
    @staticmethod
    def get_name() -> str:
        return ast.Eq.__name__

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left == right


class NotEqOperator(dsl_interpreter.CompareOperator):
    @staticmethod
    def get_name() -> str:
        return ast.NotEq.__name__

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left != right


class IsOperator(dsl_interpreter.CompareOperator):
    @staticmethod
    def get_name() -> str:
        return ast.Is.__name__

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left is right


class IsNotOperator(dsl_interpreter.CompareOperator):
    @staticmethod
    def get_name() -> str:
        return ast.IsNot.__name__

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left is not right


class AndOperator(dsl_interpreter.NaryOperator):
    MIN_PARAMS = 1

    @staticmethod
    def get_name() -> str:
        return ast.And.__name__

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        return all(self.get_computed_parameters())


class OrOperator(dsl_interpreter.NaryOperator):
    MIN_PARAMS = 1

    @staticmethod
    def get_name() -> str:
        return ast.Or.__name__

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        return any(self.get_computed_parameters())

class Add2Operator(dsl_interpreter.CallOperator):
    @staticmethod
    def get_name() -> str:
        return "add2"

    @classmethod
    def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="left", description="the left operand", required=True, type=int),
            dsl_interpreter.OperatorParameter(name="right", description="the right operand", required=True, type=int),
        ]

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left + right

class PreComputeSumOperator(dsl_interpreter.PreComputingCallOperator):
    @staticmethod
    def get_name() -> str:
        return "pre_compute_sum"

    @classmethod
    def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="a", description="first value", required=True, type=int),
            dsl_interpreter.OperatorParameter(name="b", description="second value", required=True, type=int),
        ]

    async def pre_compute(self) -> None:
        await super().pre_compute()
        value_by_parameter = self.get_computed_value_by_parameter()
        self.value = value_by_parameter["a"] + value_by_parameter["b"]


class CallWithDefaultParametersOperator(dsl_interpreter.CallOperator):
    @staticmethod
    def get_name() -> str:
        return "call_with_default_parameters"

    @classmethod
    def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="value1", description="the first value", required=True, type=int),
            dsl_interpreter.OperatorParameter(name="value2", description="the second value", required=False, type=int, default=0),
            dsl_interpreter.OperatorParameter(name="added_extra_value", description="value to add to the result", required=False, type=int, default=0),
            dsl_interpreter.OperatorParameter(name="substracted_extra_value", description="value to substract from the result", required=False, type=int, default=0),
        ]

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        value_by_parameter = self.get_computed_value_by_parameter()
        return (
            value_by_parameter["value1"]
            + value_by_parameter["value2"]
            + value_by_parameter["added_extra_value"]
            - value_by_parameter["substracted_extra_value"]
        )

    
class ParamMerger(dsl_interpreter.CallOperator):
    @staticmethod
    def get_name() -> str:
        return "param_merger"

    @classmethod
    def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="p1", description="the first value", required=True, type=int),
            dsl_interpreter.OperatorParameter(name="p2", description="the second value", required=True, type=int),
        ]

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        value_by_parameter = self.get_computed_value_by_parameter()
        return str(value_by_parameter)


class NestedDictSumOperator(dsl_interpreter.CallOperator):
    @staticmethod
    def get_name() -> str:
        return "nested_dict_sum"

    @classmethod
    def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="values", description="the dictionary to sum the values of", required=True, type=dict),
        ]

    def nested_sum(self, values: dict) -> float:
        return sum(
            self.nested_sum(value) if isinstance(value, dict) else float(value)
            for value in values.values()
        )

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        value_by_parameter = self.get_computed_value_by_parameter()
        return self.nested_sum(value_by_parameter["values"])


@pytest.fixture
def interpreter():
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators() + [
            SumPlusXOperatorWithoutInit, SumPlusXOperatorWithPreCompute, TimeFrameToSecondsOperator,
            AddOperator, SubOperator, Add2Operator, PreComputeSumOperator, CallWithDefaultParametersOperator,
            NestedDictSumOperator, ParamMerger,
            LtOperator, LtEOperator, GtOperator, GtEOperator, EqOperator, NotEqOperator,
            IsOperator, IsNotOperator, AndOperator, OrOperator
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
async def test_interpreter_basic_operations_with_named_parameters(interpreter):
    assert await interpreter.interprete("param_merger(1, 2)") == "{'p1': 1, 'p2': 2}"
    assert await interpreter.interprete("param_merger(1, p2=2)") == "{'p1': 1, 'p2': 2}"
    assert await interpreter.interprete("param_merger(p1=1, p2=2)") == "{'p1': 1, 'p2': 2}"
    assert await interpreter.interprete("param_merger(p2=1, p1=2)") == "{'p1': 2, 'p2': 1}"


@pytest.mark.asyncio
async def test_pre_computing_call_operator(interpreter):
    assert await interpreter.interprete("pre_compute_sum(1, 2)") == 3
    assert await interpreter.interprete("pre_compute_sum(10, 20)") == 30
    assert await interpreter.interprete("pre_compute_sum(1 + 1, 2 + 2)") == 6
    with pytest.raises(commons_errors.DSLInterpreterError, match="has not been pre_computed"):
        operator = PreComputeSumOperator(1, 2)
        operator.compute()


@pytest.mark.asyncio
async def test_interpreter_call_with_default_parameters(interpreter):
    assert await interpreter.interprete("call_with_default_parameters(1)") == 1
    assert await interpreter.interprete("call_with_default_parameters(1, 2)") == 3
    assert await interpreter.interprete("call_with_default_parameters(1, 2, 3)") == 6
    assert await interpreter.interprete("call_with_default_parameters(1, 2, 3, 4)") == 2
    assert await interpreter.interprete("call_with_default_parameters(1, 2, added_extra_value=3)") == 6
    assert await interpreter.interprete("call_with_default_parameters(1, 2, 3, substracted_extra_value=4)") == 2
    assert await interpreter.interprete("call_with_default_parameters(1, 2, substracted_extra_value=3)") == 0
    assert await interpreter.interprete("call_with_default_parameters(1, 2, added_extra_value=4, substracted_extra_value=5)") == 2
    with pytest.raises(commons_errors.InvalidParametersError, match="call_with_default_parameters requires at least 1 parameter"):
        await interpreter.interprete("call_with_default_parameters()")
    with pytest.raises(commons_errors.InvalidParametersError, match="call_with_default_parameters supports up to 4 parameters:"):
        await interpreter.interprete("call_with_default_parameters(1, 2, 3, 4, 5)")
    with pytest.raises(commons_errors.InvalidParametersError, match=re.escape("Parameter(s) 'added_extra_value' have multiple values")):
        await interpreter.interprete("call_with_default_parameters(1, 2, 3, added_extra_value=4)")
    with pytest.raises(commons_errors.InvalidParametersError, match=re.escape("call_with_default_parameters supports up to 4 parameters:")):
        await interpreter.interprete("call_with_default_parameters(1, 2, 3, 4, added_extra_value=5)")


@pytest.mark.asyncio
async def test_interpreter_nested_dict_sum(interpreter):
    assert await interpreter.interprete("nested_dict_sum({})") == 0
    assert await interpreter.interprete("nested_dict_sum({'a': 1})") == 1
    assert await interpreter.interprete("nested_dict_sum({'a': 1 + 1})") == 2
    assert await interpreter.interprete("nested_dict_sum({'a': 1, 'b': 2})") == 3
    assert await interpreter.interprete("nested_dict_sum({'a': 1, 'b': {'c': 2, 'd': 3}})") == 6
    assert await interpreter.interprete("nested_dict_sum({'a': 1, 'b': {'c': 2, 'd': {'e': 3}}})") == 6
    assert await interpreter.interprete("nested_dict_sum({'a': 1, 'b': {'c': 2, 'd': {'e': 3, 'f': {'g': 4}}}})") == 10
    assert await interpreter.interprete("nested_dict_sum({'a': 1, 'b': {'c': 2, 'd': {'e': 3, 'f': {'g': 4, 'h': {'i': 5}}}}})") == 15
    assert await interpreter.interprete("nested_dict_sum({'a': 1, 'b': {'c': 2, 'd': {'e': 3, 'f': {'g': 4, 'h': {'i': 5, 'j': {'k': 6}}}}}})") == 21
    assert await interpreter.interprete("nested_dict_sum({'a': 1, 'b': {'c': 2, 'd': {'e': 3, 'f': {'g': 4, 'h': {'i': 5, 'j': {'k': 6, 'l': {'m': 7}}}}}}})") == 28
    assert await interpreter.interprete("nested_dict_sum({'a': 1, 'b': {'c': 2, 'd': {'e': 3, 'f': {'g': 4, 'h': {'i': 5, 'j': {'k': 6, 'l': {'m': 7, 'n': {'o': 8}}}}}}, 'p': 9 + 0.1}})") == 45.1

@pytest.mark.asyncio
async def test_interpreter_invalid_parameters(interpreter):
    with pytest.raises(commons_errors.InvalidParametersError, match=re.escape("plus_x requires at least 1 parameter(s): 1: data")):
        interpreter.prepare("plus_x()")
    with pytest.raises(commons_errors.InvalidParametersError, match=re.escape("plus_x requires at least 1 parameter(s): 1: data")):
        await interpreter.interprete("plus_x()")
    with pytest.raises(commons_errors.InvalidParametersError, match=re.escape("add2 requires at least 2 parameter(s): 1: left")):
        interpreter.prepare("add2()")
    with pytest.raises(commons_errors.InvalidParametersError, match=re.escape("add2 requires at least 2 parameter(s): 1: left")):
        await interpreter.interprete("add2()")
    with pytest.raises(commons_errors.InvalidParametersError, match="add2 supports up to 2 parameters:"):
        interpreter.prepare("add2(1, 2, 3)")
    with pytest.raises(commons_errors.InvalidParametersError, match="add2 supports up to 2 parameters:"):
        await interpreter.interprete("add2(1, 2, 3)")
    with pytest.raises(commons_errors.InvalidParametersError, match=re.escape("time_frame_to_seconds requires at least 1 parameter(s)")):
        interpreter.prepare("time_frame_to_seconds()")
    with pytest.raises(commons_errors.InvalidParametersError, match=re.escape("time_frame_to_seconds requires at least 1 parameter(s)")):
        await interpreter.interprete("time_frame_to_seconds()")
    with pytest.raises(commons_errors.InvalidParametersError, match="time_frame_to_seconds supports up to 1 parameters"):
        interpreter.prepare("time_frame_to_seconds(1, 2, 3)")
    with pytest.raises(commons_errors.InvalidParametersError, match="time_frame_to_seconds supports up to 1 parameters"):
        await interpreter.interprete("time_frame_to_seconds(1, 2, 3)")


def test_get_input_value_by_parameter():
    # Positional arguments
    operator = ParamMerger(1, 2)
    assert operator.get_input_value_by_parameter() == {"p1": 1, "p2": 2}

    # Keyword arguments
    operator = ParamMerger(p1=10, p2=20)
    assert operator.get_input_value_by_parameter() == {"p1": 10, "p2": 20}

    # Mixed positional and keyword
    operator = ParamMerger(1, p2=2)
    assert operator.get_input_value_by_parameter() == {"p1": 1, "p2": 2}

    # Reversed keyword order
    operator = ParamMerger(p2=100, p1=200)
    assert operator.get_input_value_by_parameter() == {"p1": 200, "p2": 100}

    # Default values for optional parameters
    operator = CallWithDefaultParametersOperator(42)
    assert operator.get_input_value_by_parameter() == {
        "value1": 42,
        "value2": 0,
        "added_extra_value": 0,
        "substracted_extra_value": 0,
    }

    # Nested operator as raw (uncomputed) parameter
    nested_add = AddOperator(1, 2)
    operator = Add2Operator(nested_add, 3)
    value_by_param = operator.get_input_value_by_parameter()
    assert value_by_param["left"] is nested_add
    assert value_by_param["right"] == 3

    # Dict parameter
    operator = NestedDictSumOperator({"a": 1, "b": 2})
    assert operator.get_input_value_by_parameter() == {"values": {"a": 1, "b": 2}}

    # Unknown parameters raise InvalidParametersError
    with pytest.raises(
        commons_errors.InvalidParametersError,
        match=re.escape("Parameter(s) 'unknown_param' are unknown. Supported parameters: p1, p2"),
    ):
        ParamMerger(1, unknown_param=3).get_input_value_by_parameter()
    with pytest.raises(
        commons_errors.InvalidParametersError,
        match=re.escape("param_merger supports up to 2 parameters"),
    ):
        ParamMerger(p1=1, p2=2, extra=99, another=1).get_input_value_by_parameter()


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
    
    @classmethod
    def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
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


@pytest.mark.asyncio
async def test_chained_comparison_two_ops(interpreter):
    # 0 < 5 <= 10 => (0 < 5) and (5 <= 10) => True
    assert await interpreter.interprete("0 < 5 <= 10") is True
    # 0 < 10 <= 10 => (0 < 10) and (10 <= 10) => True
    assert await interpreter.interprete("0 < 10 <= 10") is True
    # 0 < 15 <= 10 => (0 < 15) and (15 <= 10) => False (second fails)
    assert await interpreter.interprete("0 < 15 <= 10") is False
    # 5 < 3 <= 10 => (5 < 3) and (3 <= 10) => False (first fails)
    assert await interpreter.interprete("5 < 3 <= 10") is False
    # both fail: 10 < 5 <= 3
    assert await interpreter.interprete("10 < 5 <= 3") is False


@pytest.mark.asyncio
async def test_chained_comparison_three_ops(interpreter):
    # 1 < 2 < 3 < 4 => all True
    assert await interpreter.interprete("1 < 2 < 3 < 4") is True
    # 1 < 2 < 3 < 3 => last fails (3 < 3 is False)
    assert await interpreter.interprete("1 < 2 < 3 < 3") is False
    # 1 <= 1 <= 1 <= 1 => all True
    assert await interpreter.interprete("1 <= 1 <= 1 <= 1") is True


@pytest.mark.asyncio
async def test_chained_comparison_mixed_operators(interpreter):
    # 0 < 5 >= 3 => (0 < 5) and (5 >= 3) => True
    assert await interpreter.interprete("0 < 5 >= 3") is True
    # 0 < 5 >= 6 => (0 < 5) and (5 >= 6) => False
    assert await interpreter.interprete("0 < 5 >= 6") is False
    # 1 <= 2 > 1 => (1 <= 2) and (2 > 1) => True
    assert await interpreter.interprete("1 <= 2 > 1") is True
    # 1 != 2 < 3 => (1 != 2) and (2 < 3) => True
    assert await interpreter.interprete("1 != 2 < 3") is True
    # 1 == 1 < 2 => (1 == 1) and (1 < 2) => True
    assert await interpreter.interprete("1 == 1 < 2") is True
    # 1 == 1 < 0 => (1 == 1) and (1 < 0) => False
    assert await interpreter.interprete("1 == 1 < 0") is False


@pytest.mark.asyncio
async def test_chained_comparison_with_expressions(interpreter):
    # chained comparison where operands are arithmetic expressions
    # 0 < (2 + 3) <= 10 => 0 < 5 <= 10 => True
    assert await interpreter.interprete("0 < 2 + 3 <= 10") is True
    # 0 < (10 - 3) <= 5 => 0 < 7 <= 5 => False
    assert await interpreter.interprete("0 < 10 - 3 <= 5") is False


@pytest.mark.asyncio
async def test_chained_comparison_with_function_calls(interpreter):
    # plus_42() returns 42 => 0 < 42 <= 100 => True
    assert await interpreter.interprete("0 < plus_42() <= 100") is True
    # 0 < 42 <= 41 => False
    assert await interpreter.interprete("0 < plus_42() <= 41") is False
    # 40 < 42 < 50 => True
    assert await interpreter.interprete("40 < plus_42() < 50") is True
    # middle operand shared: 0 < plus_42() <= plus_42() => 0 < 42 <= 42 => True
    assert await interpreter.interprete("0 < plus_42() <= plus_42()") is True


@pytest.mark.asyncio
async def test_chained_comparison_in_bool_context(interpreter):
    # chained comparison as part of a larger boolean expression
    # (0 < 5 <= 10) and (1 < 2) => True and True => True
    assert await interpreter.interprete("0 < 5 <= 10 and 1 < 2") is True
    # (0 < 15 <= 10) and (1 < 2) => False and True => False
    assert await interpreter.interprete("0 < 15 <= 10 and 1 < 2") is False
    # (0 < 15 <= 10) or (1 < 2) => False or True => True
    assert await interpreter.interprete("0 < 15 <= 10 or 1 < 2") is True


@pytest.mark.asyncio
async def test_chained_comparison_boundary_values(interpreter):
    # exact boundary: 0 < 0 <= 10 => (0 < 0) is False
    assert await interpreter.interprete("0 < 0 <= 10") is False
    # exact boundary: 0 < 10 <= 10 => True
    assert await interpreter.interprete("0 < 10 <= 10") is True
    # negative values via expression: (0 - 5) < 0 < 5 => True
    assert await interpreter.interprete("0 - 5 < 0 < 5") is True
    # float boundaries
    assert await interpreter.interprete("0.0 < 0.5 <= 1.0") is True
    assert await interpreter.interprete("0.0 < 1.0 <= 0.5") is False


@pytest.mark.asyncio
async def test_chained_comparison_without_and_operator_raises(interpreter):
    # create an interpreter without the And operator to verify the error message
    interpreter_no_and = dsl_interpreter.Interpreter([
        LtOperator, LtEOperator,
    ])
    # single comparison still works
    assert await interpreter_no_and.interprete("1 < 2") is True
    # chained comparison requires And and should raise
    with pytest.raises(commons_errors.UnsupportedOperatorError, match="Chained comparisons require the 'And' operator"):
        interpreter_no_and.prepare("0 < 5 <= 10")