#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import contextlib
import dataclasses
import json
import typing

import dbos as dbos_lib
import octobot_protocol.models as protocol_models

import octobot_flow.entities as flow_entities
import octobot_flow.parsers as flow_parsers

import octobot_node.models as node_models
import octobot_node.scheduler.automations.octobot_flow_client as octobot_flow_client
import octobot_node.scheduler.task_context as task_context_module
import octobot_node.scheduler.workflows_util as workflows_util_module

if typing.TYPE_CHECKING:
    import octobot_node.protocol.automations as automations_protocol

STATE_KEY = "state"


@dataclasses.dataclass
class WalletAutomationStates:
    protocol_states: list[protocol_models.AutomationState]
    flow_states_by_id: dict[str, flow_entities.AutomationState]


def get_automation_dict(description: typing.Union[str, dict]) -> dict:
    if isinstance(description, str):
        description = json.loads(description)
    if isinstance(description, dict) and (state := description.get(STATE_KEY)) and isinstance(state, dict):
        return description
    raise ValueError("No automation state found in description")


def get_automation_state_dict(workflow_status: dbos_lib.WorkflowStatus) -> typing.Optional[dict]:
    resolved_task = workflows_util_module.get_resolved_automation_task(workflow_status)
    if resolved_task is None:
        return None
    with task_context_module.encrypted_task(resolved_task):
        try:
            return get_automation_dict(resolved_task.content)[STATE_KEY]
        except ValueError:
            return None


def get_automation_state_reader(
    workflow_status: dbos_lib.WorkflowStatus,
) -> typing.Optional[flow_parsers.AutomationStateReader]:
    """Get the resolved automation state for a workflow row (input or terminal output)."""
    if state_dict := get_automation_state_dict(workflow_status):
        return flow_parsers.AutomationStateReader(
            flow_entities.AutomationState.from_dict(state_dict)
        )
    return None


def get_automation_id(workflow_status: dbos_lib.WorkflowStatus) -> typing.Optional[str]:
    if state_dict := get_automation_state_dict(workflow_status):
        return state_dict.get("automation", {}).get("metadata", {}).get("automation_id")
    return None


def get_automation_copied_strategy_ids(workflow_status: dbos_lib.WorkflowStatus) -> list[str]:
    if reader := get_automation_state_reader(workflow_status):
        return reader.get_automation_copied_strategy_ids()
    return []


def patch_task_content_degraded_state(
    task_content: str,
    error_status: str,
    error_message: str,
    *,
    since: float,
) -> str:
    description = get_automation_dict(task_content)
    automation_state = flow_entities.AutomationState.from_dict(description[STATE_KEY])
    existing_degraded_state = automation_state.automation.execution.degraded_state
    degraded_since = (
        existing_degraded_state.since
        if existing_degraded_state.since > 0
        else since
    )
    automation_state.automation.execution.degraded_state = flow_entities.DegradedStateDetails(
        since=degraded_since,
        error=error_status,
        reason=error_message,
    )
    description[STATE_KEY] = automation_state.to_dict(include_default_values=False)
    return json.dumps(description)


async def get_automation_workflow_status(automation_id: str) -> dbos_lib.WorkflowStatus:
    for workflow_status in await dbos_lib.DBOS.list_workflows_async(status=[
        dbos_lib.WorkflowStatusString.PENDING.value, dbos_lib.WorkflowStatusString.ENQUEUED.value
    ]):
        if get_automation_id(workflow_status) == automation_id:
            return workflow_status
    raise ValueError(f"No automation workflow found for automation_id: {automation_id}")


def parse_flow_automation_state(task: node_models.Task) -> flow_entities.AutomationState:
    parsed_description = octobot_flow_client.OctoBotActionsJobDescription.parse_task_description(task.content)
    automation_state: octobot_flow_client.OctoBotActionsJobDescription = (
        octobot_flow_client.OctoBotActionsJobDescription.from_dict(parsed_description)
    )
    return flow_entities.AutomationState.from_dict(automation_state.state)


def _flow_states_by_id_from_sources(
    sources: list["automations_protocol.AutomationStateSource"],
) -> dict[str, flow_entities.AutomationState]:
    flow_automation_states_by_id: dict[str, flow_entities.AutomationState] = {}
    for source in sources:
        try:
            flow_automation_states_by_id[source.task.id] = parse_flow_automation_state(source.task)
        except Exception:
            continue
    return flow_automation_states_by_id


def _protocol_states_from_sources(
    sources: list["automations_protocol.AutomationStateSource"],
) -> list[protocol_models.AutomationState]:
    import octobot_node.protocol.automations as automations_protocol

    return automations_protocol.to_protocol_automations_state(sources)


async def load_automation_state_sources(
    wallet_id: str,
    statuses: typing.Optional[list[dbos_lib.WorkflowStatusString]] = None,
) -> list["automations_protocol.AutomationStateSource"]:
    import octobot_node.protocol.automations as automations_protocol
    import octobot_node.scheduler as scheduler_module

    scheduler = scheduler_module.SCHEDULER
    workflows = await scheduler._get_latest_workflow_for_each_automation(
        wallet_id,
        statuses,
        load_output=True,
    )
    sources: list[automations_protocol.AutomationStateSource] = []
    for workflow in workflows:
        workflow_output = workflows_util_module.parse_automation_workflow_output(workflow)
        task = workflows_util_module.get_resolved_automation_task(workflow)
        if task is None:
            continue
        task.id = workflows_util_module.normalize_parent_automation_id(workflow.workflow_id)
        sources.append(automations_protocol.AutomationStateSource(
            task=task,
            workflow_status=workflow.status,
            workflow_output=workflow_output,
            workflow_error=str(workflow.error) if workflow.error else None,
        ))
    return sources


async def load_protocol_automation_states(
    wallet_id: str,
    statuses: typing.Optional[list[dbos_lib.WorkflowStatusString]] = None,
) -> list[protocol_models.AutomationState]:
    sources = await load_automation_state_sources(wallet_id, statuses)
    with contextlib.ExitStack() as exit_stack:
        for source in sources:
            exit_stack.enter_context(task_context_module.encrypted_task(source.task))
        return _protocol_states_from_sources(sources)


async def load_flow_automation_states_by_id(
    wallet_id: str,
    statuses: typing.Optional[list[dbos_lib.WorkflowStatusString]] = None,
) -> dict[str, flow_entities.AutomationState]:
    sources = await load_automation_state_sources(wallet_id, statuses)
    with contextlib.ExitStack() as exit_stack:
        for source in sources:
            exit_stack.enter_context(task_context_module.encrypted_task(source.task))
        return _flow_states_by_id_from_sources(sources)


async def load_wallet_automation_states(
    wallet_id: str,
    statuses: typing.Optional[list[dbos_lib.WorkflowStatusString]] = None,
) -> WalletAutomationStates:
    sources = await load_automation_state_sources(wallet_id, statuses)
    with contextlib.ExitStack() as exit_stack:
        for source in sources:
            exit_stack.enter_context(task_context_module.encrypted_task(source.task))
        protocol_states = _protocol_states_from_sources(sources)
        flow_states_by_id = _flow_states_by_id_from_sources(sources)
    return WalletAutomationStates(
        protocol_states=protocol_states,
        flow_states_by_id=flow_states_by_id,
    )
