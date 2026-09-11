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
import copy
import typing

import octobot_commons.errors as errors

_ROOT_FIELD_PATH = "<root>"
_CopyValue = typing.TypeVar("_CopyValue")


def _build_field_path(parent_path: str, segment: str) -> str:
    if not parent_path:
        return segment
    return f"{parent_path}.{segment}"


def _format_field_path(field_path: str) -> str:
    return field_path or _ROOT_FIELD_PATH


def _find_deepcopy_failure(value, field_path: str = "") -> tuple[str, object]:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            nested_path = _build_field_path(field_path, str(key))
            try:
                copy.deepcopy(nested_value)
            except Exception:
                return _find_deepcopy_failure(nested_value, nested_path)
    elif isinstance(value, list):
        for index, nested_value in enumerate(value):
            nested_path = f"{field_path}[{index}]"
            try:
                copy.deepcopy(nested_value)
            except Exception:
                return _find_deepcopy_failure(nested_value, nested_path)
    elif isinstance(value, tuple):
        for index, nested_value in enumerate(value):
            nested_path = f"{field_path}[{index}]"
            try:
                copy.deepcopy(nested_value)
            except Exception:
                return _find_deepcopy_failure(nested_value, nested_path)
    return field_path, value


def deepcopy(value: _CopyValue, context: str = "", root_path: str = "") -> _CopyValue:
    """
    Deepcopy a value and raise CopyError with field path context on failure.
    :param value: the value to deepcopy
    :param context: caller context included in the error message
    :param root_path: optional prefix for nested field paths
    :return: the deepcopied value
    """
    try:
        return copy.deepcopy(value)
    except Exception as err:
        failing_path, failing_value = _find_deepcopy_failure(value, root_path)
        formatted_path = _format_field_path(failing_path)
        context_message = f" during {context}" if context else ""
        raise errors.CopyError(
            f"Cannot deepcopy{context_message} at field {formatted_path!r}: "
            f"{type(failing_value).__name__}={failing_value!r}"
        ) from err
