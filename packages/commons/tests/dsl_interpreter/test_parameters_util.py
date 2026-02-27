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
import mock
import pytest

import octobot_commons.dsl_interpreter.parameters_util as parameters_util
import octobot_commons.dsl_interpreter.operator_parameter as operator_parameter
import octobot_commons.errors as commons_errors


class TestFormatParameterValue:
    def test_none(self):
        assert parameters_util.format_parameter_value(None) == "None"

    def test_true(self):
        assert parameters_util.format_parameter_value(True) == "True"

    def test_false(self):
        assert parameters_util.format_parameter_value(False) == "False"

    def test_int(self):
        assert parameters_util.format_parameter_value(42) == "42"
        assert parameters_util.format_parameter_value(-10) == "-10"

    def test_float(self):
        assert parameters_util.format_parameter_value(3.14) == "3.14"
        assert parameters_util.format_parameter_value(1.0) == "1.0"

    def test_plain_string(self):
        assert parameters_util.format_parameter_value("hello") == "'hello'"
        assert parameters_util.format_parameter_value("") == "''"

    def test_string_json_list(self):
        assert parameters_util.format_parameter_value("[1, 2, 3]") == "[1, 2, 3]"

    def test_string_json_dict(self):
        assert parameters_util.format_parameter_value('{"a": 1}') == "{'a': 1}"

    def test_string_invalid_json(self):
        assert parameters_util.format_parameter_value("not valid json") == "'not valid json'"

    def test_list(self):
        assert parameters_util.format_parameter_value([1, 2, 3]) == "[1, 2, 3]"
        assert parameters_util.format_parameter_value([]) == "[]"

    def test_dict(self):
        assert parameters_util.format_parameter_value({"a": 1}) == "{'a': 1}"
        assert parameters_util.format_parameter_value({}) == "{}"

    def test_other_type_uses_repr(self):
        class Custom:
            def __repr__(self):
                return "Custom()"
        assert parameters_util.format_parameter_value(Custom()) == "Custom()"


class TestResoveOperatorParams:
    def test_empty_params_and_empty_values(self):
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = []
        result = parameters_util.resove_operator_params(operator_class, {})
        assert result == []

    def test_required_params_only(self):
        param_a = operator_parameter.OperatorParameter(
            name="a", description="first", required=True, type=int
        )
        param_b = operator_parameter.OperatorParameter(
            name="b", description="second", required=True, type=str
        )
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = [param_a, param_b]
        param_value_by_name = {"a": 1, "b": "hello"}
        result = parameters_util.resove_operator_params(operator_class, param_value_by_name)
        assert result == ["1", "'hello'"]

    def test_optional_params_only(self):
        param_x = operator_parameter.OperatorParameter(
            name="x", description="optional", required=False, type=int
        )
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = [param_x]
        param_value_by_name = {"x": 99}
        result = parameters_util.resove_operator_params(operator_class, param_value_by_name)
        assert result == ["x=99"]

    def test_mixed_required_and_optional(self):
        param_req = operator_parameter.OperatorParameter(
            name="req", description="required", required=True, type=int
        )
        param_opt = operator_parameter.OperatorParameter(
            name="opt", description="optional", required=False, type=str
        )
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = [param_req, param_opt]
        param_value_by_name = {"req": 42, "opt": "value"}
        result = parameters_util.resove_operator_params(operator_class, param_value_by_name)
        assert result == ["42", "opt='value'"]

    def test_skips_missing_params(self):
        param_req = operator_parameter.OperatorParameter(
            name="req", description="required", required=True, type=int
        )
        param_opt = operator_parameter.OperatorParameter(
            name="opt", description="optional", required=False, type=str
        )
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = [param_req, param_opt]
        param_value_by_name = {"req": 1}
        result = parameters_util.resove_operator_params(operator_class, param_value_by_name)
        assert result == ["1"]

    def test_extra_values_ignored(self):
        param_a = operator_parameter.OperatorParameter(
            name="a", description="first", required=True, type=int
        )
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = [param_a]
        param_value_by_name = {"a": 1, "unknown": "ignored"}
        result = parameters_util.resove_operator_params(operator_class, param_value_by_name)
        assert result == ["1"]


class TestResolveOperatorArgsAndKwargs:
    def test_empty_params_returns_unchanged(self):
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = []
        args, kwargs = parameters_util.resolve_operator_args_and_kwargs(
            operator_class, [1, 2], {"extra": "val"}
        )
        assert args == [1, 2]
        assert kwargs == {"extra": "val"}

    def test_positional_args_only(self):
        param_a = operator_parameter.OperatorParameter(
            name="a", description="first", required=True, type=int
        )
        param_b = operator_parameter.OperatorParameter(
            name="b", description="second", required=True, type=int
        )
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = [param_a, param_b]
        args, kwargs = parameters_util.resolve_operator_args_and_kwargs(
            operator_class, [1, 2], {}
        )
        assert args == [1, 2]
        assert kwargs == {}

    def test_positional_arg_as_keyword_arg(self):
        param_a = operator_parameter.OperatorParameter(
            name="a", description="first", required=True, type=int
        )
        param_b = operator_parameter.OperatorParameter(
            name="b", description="second", required=True, type=int
        )
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = [param_a, param_b]
        args, kwargs = parameters_util.resolve_operator_args_and_kwargs(
            operator_class, [1], {"b": 3}
        )
        assert args == [1, 3]
        assert kwargs == {}

    def test_positional_arg_as_keyword_arg_in_a_wrong_order(self):
        param_a = operator_parameter.OperatorParameter(
            name="a", description="first", required=True, type=int
        )
        param_b = operator_parameter.OperatorParameter(
            name="b", description="second", required=True, type=int
        )
        param_c = operator_parameter.OperatorParameter(
            name="c", description="third", required=True, type=int
        )
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = [param_a, param_b, param_c]
        args, kwargs = parameters_util.resolve_operator_args_and_kwargs(
            operator_class, [1], {"c": 3, "b": 2}
        )
        assert args == [1, 2, 3]
        assert kwargs == {}

    def test_positional_all_args_as_keywords_in_a_wrong_order(self):
        param_a = operator_parameter.OperatorParameter(
            name="a", description="first", required=True, type=int
        )
        param_b = operator_parameter.OperatorParameter(
            name="b", description="second", required=True, type=int
        )
        param_c = operator_parameter.OperatorParameter(
            name="c", description="third", required=True, type=int
        )
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = [param_a, param_b, param_c]
        args, kwargs = parameters_util.resolve_operator_args_and_kwargs(
            operator_class, [], {"b": 2, "a": 1, "c": 3}
        )
        assert args == [1, 2, 3]
        assert kwargs == {}

    def test_kwargs_only(self):
        param_a = operator_parameter.OperatorParameter(
            name="a", description="first", required=True, type=int
        )
        param_b = operator_parameter.OperatorParameter(
            name="b", description="second", required=True, type=int
        )
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = [param_a, param_b]
        args, kwargs = parameters_util.resolve_operator_args_and_kwargs(
            operator_class, [], {"a": 1, "b": 2}
        )
        assert args == [1, 2]
        assert kwargs == {}

    def test_mixed_args_and_kwargs(self):
        param_a = operator_parameter.OperatorParameter(
            name="a", description="first", required=True, type=int
        )
        param_b = operator_parameter.OperatorParameter(
            name="b", description="second", required=True, type=int
        )
        param_c = operator_parameter.OperatorParameter(
            name="c", description="optional", required=False, type=int
        )
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = [param_a, param_b, param_c]
        args, kwargs = parameters_util.resolve_operator_args_and_kwargs(
            operator_class, [1], {"b": 2, "c": 3}
        )
        assert args == [1, 2, 3]
        assert kwargs == {}

    def test_extra_kwargs_preserved(self):
        param_a = operator_parameter.OperatorParameter(
            name="a", description="first", required=True, type=int
        )
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = [param_a]
        args, kwargs = parameters_util.resolve_operator_args_and_kwargs(
            operator_class, [1], {"other": "value"}
        )
        assert args == [1]
        assert kwargs == {"other": "value"}

    def test_raises_when_too_many_positional_args(self):
        param_a = operator_parameter.OperatorParameter(
            name="a", description="first", required=True, type=int
        )
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = [param_a]
        operator_class.get_name.return_value = "test_op"
        operator_class.get_parameters_description.return_value = "1: a [int] - first"
        with pytest.raises(commons_errors.InvalidParametersError, match="test_op supports up to 1 parameters"):
            parameters_util.resolve_operator_args_and_kwargs(
                operator_class, [1, 2, 3], {}
            )

    def test_partial_params_allowed(self):
        param_a = operator_parameter.OperatorParameter(
            name="a", description="first", required=True, type=int
        )
        param_b = operator_parameter.OperatorParameter(
            name="b", description="second", required=False, type=int
        )
        operator_class = mock.Mock()
        operator_class.get_parameters.return_value = [param_a, param_b]
        args, kwargs = parameters_util.resolve_operator_args_and_kwargs(
            operator_class, [1], {}
        )
        assert args == [1]
        assert kwargs == {}
