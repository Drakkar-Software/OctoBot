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
import typing

import octobot_commons.dataclasses.minimizable_dataclass
import octobot_node.models
import octobot_node.scheduler.workflows.params.base_params as base_params


@dataclasses.dataclass
class AutomationWorkflowInputs(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    task: octobot_node.models.Task
    execution_time: float = 0


@dataclasses.dataclass
class AutomationWorkflowIterationResult(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    progress_status: base_params.ProgressStatus
    next_iteration_description: typing.Optional[str]
