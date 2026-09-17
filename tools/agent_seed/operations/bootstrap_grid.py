#  Demo-only grid automation bootstrap via debug HTTP API.

import json
import time
import typing

import octobot_protocol.models as protocol_models

import octobot_node.agent_seed.constants as demo_agent_seed_constants

import tools.agent_seed.operations.bootstrap_http as agent_seed_bootstrap_http
import tools.agent_seed.protocol.builders as agent_seed_protocol_builders
import tools.agent_seed.secrets as agent_seed_secrets

DEFAULT_POLL_INTERVAL_SECONDS = 2.0
DEFAULT_TIMEOUT_SECONDS = 30.0


def grid_automation_is_running(debug_payload: dict) -> bool:
    debug_section = debug_payload.get("debug") or {}
    automations = debug_section.get("automations") or []
    target_name = demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_AUTOMATION_DISPLAY_NAME
    for automation in automations:
        status = automation.get("status")
        metadata = automation.get("metadata") or {}
        automation_name = metadata.get("name")
        if automation_name == target_name and status == protocol_models.WorkflowStatus.RUNNING.value:
            return True
    return False


def _find_user_action(debug_payload: dict, user_action_id: str) -> typing.Optional[dict]:
    debug_section = debug_payload.get("debug") or {}
    user_actions = debug_section.get("user_actions") or []
    for user_action in user_actions:
        if user_action.get("id") == user_action_id:
            return user_action
    return None


def _format_automation_user_action_error(user_action: dict) -> str:
    user_action_id = user_action.get("id", "<unknown>")
    status = user_action.get("status", "<unknown>")
    result = user_action.get("result")
    error_message = None
    error_details = None
    if isinstance(result, dict):
        automation_result = result.get("actual_instance")
        if isinstance(automation_result, dict):
            error_message = automation_result.get("error_message")
            error_details = automation_result.get("error_details")
        if error_message is None and error_details is None:
            error_message = result.get("error_message")
            error_details = result.get("error_details")
    parts = [
        f"grid automation user action {user_action_id!r} failed (status={status!r})",
    ]
    if error_message is not None:
        parts.append(f"error_message={error_message!r}")
    if error_details is not None:
        parts.append(f"error_details={error_details!r}")
    if error_message is None and error_details is None and result is not None:
        parts.append(f"result={result!r}")
    return ": ".join(parts)


def _ensure_user_action_not_failed(debug_payload: dict, user_action_id: str) -> None:
    user_action = _find_user_action(debug_payload, user_action_id)
    if user_action is None:
        return
    if user_action.get("status") != protocol_models.UserActionStatus.FAILED.value:
        return
    raise RuntimeError(_format_automation_user_action_error(user_action))


def _poll_debug_after_create(
    *,
    debug_url: str,
    headers: dict[str, str],
    user_action_id: str,
    deadline: float,
    poll_interval_seconds: float,
    timeout_seconds: float,
) -> None:
    while time.monotonic() < deadline:
        status_code, debug_payload = agent_seed_bootstrap_http.request_json("GET", debug_url, headers)
        if status_code == 200 and isinstance(debug_payload, dict):
            _ensure_user_action_not_failed(debug_payload, user_action_id)
            if grid_automation_is_running(debug_payload):
                return
        time.sleep(poll_interval_seconds)

    raise TimeoutError(
        f"Grid automation did not reach RUNNING within {timeout_seconds}s ({debug_url})",
    )


def bootstrap_grid_automation(
    *,
    base_url: str,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    wallet_address = demo_agent_seed_constants.DEMO_AGENT_SEED_WALLET_EVM_ADDRESS
    headers = agent_seed_bootstrap_http.basic_auth_header(
        wallet_address,
        agent_seed_secrets.DEMO_INSECURE_WALLET_PASSPHRASE,
    )
    debug_url = f"{base_url.rstrip('/')}/api/v1/debug/"
    deadline = time.monotonic() + timeout_seconds

    status_code, debug_payload = agent_seed_bootstrap_http.request_json("GET", debug_url, headers)
    if status_code == 200 and isinstance(debug_payload, dict) and grid_automation_is_running(
        debug_payload,
    ):
        return

    user_action = agent_seed_protocol_builders.build_create_grid_automation_user_action()
    user_action_id = user_action.id
    create_status, create_body = agent_seed_bootstrap_http.request_json(
        "POST",
        debug_url,
        headers,
        json.loads(user_action.to_json()),
    )
    if create_status != 204:
        raise RuntimeError(
            f"automation_create failed with HTTP {create_status}: {create_body}",
        )

    _poll_debug_after_create(
        debug_url=debug_url,
        headers=headers,
        user_action_id=user_action_id,
        deadline=deadline,
        poll_interval_seconds=poll_interval_seconds,
        timeout_seconds=timeout_seconds,
    )
