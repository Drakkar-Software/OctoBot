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
import dataclasses
import pydantic
import typing

import octobot_commons.logging
import octobot_commons.dataclasses


class ProgressStatus(pydantic.BaseModel):
    latest_step: typing.Optional[str] = None
    latest_step_result: typing.Optional[dict] = None
    next_step: typing.Optional[str] = None
    next_step_at: typing.Optional[float] = None
    remaining_steps: typing.Optional[int] = None
    error: typing.Optional[str] = None

    def update(self, progress_status: "ProgressStatus"):
        self.latest_step = progress_status.latest_step
        self.latest_step_result = progress_status.latest_step_result
        self.next_step = progress_status.next_step
        self.next_step_at = progress_status.next_step_at
        self.remaining_steps = progress_status.remaining_steps
        self.error = progress_status.error


@dataclasses.dataclass
class Tracker(octobot_commons.dataclasses.MinimizableDataclass):
    name: str

    @property
    def logger(self) -> octobot_commons.logging.BotLogger:
        return octobot_commons.logging.get_logger(self.name)
