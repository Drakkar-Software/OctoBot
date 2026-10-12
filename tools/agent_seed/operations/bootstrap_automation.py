#  Shared debug automation lookup and id conflict checks for bootstrap scenarios.

import typing

import octobot_protocol.models as protocol_models

import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.operations.scheduler_sqlite as agent_seed_scheduler_sqlite


def find_automation(debug_payload: dict, automation_id: str) -> typing.Optional[dict]:
    debug_section = debug_payload.get("debug") or {}
    for automation in debug_section.get("automations") or []:
        if automation.get("id") == automation_id:
            return automation
    return None


def automation_is_running(debug_payload: dict, automation_id: str) -> bool:
    automation = find_automation(debug_payload, automation_id)
    if automation is None:
        return False
    return automation.get("status") == protocol_models.WorkflowStatus.RUNNING.value


def format_automation_id_conflict_error(
    automation_id: str,
    automation: dict,
    scheduler_sqlite_file: str,
) -> str:
    status = automation.get("status", "<unknown>")
    return (
        f"Automation bootstrap blocked: an automation with id {automation_id} already exists "
        f"with status {status!r} (expected no record or RUNNING). "
        f"The node scheduler database is {scheduler_sqlite_file!r}. "
        "Stop the OctoBot node, then run `bash .cursor/seed-agent.sh --clear` to wipe that "
        "database and user folder, or ensure SCHEDULER_SQLITE_FILE matches NODE_SQLITE_FILE "
        "(see tools/agent_seed/README.md)."
    )


def _raise_automation_id_conflict(automation_id: str, automation: dict) -> None:
    raise agent_seed_errors.AutomationIdConflictError(
        format_automation_id_conflict_error(
            automation_id,
            automation,
            agent_seed_scheduler_sqlite.scheduler_sqlite_path_for_errors(),
        ),
    )


def ensure_automation_id_available_for_create(debug_payload: dict, automation_id: str) -> None:
    automation = find_automation(debug_payload, automation_id)
    if automation is None:
        return
    status = automation.get("status")
    if status == protocol_models.WorkflowStatus.RUNNING.value:
        return
    _raise_automation_id_conflict(automation_id, automation)


def ensure_automation_not_stale_while_waiting_running(
    debug_payload: dict,
    automation_id: str,
) -> None:
    """After automation_create: allow in-flight pending/scheduled; fail on terminal stale rows."""
    automation = find_automation(debug_payload, automation_id)
    if automation is None:
        return
    status = automation.get("status")
    if status in (
        protocol_models.WorkflowStatus.RUNNING.value,
        protocol_models.WorkflowStatus.PENDING.value,
        protocol_models.WorkflowStatus.SCHEDULED.value,
        protocol_models.WorkflowStatus.PERIODIC.value,
    ):
        return
    _raise_automation_id_conflict(automation_id, automation)
