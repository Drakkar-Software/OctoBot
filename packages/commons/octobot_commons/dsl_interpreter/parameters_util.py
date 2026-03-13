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
import re
import typing
import json

import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator
import octobot_commons.errors
import octobot_commons.constants


def format_parameter_value(value: typing.Any) -> str: # pylint: disable=too-many-return-statements
    """
    Formats a parameter value to a string usable in a DSL expression.
    Handles special cases for some values (ex: lists, dicts, ...).
    """
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return repr(parsed)
            if isinstance(parsed, dict):
                return repr(parsed)
        except (json.JSONDecodeError, TypeError):
            return repr(value)
    if isinstance(value, list):
        return repr(value)
    if isinstance(value, dict):
        return repr(value)
    return repr(value)


def resove_operator_params(
    operator_class: dsl_interpreter_operator.Operator,
    param_value_by_name: dict[str, typing.Any]
) -> list[str]:
    """
    Resolves operator parameters to a list of positional and keyword arguments.
    Returns a list of formatted strings usable in a DSL expression.
    """
    operator_params = operator_class.get_parameters()
    required_params = [p for p in operator_params if p.required]
    optional_params = [p for p in operator_params if not p.required]
    positional_parts = []
    keyword_parts = []
    for param_def in required_params:
        name = param_def.name
        if name in param_value_by_name:
            value = param_value_by_name[name]
            positional_parts.append(
                format_parameter_value(value)
            )
    for param_def in optional_params:
        name = param_def.name
        if name in param_value_by_name:
            value = param_value_by_name[name]
            keyword_parts.append(f"{name}={format_parameter_value(value)}")
    return positional_parts + keyword_parts


def resolve_operator_args_and_kwargs(
    operator_class: typing.Type[dsl_interpreter_operator.Operator],
    args: typing.List,
    kwargs: typing.Dict[str, typing.Any],
) -> typing.Tuple[typing.List, typing.Dict[str, typing.Any]]:
    """
    For operators with get_parameters(), merge positional args and kwargs
    into a single args tuple in parameter order. This ensures validation
    passes when using named parameters (e.g. xyz(1, p2=2) where p2 is a required parameter).
    """
    expected_params = operator_class.get_parameters()
    if not expected_params:
        return args, kwargs

    max_params = len(expected_params)
    merged_args = []
    args_index = 0
    remaining_kwargs = dict(kwargs)

    for param in expected_params:
        if args_index < len(args):
            merged_args.append(args[args_index])
            args_index += 1
        elif param.name in remaining_kwargs:
            merged_args.append(remaining_kwargs.pop(param.name))
        else:
            # Parameter not provided - leave for Operator's default handling
            break

    if args_index < len(args):
        raise octobot_commons.errors.InvalidParametersError(
            f"{operator_class.get_name()} supports up to {max_params} "
            f"parameters: {operator_class.get_parameters_description()}"
        )

    return merged_args, remaining_kwargs


def apply_resolved_parameter_value(script: str, parameter: str, value: typing.Any):
    """
    Apply a resolved parameter value to a DSL script.
    """
    to_replace = f"{parameter}={octobot_commons.constants.UNRESOLVED_PARAMETER_PLACEHOLDER}"
    if to_replace not in script:
        raise octobot_commons.errors.ResolvedParameterNotFoundError(
            f"Parameter {parameter} not found in script: {script}"
        )
    new_value = f"{parameter}={format_parameter_value(value)}"
    return script.replace(to_replace, new_value)


def add_resolved_parameter_value(script: str, parameter: str, value: typing.Any):
    """
    Append a resolved parameter value to the end of a DSL script.
    Supports:
    - Calls with no parenthesis (e.g. op -> op(x='a'))
    - Calls with no existing params (e.g. op() -> op(x='a'))
    - Calls with existing params (e.g. op(1) -> op(1, x='a'))
    Raises InvalidParametersError if the parameter is already in the operator keyword args.
    """
    param_str = f"{parameter}={format_parameter_value(value)}"
    if script[-1] == ")":
        # Script ends with ) - append to existing call
        if re.search(rf"(?:\(|,)\s*{re.escape(parameter)}\s*=", script):
            raise octobot_commons.errors.InvalidParametersError(
                f"Parameter {parameter} is already in operator keyword args: {script}"
            )
        inner = script[:-1]
        has_existing_params = inner.rstrip().endswith("(")
        if has_existing_params:
            return f"{inner}{param_str})"
        return f"{inner}, {param_str})"
    if "(" in script:
        raise octobot_commons.errors.InvalidParametersError(
            f"Script {script} has unclosed parenthesis"
        )
    return f"{script}({param_str})"


def has_unresolved_parameters(script: str) -> bool:
    """
    Check if a DSL script has unresolved parameters.
    """
    return octobot_commons.constants.UNRESOLVED_PARAMETER_PLACEHOLDER in script
