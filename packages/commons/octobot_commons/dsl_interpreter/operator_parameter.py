# pylint: disable=too-many-branches,too-many-return-statements,too-many-instance-attributes
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
import dataclasses
import typing

import octobot_commons.enums as commons_enums


UNSET_VALUE = "UNSET_VALUE"
UNINITIALIZED_VALUE = object()


@dataclasses.dataclass
class OperatorParameterOption:
    """Selectable value for an operator parameter (protocol options)."""

    value: str
    label: str

    def to_json(self) -> dict:
        """Convert the option to a JSON serializable dict."""
        return dataclasses.asdict(self)


TIME_FRAME_OPERATOR_PARAMETER_OPTIONS = [
    OperatorParameterOption(value=time_frame.value, label=time_frame.value)
    for time_frame in commons_enums.TimeFrames
]


def dsl_value_type_for_user_input(input_type: str) -> str:
    """Map a user input type string to its DSL value type."""
    try:
        return commons_enums.USER_INPUT_TYPE_TO_DSL_VALUE_TYPE[input_type]
    except KeyError as error:
        raise ValueError(
            f"Unsupported user input type {input_type!r} for DSL catalog type"
        ) from error


@dataclasses.dataclass
class OperatorParameter:
    name: str
    description: str
    required: bool
    type: str  # DslValueType string
    default: typing.Any = UNSET_VALUE
    options: typing.Optional[list[OperatorParameterOption]] = None
    minimum: typing.Optional[float] = None
    maximum: typing.Optional[float] = None
    step: typing.Optional[float] = None
    multiple: typing.Optional[bool] = None
    primary: typing.Optional[bool] = None

    def __repr__(self) -> str:
        default_str = f' (default: {self.default})' if self.default is not UNSET_VALUE else ''
        return (
            f"{self.name}{' (required)' if self.required else default_str}"
            f"[{self.type}] - {self.description}"
        )

    def to_json(self) -> dict:
        """
        Convert the operator parameter to a JSON serializable dict.
        """
        payload = {
            "name": self.name,
            "description": self.description,
            "required": self.required,
            "type": self.type,
            "default": self.default,
            "label": self.name,
        }
        if self.options is not None:
            payload["options"] = [option.to_json() for option in self.options]
        if self.minimum is not None:
            payload["minimum"] = self.minimum
        if self.maximum is not None:
            payload["maximum"] = self.maximum
        if self.step is not None:
            payload["step"] = self.step
        if self.multiple is not None:
            payload["multiple"] = self.multiple
        if self.primary is not None:
            payload["primary"] = self.primary
        return payload
