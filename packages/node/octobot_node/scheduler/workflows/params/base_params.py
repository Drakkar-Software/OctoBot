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


class BaseHistory(pydantic.BaseModel):
    completed_iterations: int = 1
    created_orders: list[dict] = pydantic.Field(default_factory=list)
    cancelled_orders: list[str] = pydantic.Field(default_factory=list)
    transfers: list[dict] = pydantic.Field(default_factory=list)

    def update(self, history: "BaseHistory"):
        self.completed_iterations += history.completed_iterations
        self.created_orders.extend(history.created_orders)  # pylint: disable=no-member
        self.cancelled_orders.extend(history.cancelled_orders)  # pylint: disable=no-member
        self.transfers.extend(history.transfers)  # pylint: disable=no-member


class ProgressStatus(pydantic.BaseModel):
    latest_step_by_automation_id: typing.Optional[dict[str, str]] = None
    latest_step_result: typing.Optional[dict] = None
    next_step_by_automation_id: typing.Optional[dict[str, str]] = None
    next_step_at: typing.Optional[float] = None
    remaining_steps: typing.Optional[int] = None
    error: typing.Optional[str] = None
    history: typing.Optional[BaseHistory] = None

    def update(self, progress_status: "ProgressStatus"):
        self.latest_step_by_automation_id = progress_status.latest_step_by_automation_id
        self.latest_step_result = progress_status.latest_step_result
        self.next_step_by_automation_id = progress_status.next_step_by_automation_id
        self.next_step_at = progress_status.next_step_at
        self.remaining_steps = progress_status.remaining_steps
        self.error = progress_status.error
        if self.history is None:
            self.history = BaseHistory()
        if progress_status.history:
            self.history.update(progress_status.history)


@dataclasses.dataclass
class Tracker(octobot_commons.dataclasses.MinimizableDataclass):
    name: str

    @property
    def logger(self) -> octobot_commons.logging.BotLogger:
        return octobot_commons.logging.get_logger(self.name)
