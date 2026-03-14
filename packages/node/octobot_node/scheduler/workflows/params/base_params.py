#  Drakkar-Software OctoBot-Node
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
import pydantic
import typing


class ProgressStatus(pydantic.BaseModel):
    latest_step: typing.Optional[str] = None
    next_step: typing.Optional[str] = None
    next_step_at: typing.Optional[float] = None
    remaining_steps: typing.Optional[int] = None
    error: typing.Optional[str] = None
    should_stop: bool = False
