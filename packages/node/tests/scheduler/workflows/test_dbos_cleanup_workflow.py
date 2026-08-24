#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import datetime
import mock
import pytest

import octobot_node.enums

from tests.scheduler import temp_dbos_scheduler

_PARENT_WORKFLOW_ID_A = "741ce171-dac9-40be-83dc-b443c0eaf0e2"


class TestDbosCleanupWorkflowDbosCleanup:
    @pytest.fixture
    def dbos_cleanup_workflow_module(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow_module_loaded

        yield dbos_cleanup_workflow_module_loaded

    @pytest.mark.asyncio
    async def test_delegates_to_cleanup_outdated_automation_executions(self, dbos_cleanup_workflow_module):
        expected_summary = {
            "deleted_by_automation": {_PARENT_WORKFLOW_ID_A: 2},
            "deleted_cleanup_executions": 1,
            "total_deleted": 3,
        }
        with mock.patch(
            "octobot_node.scheduler.workflows.dbos_cleanup_workflow.workflows_retention.should_skip_retention_cleanup_on_this_node",
            return_value=False,
        ), mock.patch(
            "octobot_node.scheduler.workflows.dbos_cleanup_workflow.workflows_retention.should_skip_retention_cleanup_for_scheduled_time",
            mock.AsyncMock(return_value=False),
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention.cleanup_outdated_automation_executions",
            mock.AsyncMock(return_value=expected_summary),
        ) as cleanup_mock, mock.patch(
            "octobot_node.scheduler.workflows_retention.finalize_dbos_cleanup_run",
            mock.AsyncMock(return_value={**expected_summary, "database_size_bytes": 1024, "cleanup_schedule_cron": "0 0 * * *", "cleanup_schedule_updated": False}),
        ) as finalize_mock:
            result = await dbos_cleanup_workflow_module.DbosCleanupWorkflow._cleanup_outdated_automation_executions(
                datetime.datetime.now(datetime.timezone.utc),
            )

        cleanup_mock.assert_awaited_once()
        finalize_mock.assert_awaited_once()
        assert result["total_deleted"] == 3

    @pytest.mark.asyncio
    async def test_skips_cleanup_on_consumer_only(self, dbos_cleanup_workflow_module):
        mock_logger = mock.Mock()
        with mock.patch(
            "octobot_node.scheduler.workflows.dbos_cleanup_workflow.workflows_retention.should_skip_retention_cleanup_on_this_node",
            return_value=True,
        ), mock.patch(
            "octobot_node.scheduler.workflows.dbos_cleanup_workflow.logging.get_logger",
            return_value=mock_logger,
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention.cleanup_outdated_automation_executions",
            mock.AsyncMock(),
        ) as cleanup_mock, mock.patch(
            "octobot_node.scheduler.workflows.dbos_cleanup_workflow.workflows_retention.should_skip_retention_cleanup_for_scheduled_time",
            mock.AsyncMock(),
        ) as skip_for_scheduled_time_mock:
            result = await dbos_cleanup_workflow_module.DbosCleanupWorkflow._cleanup_outdated_automation_executions(
                datetime.datetime.now(datetime.timezone.utc),
            )

        cleanup_mock.assert_not_called()
        skip_for_scheduled_time_mock.assert_not_called()
        mock_logger.info.assert_called_once_with("dbos_cleanup skipped: consumer-only node")
        assert result == {
            "deleted_by_automation": {},
            "deleted_cleanup_executions": 0,
            "deleted_global_view_executions": 0,
            "deleted_portfolio_history_executions": 0,
            "total_deleted": 0,
        }

    @pytest.mark.asyncio
    async def test_skips_cleanup_when_newer_execution_already_ran(self, dbos_cleanup_workflow_module):
        scheduled_time = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
        mock_logger = mock.Mock()
        with mock.patch(
            "octobot_node.scheduler.workflows.dbos_cleanup_workflow.workflows_retention.should_skip_retention_cleanup_on_this_node",
            return_value=False,
        ), mock.patch(
            "octobot_node.scheduler.workflows.dbos_cleanup_workflow.logging.get_logger",
            return_value=mock_logger,
        ), mock.patch(
            "octobot_node.scheduler.workflows.dbos_cleanup_workflow.workflows_retention.should_skip_retention_cleanup_for_scheduled_time",
            mock.AsyncMock(return_value=True),
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention.cleanup_outdated_automation_executions",
            mock.AsyncMock(),
        ) as cleanup_mock:
            result = await dbos_cleanup_workflow_module.DbosCleanupWorkflow._cleanup_outdated_automation_executions(
                scheduled_time,
            )

        cleanup_mock.assert_not_called()
        mock_logger.info.assert_called_once_with(
            "dbos_cleanup skipped for scheduled_time %s: latest completed cleanup is newer",
            scheduled_time.isoformat(),
        )
        assert result == {
            "deleted_by_automation": {},
            "deleted_cleanup_executions": 0,
            "deleted_global_view_executions": 0,
            "deleted_portfolio_history_executions": 0,
            "total_deleted": 0,
        }


class TestDbosCleanupWorkflowGetScheduleInput:
    def test_returns_daily_schedule_input(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow_module

        schedule_input = dbos_cleanup_workflow_module.get_schedule_input()

        assert schedule_input == {
            "schedule_name": dbos_cleanup_workflow_module.SCHEDULE_NAME,
            "workflow_fn": dbos_cleanup_workflow_module.DbosCleanupWorkflow.dbos_cleanup,
            "schedule": dbos_cleanup_workflow_module.SCHEDULE_CRON,
            "context": None,
            "automatic_backfill": True,
            "queue_name": octobot_node.enums.SchedulerQueues.DBOS_CLEANUP_QUEUE.value,
        }

    def test_accepts_custom_cron(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow_module

        schedule_input = dbos_cleanup_workflow_module.get_schedule_input(cron="0 */6 * * *")

        assert schedule_input["schedule"] == "0 */6 * * *"

