#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
"""User-action completion assertion helpers for workflow functional tests."""

from __future__ import annotations

import datetime

import octobot_protocol.models as protocol_models_module

import octobot_node.scheduler


def resolve_create_automation_metadata_id(
    user_action: protocol_models_module.UserAction,
) -> str:
    """Metadata automation_id: configuration.id when set, else user_action.id."""
    wrapper = user_action.configuration
    if wrapper is None or wrapper.actual_instance is None:
        return user_action.id
    payload = wrapper.actual_instance
    if not isinstance(payload, protocol_models_module.CreateAutomationConfiguration):
        return user_action.id
    configuration = payload.configuration
    if configuration is not None and configuration.id:
        return configuration.id
    return user_action.id


def merge_user_actions_latest_per_id(
    user_actions: list[protocol_models_module.UserAction],
) -> dict[str, protocol_models_module.UserAction]:
    grouped: dict[str, list[protocol_models_module.UserAction]] = {}
    for user_action in user_actions:
        grouped.setdefault(user_action.id, []).append(user_action)
    min_utc = datetime.datetime.min.replace(tzinfo=datetime.UTC)

    def activity_stamp(user_action: protocol_models_module.UserAction) -> datetime.datetime:
        stamp = user_action.updated_at or user_action.created_at
        if stamp is None:
            return min_utc
        if stamp.tzinfo is None:
            return stamp.replace(tzinfo=datetime.UTC)
        return stamp

    return {
        user_action_id: max(group, key=activity_stamp)
        for user_action_id, group in grouped.items()
    }


def workflow_row_id_matches_user_action_selector_created_automation_id(
    *,
    workflow_row_id: str,
    user_action_selector_created_automation_id: str | None,
) -> None:
    assert user_action_selector_created_automation_id
    assert (
        workflow_row_id == user_action_selector_created_automation_id
        or workflow_row_id.startswith(f"{user_action_selector_created_automation_id}_")
    ), (
        f"workflow row id {workflow_row_id!r} should equal or extend user action selector created_automation_id "
        f"{user_action_selector_created_automation_id!r}"
    )


async def assert_user_action_selector_completed_automation_create(
    *,
    user_action_id: str,
    user_id: str,
    expected_workflow_id: str | None,
) -> None:
    listed = await octobot_node.scheduler.SCHEDULER.list_user_actions(user_id)
    by_id = merge_user_actions_latest_per_id(listed)
    assert user_action_id in by_id, f"expected {user_action_id!r} in user action workflows, got {sorted(by_id)!r}"
    stored = by_id[user_action_id]
    assert stored.status == protocol_models_module.UserActionStatus.COMPLETED
    assert stored.result is not None
    inner = stored.result.actual_instance
    assert isinstance(inner, protocol_models_module.AutomationActionResult)
    assert inner.result_type == protocol_models_module.UserActionResultType.AUTOMATION
    assert inner.error_details is None
    assert inner.error_message is None
    if expected_workflow_id is not None:
        assert inner.created_automation_id
        workflow_row_id_matches_user_action_selector_created_automation_id(
            workflow_row_id=expected_workflow_id,
            user_action_selector_created_automation_id=inner.created_automation_id,
        )
    else:
        assert inner.created_automation_id
        assert len(inner.created_automation_id) > 0


async def get_created_automation_id_from_user_action(
    *,
    user_action_id: str,
    user_id: str,
) -> str:
    listed = await octobot_node.scheduler.SCHEDULER.list_user_actions(user_id)
    by_id = merge_user_actions_latest_per_id(listed)
    stored = by_id[user_action_id]
    assert stored.result is not None
    inner = stored.result.actual_instance
    assert isinstance(inner, protocol_models_module.AutomationActionResult)
    assert inner.created_automation_id
    return inner.created_automation_id


async def assert_user_action_selector_completed_automation_stop(
    *,
    user_action_id: str,
    user_id: str,
) -> None:
    listed = await octobot_node.scheduler.SCHEDULER.list_user_actions(user_id)
    by_id = merge_user_actions_latest_per_id(listed)
    assert user_action_id in by_id, f"expected {user_action_id!r} in user action workflows, got {sorted(by_id)!r}"
    stored = by_id[user_action_id]
    assert stored.status == protocol_models_module.UserActionStatus.COMPLETED
    assert stored.result is not None
    inner = stored.result.actual_instance
    assert isinstance(inner, protocol_models_module.AutomationActionResult)
    assert inner.result_type == protocol_models_module.UserActionResultType.AUTOMATION
    assert inner.error_details is None
    assert inner.error_message is None


async def assert_user_action_selector_completed_automation_signal(
    *,
    user_action_id: str,
    user_id: str,
) -> None:
    listed = await octobot_node.scheduler.SCHEDULER.list_user_actions(user_id)
    by_id = merge_user_actions_latest_per_id(listed)
    assert user_action_id in by_id, f"expected {user_action_id!r} in user action workflows, got {sorted(by_id)!r}"
    stored = by_id[user_action_id]
    assert stored.status == protocol_models_module.UserActionStatus.COMPLETED
    assert stored.result is not None
    inner = stored.result.actual_instance
    assert isinstance(inner, protocol_models_module.AutomationActionResult)
    assert inner.result_type == protocol_models_module.UserActionResultType.AUTOMATION
    assert inner.error_details is None
    assert inner.error_message is None
