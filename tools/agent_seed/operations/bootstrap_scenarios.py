#  Demo-only extra bootstrap scenarios (index, completed, lifecycle) via debug HTTP API.

import time
import typing

import octobot_protocol.models as protocol_models

import octobot_node.agent_seed.constants as demo_agent_seed_constants

import tools.agent_seed.enums as agent_seed_enums
import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.operations.bootstrap_grid as agent_seed_bootstrap_grid
import tools.agent_seed.operations.bootstrap_http as agent_seed_bootstrap_http
import tools.agent_seed.protocol.builders as agent_seed_protocol_builders
import tools.agent_seed.secrets as agent_seed_secrets

# ALL expands to these, in order: grid first (lifecycle needs it), completed after index.
_SCENARIO_ORDER = (
    agent_seed_enums.BootstrapScenario.GRID,
    agent_seed_enums.BootstrapScenario.INDEX,
    agent_seed_enums.BootstrapScenario.COMPLETED,
    agent_seed_enums.BootstrapScenario.LIFECYCLE,
)


def find_automation(debug_payload: dict, automation_id: str) -> typing.Optional[dict]:
    debug_section = debug_payload.get("debug") or {}
    for automation in debug_section.get("automations") or []:
        if automation.get("id") == automation_id:
            return automation
    return None


def expand_scenarios(
    scenarios: typing.Optional[typing.Iterable[agent_seed_enums.BootstrapScenario]],
) -> list[agent_seed_enums.BootstrapScenario]:
    requested = set(scenarios or [agent_seed_enums.BootstrapScenario.GRID])
    if agent_seed_enums.BootstrapScenario.ALL in requested:
        return list(_SCENARIO_ORDER)
    return [scenario for scenario in _SCENARIO_ORDER if scenario in requested]


def _get_debug_payload(debug_url: str, headers: dict[str, str]) -> dict:
    status_code, debug_payload = agent_seed_bootstrap_http.request_json("GET", debug_url, headers)
    if status_code != 200 or not isinstance(debug_payload, dict):
        raise RuntimeError(f"GET {debug_url} failed with HTTP {status_code}: {debug_payload}")
    return debug_payload


def _submit_user_action(
    debug_url: str,
    headers: dict[str, str],
    user_action: protocol_models.UserAction,
) -> str:
    status_code, body = agent_seed_bootstrap_http.request_json(
        "POST",
        debug_url,
        headers,
        agent_seed_bootstrap_http.user_action_to_payload(user_action),
    )
    if status_code != 204:
        raise RuntimeError(f"{user_action.id} rejected with HTTP {status_code}: {body}")
    return user_action.id


def _wait_for_automation_status(
    *,
    debug_url: str,
    headers: dict[str, str],
    automation_id: str,
    expected_status: protocol_models.WorkflowStatus,
    user_action_id: typing.Optional[str],
    poll_interval_seconds: float,
    timeout_seconds: float,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        debug_payload = _get_debug_payload(debug_url, headers)
        if user_action_id is not None:
            agent_seed_bootstrap_grid.ensure_user_action_not_failed(debug_payload, user_action_id)
        automation = find_automation(debug_payload, automation_id)
        if automation is not None and automation.get("status") == expected_status.value:
            return automation
        time.sleep(poll_interval_seconds)
    raise TimeoutError(
        f"Automation {automation_id} did not reach {expected_status.value} within {timeout_seconds}s ({debug_url})",
    )


def _session(base_url: str) -> tuple[str, dict[str, str]]:
    headers = agent_seed_bootstrap_http.basic_auth_header(
        demo_agent_seed_constants.DEMO_AGENT_SEED_WALLET_EVM_ADDRESS,
        agent_seed_secrets.DEMO_INSECURE_WALLET_PASSPHRASE,
    )
    return f"{base_url.rstrip('/')}/api/v1/debug/", headers


def _current_status(debug_url: str, headers: dict[str, str], automation_id: str) -> typing.Optional[str]:
    automation = find_automation(_get_debug_payload(debug_url, headers), automation_id)
    return None if automation is None else automation.get("status")


def _create_and_wait_running(
    *,
    debug_url: str,
    headers: dict[str, str],
    user_action: protocol_models.UserAction,
    automation_id: str,
    poll_interval_seconds: float,
    timeout_seconds: float,
) -> None:
    user_action_id = _submit_user_action(debug_url, headers, user_action)
    _wait_for_automation_status(
        debug_url=debug_url,
        headers=headers,
        automation_id=automation_id,
        expected_status=protocol_models.WorkflowStatus.RUNNING,
        user_action_id=user_action_id,
        poll_interval_seconds=poll_interval_seconds,
        timeout_seconds=timeout_seconds,
    )


def _stop_and_wait_completed(
    *,
    debug_url: str,
    headers: dict[str, str],
    automation_id: str,
    poll_interval_seconds: float,
    timeout_seconds: float,
) -> None:
    user_action_id = _submit_user_action(
        debug_url,
        headers,
        agent_seed_protocol_builders.build_stop_automation_user_action(automation_id),
    )
    _wait_for_automation_status(
        debug_url=debug_url,
        headers=headers,
        automation_id=automation_id,
        expected_status=protocol_models.WorkflowStatus.COMPLETED,
        user_action_id=user_action_id,
        poll_interval_seconds=poll_interval_seconds,
        timeout_seconds=timeout_seconds,
    )


def bootstrap_index_automation(
    *,
    base_url: str,
    poll_interval_seconds: float = agent_seed_bootstrap_grid.DEFAULT_POLL_INTERVAL_SECONDS,
    timeout_seconds: float = agent_seed_bootstrap_grid.DEFAULT_TIMEOUT_SECONDS,
) -> None:
    debug_url, headers = _session(base_url)
    automation_id = demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_INDEX_ID
    if _current_status(debug_url, headers, automation_id) == protocol_models.WorkflowStatus.RUNNING.value:
        return
    _create_and_wait_running(
        debug_url=debug_url,
        headers=headers,
        user_action=agent_seed_protocol_builders.build_create_index_automation_user_action(),
        automation_id=automation_id,
        poll_interval_seconds=poll_interval_seconds,
        timeout_seconds=timeout_seconds,
    )


def bootstrap_completed_automation(
    *,
    base_url: str,
    poll_interval_seconds: float = agent_seed_bootstrap_grid.DEFAULT_POLL_INTERVAL_SECONDS,
    timeout_seconds: float = agent_seed_bootstrap_grid.DEFAULT_TIMEOUT_SECONDS,
) -> None:
    debug_url, headers = _session(base_url)
    automation_id = demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_COMPLETED_ID
    status = _current_status(debug_url, headers, automation_id)
    if status == protocol_models.WorkflowStatus.COMPLETED.value:
        return
    if status != protocol_models.WorkflowStatus.RUNNING.value:
        _create_and_wait_running(
            debug_url=debug_url,
            headers=headers,
            user_action=agent_seed_protocol_builders.build_create_index_automation_user_action(
                automation_id=automation_id,
                automation_name=demo_agent_seed_constants.DEMO_AGENT_SEED_COMPLETED_AUTOMATION_DISPLAY_NAME,
            ),
            automation_id=automation_id,
            poll_interval_seconds=poll_interval_seconds,
            timeout_seconds=timeout_seconds,
        )
    _stop_and_wait_completed(
        debug_url=debug_url,
        headers=headers,
        automation_id=automation_id,
        poll_interval_seconds=poll_interval_seconds,
        timeout_seconds=timeout_seconds,
    )


def check_grid_automation_lifecycle(
    *,
    base_url: str,
    poll_interval_seconds: float = agent_seed_bootstrap_grid.DEFAULT_POLL_INTERVAL_SECONDS,
    timeout_seconds: float = agent_seed_bootstrap_grid.DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """
    Stop then restart the seeded grid automation and check it is RUNNING again with its display name.
    Raises AutomationNameLostError when the restarted automation has lost its name.
    """
    debug_url, headers = _session(base_url)
    automation_id = demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID
    if _current_status(debug_url, headers, automation_id) != protocol_models.WorkflowStatus.RUNNING.value:
        agent_seed_bootstrap_grid.bootstrap_grid_automation(
            base_url=base_url,
            poll_interval_seconds=poll_interval_seconds,
            timeout_seconds=timeout_seconds,
        )
    _stop_and_wait_completed(
        debug_url=debug_url,
        headers=headers,
        automation_id=automation_id,
        poll_interval_seconds=poll_interval_seconds,
        timeout_seconds=timeout_seconds,
    )
    restart_action_id = _submit_user_action(
        debug_url,
        headers,
        agent_seed_protocol_builders.build_restart_automation_user_action(automation_id),
    )
    automation = _wait_for_automation_status(
        debug_url=debug_url,
        headers=headers,
        automation_id=automation_id,
        expected_status=protocol_models.WorkflowStatus.RUNNING,
        user_action_id=restart_action_id,
        poll_interval_seconds=poll_interval_seconds,
        timeout_seconds=timeout_seconds,
    )
    expected_name = demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_AUTOMATION_DISPLAY_NAME
    restarted_name = (automation.get("metadata") or {}).get("name")
    if restarted_name != expected_name:
        raise agent_seed_errors.AutomationNameLostError(
            f"Automation {automation_id} is RUNNING after restart but its name is {restarted_name!r}, "
            f"expected {expected_name!r}",
        )


def run_scenarios(
    *,
    base_url: str,
    scenarios: typing.Optional[typing.Iterable[agent_seed_enums.BootstrapScenario]],
    poll_interval_seconds: float = agent_seed_bootstrap_grid.DEFAULT_POLL_INTERVAL_SECONDS,
    timeout_seconds: float = agent_seed_bootstrap_grid.DEFAULT_TIMEOUT_SECONDS,
) -> None:
    common = {
        "base_url": base_url,
        "poll_interval_seconds": poll_interval_seconds,
        "timeout_seconds": timeout_seconds,
    }
    runners = {
        agent_seed_enums.BootstrapScenario.GRID: agent_seed_bootstrap_grid.bootstrap_grid_automation,
        agent_seed_enums.BootstrapScenario.INDEX: bootstrap_index_automation,
        agent_seed_enums.BootstrapScenario.COMPLETED: bootstrap_completed_automation,
        agent_seed_enums.BootstrapScenario.LIFECYCLE: check_grid_automation_lifecycle,
    }
    for scenario in expand_scenarios(scenarios):
        runners[scenario](**common)
