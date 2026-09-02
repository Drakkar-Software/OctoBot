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
class AutomationWorkflowExecutionResultCallback(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    reply_workflow_id: str
    user_action_id: str


@dataclasses.dataclass
class PriorityActionExecutionResult(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    priority_action_id: str
    error_status: typing.Optional[str] = None
    error_message: typing.Optional[str] = None


@dataclasses.dataclass
class AutomationWorkflowSignalExecutionResult(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    user_action_id: str
    priority_action_results: list[PriorityActionExecutionResult]
    iteration_error: typing.Optional[str] = None
    iteration_error_message: typing.Optional[str] = None

    def __post_init__(self):
        if self.priority_action_results:
            self.priority_action_results = [
                PriorityActionExecutionResult.from_dict(priority_action_result)
                if isinstance(priority_action_result, dict)
                else priority_action_result
                for priority_action_result in self.priority_action_results
            ]


@dataclasses.dataclass
class AutomationWorkflowInputs(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    task: octobot_node.models.Task
    execution_time: float = 0


@dataclasses.dataclass
class AutomationWorkflowOutput(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    state: typing.Optional[str] = None
    state_metadata: typing.Optional[str] = None
    error: typing.Optional[str] = None
    error_message: typing.Optional[str] = None


@dataclasses.dataclass
class AutomationWorkflowIterationResult(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    progress_status: base_params.ProgressStatus
    next_iteration_description: typing.Optional[str]
    next_iteration_description_metadata: typing.Optional[str] = None
    has_next_actions: bool = False


@dataclasses.dataclass
class AutomationWorkflowActionUpdate(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    actions_type: str  # octobot_node.enums.AutomationWorkflowActionTypes value
    actions_details: list[dict]  # list of actions dicts
    execution_result_callback: typing.Optional[AutomationWorkflowExecutionResultCallback] = None

    def __post_init__(self):
        if isinstance(self.execution_result_callback, dict):
            self.execution_result_callback = AutomationWorkflowExecutionResultCallback.from_dict(
                self.execution_result_callback
            )
