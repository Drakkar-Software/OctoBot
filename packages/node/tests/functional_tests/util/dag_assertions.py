#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
"""DAG assertion helpers for node DBOS functional workflow tests."""

from __future__ import annotations

import asyncio
import time
import typing

import pytest

import octobot_flow.enums as octobot_flow_enums_module
import octobot_node.scheduler.workflows_util as workflows_util_module

from . import workflow_common as workflow_common_module


def actions_dag_from_workflow_row(workflow_row: typing.Any):
    state_reader = workflows_util_module.get_automation_state_reader(workflow_row)
    if state_reader is None:
        return None
    return state_reader.state.automation.actions_dag


def _evaluator_results(action) -> list[dict]:
    if action.result is None:
        return []
    if isinstance(action.result, list):
        return action.result
    return [action.result]


def evaluator_result_for_symbol(action, symbol: str) -> dict:
    matching_results = [
        evaluator_result
        for evaluator_result in _evaluator_results(action)
        if evaluator_result.get("symbol") == symbol
    ]
    assert len(matching_results) == 1, (
        f"Expected one evaluator result for {symbol}, got {matching_results}"
    )
    return matching_results[0]


def assert_evaluator_results_for_symbols(
    action,
    *,
    eval_note_by_symbol: dict[str, float],
    evaluator_name: str,
    time_frame: str,
) -> None:
    assert len(_evaluator_results(action)) == len(eval_note_by_symbol)
    for symbol, expected_eval_note in eval_note_by_symbol.items():
        evaluator_result = evaluator_result_for_symbol(action, symbol)
        assert float(evaluator_result["eval_note"]) == float(expected_eval_note)
        assert evaluator_result["evaluator_name"] == evaluator_name
        assert evaluator_result["time_frame"] == time_frame


def assert_dag_action(
    actions_dag,
    action_id: str,
    *,
    completed: bool,
    error_status: str = octobot_flow_enums_module.ActionErrorStatus.NO_ERROR.value,
    result_is_none: bool | None = None,
    previous_result_is_none: bool | None = None,
) -> None:
    action = actions_dag.get_actions_by_id()[action_id]
    assert action.error_status == error_status
    assert action.is_completed() == completed
    if result_is_none is not None:
        assert (action.result is None) == result_is_none
    if previous_result_is_none is not None:
        assert (action.previous_execution_result is None) == previous_result_is_none


def assert_dag_snapshot(actions_dag, expected: dict[str, dict]) -> None:
    for action_id, assertion_kwargs in expected.items():
        assert_dag_action(actions_dag, action_id, **assertion_kwargs)


async def wait_for_workflow_matching_automation_id(
    scheduler: typing.Any,
    automation_id: str,
    *,
    timeout_seconds: float,
    poll_interval_seconds: float = workflow_common_module.DEFAULT_WORKFLOW_POLL_INTERVAL_SECONDS,
) -> typing.Any | None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        for workflow_row in await scheduler.INSTANCE.list_workflows_async():
            if workflows_util_module.get_automation_id(workflow_row) != automation_id:
                continue
            if workflows_util_module.get_automation_state_reader(workflow_row) is not None:
                return workflow_row
        await asyncio.sleep(poll_interval_seconds)
    return None


async def wait_for_executable_action_ids(
    scheduler: typing.Any,
    automation_id: str,
    expected_executable_action_ids: set[str],
    *,
    timeout_seconds: float,
) -> typing.Any:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        for workflow_row in await scheduler.INSTANCE.list_workflows_async():
            if workflows_util_module.get_automation_id(workflow_row) != automation_id:
                continue
            actions_dag = actions_dag_from_workflow_row(workflow_row)
            if actions_dag is None:
                continue
            executable_action_ids = {
                action.id for action in actions_dag.get_executable_actions()
            }
            if executable_action_ids == expected_executable_action_ids:
                return workflow_row
        await asyncio.sleep(workflow_common_module.DEFAULT_WORKFLOW_POLL_INTERVAL_SECONDS)
    pytest.fail(
        f"Timed out waiting for executable actions {sorted(expected_executable_action_ids)!r} "
        f"for automation {automation_id!r}"
    )


async def wait_for_dag_snapshot(
    scheduler: typing.Any,
    automation_id: str,
    expected_snapshot: dict[str, dict],
    *,
    timeout_seconds: float,
) -> typing.Any:
    deadline = time.monotonic() + timeout_seconds
    last_actions_dag = None
    while time.monotonic() < deadline:
        for workflow_row in await scheduler.INSTANCE.list_workflows_async():
            if workflows_util_module.get_automation_id(workflow_row) != automation_id:
                continue
            actions_dag = actions_dag_from_workflow_row(workflow_row)
            if actions_dag is None:
                continue
            last_actions_dag = actions_dag
            try:
                assert_dag_snapshot(actions_dag, expected_snapshot)
            except AssertionError:
                continue
            return workflow_row
        await asyncio.sleep(workflow_common_module.DEFAULT_WORKFLOW_POLL_INTERVAL_SECONDS)
    pytest.fail(
        f"Timed out waiting for DAG snapshot {expected_snapshot!r} for automation {automation_id!r}; "
        f"last dag actions: "
        f"{list(last_actions_dag.get_actions_by_id()) if last_actions_dag is not None else None}"
    )
