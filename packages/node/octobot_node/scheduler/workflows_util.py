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
import json
import typing
import dbos as dbos_lib

import octobot_commons.logging
import octobot_node.models as models
import octobot_node.scheduler.workflows.params as params


try:
    import octobot_flow
except ImportError:
    octobot_commons.logging.get_logger("octobot_node.scheduler.workflows_util").warning(
        "octobot_flow is not installed, workflows utilities will not be available"
    )


STATE_KEY = "state"


def get_automation_state(workflow_status: dbos_lib.WorkflowStatus) -> typing.Optional["octobot_flow.AutomationState"]:
    """Get the automation state from the workflow status"""
    if state_dict := get_automation_state_dict(workflow_status):
        return octobot_flow.AutomationState.from_dict(state_dict)
    return None


def get_automation_id(workflow_status: dbos_lib.WorkflowStatus) -> typing.Optional[str]:
    if state_dict := get_automation_state_dict(workflow_status):
        return state_dict.get("automation", {}).get("metadata", {}).get("automation_id")
    return None


def get_automation_state_dict(workflow_status: dbos_lib.WorkflowStatus) -> typing.Optional[dict]:
    if inputs := get_automation_workflow_inputs(workflow_status):
        try:
            return get_automation_dict(inputs.task.content)[STATE_KEY]
        except ValueError:
            return None
    return None


def get_input_task(workflow_status: dbos_lib.WorkflowStatus) -> typing.Optional[models.Task]:
    if inputs := get_automation_workflow_inputs(workflow_status):
        return inputs.task
    return None


def get_automation_workflow_inputs(workflow_status: dbos_lib.WorkflowStatus) -> typing.Optional[params.AutomationWorkflowInputs]:
    for input in list(workflow_status.input.get("args", [])) + list(workflow_status.input.get("kwargs", {}).values()):
        if isinstance(input, dict):
            try:
                parsed_inputs = params.AutomationWorkflowInputs.from_dict(input)
                return parsed_inputs
            except TypeError:
                print(f"Failed to parse inputs: {input}")
                pass
    return None


def get_automation_dict(description: typing.Union[str, dict]) -> dict:
    if isinstance(description, str):
        description = json.loads(description)
    if isinstance(description, dict) and (state := description.get(STATE_KEY)) and isinstance(state, dict):
        return description
    raise ValueError("No automation state found in description")


async def get_automation_workflow_status(automation_id: str) -> dbos_lib.WorkflowStatus:
    for workflow_status in await dbos_lib.DBOS.list_workflows_async(status=[
        dbos_lib.WorkflowStatusString.PENDING.value, dbos_lib.WorkflowStatusString.ENQUEUED.value
    ]):
        if get_automation_id(workflow_status) == automation_id:
            return workflow_status
    raise ValueError(f"No automation workflow found for automation_id: {automation_id}")
