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
import json
import typing
import dbos as dbos_lib

import octobot_commons.logging
import octobot_protocol.models as protocol_models
import octobot_node.config
import octobot_node.constants
import octobot_node.enums as octobot_node_enums
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

_USER_ACTION_TERMINAL_WORKFLOW_STATUSES = (
    dbos_lib.WorkflowStatusString.SUCCESS,
    dbos_lib.WorkflowStatusString.ERROR,
    dbos_lib.WorkflowStatusString.CANCELLED,
    dbos_lib.WorkflowStatusString.MAX_RECOVERY_ATTEMPTS_EXCEEDED,
)
_USER_ACTION_INPUT_WORKFLOW_STATUSES = tuple(
    workflow_status
    for workflow_status in dbos_lib.WorkflowStatusString
    if workflow_status not in _USER_ACTION_TERMINAL_WORKFLOW_STATUSES
)


def get_user_action_input_workflow_statuses() -> tuple[dbos_lib.WorkflowStatusString, ...]:
    return _USER_ACTION_INPUT_WORKFLOW_STATUSES


def get_user_action_terminal_workflow_statuses() -> tuple[dbos_lib.WorkflowStatusString, ...]:
    return _USER_ACTION_TERMINAL_WORKFLOW_STATUSES


@dataclasses.dataclass
class ResolvedUserActionWorkflowInputs:
    inputs: typing.Optional[params.UserActionWorkflowInputs] = None
    parse_error: typing.Optional[str] = None
    partial_user_id: typing.Optional[str] = None
    partial_user_action_id: typing.Optional[str] = None


def _is_user_action_workflow_input_dict(candidate: dict) -> bool:
    return "user_id" in candidate or "user_action" in candidate


def _yield_user_action_input_dicts_from_container(
    container: typing.Any,
) -> typing.Iterator[dict]:
    if not isinstance(container, dict):
        return
    if _is_user_action_workflow_input_dict(container):
        yield container
        return
    inputs_value = container.get("inputs")
    if isinstance(inputs_value, dict) and _is_user_action_workflow_input_dict(inputs_value):
        yield inputs_value
    named_args = container.get("namedArgs")
    if isinstance(named_args, dict):
        named_inputs = named_args.get("inputs")
        if isinstance(named_inputs, dict) and _is_user_action_workflow_input_dict(named_inputs):
            yield named_inputs
    for positional_arg in container.get("args") or []:
        yield from _yield_user_action_input_dicts_from_container(positional_arg)
    kwargs = container.get("kwargs")
    if isinstance(kwargs, dict):
        for kwarg_value in kwargs.values():
            yield from _yield_user_action_input_dicts_from_container(kwarg_value)


def _iter_workflow_input_dicts(workflow_status: dbos_lib.WorkflowStatus) -> typing.Iterator[dict]:
    if not workflow_status.input:
        return
    seen_candidate_ids: set[int] = set()
    for input_candidate in _yield_user_action_input_dicts_from_container(workflow_status.input):
        candidate_id = id(input_candidate)
        if candidate_id in seen_candidate_ids:
            continue
        seen_candidate_ids.add(candidate_id)
        yield input_candidate


def _partial_user_action_workflow_fragments(input_dict: dict) -> tuple[typing.Optional[str], typing.Optional[str]]:
    user_id = input_dict.get("user_id")
    partial_wallet = user_id if isinstance(user_id, str) else None
    user_action_raw = input_dict.get("user_action")
    partial_action_id = None
    if isinstance(user_action_raw, dict):
        user_action_id = user_action_raw.get("id")
        if isinstance(user_action_id, str):
            partial_action_id = user_action_id
    return partial_wallet, partial_action_id


def _parse_user_action_workflow_inputs_from_dict(input_dict: dict) -> params.UserActionWorkflowInputs:
    try:
        return params.UserActionWorkflowInputs.from_dict(input_dict)
    except (TypeError, ValueError) as first_error:
        user_action_raw = input_dict.get("user_action")
        if not isinstance(user_action_raw, dict):
            raise first_error from first_error
        try:
            reparsed_user_action = protocol_models.UserAction.from_json(json.dumps(user_action_raw))
        except (TypeError, ValueError, json.JSONDecodeError) as nested_error:
            raise first_error from nested_error
        if reparsed_user_action is None:
            raise first_error from first_error
        user_id = input_dict.get("user_id")
        if not isinstance(user_id, str):
            raise first_error from first_error
        return params.UserActionWorkflowInputs(
            user_id=user_id,
            user_action=reparsed_user_action,
        )


def resolve_user_action_workflow_inputs(
    workflow_status: dbos_lib.WorkflowStatus,
) -> ResolvedUserActionWorkflowInputs:
    last_parse_error: typing.Optional[str] = None
    partial_user_id: typing.Optional[str] = None
    partial_user_action_id: typing.Optional[str] = None
    for input_dict in _iter_workflow_input_dicts(workflow_status):
        partial_wallet, partial_action_id = _partial_user_action_workflow_fragments(input_dict)
        if partial_wallet is not None:
            partial_user_id = partial_wallet
        if partial_action_id is not None:
            partial_user_action_id = partial_action_id
        try:
            parsed_inputs = _parse_user_action_workflow_inputs_from_dict(input_dict)
        except (TypeError, ValueError) as parse_error:
            last_parse_error = str(parse_error)
            continue
        if parsed_inputs.user_action is None:
            last_parse_error = "user_action is missing after parse"
            continue
        return ResolvedUserActionWorkflowInputs(inputs=parsed_inputs)
    return ResolvedUserActionWorkflowInputs(
        parse_error=last_parse_error or "no user-action workflow inputs found",
        partial_user_id=partial_user_id,
        partial_user_action_id=partial_user_action_id,
    )


def filter_by_wallet(
    statuses: typing.Optional[list[dbos_lib.WorkflowStatus]],
    user_id: typing.Optional[str],
    queue: octobot_node_enums.SchedulerQueues,
) -> list[dbos_lib.WorkflowStatus]:
    """Return statuses for ``user_id`` using automation task wallet or user-action input wallet."""
    if not statuses or user_id is None:
        return statuses or []
    if queue == octobot_node_enums.SchedulerQueues.USER_ACTION_QUEUE:
        kept = []
        for status_row in statuses:
            ua_inputs = get_user_action_workflow_inputs(status_row)
            if ua_inputs is None:
                kept.append(status_row)
                continue
            if ua_inputs.user_id and ua_inputs.user_id != user_id:
                continue
            kept.append(status_row)
        return kept
    if queue == octobot_node_enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE:
        kept = []
        for status_row in statuses:
            task = get_automation_input_task(status_row)
            if task is None or not task.user_id or task.user_id == user_id:
                kept.append(status_row)
        return kept
    raise ValueError(f"Unsupported scheduler queue for wallet filter: {queue!r}")


def parse_automation_child_workflow_index(workflow_id: str) -> int:
    """
    Return the child iteration index encoded in a workflow ID.
    Parent-only IDs (no suffix after PARENT_WORKFLOW_ID_LENGTH) map to 0.
    Child IDs use a single ``_N`` or ``-N`` suffix (digits only after the separator).
    """
    suffix = workflow_id[octobot_node.constants.PARENT_WORKFLOW_ID_LENGTH:]
    if not suffix:
        return 0
    if len(suffix) >= 2 and suffix[0] in "_-" and suffix[1:].isdigit():
        return int(suffix[1:])
    raise ValueError(
        f"Invalid child workflow suffix format in workflow ID: {workflow_id!r}."
    )


def _automation_child_workflow_sort_key(
    workflow_status: dbos_lib.WorkflowStatus,
) -> tuple[int, int]:
    try:
        child_index = parse_automation_child_workflow_index(workflow_status.workflow_id)
    except ValueError:
        # Unrelated workflow IDs can share the parent UUID prefix (e.g. ``uuid-4-4``).
        child_index = -1
    return child_index, workflow_status.updated_at or 0


def get_latest_child_workflow(
    workflows: list[dbos_lib.WorkflowStatus],
) -> dbos_lib.WorkflowStatus:
    return sorted(workflows, key=_automation_child_workflow_sort_key)[-1]


def get_latest_workflow(
    workflows: list[dbos_lib.WorkflowStatus],
) -> dbos_lib.WorkflowStatus:
    return get_latest_child_workflow(workflows)


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
    """Get the resolved automation state for a workflow row (input or terminal output)."""
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


def parse_automation_workflow_output(
    workflow_status: dbos_lib.WorkflowStatus,
) -> typing.Optional[params.AutomationWorkflowOutput]:
    if not workflow_status.output:
        return None
    try:
        return params.AutomationWorkflowOutput.from_dict(json.loads(workflow_status.output))
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        logger.warning(
            "Failed to parse automation workflow output for %s: %s",
            workflow_status.workflow_id,
            error,
        )
        return None


def get_resolved_automation_task(workflow_status: dbos_lib.WorkflowStatus) -> typing.Optional[models.Task]:
    """
    Return the task whose content reflects the authoritative automation state for this workflow row.

    Running iterations expose state from workflow input. Completed SUCCESS/ERROR iterations expose
    state from workflow output so protocol consumers match end-of-iteration exchange snapshots.
    """
    input_task = get_automation_input_task(workflow_status)
    workflow_output = parse_automation_workflow_output(workflow_status)
    if (
        workflow_output is not None
        and workflow_output.state is not None
        and workflow_status.status
        in (
            dbos_lib.WorkflowStatusString.SUCCESS.value,
            dbos_lib.WorkflowStatusString.ERROR.value,
        )
    ):
        return models.Task(
            name=input_task.name if input_task is not None else None,
            content=workflow_output.state,
            content_metadata=workflow_output.state_metadata,
            type=models.TaskType.EXECUTE_ACTIONS.value,
        )
    return input_task


def get_automation_state_dict(workflow_status: dbos_lib.WorkflowStatus) -> typing.Optional[dict]:
    resolved_task = get_resolved_automation_task(workflow_status)
    if resolved_task is None:
        return None
    with task_context.encrypted_task(resolved_task):
        try:
            return get_automation_dict(resolved_task.content)[STATE_KEY]
        except ValueError:
            return None


def get_automation_input_task(workflow_status: dbos_lib.WorkflowStatus) -> typing.Optional[models.Task]:
    if inputs := get_automation_workflow_inputs(workflow_status):
        return inputs.task
    return None


def get_automation_workflow_inputs(workflow_status: dbos_lib.WorkflowStatus) -> typing.Optional[params.AutomationWorkflowInputs]:
    if not workflow_status.input:
        return None
    for input in list(workflow_status.input.get("args", [])) + list(workflow_status.input.get("kwargs", {}).values()):
        if isinstance(input, dict):
            try:
                parsed_inputs = params.AutomationWorkflowInputs.from_dict(input)
                return parsed_inputs
            except TypeError:
                print(f"Failed to parse inputs: {input}")
                pass
    return None


def get_user_action_workflow_inputs(workflow_status: dbos_lib.WorkflowStatus) -> typing.Optional[params.UserActionWorkflowInputs]:
    resolved = resolve_user_action_workflow_inputs(workflow_status)
    return resolved.inputs


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
