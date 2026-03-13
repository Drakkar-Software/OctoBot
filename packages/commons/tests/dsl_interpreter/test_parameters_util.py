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

import octobot_commons.constants as constants
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


class TestApplyResolvedParameterValue:
    def test_replaces_single_parameter_with_int(self):
        script = f"op(x=1, y={constants.UNRESOLVED_PARAMETER_PLACEHOLDER})"
        result = parameters_util.apply_resolved_parameter_value(script, "y", 42)
        assert result == "op(x=1, y=42)"

    def test_replaces_single_parameter_with_string(self):
        script = f"op(name={constants.UNRESOLVED_PARAMETER_PLACEHOLDER})"
        result = parameters_util.apply_resolved_parameter_value(script, "name", "hello")
        assert result == "op(name='hello')"

    def test_replaces_single_parameter_with_bool(self):
        script = f"op(flag={constants.UNRESOLVED_PARAMETER_PLACEHOLDER})"
        result = parameters_util.apply_resolved_parameter_value(script, "flag", True)
        assert result == "op(flag=True)"

    def test_replaces_single_parameter_with_list(self):
        script = f"op(items={constants.UNRESOLVED_PARAMETER_PLACEHOLDER})"
        result = parameters_util.apply_resolved_parameter_value(script, "items", [1, 2])
        assert result == "op(items=[1, 2])"

    def test_replaces_single_parameter_with_dict(self):
        script = f"op(config={constants.UNRESOLVED_PARAMETER_PLACEHOLDER})"
        result = parameters_util.apply_resolved_parameter_value(
            script, "config", {"a": 1}
        )
        assert result == "op(config={'a': 1})"

    def test_replaces_single_parameter_with_none(self):
        script = f"op(val={constants.UNRESOLVED_PARAMETER_PLACEHOLDER})"
        result = parameters_util.apply_resolved_parameter_value(script, "val", None)
        assert result == "op(val=None)"

    def test_raises_when_parameter_not_found(self):
        script = "op(x=1, y=2)"
        with pytest.raises(commons_errors.ResolvedParameterNotFoundError, match="Parameter z not found in script"):
            parameters_util.apply_resolved_parameter_value(script, "z", 42)

    def test_raises_when_placeholder_not_in_script_for_parameter(self):
        script = f"op(x={constants.UNRESOLVED_PARAMETER_PLACEHOLDER}, y=2)"
        with pytest.raises(commons_errors.ResolvedParameterNotFoundError, match="Parameter z not found in script"):
            parameters_util.apply_resolved_parameter_value(script, "z", 42)

    def test_replaces_only_exact_parameter_pattern(self):
        script = f"op(a=1, b={constants.UNRESOLVED_PARAMETER_PLACEHOLDER})"
        result = parameters_util.apply_resolved_parameter_value(script, "b", 100)
        assert result == "op(a=1, b=100)"
        # Ensure 'a' was not touched
        assert "a=1" in result


class TestAddResolvedParameterValue:
    def test_adds_to_call_with_no_parenthesis(self):
        result = parameters_util.add_resolved_parameter_value("op", "x", "a")
        assert result == "op(x='a')"

    def test_adds_to_empty_params_op(self):
        result = parameters_util.add_resolved_parameter_value("op()", "x", 42)
        assert result == "op(x=42)"

    def test_adds_to_empty_params_with_spaces(self):
        result = parameters_util.add_resolved_parameter_value("op( )", "x", 42)
        assert result == "op( x=42)"

    def test_adds_after_positional_arg(self):
        result = parameters_util.add_resolved_parameter_value("op(1)", "x", 42)
        assert result == "op(1, x=42)"

    def test_adds_after_keyword_arg(self):
        result = parameters_util.add_resolved_parameter_value("op(a=1)", "x", 42)
        assert result == "op(a=1, x=42)"

    def test_adds_after_multiple_args(self):
        result = parameters_util.add_resolved_parameter_value("op(1, b=2)", "x", 42)
        assert result == "op(1, b=2, x=42)"

    def test_adds_string_value(self):
        result = parameters_util.add_resolved_parameter_value("op()", "name", "hello")
        assert result == "op(name='hello')"

    def test_raises_when_parameter_already_in_kwargs(self):
        with pytest.raises(commons_errors.InvalidParametersError, match="Parameter x is already in operator keyword args"):
            parameters_util.add_resolved_parameter_value("op(x=1)", "x", 42)

    def test_raises_when_parameter_already_first_kwarg(self):
        with pytest.raises(commons_errors.InvalidParametersError, match="Parameter a is already"):
            parameters_util.add_resolved_parameter_value("op(a=1, b=2)", "a", 99)

    def test_raises_when_parameter_already_last_kwarg(self):
        with pytest.raises(commons_errors.InvalidParametersError, match="Parameter b is already"):
            parameters_util.add_resolved_parameter_value("op(a=1, b=2)", "b", 99)

    def test_raises_when_script_has_unclosed_parenthesis(self):
        with pytest.raises(commons_errors.InvalidParametersError, match="has unclosed parenthesis"):
            parameters_util.add_resolved_parameter_value("op(1", "x", 42)


class TestHasUnresolvedParameters:
    def test_returns_true_when_placeholder_present(self):
        script = f"op(x={constants.UNRESOLVED_PARAMETER_PLACEHOLDER})"
        assert parameters_util.has_unresolved_parameters(script) is True

    def test_returns_true_when_multiple_placeholders(self):
        placeholder = constants.UNRESOLVED_PARAMETER_PLACEHOLDER
        script = f"op(a={placeholder}, b={placeholder})"
        assert parameters_util.has_unresolved_parameters(script) is True

    def test_returns_false_when_no_placeholder(self):
        script = "op(x=1, y=2)"
        assert parameters_util.has_unresolved_parameters(script) is False

    def test_returns_false_for_empty_script(self):
        assert parameters_util.has_unresolved_parameters("") is False

    def test_returns_true_when_placeholder_part_of_larger_string(self):
        script = f"op(x='prefix_{constants.UNRESOLVED_PARAMETER_PLACEHOLDER}_suffix')"
        assert parameters_util.has_unresolved_parameters(script) is True

    def test_returns_true_when_placeholder_alone(self):
        script = constants.UNRESOLVED_PARAMETER_PLACEHOLDER
        assert parameters_util.has_unresolved_parameters(script) is True
