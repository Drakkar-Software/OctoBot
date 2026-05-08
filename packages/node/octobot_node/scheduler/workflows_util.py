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
import octobot_node.config
import octobot_node.constants
import octobot_node.models as models
import octobot_node.scheduler.task_context as task_context
import octobot_node.scheduler.workflows.params as params


try:
    import octobot_flow.entities
    import octobot_flow.parsers
except ImportError:
    octobot_flow = None  # type: ignore
    octobot_commons.logging.get_logger("octobot_node.scheduler.workflows_util").warning(
        "octobot_flow is not installed, workflows utilities will not be available"
    )

logger = octobot_commons.logging.get_logger("octobot_node.scheduler.workflows_util")

STATE_KEY = "state"


def filter_by_wallet(
    statuses: typing.Optional[list[dbos_lib.WorkflowStatus]],
    wallet_address: typing.Optional[str],
) -> list[dbos_lib.WorkflowStatus]:
    """Return statuses whose task wallet_address matches, or has no wallet restriction."""
    if not statuses or wallet_address is None:
        return statuses or []
    kept = []
    for s in statuses:
        task = get_input_task(s)
        if task is None or not task.wallet_address or task.wallet_address == wallet_address:
            kept.append(s)
    return kept


def get_latest_workflow(
    workflows: list[dbos_lib.WorkflowStatus],
) -> dbos_lib.WorkflowStatus:
    return sorted(workflows, key=lambda w: w.updated_at or 0)[-1]


def get_automation_copied_strategy_ids(workflow_status: dbos_lib.WorkflowStatus) -> list[str]:
    if reader := get_automation_state_reader(workflow_status):
        return reader.get_automation_copied_strategy_ids()
    return []


def get_workflows_by_parent_id(
    workflows: list[dbos_lib.WorkflowStatus]
) -> dict[str, list[dbos_lib.WorkflowStatus]]:
    by_parent: dict[str, list[dbos_lib.WorkflowStatus]] = {}
    for w in workflows:
        parent_id = w.workflow_id[:octobot_node.constants.PARENT_WORKFLOW_ID_LENGTH]
        by_parent.setdefault(parent_id, []).append(w)
    return by_parent


def get_automation_state_reader(workflow_status: dbos_lib.WorkflowStatus) -> typing.Optional["octobot_flow.parsers.AutomationStateReader"]:
    """Get the automation state from the workflow status (input task content)."""
    try:
        import octobot_flow.entities
        import octobot_flow.parsers
    except ImportError:
        return None
    if state_dict := get_automation_state_dict(workflow_status):
        return octobot_flow.parsers.AutomationStateReader(
            octobot_flow.entities.AutomationState.from_dict(state_dict)
        )
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
