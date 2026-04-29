# pylint: disable=too-many-branches,too-many-return-statements
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


UNSET_VALUE = "UNSET_VALUE"
UNINITIALIZED_VALUE = object()


@dataclasses.dataclass
class OperatorParameter:
    name: str
    description: str
    required: bool
    type: typing.Type[typing.Any]
    default: typing.Any = UNSET_VALUE

    def __repr__(self) -> str:
        default_str = f' (default: {self.default})' if self.default is not UNSET_VALUE else ''
        return (
            f"{self.name}{' (required)' if self.required else default_str}"
            f"[{self.type.__name__}] - {self.description}"
        )

    def to_json(self) -> dict:
        """
        Convert the operator parameter to a JSON serializable dict.
        """
        return {
            "name": self.name,
            "description": self.description,
            "required": self.required,
            "type": self.type.__name__,
            "default": self.default,
        }
