#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import datetime
import json
import mock
import pytest
import dbos

import octobot_protocol.models as protocol_models
import octobot_node.enums
import octobot_node.models
import octobot_node.scheduler.scheduler as scheduler_module
import octobot_node.scheduler.workflows.params as params
import octobot_node.scheduler.workflows_retention as workflows_retention

from tests.scheduler import temp_dbos_scheduler

_AUTOMATION_WORKFLOW_NAME = "execute_automation"
_DBOS_CLEANUP_WORKFLOW_NAME = "dbos_cleanup"
_GLOBAL_VIEW_WORKFLOW_NAME = "global_view_refresh"
_PORTFOLIO_HISTORY_WORKFLOW_NAME = "portfolio_history_collection"

_PARENT_WORKFLOW_ID_A = "741ce171-dac9-40be-83dc-b443c0eaf0e2"
_PARENT_WORKFLOW_ID_B = "852df282-edb0-51cf-94ed-c554d1fbf1f3"
_PARENT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _child_workflow_id(parent_id: str, child_index: int) -> str:
    if child_index == 0:
        return parent_id
    return f"{parent_id}_{child_index}"


def _workflow_status_row(
    *,
    workflow_id: str,
    updated_at: int = 0,
    status: str = dbos.WorkflowStatusString.SUCCESS.value,
    name: str = _AUTOMATION_WORKFLOW_NAME,
) -> mock.Mock:
    workflow_status = mock.Mock(spec=dbos.WorkflowStatus)
    workflow_status.workflow_id = workflow_id
    workflow_status.updated_at = updated_at
    workflow_status.status = status
    workflow_status.name = name
    return workflow_status


def _build_mock_workflow_status(
    task: octobot_node.models.Task,
    encrypted_state: str,
    state_metadata: str,
    workflow_id: str = _PARENT_ID,
) -> mock.Mock:
    output = params.AutomationWorkflowOutput(state=encrypted_state, state_metadata=state_metadata)
    inputs = params.AutomationWorkflowInputs(task=task, execution_time=0)
    workflow_status = mock.Mock(spec=dbos.WorkflowStatus)
    workflow_status.workflow_id = workflow_id
    workflow_status.name = "test-task"
    workflow_status.status = dbos.WorkflowStatusString.SUCCESS.value
    workflow_status.output = json.dumps(output.to_dict())
    workflow_status.input = {"args": [inputs.to_dict()], "kwargs": {}}
    workflow_status.created_at = None
    workflow_status.updated_at = None
    return workflow_status


def _build_user_action_workflow_with_output(
    user_action_id: str,
    workflow_id: str,
    user_id: str = "0xw1",
) -> mock.Mock:
    user_action = protocol_models.UserAction(
        id=user_action_id,
        status=protocol_models.UserActionStatus.COMPLETED,
        configuration=None,
    )
    output_payload = params.UserActionWorkflowOutput(
        user_id=user_id,
        updated_user_action=user_action,
    ).to_dict(include_default_values=False)
    workflow_status = mock.Mock(spec=dbos.WorkflowStatus)
    workflow_status.workflow_id = workflow_id
    workflow_status.input = {"args": [], "kwargs": {}}
    workflow_status.output = output_payload
    return workflow_status


def _make_scheduler_with_mock_instance() -> tuple[scheduler_module.Scheduler, mock.AsyncMock]:
    sched = scheduler_module.Scheduler()
    sched.INSTANCE = mock.AsyncMock()
    return sched, sched.INSTANCE


class TestIsTerminalWorkflow:
    def test_returns_true_for_terminal_status(self):
        workflow_status = _workflow_status_row(
            workflow_id="wf-terminal",
            status=dbos.WorkflowStatusString.SUCCESS.value,
        )
        assert workflows_retention.is_terminal_workflow(workflow_status) is True

    def test_returns_false_for_non_terminal_status(self):
        workflow_status = _workflow_status_row(
            workflow_id="wf-pending",
            status=dbos.WorkflowStatusString.PENDING.value,
        )
        assert workflows_retention.is_terminal_workflow(workflow_status) is False


class TestGetOutdatedAutomationExecutionDeletions:
    def test_keeps_latest_two_and_deletes_older_terminal_executions(self):
        now_ms = 10_000_000
        retention_seconds = 100.0
        cutoff_ms = now_ms - int(retention_seconds * 1000)
        workflows = [
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 0),
                updated_at=cutoff_ms - 2,
            ),
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 1),
                updated_at=cutoff_ms - 1,
            ),
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 2),
                updated_at=cutoff_ms + 1,
            ),
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 3),
                updated_at=cutoff_ms + 2,
            ),
        ]

        deletions = workflows_retention.get_outdated_automation_execution_deletions(
            workflows,
            retention_seconds=retention_seconds,
            now_ms=now_ms,
        )

        assert deletions == {
            _PARENT_WORKFLOW_ID_A: [
                _child_workflow_id(_PARENT_WORKFLOW_ID_A, 1),
                _child_workflow_id(_PARENT_WORKFLOW_ID_A, 0),
            ],
        }

    def test_skips_non_terminal_executions(self):
        now_ms = 10_000_000
        retention_seconds = 100.0
        old_updated_at = now_ms - int(retention_seconds * 1000) - 1
        workflows = [
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 0),
                updated_at=old_updated_at,
                status=dbos.WorkflowStatusString.PENDING.value,
            ),
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 1),
                updated_at=old_updated_at,
            ),
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 2),
                updated_at=old_updated_at,
            ),
        ]

        deletions = workflows_retention.get_outdated_automation_execution_deletions(
            workflows,
            retention_seconds=retention_seconds,
            now_ms=now_ms,
        )

        assert deletions == {}

    def test_does_not_delete_recent_terminal_executions_beyond_keep_count(self):
        now_ms = 10_000_000
        retention_seconds = 100.0
        recent_updated_at = now_ms - 1
        workflows = [
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 0),
                updated_at=recent_updated_at,
            ),
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 1),
                updated_at=recent_updated_at + 1,
            ),
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 2),
                updated_at=recent_updated_at + 2,
            ),
        ]

        deletions = workflows_retention.get_outdated_automation_execution_deletions(
            workflows,
            retention_seconds=retention_seconds,
            now_ms=now_ms,
        )

        assert deletions == {}

    def test_isolates_deletions_per_parent(self):
        now_ms = 10_000_000
        retention_seconds = 100.0
        old_updated_at = now_ms - int(retention_seconds * 1000) - 1
        workflows = [
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 0),
                updated_at=old_updated_at,
            ),
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 1),
                updated_at=old_updated_at + 1,
            ),
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 2),
                updated_at=old_updated_at + 2,
            ),
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_B, 0),
                updated_at=old_updated_at,
            ),
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_B, 1),
                updated_at=old_updated_at + 1,
            ),
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_B, 2),
                updated_at=old_updated_at + 2,
            ),
        ]

        deletions = workflows_retention.get_outdated_automation_execution_deletions(
            workflows,
            retention_seconds=retention_seconds,
            now_ms=now_ms,
        )

        assert set(deletions.keys()) == {_PARENT_WORKFLOW_ID_A, _PARENT_WORKFLOW_ID_B}
        assert len(deletions[_PARENT_WORKFLOW_ID_A]) == 1
        assert len(deletions[_PARENT_WORKFLOW_ID_B]) == 1


class TestGetOutdatedDbosCleanupExecutionWorkflowIds:
    def test_deletes_old_terminal_cleanup_runs(self):
        now_ms = 10_000_000
        retention_seconds = 100.0
        old_updated_at = now_ms - int(retention_seconds * 1000) - 1
        cleanup_workflows = [
            _workflow_status_row(
                workflow_id="cleanup-run-1",
                updated_at=old_updated_at,
                name=_DBOS_CLEANUP_WORKFLOW_NAME,
            ),
            _workflow_status_row(
                workflow_id="cleanup-run-2",
                updated_at=now_ms - 1,
                name=_DBOS_CLEANUP_WORKFLOW_NAME,
            ),
        ]

        deleted_ids = workflows_retention.get_outdated_dbos_cleanup_execution_workflow_ids(
            cleanup_workflows,
            retention_seconds=retention_seconds,
            now_ms=now_ms,
        )

        assert deleted_ids == ["cleanup-run-1"]

    def test_skips_non_terminal_cleanup_runs(self):
        now_ms = 10_000_000
        retention_seconds = 100.0
        old_updated_at = now_ms - int(retention_seconds * 1000) - 1
        cleanup_workflows = [
            _workflow_status_row(
                workflow_id="cleanup-run-pending",
                updated_at=old_updated_at,
                status=dbos.WorkflowStatusString.PENDING.value,
                name=_DBOS_CLEANUP_WORKFLOW_NAME,
            ),
        ]

        deleted_ids = workflows_retention.get_outdated_dbos_cleanup_execution_workflow_ids(
            cleanup_workflows,
            retention_seconds=retention_seconds,
            now_ms=now_ms,
        )

        assert deleted_ids == []


class TestGetWorkflowsToDelete:
    @pytest.mark.asyncio
    async def test_merges_automation_and_user_action_ids(self):
        automation_task = octobot_node.models.Task(
            id=_PARENT_ID,
            name="automation-task",
            content="encrypted_content",
            content_metadata="meta",
            type="execute_actions",
        )
        automation_workflow = _build_mock_workflow_status(
            automation_task,
            "encrypted_state",
            None,
            workflow_id=_PARENT_ID,
        )
        user_action_workflow = _build_user_action_workflow_with_output("ua-delete", "wf-ua-delete")

        async def list_workflows_side_effect(**kwargs):
            queue_name = kwargs.get("queue_name")
            if queue_name == [octobot_node.enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE.value]:
                return [automation_workflow]
            if queue_name == [octobot_node.enums.SchedulerQueues.USER_ACTION_QUEUE.value]:
                return [user_action_workflow]
            return []

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(side_effect=list_workflows_side_effect)
        result = await workflows_retention.get_workflows_to_delete(sched, [_PARENT_ID, "ua-delete"])
        assert result == [_PARENT_ID, "wf-ua-delete"]


class TestVacuumDbosSystemDatabase:
    def test_executes_vacuum_on_system_database(self):
        mock_instance = mock.Mock()
        mock_connection = mock.Mock()
        mock_engine = mock.Mock()
        mock_engine.begin.return_value.__enter__ = mock.Mock(return_value=mock_connection)
        mock_engine.begin.return_value.__exit__ = mock.Mock(return_value=False)
        mock_instance._sys_db.engine = mock_engine
        mock_logger = mock.Mock()

        with mock.patch(
            "octobot_node.scheduler.workflows_retention._get_logger",
            return_value=mock_logger,
        ):
            workflows_retention.vacuum_dbos_system_database(mock_instance)

        mock_connection.execute.assert_called_once()
        assert mock_connection.execute.call_args[0][0].text == "VACUUM"
        mock_logger.info.assert_any_call("Vacuuming database")
        mock_logger.info.assert_any_call("Database vacuum completed")


class TestDeleteWorkflowsAndVacuum:
    @pytest.mark.asyncio
    async def test_deletes_workflows_then_vacuums(self):
        mock_instance = mock.Mock()
        mock_instance.delete_workflows_async = mock.AsyncMock()
        mock_connection = mock.Mock()
        mock_engine = mock.Mock()
        mock_engine.begin.return_value.__enter__ = mock.Mock(return_value=mock_connection)
        mock_engine.begin.return_value.__exit__ = mock.Mock(return_value=False)
        mock_instance._sys_db.engine = mock_engine
        mock_logger = mock.Mock()
        workflow_ids = ["wf-a", "wf-b"]

        with mock.patch(
            "octobot_node.scheduler.workflows_retention._get_logger",
            return_value=mock_logger,
        ):
            await workflows_retention.delete_workflows_and_vacuum(
                mock_instance,
                workflow_ids,
            )

        mock_instance.delete_workflows_async.assert_awaited_once_with(
            workflow_ids,
            delete_children=False,
        )
        mock_connection.execute.assert_called_once()
        assert mock_connection.execute.call_args[0][0].text == "VACUUM"
        mock_logger.info.assert_any_call("Deleting %s workflows", len(workflow_ids))
        mock_logger.info.assert_any_call("Vacuuming database")
        mock_logger.info.assert_any_call("Database vacuum completed")


class TestCleanupOutdatedAutomationExecutions:
    @pytest.mark.asyncio
    async def test_returns_per_automation_summary_and_deletes_once(self, temp_dbos_scheduler):
        now_ms = 10_000_000
        retention_seconds = 100.0
        cutoff_ms = now_ms - int(retention_seconds * 1000)
        automation_workflows = [
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 0),
                updated_at=cutoff_ms - 1,
            ),
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 1),
                updated_at=cutoff_ms + 1,
            ),
            _workflow_status_row(
                workflow_id=_child_workflow_id(_PARENT_WORKFLOW_ID_A, 2),
                updated_at=cutoff_ms + 2,
            ),
        ]
        cleanup_workflows = [
            _workflow_status_row(
                workflow_id="cleanup-run-old",
                updated_at=cutoff_ms - 1,
                name=_DBOS_CLEANUP_WORKFLOW_NAME,
            ),
        ]

        sched = scheduler_module.Scheduler()
        mock_instance = mock.Mock()
        mock_instance.list_workflows_async = mock.AsyncMock(
            side_effect=[automation_workflows, cleanup_workflows, [], []]
        )
        mock_instance.delete_workflows_async = mock.AsyncMock()
        mock_engine = mock.Mock()
        mock_connection = mock.Mock()
        mock_engine.begin.return_value.__enter__ = mock.Mock(return_value=mock_connection)
        mock_engine.begin.return_value.__exit__ = mock.Mock(return_value=False)
        mock_instance._sys_db.engine = mock_engine
        sched.INSTANCE = mock_instance
        mock_logger = mock.Mock()

        with mock.patch("octobot_node.scheduler.workflows_retention.time.time", return_value=now_ms / 1000), mock.patch(
            "octobot_node.scheduler.workflows_retention.get_scheduler_database_size_bytes",
            return_value=None,
        ), mock.patch.object(
            workflows_retention,
            "select_retention_seconds_for_database_size",
            return_value=retention_seconds,
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention._get_logger",
            return_value=mock_logger,
        ):
            summary = await workflows_retention.cleanup_outdated_automation_executions(sched)

        assert summary == {
            "deleted_by_automation": {_PARENT_WORKFLOW_ID_A: 1},
            "deleted_cleanup_executions": 1,
            "deleted_global_view_executions": 0,
            "deleted_portfolio_history_executions": 0,
            "total_deleted": 2,
            "database_size_bytes": None,
            "retention_seconds": retention_seconds,
        }
        mock_instance.delete_workflows_async.assert_awaited_once_with(
            [
                _child_workflow_id(_PARENT_WORKFLOW_ID_A, 0),
                "cleanup-run-old",
            ],
            delete_children=False,
        )
        mock_logger.info.assert_any_call(
            "Deleting %s outdated workflow executions: %s automation groups, %s cleanup runs, "
            "%s global view runs, %s portfolio history runs",
            2,
            1,
            1,
            0,
            0,
        )
        mock_logger.info.assert_any_call("DBOS cleanup summary: %s", summary)

    @pytest.mark.asyncio
    async def test_skips_delete_and_vacuum_when_nothing_to_delete(self, temp_dbos_scheduler):
        sched = scheduler_module.Scheduler()
        mock_instance = mock.Mock()
        mock_instance.list_workflows_async = mock.AsyncMock(side_effect=[[], [], [], []])
        mock_instance.delete_workflows_async = mock.AsyncMock()
        mock_instance._sys_db.engine = mock.Mock()
        sched.INSTANCE = mock_instance
        mock_logger = mock.Mock()

        with mock.patch(
            "octobot_node.scheduler.workflows_retention.get_scheduler_database_size_bytes",
            return_value=None,
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention._get_logger",
            return_value=mock_logger,
        ):
            summary = await workflows_retention.cleanup_outdated_automation_executions(sched)

        assert summary == {
            "deleted_by_automation": {},
            "deleted_cleanup_executions": 0,
            "deleted_global_view_executions": 0,
            "deleted_portfolio_history_executions": 0,
            "total_deleted": 0,
            "database_size_bytes": None,
            "retention_seconds": workflows_retention.RETENTION_SECONDS_2_DAYS,
        }
        mock_instance.delete_workflows_async.assert_not_called()
        mock_instance._sys_db.engine.begin.assert_not_called()
        mock_logger.info.assert_called_once_with("DBOS cleanup summary: %s", summary)



class TestShouldSkipRetentionCleanupForScheduledTime:
    @pytest.mark.asyncio
    async def test_returns_true_when_scheduler_not_initialized(self, temp_dbos_scheduler):
        sched = scheduler_module.Scheduler()
        sched.INSTANCE = None

        result = await workflows_retention.should_skip_retention_cleanup_for_scheduled_time(
            sched,
            datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_cleanup_never_ran(self, temp_dbos_scheduler):
        sched = scheduler_module.Scheduler()
        mock_instance = mock.Mock()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[])
        sched.INSTANCE = mock_instance

        result = await workflows_retention.should_skip_retention_cleanup_for_scheduled_time(
            sched,
            datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
        )

        assert result is False
        mock_instance.list_workflows_async.assert_awaited_once_with(
            name="dbos_cleanup",
            status=[dbos.WorkflowStatusString.SUCCESS.value],
            sort_desc=True,
            limit=1,
            load_input=False,
            load_output=False,
        )

    @pytest.mark.asyncio
    async def test_returns_true_when_latest_cleanup_is_newer_than_scheduled_time(self, temp_dbos_scheduler):
        scheduled_time = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
        latest_cleanup = mock.Mock(spec=dbos.WorkflowStatus)
        latest_cleanup.status = dbos.WorkflowStatusString.SUCCESS.value
        latest_cleanup.updated_at = int(datetime.datetime(2025, 1, 2, tzinfo=datetime.timezone.utc).timestamp() * 1000)
        latest_cleanup.created_at = 0

        sched = scheduler_module.Scheduler()
        mock_instance = mock.Mock()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[latest_cleanup])
        sched.INSTANCE = mock_instance

        result = await workflows_retention.should_skip_retention_cleanup_for_scheduled_time(
            sched,
            scheduled_time,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_latest_cleanup_is_older_than_scheduled_time(self, temp_dbos_scheduler):
        scheduled_time = datetime.datetime(2025, 1, 2, tzinfo=datetime.timezone.utc)
        latest_cleanup = mock.Mock(spec=dbos.WorkflowStatus)
        latest_cleanup.status = dbos.WorkflowStatusString.SUCCESS.value
        latest_cleanup.updated_at = int(datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc).timestamp() * 1000)
        latest_cleanup.created_at = 0

        sched = scheduler_module.Scheduler()
        mock_instance = mock.Mock()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[latest_cleanup])
        sched.INSTANCE = mock_instance

        result = await workflows_retention.should_skip_retention_cleanup_for_scheduled_time(
            sched,
            scheduled_time,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_latest_non_terminal_cleanup_is_newer_than_scheduled_time(
        self,
        temp_dbos_scheduler,
    ):
        scheduled_time = datetime.datetime(2026, 7, 15, 0, 0, 0, tzinfo=datetime.timezone.utc)

        sched = scheduler_module.Scheduler()
        mock_instance = mock.Mock()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[])
        sched.INSTANCE = mock_instance

        result = await workflows_retention.should_skip_retention_cleanup_for_scheduled_time(
            sched,
            scheduled_time,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_latest_terminal_cleanup_is_older_than_backfilled_slot(
        self,
        temp_dbos_scheduler,
    ):
        scheduled_time = datetime.datetime(2026, 7, 15, 0, 0, 0, tzinfo=datetime.timezone.utc)
        latest_cleanup = mock.Mock(spec=dbos.WorkflowStatus)
        latest_cleanup.status = dbos.WorkflowStatusString.SUCCESS.value
        latest_cleanup.updated_at = int(
            datetime.datetime(2026, 7, 7, 20, 16, 40, tzinfo=datetime.timezone.utc).timestamp() * 1000,
        )
        latest_cleanup.created_at = 0

        sched = scheduler_module.Scheduler()
        mock_instance = mock.Mock()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[latest_cleanup])
        sched.INSTANCE = mock_instance

        result = await workflows_retention.should_skip_retention_cleanup_for_scheduled_time(
            sched,
            scheduled_time,
        )

        assert result is False


class TestGetOutdatedTerminalWorkflowIds:
    def test_deletes_old_terminal_workflows(self):
        now_ms = 10_000_000
        retention_seconds = 100.0
        old_updated_at = now_ms - int(retention_seconds * 1000) - 1
        workflows = [
            _workflow_status_row(
                workflow_id="global-view-old",
                updated_at=old_updated_at,
                name=_GLOBAL_VIEW_WORKFLOW_NAME,
            ),
            _workflow_status_row(
                workflow_id="global-view-recent",
                updated_at=now_ms - 1,
                name=_GLOBAL_VIEW_WORKFLOW_NAME,
            ),
        ]

        deleted_ids = workflows_retention.get_outdated_terminal_workflow_ids(
            workflows,
            retention_seconds=retention_seconds,
            now_ms=now_ms,
        )

        assert deleted_ids == ["global-view-old"]

    def test_skips_non_terminal_workflows(self):
        now_ms = 10_000_000
        retention_seconds = 100.0
        old_updated_at = now_ms - int(retention_seconds * 1000) - 1
        workflows = [
            _workflow_status_row(
                workflow_id="portfolio-history-pending",
                updated_at=old_updated_at,
                status=dbos.WorkflowStatusString.PENDING.value,
                name=_PORTFOLIO_HISTORY_WORKFLOW_NAME,
            ),
        ]

        deleted_ids = workflows_retention.get_outdated_terminal_workflow_ids(
            workflows,
            retention_seconds=retention_seconds,
            now_ms=now_ms,
        )

        assert deleted_ids == []


class TestSelectRetentionSecondsForDatabaseSize:
    def test_returns_2_day_retention_when_size_unknown(self):
        assert workflows_retention.select_retention_seconds_for_database_size(None) == workflows_retention.RETENTION_SECONDS_2_DAYS

    def test_returns_2_day_retention_below_first_tier(self):
        size_bytes = workflows_retention.DBOS_CLEANUP_SIZE_TIER_1_BYTES - 1
        assert workflows_retention.select_retention_seconds_for_database_size(size_bytes) == workflows_retention.RETENTION_SECONDS_2_DAYS

    def test_returns_1_day_retention_between_tiers(self):
        size_bytes = workflows_retention.DBOS_CLEANUP_SIZE_TIER_1_BYTES
        assert workflows_retention.select_retention_seconds_for_database_size(size_bytes) == workflows_retention.RETENTION_SECONDS_1_DAY

    def test_returns_6_hour_retention_at_second_tier(self):
        size_bytes = workflows_retention.DBOS_CLEANUP_SIZE_TIER_2_BYTES
        assert workflows_retention.select_retention_seconds_for_database_size(size_bytes) == workflows_retention.RETENTION_SECONDS_6_HOURS


class TestSelectCleanupCronForDatabaseSize:
    def test_returns_daily_cron_when_size_unknown(self):
        assert workflows_retention.select_cleanup_cron_for_database_size(None) == workflows_retention.DBOS_CLEANUP_CRON_DAILY

    def test_returns_daily_cron_below_first_tier(self):
        size_bytes = workflows_retention.DBOS_CLEANUP_SIZE_TIER_1_BYTES - 1
        assert workflows_retention.select_cleanup_cron_for_database_size(size_bytes) == workflows_retention.DBOS_CLEANUP_CRON_DAILY

    def test_returns_12h_cron_between_tiers(self):
        size_bytes = workflows_retention.DBOS_CLEANUP_SIZE_TIER_1_BYTES
        assert workflows_retention.select_cleanup_cron_for_database_size(size_bytes) == workflows_retention.DBOS_CLEANUP_CRON_12H

    def test_returns_6h_cron_at_second_tier(self):
        size_bytes = workflows_retention.DBOS_CLEANUP_SIZE_TIER_2_BYTES
        assert workflows_retention.select_cleanup_cron_for_database_size(size_bytes) == workflows_retention.DBOS_CLEANUP_CRON_6H


class TestGetSchedulerDatabaseSizeBytes:
    def test_sums_sqlite_file_and_sidecars(self, tmp_path):
        sqlite_path = tmp_path / "tasks.db"
        sqlite_path.write_bytes(b"x" * 10)
        wal_path = tmp_path / "tasks.db-wal"
        wal_path.write_bytes(b"y" * 5)
        mock_dbos_instance = mock.Mock()

        with mock.patch(
            "octobot_node.config.settings.SCHEDULER_SQLITE_FILE",
            str(sqlite_path),
        ), mock.patch(
            "octobot_node.config.settings.SCHEDULER_POSTGRES_URL",
            None,
        ):
            size_bytes = workflows_retention.get_scheduler_database_size_bytes(mock_dbos_instance)

        assert size_bytes == 15

    def test_returns_none_when_sqlite_file_missing(self):
        mock_dbos_instance = mock.Mock()
        mock_logger = mock.Mock()
        with mock.patch(
            "octobot_node.config.settings.SCHEDULER_SQLITE_FILE",
            "missing-tasks.db",
        ), mock.patch(
            "octobot_node.config.settings.SCHEDULER_POSTGRES_URL",
            None,
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention._get_logger",
            return_value=mock_logger,
        ):
            size_bytes = workflows_retention.get_scheduler_database_size_bytes(mock_dbos_instance)

        assert size_bytes is None
        mock_logger.exception.assert_called_once()


class TestCleanupOutdatedAutomationExecutionsScheduledWorkflows:
    @pytest.mark.asyncio
    async def test_deletes_outdated_global_view_and_portfolio_history_workflows(self, temp_dbos_scheduler):
        now_ms = 10_000_000
        retention_seconds = 100.0
        cutoff_ms = now_ms - int(retention_seconds * 1000)
        global_view_workflows = [
            _workflow_status_row(
                workflow_id="global-view-old",
                updated_at=cutoff_ms - 1,
                name=_GLOBAL_VIEW_WORKFLOW_NAME,
            ),
        ]
        portfolio_history_workflows = [
            _workflow_status_row(
                workflow_id="portfolio-history-old",
                updated_at=cutoff_ms - 1,
                name=_PORTFOLIO_HISTORY_WORKFLOW_NAME,
            ),
        ]

        sched = scheduler_module.Scheduler()
        mock_instance = mock.Mock()
        mock_instance.list_workflows_async = mock.AsyncMock(
            side_effect=[[], [], global_view_workflows, portfolio_history_workflows]
        )
        mock_instance.delete_workflows_async = mock.AsyncMock()
        mock_connection = mock.Mock()
        mock_engine = mock.Mock()
        mock_engine.begin.return_value.__enter__ = mock.Mock(return_value=mock_connection)
        mock_engine.begin.return_value.__exit__ = mock.Mock(return_value=False)
        mock_instance._sys_db.engine = mock_engine
        sched.INSTANCE = mock_instance

        with mock.patch("octobot_node.scheduler.workflows_retention.time.time", return_value=now_ms / 1000), mock.patch(
            "octobot_node.scheduler.workflows_retention.get_scheduler_database_size_bytes",
            return_value=None,
        ), mock.patch.object(
            workflows_retention,
            "select_retention_seconds_for_database_size",
            return_value=retention_seconds,
        ):
            summary = await workflows_retention.cleanup_outdated_automation_executions(sched)

        assert summary["deleted_global_view_executions"] == 1
        assert summary["deleted_portfolio_history_executions"] == 1
        assert summary["total_deleted"] == 2
        assert summary["retention_seconds"] == retention_seconds
        mock_instance.delete_workflows_async.assert_awaited_once_with(
            ["global-view-old", "portfolio-history-old"],
            delete_children=False,
        )

    @pytest.mark.asyncio
    async def test_uses_shorter_retention_when_database_is_large(self, temp_dbos_scheduler):
        now_ms = 10_000_000
        six_hour_retention_seconds = workflows_retention.RETENTION_SECONDS_6_HOURS
        twelve_hours_ms = int(12 * 60 * 60 * 1000)
        updated_at_ms = now_ms - twelve_hours_ms
        global_view_workflows = [
            _workflow_status_row(
                workflow_id="global-view-12h-old",
                updated_at=updated_at_ms,
                name=_GLOBAL_VIEW_WORKFLOW_NAME,
            ),
        ]

        sched = scheduler_module.Scheduler()
        mock_instance = mock.Mock()
        mock_instance.list_workflows_async = mock.AsyncMock(
            side_effect=[[], [], global_view_workflows, []]
        )
        mock_instance.delete_workflows_async = mock.AsyncMock()
        mock_instance._sys_db.engine = mock.Mock()
        sched.INSTANCE = mock_instance
        large_database_size_bytes = workflows_retention.DBOS_CLEANUP_SIZE_TIER_2_BYTES
        mock_logger = mock.Mock()

        with mock.patch("octobot_node.scheduler.workflows_retention.time.time", return_value=now_ms / 1000), mock.patch(
            "octobot_node.scheduler.workflows_retention.get_scheduler_database_size_bytes",
            return_value=large_database_size_bytes,
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention._get_logger",
            return_value=mock_logger,
        ):
            summary = await workflows_retention.cleanup_outdated_automation_executions(sched)

        assert summary["retention_seconds"] == six_hour_retention_seconds
        assert summary["database_size_bytes"] == large_database_size_bytes
        assert summary["deleted_global_view_executions"] == 1
        assert summary["total_deleted"] == 1
        mock_instance.delete_workflows_async.assert_awaited_once_with(
            ["global-view-12h-old"],
            delete_children=False,
        )
        mock_logger.info.assert_any_call(
            "Using retention %s s for database size %s bytes",
            six_hour_retention_seconds,
            large_database_size_bytes,
        )


class TestFinalizeDbosCleanupRun:
    @pytest.mark.asyncio
    async def test_adds_size_and_updates_schedule(self, temp_dbos_scheduler):
        sched = scheduler_module.Scheduler()
        mock_instance = mock.Mock()
        sched.INSTANCE = mock_instance
        cleanup_summary = {
            "deleted_by_automation": {},
            "deleted_cleanup_executions": 0,
            "deleted_global_view_executions": 0,
            "deleted_portfolio_history_executions": 0,
            "total_deleted": 0,
        }

        with mock.patch(
            "octobot_node.scheduler.workflows_retention.get_scheduler_database_size_bytes",
            return_value=workflows_retention.DBOS_CLEANUP_SIZE_TIER_1_BYTES,
        ), mock.patch(
            "octobot_node.scheduler.schedules.update_cleanup_schedule_cron",
            mock.AsyncMock(return_value={"changed": True, "cron": workflows_retention.DBOS_CLEANUP_CRON_12H}),
        ) as update_schedule_mock:
            summary = await workflows_retention.finalize_dbos_cleanup_run(sched, cleanup_summary)

        assert summary["database_size_bytes"] == workflows_retention.DBOS_CLEANUP_SIZE_TIER_1_BYTES
        assert summary["cleanup_schedule_cron"] == workflows_retention.DBOS_CLEANUP_CRON_12H
        assert summary["cleanup_schedule_updated"] is True
        update_schedule_mock.assert_awaited_once_with(
            sched,
            workflows_retention.DBOS_CLEANUP_CRON_12H,
        )

    @pytest.mark.asyncio
    async def test_vacuums_when_workflows_were_deleted(self, temp_dbos_scheduler):
        sched = scheduler_module.Scheduler()
        mock_instance = mock.Mock()
        mock_connection = mock.Mock()
        mock_engine = mock.Mock()
        mock_engine.begin.return_value.__enter__ = mock.Mock(return_value=mock_connection)
        mock_engine.begin.return_value.__exit__ = mock.Mock(return_value=False)
        mock_instance._sys_db.engine = mock_engine
        sched.INSTANCE = mock_instance

        with mock.patch(
            "octobot_node.scheduler.workflows_retention.get_scheduler_database_size_bytes",
            return_value=0,
        ), mock.patch(
            "octobot_node.scheduler.schedules.update_cleanup_schedule_cron",
            mock.AsyncMock(return_value={"changed": False, "cron": workflows_retention.DBOS_CLEANUP_CRON_DAILY}),
        ):
            await workflows_retention.finalize_dbos_cleanup_run(
                sched,
                {"total_deleted": 3},
            )

        mock_connection.execute.assert_called_once()
        assert mock_connection.execute.call_args[0][0].text == "VACUUM"

    @pytest.mark.asyncio
    async def test_vacuums_when_large_database_and_nothing_deleted(self, temp_dbos_scheduler):
        sched = scheduler_module.Scheduler()
        mock_instance = mock.Mock()
        mock_connection = mock.Mock()
        mock_engine = mock.Mock()
        mock_engine.begin.return_value.__enter__ = mock.Mock(return_value=mock_connection)
        mock_engine.begin.return_value.__exit__ = mock.Mock(return_value=False)
        mock_instance._sys_db.engine = mock_engine
        sched.INSTANCE = mock_instance

        with mock.patch(
            "octobot_node.scheduler.workflows_retention.get_scheduler_database_size_bytes",
            return_value=workflows_retention.DBOS_CLEANUP_SIZE_TIER_2_BYTES,
        ), mock.patch(
            "octobot_node.scheduler.schedules.update_cleanup_schedule_cron",
            mock.AsyncMock(return_value={"changed": False, "cron": workflows_retention.DBOS_CLEANUP_CRON_6H}),
        ):
            await workflows_retention.finalize_dbos_cleanup_run(
                sched,
                {"total_deleted": 0},
            )

        mock_connection.execute.assert_called_once()
        assert mock_connection.execute.call_args[0][0].text == "VACUUM"
