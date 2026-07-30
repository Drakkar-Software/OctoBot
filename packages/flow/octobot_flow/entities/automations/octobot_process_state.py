#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.
import typing

import pydantic

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_flow.entities.actions.action_details as action_details_module

class OctobotProcessState(pydantic.BaseModel):
    """Master-side recall payload for run_octobot_process (former EnsureOctobotProcessState)."""

    model_config = pydantic.ConfigDict(validate_assignment=True, extra="ignore")

    http_base_url: str
    web_port: int
    node_port: int
    user_root: str
    user_folder: str
    log_folder: str
    profile_id: str | None
    pid: int  # Last known child PID on the master; may lag after a child self-restart until adoption.
    state_file_path: str = ""
    started_waiting_at: float = 0.0  # Wall-clock when the first spawn began; used only while `init_state_ok` is False (`ping_timeout`).
    init_state_ok: bool = False  # True once the child reached confirmed-alive; switches from init `ping_timeout` to recall/grace rules.
    executor_id: str  # Required scheduler executor id at emit time; compared on recall to detect worker restart.

def parse_octobot_process_state(raw: dict) -> OctobotProcessState | None:
    """Parse recall inner dict; empty or invalid dict → None."""
    if not raw:
        return None
    try:
        return OctobotProcessState.model_validate(raw)
    except pydantic.ValidationError:
        return None

def _run_octobot_process_operator_name() -> str:
    import tentacles.Meta.DSL_operators.octobot_process_operators.octobot_process_ops as octobot_process_ops

    return octobot_process_ops.RUN_OCTOBOT_PROCESS_OPERATOR_NAME

def is_run_octobot_process_dsl_action(
    flow_action: action_details_module.DSLScriptActionDetails,
) -> bool:
    """True when the action DSL script invokes the run_octobot_process operator."""
    dsl_value = flow_action.resolved_dsl_script or flow_action.dsl_script
    if not dsl_value:
        return False
    return dsl_value.strip().startswith(f"{_run_octobot_process_operator_name()}(")

def recall_inner_from_action_result(
    action_result: typing.Any,
) -> dict | None:
    """Unwrap ReCallingOperatorResult.last_execution_result from a DAG action result."""
    if not isinstance(action_result, dict):
        return None
    if dsl_interpreter.ReCallingOperatorResult.is_re_calling_operator_result(action_result):
        recall_wrapper = dsl_interpreter.ReCallingOperatorResult.from_dict(
            action_result[dsl_interpreter.ReCallingOperatorResult.__name__]
        )
        inner_last = recall_wrapper.last_execution_result
        return inner_last if isinstance(inner_last, dict) else None
    return action_result if action_result else None
