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
import decimal
import re
import typing
import json

import numpy

import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator
import octobot_commons.errors
import octobot_commons.constants


def _normalize_dsl_serializable_value(value: typing.Any) -> typing.Any:
    """
    Convert nested values to types that repr() into valid DSL literals.
    """
    if isinstance(value, type):
        return value.__name__
    if isinstance(value, numpy.generic):
        return value.item()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, dict):
        return {
            key: _normalize_dsl_serializable_value(nested_value)
            for key, nested_value in value.items()
        }
    if isinstance(value, list):
        return [_normalize_dsl_serializable_value(nested_value) for nested_value in value]
    return value


def get_dsl_statement_operator_name(dsl_script: str) -> str:
    """
    Extract the root operator name from a single-call DSL expression.
    """
    try:
        parsed_expression = ast.parse(dsl_script, mode="eval")
    except SyntaxError as error:
        raise ValueError(f"Cannot parse DSL script operator name from: {dsl_script}") from error
    if not isinstance(parsed_expression.body, ast.Call):
        raise ValueError(f"DSL script is not a single operator call: {dsl_script}")
    function_node = parsed_expression.body.func
    if isinstance(function_node, ast.Name):
        return function_node.id
    raise ValueError(f"Cannot extract operator name from DSL script: {dsl_script}")


def format_parameter_value(value: typing.Any) -> str: # pylint: disable=too-many-return-statements
    """
    Formats a parameter value to a string usable in a DSL expression.
    Handles special cases for some values (ex: lists, dicts, ...).
    """
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, numpy.generic):
        return repr(value.item())
    if isinstance(value, decimal.Decimal):
        return repr(float(value))
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
        return repr(_normalize_dsl_serializable_value(value))
    if isinstance(value, dict):
        return repr(_normalize_dsl_serializable_value(value))
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
    unresolved = octobot_commons.constants.UNRESOLVED_PARAMETER_PLACEHOLDER
    formatted_value = format_parameter_value(value)
    possible_to_replace = [
        (f"{parameter}={unresolved}", f"{parameter}={formatted_value}"),
        (f"{parameter!r}: {unresolved!r}", f"{parameter!r}: {formatted_value}"),
        (f"{parameter!r}: {unresolved}", f"{parameter!r}: {formatted_value}"),
    ]
    for to_replace, replacement in possible_to_replace:
        if to_replace in script:
            return script.replace(to_replace, replacement)
    raise octobot_commons.errors.ResolvedParameterNotFoundError(
        f"Parameter {parameter} not found in script: {script}"
    )


def _find_matching_close_paren(source: str, open_paren_index: int) -> int:
    if open_paren_index >= len(source) or source[open_paren_index] != "(":
        raise octobot_commons.errors.InvalidParametersError(
            f"Expected '(' at index {open_paren_index} in script: {source!r}"
        )
    nesting_depth = 0
    for char_index in range(open_paren_index, len(source)):
        char = source[char_index]
        if char == "(":
            nesting_depth += 1
        elif char == ")":
            nesting_depth -= 1
            if nesting_depth == 0:
                return char_index
    raise octobot_commons.errors.InvalidParametersError(
        f"Script {source} has unclosed parenthesis"
    )


def _inject_kwarg_into_call(
    source: str,
    open_paren_index: int,
    close_paren_index: int,
    parameter: str,
    formatted_kwarg: str,
) -> str:
    existing_call_arguments = source[open_paren_index + 1 : close_paren_index]
    # Match keyword only at the top level of this call's argument list: after `(` is
    # stripped, so use start-of-string or comma — not `(|`, which would miss `op(x=1)`.
    if re.search(rf"(?:^|,)\s*{re.escape(parameter)}\s*=", existing_call_arguments):
        raise octobot_commons.errors.InvalidParametersError(
            f"Parameter {parameter} is already in operator keyword args: "
            f"{source[open_paren_index : close_paren_index + 1]}"
        )
    if not existing_call_arguments.strip():
        call_arguments_with_kwarg = f"{existing_call_arguments}{formatted_kwarg}"
    else:
        call_arguments_with_kwarg = f"{existing_call_arguments.rstrip()}, {formatted_kwarg}"
    return (
        source[: open_paren_index + 1]
        + call_arguments_with_kwarg
        + source[close_paren_index:]
    )


def add_resolved_parameter_value(script: str, operator: str, parameter: str, value: typing.Any) -> str:
    """
    Append a resolved keyword argument to every call to ``operator`` in ``script``.
    Supports:
    - Calls with no parenthesis when the whole script is only the operator name
      (e.g. op -> op(x='a'))
    - Calls with no existing params (e.g. op() -> op(x='a'))
    - Calls with existing params (e.g. op(1) -> op(1, x='a'))
    - Multiple calls (e.g. wait(1) if wait(2) -> both wait(...) gain the new kwarg)
    Raises InvalidParametersError if the parameter is already in one of those calls' kwargs,
    or if parentheses are unbalanced.
    """
    formatted_kwarg = f"{parameter}={format_parameter_value(value)}"
    operator_name_pattern = re.compile(rf"(?<![\w.])\b{re.escape(operator)}\b")

    call_opening_and_closing_indices: list[tuple[int, int]] = []
    for operator_match in operator_name_pattern.finditer(script):
        index_after_operator_name = operator_match.end()
        while index_after_operator_name < len(script) and script[index_after_operator_name] in " \t":
            index_after_operator_name += 1
        if index_after_operator_name < len(script) and script[index_after_operator_name] == "(":
            opening_paren_index = index_after_operator_name
            closing_paren_index = _find_matching_close_paren(script, opening_paren_index)
            call_opening_and_closing_indices.append((opening_paren_index, closing_paren_index))

    if call_opening_and_closing_indices:
        updated_script = script
        for opening_paren_index, closing_paren_index in sorted(
            call_opening_and_closing_indices,
            key=lambda open_close: open_close[0],
            reverse=True,
        ):
            updated_script = _inject_kwarg_into_call(
                updated_script,
                opening_paren_index,
                closing_paren_index,
                parameter,
                formatted_kwarg,
            )
        return updated_script

    if "(" in script:
        raise octobot_commons.errors.InvalidParametersError(
            f"Operator {operator!r} call sites not found or script has unclosed parenthesis: {script!r}"
        )

    if operator_name_pattern.fullmatch(script.strip()) is not None:
        return f"{script.strip()}({formatted_kwarg})"

    return f"{script}({formatted_kwarg})"


def has_unresolved_parameters(script: str) -> bool:
    """
    Check if a DSL script has unresolved parameters.
    """
    return octobot_commons.constants.UNRESOLVED_PARAMETER_PLACEHOLDER in script
