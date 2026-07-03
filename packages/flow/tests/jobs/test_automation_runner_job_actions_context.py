#  Drakkar-Software OctoBot-Flow

import contextlib
import time
import typing

import mock
import pytest

import octobot_flow.entities
import octobot_flow.entities.actions.action_details as action_details
import octobot_flow.jobs.automation_runner_job as automation_runner_job_module


def _automation_state() -> octobot_flow.entities.AutomationState:
    return octobot_flow.entities.AutomationState.from_dict(
        {
            "exchange_account_details": {
                "exchange_details": {"internal_name": "binanceus"},
                "auth_details": {},
                "portfolio": {},
            },
            "automation": {
                "metadata": {"automation_id": "automation_1"},
                "actions_dag": {"actions": []},
            },
        }
    )


def _fetched_dependencies(*, skip_exchange: bool = False) -> octobot_flow.entities.FetchedDependencies:
    return octobot_flow.entities.FetchedDependencies(skip_exchange=skip_exchange)


def _runner_job(
    *,
    skip_exchange: bool = False,
    automation_state: octobot_flow.entities.AutomationState | None = None,
) -> automation_runner_job_module.AutomationRunnerJob:
    return automation_runner_job_module.AutomationRunnerJob(
        automation_state or _automation_state(),
        _fetched_dependencies(skip_exchange=skip_exchange),
        None,
        0.0,
    )


def _dsl_action(dsl_script: str) -> action_details.DSLScriptActionDetails:
    return action_details.DSLScriptActionDetails(
        id="action_dsl",
        dsl_script=dsl_script,
        dependencies=[],
        resolved_dsl_script=dsl_script,
    )


@contextlib.asynccontextmanager
async def _track_exchange_manager_context(
    entered_calls: list[bool],
) -> typing.AsyncGenerator[None, None]:
    @contextlib.asynccontextmanager
    async def counting_exchange_manager_context(self):
        entered_calls.append(True)
        self._exchange_manager = mock.Mock()
        yield self._exchange_manager

    with mock.patch.object(
        automation_runner_job_module.AutomationRunnerJob,
        "exchange_manager_context",
        counting_exchange_manager_context,
    ):
        yield


def _automation_state_with_dag(
    *dag_actions: action_details.AbstractActionDetails,
) -> octobot_flow.entities.AutomationState:
    automation_state = _automation_state()
    automation_state.automation.actions_dag.actions = list(dag_actions)
    return automation_state


class TestAutomationRunnerJobActionsContext:
    @pytest.mark.asyncio
    async def test_skips_exchange_manager_for_process_bound_actions(self):
        runner_job = _runner_job(skip_exchange=True)
        entered_calls: list[bool] = []
        process_bound_action = _dsl_action(
            "run_octobot_process('bots/b1', user_id='user_1', waiting_time=1.0, ping_timeout=30.0)"
        )

        async with _track_exchange_manager_context(entered_calls):
            async with runner_job.actions_context([process_bound_action], True):
                pass

        assert entered_calls == []
        assert runner_job._exchange_manager is None

    @pytest.mark.asyncio
    async def test_enters_exchange_manager_for_non_process_bound_dsl_action(self):
        runner_job = _runner_job()
        entered_calls: list[bool] = []
        wait_action = _dsl_action("wait(1.0, 1.0)")

        async with _track_exchange_manager_context(entered_calls):
            async with runner_job.actions_context([wait_action], True):
                pass

        assert len(entered_calls) == 1

    @pytest.mark.asyncio
    async def test_enters_exchange_manager_for_configured_action(self):
        runner_job = _runner_job()
        entered_calls: list[bool] = []
        configured_action = action_details.ConfiguredActionDetails(id="action_init")

        async with _track_exchange_manager_context(entered_calls):
            async with runner_job.actions_context([configured_action], True):
                pass

        assert len(entered_calls) == 1

    @pytest.mark.asyncio
    async def test_enters_exchange_manager_for_empty_actions(self):
        runner_job = _runner_job()
        entered_calls: list[bool] = []

        async with _track_exchange_manager_context(entered_calls):
            async with runner_job.actions_context([], True):
                pass

        assert len(entered_calls) == 1

    @pytest.mark.asyncio
    async def test_skips_exchange_manager_for_stop_automation_on_process_bound_dag(self):
        process_bound_dag_action = _dsl_action(
            "run_octobot_process('bots/b1', user_id='user_1', waiting_time=1.0, ping_timeout=30.0)"
        )
        runner_job = _runner_job(
            skip_exchange=True,
            automation_state=_automation_state_with_dag(process_bound_dag_action),
        )
        entered_calls: list[bool] = []
        stop_automation_action = _dsl_action("stop_automation()")

        async with _track_exchange_manager_context(entered_calls):
            async with runner_job.actions_context([stop_automation_action], True):
                pass

        assert entered_calls == []
        assert runner_job._exchange_manager is None

    @pytest.mark.asyncio
    async def test_skips_exchange_manager_for_stop_automation_when_dag_action_between_recalls(self):
        process_bound_dag_action = _dsl_action(
            "run_octobot_process('bots/b1', user_id='user_1', waiting_time=1.0, ping_timeout=30.0)"
        )
        process_bound_dag_action.executed_at = time.time()
        runner_job = _runner_job(
            skip_exchange=True,
            automation_state=_automation_state_with_dag(process_bound_dag_action),
        )
        entered_calls: list[bool] = []
        stop_automation_action = _dsl_action("stop_automation()")

        async with _track_exchange_manager_context(entered_calls):
            async with runner_job.actions_context([stop_automation_action], True):
                pass

        assert entered_calls == []
        assert runner_job._exchange_manager is None
