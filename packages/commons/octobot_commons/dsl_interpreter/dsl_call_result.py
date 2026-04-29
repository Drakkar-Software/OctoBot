#  Drakkar-Software OctoBot
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

import octobot_commons.dataclasses


@dataclasses.dataclass
class DSLCallResult(octobot_commons.dataclasses.FlexibleDataclass):
    """
    Stores a DSL call result alongside its statement (and error if any)
    """
    statement: str
    result: typing.Optional[typing.Any] = None
    error: typing.Optional[str] = None

    def succeeded(self) -> bool:
        """
        Check if the DSL call succeeded
        :return: True if the DSL call succeeded, False otherwise
        """
        return self.error is None
