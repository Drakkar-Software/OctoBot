#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import mock
import pytest
import dbos

from tests.scheduler import temp_dbos_scheduler


@pytest.fixture
def workflows_retention_module(temp_dbos_scheduler):
    import octobot_node.scheduler.scheduler as scheduler_module
    import octobot_node.scheduler.workflows_retention as workflows_retention_module_loaded

    scheduler_module.Scheduler.STARTUP_CLEANUP_TASK = None
    yield workflows_retention_module_loaded
    scheduler_module.Scheduler.STARTUP_CLEANUP_TASK = None


def _workflow_status(*, updated_at: int = 0, created_at: int = 0) -> mock.Mock:
    workflow_status = mock.Mock(spec=dbos.WorkflowStatus)
    workflow_status.updated_at = updated_at
    workflow_status.created_at = created_at
    return workflow_status


class TestGetLatestCleanupExecutionTimestampMs:
    def test_returns_zero_when_no_workflows(self, workflows_retention_module):
        assert workflows_retention_module._get_latest_cleanup_execution_timestamp_ms([]) == 0

    def test_uses_updated_at_from_latest_workflow(self, workflows_retention_module):
        workflow_status = _workflow_status(updated_at=42_000, created_at=1_000)
        assert workflows_retention_module._get_latest_cleanup_execution_timestamp_ms([workflow_status]) == 42_000

    def test_falls_back_to_created_at_when_updated_at_missing(self, workflows_retention_module):
        workflow_status = _workflow_status(updated_at=0, created_at=9_000)
        assert workflows_retention_module._get_latest_cleanup_execution_timestamp_ms([workflow_status]) == 9_000


class TestIsCleanupExecutionStale:
    def test_stale_when_never_ran(self, workflows_retention_module):
        assert workflows_retention_module._is_cleanup_execution_stale(
            latest_timestamp_ms=0,
            now_ms=100_000,
            threshold_seconds=60 * 60 * 24,
        ) is True

    def test_stale_when_older_than_threshold(self, workflows_retention_module):
        now_ms = 100_000_000
        threshold_seconds = 60 * 60 * 24
        old_timestamp_ms = now_ms - int(threshold_seconds * 1000) - 1
        assert workflows_retention_module._is_cleanup_execution_stale(
            latest_timestamp_ms=old_timestamp_ms,
            now_ms=now_ms,
            threshold_seconds=threshold_seconds,
        ) is True

    def test_fresh_when_within_threshold(self, workflows_retention_module):
        now_ms = 100_000_000
        threshold_seconds = 60 * 60 * 24
        recent_timestamp_ms = now_ms - int(threshold_seconds * 1000) + 1
        assert workflows_retention_module._is_cleanup_execution_stale(
            latest_timestamp_ms=recent_timestamp_ms,
            now_ms=now_ms,
            threshold_seconds=threshold_seconds,
        ) is False


class TestShouldTriggerStaleCleanup:
    @pytest.mark.asyncio
    async def test_returns_false_when_consumer_only(self, workflows_retention_module):
        sched = mock.Mock()
        with mock.patch(
            "octobot_node.scheduler.workflows_retention.should_skip_retention_cleanup_on_this_node",
            return_value=True,
        ):
            result = await workflows_retention_module._should_trigger_stale_cleanup(sched)
        assert result is False
        sched.INSTANCE.list_workflows_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_true_when_stale(self, workflows_retention_module):
        sched = mock.Mock()
        sched.is_initialized.return_value = True
        sched.INSTANCE.list_workflows_async = mock.AsyncMock(
            return_value=[_workflow_status(updated_at=1)],
        )
        with mock.patch(
            "octobot_node.scheduler.workflows_retention.should_skip_retention_cleanup_on_this_node",
            return_value=False,
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention.time.time",
            return_value=100_000,
        ), mock.patch(
            "octobot_node.scheduler.workflows.dbos_cleanup_workflow.STALE_EXECUTION_THRESHOLD_SECONDS",
            60 * 60 * 24,
        ):
            result = await workflows_retention_module._should_trigger_stale_cleanup(sched)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_recent(self, workflows_retention_module):
        sched = mock.Mock()
        sched.is_initialized.return_value = True
        now_ms = 100_000_000
        sched.INSTANCE.list_workflows_async = mock.AsyncMock(
            return_value=[_workflow_status(updated_at=now_ms - 1)],
        )
        with mock.patch(
            "octobot_node.scheduler.workflows_retention.should_skip_retention_cleanup_on_this_node",
            return_value=False,
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention.time.time",
            return_value=now_ms / 1000,
        ), mock.patch(
            "octobot_node.scheduler.workflows.dbos_cleanup_workflow.STALE_EXECUTION_THRESHOLD_SECONDS",
            60 * 60 * 24,
        ):
            result = await workflows_retention_module._should_trigger_stale_cleanup(sched)
        assert result is False


class TestRunDelayedCleanupTriggerIfStale:
    @pytest.mark.asyncio
    async def test_triggers_schedule_when_stale(self, workflows_retention_module):
        sched = mock.Mock()
        sched.is_initialized.return_value = True
        with mock.patch(
            "octobot_node.scheduler.workflows_retention.asyncio.sleep",
            mock.AsyncMock(),
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention._should_trigger_stale_cleanup",
            mock.AsyncMock(return_value=True),
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention.dbos.DBOS.trigger_schedule",
        ) as trigger_schedule_mock, mock.patch(
            "octobot_node.scheduler.workflows_retention.logging.getLogger",
            return_value=mock.Mock(),
        ), mock.patch(
            "octobot_node.scheduler.workflows.dbos_cleanup_workflow.SCHEDULE_NAME",
            "dbos_cleanup_daily",
        ):
            await workflows_retention_module._run_delayed_cleanup_trigger_if_stale(sched)

        trigger_schedule_mock.assert_called_once_with("dbos_cleanup_daily")

    @pytest.mark.asyncio
    async def test_skips_trigger_when_not_stale(self, workflows_retention_module):
        sched = mock.Mock()
        sched.is_initialized.return_value = True
        with mock.patch(
            "octobot_node.scheduler.workflows_retention.asyncio.sleep",
            mock.AsyncMock(),
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention._should_trigger_stale_cleanup",
            mock.AsyncMock(return_value=False),
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention.dbos.DBOS.trigger_schedule",
        ) as trigger_schedule_mock, mock.patch(
            "octobot_node.scheduler.workflows_retention.logging.getLogger",
            return_value=mock.Mock(),
        ):
            await workflows_retention_module._run_delayed_cleanup_trigger_if_stale(sched)

        trigger_schedule_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_trigger_when_scheduler_stopped_before_delay(self, workflows_retention_module):
        sched = mock.Mock()
        sched.is_initialized.return_value = False
        with mock.patch(
            "octobot_node.scheduler.workflows_retention.asyncio.sleep",
            mock.AsyncMock(),
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention._should_trigger_stale_cleanup",
            mock.AsyncMock(),
        ) as should_trigger_mock, mock.patch(
            "octobot_node.scheduler.workflows_retention.dbos.DBOS.trigger_schedule",
        ) as trigger_schedule_mock, mock.patch(
            "octobot_node.scheduler.workflows_retention.logging.getLogger",
            return_value=mock.Mock(),
        ):
            await workflows_retention_module._run_delayed_cleanup_trigger_if_stale(sched)

        should_trigger_mock.assert_not_called()
        trigger_schedule_mock.assert_not_called()


class TestScheduleStartupCleanupTrigger:
    def test_creates_task_with_running_loop(self, workflows_retention_module):
        import octobot_node.scheduler.scheduler as scheduler_module

        sched = scheduler_module.Scheduler()
        mock_loop = mock.Mock()
        mock_task = mock.Mock()
        mock_loop.create_task.return_value = mock_task
        with mock.patch(
            "octobot_node.scheduler.workflows_retention.should_skip_retention_cleanup_on_this_node",
            return_value=False,
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention.asyncio.get_running_loop",
            return_value=mock_loop,
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention.logging.getLogger",
            return_value=mock.Mock(),
        ):
            workflows_retention_module.schedule_startup_cleanup_trigger(sched)

        mock_loop.create_task.assert_called_once()
        assert scheduler_module.Scheduler.STARTUP_CLEANUP_TASK is mock_task

    def test_skips_when_consumer_only(self, workflows_retention_module):
        import octobot_node.scheduler.scheduler as scheduler_module

        sched = scheduler_module.Scheduler()
        with mock.patch(
            "octobot_node.scheduler.workflows_retention.should_skip_retention_cleanup_on_this_node",
            return_value=True,
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention.asyncio.get_running_loop",
        ) as get_running_loop_mock, mock.patch(
            "octobot_node.scheduler.workflows_retention.logging.getLogger",
            return_value=mock.Mock(),
        ):
            workflows_retention_module.schedule_startup_cleanup_trigger(sched)

        get_running_loop_mock.assert_not_called()
        assert scheduler_module.Scheduler.STARTUP_CLEANUP_TASK is None

    def test_logs_and_skips_when_no_running_loop(self, workflows_retention_module):
        import octobot_node.scheduler.scheduler as scheduler_module

        sched = scheduler_module.Scheduler()
        mock_logger = mock.Mock()
        with mock.patch(
            "octobot_node.scheduler.workflows_retention.should_skip_retention_cleanup_on_this_node",
            return_value=False,
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention.asyncio.get_running_loop",
            side_effect=RuntimeError,
        ), mock.patch(
            "octobot_node.scheduler.workflows_retention.logging.getLogger",
            return_value=mock_logger,
        ):
            workflows_retention_module.schedule_startup_cleanup_trigger(sched)

        mock_logger.warning.assert_called_once()
        assert scheduler_module.Scheduler.STARTUP_CLEANUP_TASK is None


class TestCancelStartupCleanupTrigger:
    def test_cancels_pending_task_and_clears_reference(self, workflows_retention_module):
        import octobot_node.scheduler.scheduler as scheduler_module

        sched = scheduler_module.Scheduler()
        mock_task = mock.Mock()
        mock_task.done.return_value = False
        scheduler_module.Scheduler.STARTUP_CLEANUP_TASK = mock_task
        mock_logger = mock.Mock()

        with mock.patch(
            "octobot_node.scheduler.workflows_retention.logging.getLogger",
            return_value=mock_logger,
        ):
            workflows_retention_module.cancel_startup_cleanup_trigger(sched)

        mock_task.cancel.assert_called_once()
        mock_logger.info.assert_called_once()
        assert scheduler_module.Scheduler.STARTUP_CLEANUP_TASK is None

    def test_no_op_when_no_task(self, workflows_retention_module):
        import octobot_node.scheduler.scheduler as scheduler_module

        sched = scheduler_module.Scheduler()
        scheduler_module.Scheduler.STARTUP_CLEANUP_TASK = None
        mock_logger = mock.Mock()

        with mock.patch(
            "octobot_node.scheduler.workflows_retention.logging.getLogger",
            return_value=mock_logger,
        ):
            workflows_retention_module.cancel_startup_cleanup_trigger(sched)

        mock_logger.info.assert_not_called()
        assert scheduler_module.Scheduler.STARTUP_CLEANUP_TASK is None

    def test_no_op_when_task_already_done(self, workflows_retention_module):
        import octobot_node.scheduler.scheduler as scheduler_module

        sched = scheduler_module.Scheduler()
        mock_task = mock.Mock()
        mock_task.done.return_value = True
        scheduler_module.Scheduler.STARTUP_CLEANUP_TASK = mock_task
        mock_logger = mock.Mock()

        with mock.patch(
            "octobot_node.scheduler.workflows_retention.logging.getLogger",
            return_value=mock_logger,
        ):
            workflows_retention_module.cancel_startup_cleanup_trigger(sched)

        mock_task.cancel.assert_not_called()
        assert scheduler_module.Scheduler.STARTUP_CLEANUP_TASK is None
