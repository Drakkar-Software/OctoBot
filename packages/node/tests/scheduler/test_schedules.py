#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import datetime

import dbos
import mock
import pytest

import octobot_node.constants
import octobot_node.enums

from tests.scheduler import temp_dbos_scheduler


def _configured_cleanup_schedule_input(dbos_cleanup_workflow_module) -> dict:
    return dbos_cleanup_workflow_module.get_schedule_input()


def _matching_existing_schedule(
    dbos_cleanup_workflow_module,
    scheduler,
    *,
    automatic_backfill: bool = True,
    queue_name: str | None = None,
) -> dict:
    schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
    if queue_name is None:
        queue_name = octobot_node.enums.SchedulerQueues.DBOS_CLEANUP_QUEUE.value
    return {
        "schedule_id": "existing-schedule-id",
        "schedule_name": dbos_cleanup_workflow_module.SCHEDULE_NAME,
        "workflow_name": "ignored-workflow-name",
        "workflow_class_name": None,
        "schedule": schedule_input["schedule"],
        "status": "ACTIVE",
        "context": None,
        "last_fired_at": "2026-07-13T00:00:00+00:00",
        "automatic_backfill": automatic_backfill,
        "cron_timezone": schedule_input.get("cron_timezone"),
        "queue_name": queue_name,
    }


class TestExistingScheduleMatchesConfigured:
    def test_returns_true_when_all_fields_match(self, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module
        import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        existing_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
        )

        assert schedules_module._existing_schedule_matches_configured(
            existing_schedule,
            schedule_input,
        ) is True

    def test_returns_false_when_cron_differs(self, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module
        import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        existing_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
        )
        existing_schedule["schedule"] = "0 1 * * *"

        assert schedules_module._existing_schedule_matches_configured(
            existing_schedule,
            schedule_input,
        ) is False

    def test_returns_false_when_queue_name_differs(self, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module
        import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        existing_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
            queue_name="other_queue",
        )

        assert schedules_module._existing_schedule_matches_configured(
            existing_schedule,
            schedule_input,
        ) is False

    def test_returns_false_when_automatic_backfill_differs(self, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module
        import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        existing_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
            automatic_backfill=False,
        )

        assert schedules_module._existing_schedule_matches_configured(
            existing_schedule,
            schedule_input,
        ) is False


class TestGetBackfillScheduleDefaultAnchor:
    def test_returns_utc_now_minus_one_day(self, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module

        expected_now = datetime.datetime.now(datetime.timezone.utc)
        anchor = schedules_module.get_backfill_schedule_default_anchor()
        expected_anchor = expected_now - datetime.timedelta(
            days=octobot_node.constants.SCHEDULES_DEFAULT_BACKFILL_DAYS,
        )

        assert anchor.tzinfo == datetime.timezone.utc
        assert abs((anchor - expected_anchor).total_seconds()) < 1


class TestBuildScheduledWorkflowId:
    def test_builds_expected_workflow_id(self, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module
        import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow_module

        trigger_time = datetime.datetime(2026, 7, 15, 0, 0, 0, tzinfo=datetime.timezone.utc)
        assert schedules_module.build_scheduled_workflow_id(
            dbos_cleanup_workflow_module.SCHEDULE_NAME,
            trigger_time,
        ) == f"sched-{dbos_cleanup_workflow_module.SCHEDULE_NAME}-2026-07-15T00:00:00+00:00"


class TestEnumerateScheduleWorkflowIdsInWindow:
    def test_daily_cron_yields_expected_workflow_id(self, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module
        import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        start = datetime.datetime(2026, 7, 14, 6, 30, 0, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2026, 7, 15, 8, 30, 0, tzinfo=datetime.timezone.utc)
        workflow_ids = schedules_module._enumerate_schedule_workflow_ids_in_window(
            dbos_cleanup_workflow_module.SCHEDULE_NAME,
            schedule_input,
            start,
            end,
        )
        assert workflow_ids == [
            f"sched-{dbos_cleanup_workflow_module.SCHEDULE_NAME}-2026-07-15T00:00:00+00:00",
        ]


class TestGetScheduledWorkflowTriggerTime:
    def test_returns_trigger_time_from_workflow_id(self, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module
        import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow_module

        workflow_id = (
            f"sched-{dbos_cleanup_workflow_module.SCHEDULE_NAME}-"
            "2026-07-15T00:00:00+00:00"
        )
        assert schedules_module.get_scheduled_workflow_trigger_time(
            workflow_id,
            dbos_cleanup_workflow_module.SCHEDULE_NAME,
        ) == "2026-07-15T00:00:00+00:00"

    def test_returns_none_for_unexpected_workflow_id(self, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module
        import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow_module

        assert schedules_module.get_scheduled_workflow_trigger_time(
            "trigger-dbos_cleanup_daily-2026-07-15T00:00:00+00:00",
            dbos_cleanup_workflow_module.SCHEDULE_NAME,
        ) is None


class TestRegisterSchedules:
    pytestmark = pytest.mark.asyncio

    @pytest.fixture
    def dbos_cleanup_workflow_module(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow_module_loaded

        yield dbos_cleanup_workflow_module_loaded

    async def test_creates_schedule_when_missing(self, dbos_cleanup_workflow_module, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        mock_logger = mock.Mock()

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos_cleanup_workflow.get_schedule_input",
            return_value=schedule_input,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            new_callable=mock.AsyncMock,
            return_value=None,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.create_schedule_async",
            new_callable=mock.AsyncMock,
        ) as create_schedule_mock, mock.patch(
            "octobot_node.scheduler.schedules._get_logger",
            return_value=mock_logger,
        ), mock.patch.object(
            temp_dbos_scheduler.INSTANCE,
            "apply_schedules_async",
            new_callable=mock.AsyncMock,
        ) as apply_schedules_mock, mock.patch(
            "octobot_node.scheduler.schedules.asyncio.to_thread",
            new_callable=mock.AsyncMock,
        ) as backfill_to_thread_mock:
            await schedules_module.register_schedules(temp_dbos_scheduler)

        create_schedule_mock.assert_awaited_once_with(
            schedule_name=schedule_input["schedule_name"],
            workflow_fn=schedule_input["workflow_fn"],
            schedule=schedule_input["schedule"],
            context=schedule_input.get("context"),
            automatic_backfill=schedule_input.get("automatic_backfill", False),
            cron_timezone=schedule_input.get("cron_timezone"),
            queue_name=schedule_input.get("queue_name"),
        )
        apply_schedules_mock.assert_not_awaited()
        backfill_to_thread_mock.assert_not_awaited()
        mock_logger.info.assert_called_once_with(
            "Creating schedule %s (%s)",
            schedule_input["schedule_name"],
            schedule_input["schedule"],
        )

    async def test_keeps_schedule_when_config_matches(self, dbos_cleanup_workflow_module, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        existing_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
        )
        mock_logger = mock.Mock()

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos_cleanup_workflow.get_schedule_input",
            return_value=schedule_input,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            new_callable=mock.AsyncMock,
            return_value=existing_schedule,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.create_schedule_async",
            new_callable=mock.AsyncMock,
        ) as create_schedule_mock, mock.patch(
            "octobot_node.scheduler.schedules._get_logger",
            return_value=mock_logger,
        ), mock.patch.object(
            temp_dbos_scheduler.INSTANCE,
            "apply_schedules_async",
            new_callable=mock.AsyncMock,
        ) as apply_schedules_mock, mock.patch(
            "octobot_node.scheduler.schedules.asyncio.to_thread",
            new_callable=mock.AsyncMock,
        ) as backfill_to_thread_mock:
            await schedules_module.register_schedules(temp_dbos_scheduler)

        create_schedule_mock.assert_not_awaited()
        apply_schedules_mock.assert_not_awaited()
        backfill_to_thread_mock.assert_not_awaited()
        mock_logger.info.assert_called_once_with(
            "Keeping existing schedule %s (%s)",
            schedule_input["schedule_name"],
            schedule_input["schedule"],
        )

    async def test_recreates_schedule_when_config_differs(self, dbos_cleanup_workflow_module, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        existing_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
            automatic_backfill=False,
        )
        mock_logger = mock.Mock()

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos_cleanup_workflow.get_schedule_input",
            return_value=schedule_input,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            new_callable=mock.AsyncMock,
            return_value=existing_schedule,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.create_schedule_async",
            new_callable=mock.AsyncMock,
        ) as create_schedule_mock, mock.patch(
            "octobot_node.scheduler.schedules._get_logger",
            return_value=mock_logger,
        ), mock.patch.object(
            temp_dbos_scheduler.INSTANCE,
            "apply_schedules_async",
            new_callable=mock.AsyncMock,
        ) as apply_schedules_mock, mock.patch(
            "octobot_node.scheduler.schedules.asyncio.to_thread",
            new_callable=mock.AsyncMock,
        ) as backfill_to_thread_mock:
            await schedules_module.register_schedules(temp_dbos_scheduler)

        create_schedule_mock.assert_not_awaited()
        apply_schedules_mock.assert_awaited_once_with([schedule_input])
        backfill_to_thread_mock.assert_not_awaited()
        mock_logger.info.assert_called_once_with(
            "Updating schedule %s (%s): configuration changed",
            schedule_input["schedule_name"],
            schedule_input["schedule"],
        )

    async def test_backfills_when_last_fired_at_is_null(
        self,
        dbos_cleanup_workflow_module,
        temp_dbos_scheduler,
    ):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        existing_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
        )
        existing_schedule["last_fired_at"] = None
        anchor = datetime.datetime(2026, 7, 14, 6, 30, 0, tzinfo=datetime.timezone.utc)
        workflow_id = (
            f"sched-{schedule_input['schedule_name']}-2026-07-15T00:00:00+00:00"
        )
        mock_handle = mock.Mock()
        mock_handle.get_workflow_id.return_value = workflow_id
        mock_logger = mock.Mock()
        backfill_end = datetime.datetime(2026, 7, 15, 8, 30, 0, tzinfo=datetime.timezone.utc)
        datetime_class_mock = mock.Mock(wraps=datetime.datetime)
        datetime_class_mock.now.return_value = backfill_end

        async def backfill_to_thread_side_effect(func, *args, **kwargs):
            return func(*args, **kwargs)

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos_cleanup_workflow.get_schedule_input",
            return_value=schedule_input,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            new_callable=mock.AsyncMock,
            return_value=existing_schedule,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.create_schedule_async",
            new_callable=mock.AsyncMock,
        ), mock.patch(
            "octobot_node.scheduler.schedules._get_logger",
            return_value=mock_logger,
        ), mock.patch.object(
            temp_dbos_scheduler.INSTANCE,
            "apply_schedules_async",
            new_callable=mock.AsyncMock,
        ), mock.patch(
            "octobot_node.scheduler.schedules.get_backfill_schedule_default_anchor",
            return_value=anchor,
        ), mock.patch(
            "octobot_node.scheduler.schedules.datetime",
            mock.Mock(
                datetime=datetime_class_mock,
                timezone=datetime.timezone,
                timedelta=datetime.timedelta,
            ),
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_workflow_status_async",
            new_callable=mock.AsyncMock,
            return_value=None,
        ), mock.patch(
            "octobot_node.scheduler.schedules.asyncio.to_thread",
            side_effect=backfill_to_thread_side_effect,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.backfill_schedule",
            return_value=[mock_handle],
        ) as backfill_schedule_mock:
            await schedules_module.register_schedules(temp_dbos_scheduler)

        backfill_schedule_mock.assert_called_once()
        schedule_name, backfill_start, backfill_end_arg = backfill_schedule_mock.call_args[0]
        assert schedule_name == schedule_input["schedule_name"]
        assert backfill_start == anchor
        assert backfill_end_arg == backfill_end
        mock_logger.info.assert_any_call(
            "Startup backfill for schedule %s: last_fired_at unset, checking missed cron slots in [%s, %s)",
            schedule_input["schedule_name"],
            anchor.isoformat(),
            backfill_end.isoformat(),
        )
        mock_logger.info.assert_any_call(
            "Startup backfill enqueued schedule %s workflow %s",
            schedule_input["schedule_name"],
            workflow_id,
        )
        mock_logger.info.assert_any_call(
            "Startup backfill finished for schedule %s: %s enqueued, %s unchanged",
            schedule_input["schedule_name"],
            1,
            0,
        )

    async def test_skips_backfill_when_all_window_slots_terminal(
        self,
        dbos_cleanup_workflow_module,
        temp_dbos_scheduler,
    ):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        existing_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
        )
        existing_schedule["last_fired_at"] = None
        anchor = datetime.datetime(2026, 7, 14, 6, 30, 0, tzinfo=datetime.timezone.utc)
        backfill_end = datetime.datetime(2026, 7, 15, 8, 30, 0, tzinfo=datetime.timezone.utc)
        workflow_id = (
            f"sched-{schedule_input['schedule_name']}-2026-07-15T00:00:00+00:00"
        )
        success_status = mock.Mock(spec=dbos.WorkflowStatus)
        success_status.status = dbos.WorkflowStatusString.SUCCESS.value
        mock_logger = mock.Mock()
        datetime_class_mock = mock.Mock(wraps=datetime.datetime)
        datetime_class_mock.now.return_value = backfill_end

        async def get_workflow_status_side_effect(requested_workflow_id: str):
            if requested_workflow_id == workflow_id:
                return success_status
            return None

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos_cleanup_workflow.get_schedule_input",
            return_value=schedule_input,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            new_callable=mock.AsyncMock,
            return_value=existing_schedule,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.create_schedule_async",
            new_callable=mock.AsyncMock,
        ), mock.patch(
            "octobot_node.scheduler.schedules._get_logger",
            return_value=mock_logger,
        ), mock.patch.object(
            temp_dbos_scheduler.INSTANCE,
            "apply_schedules_async",
            new_callable=mock.AsyncMock,
        ), mock.patch(
            "octobot_node.scheduler.schedules.get_backfill_schedule_default_anchor",
            return_value=anchor,
        ), mock.patch(
            "octobot_node.scheduler.schedules.datetime",
            mock.Mock(
                datetime=datetime_class_mock,
                timezone=datetime.timezone,
                timedelta=datetime.timedelta,
            ),
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_workflow_status_async",
            side_effect=get_workflow_status_side_effect,
        ), mock.patch(
            "octobot_node.scheduler.schedules.asyncio.to_thread",
            new_callable=mock.AsyncMock,
        ) as backfill_to_thread_mock:
            await schedules_module.register_schedules(temp_dbos_scheduler)

        backfill_to_thread_mock.assert_not_awaited()
        mock_logger.info.assert_any_call(
            "Startup backfill not needed for schedule %s: last_fired_at unset but %s cron slot(s) in [%s, %s) already terminal",
            schedule_input["schedule_name"],
            1,
            anchor.isoformat(),
            backfill_end.isoformat(),
        )
        mock_logger.info.assert_any_call(
            "Schedule %s slot %s already %s",
            schedule_input["schedule_name"],
            workflow_id,
            dbos.WorkflowStatusString.SUCCESS.value,
        )

    async def test_backfill_logs_unchanged_when_slot_already_terminal_in_mixed_window(
        self,
        dbos_cleanup_workflow_module,
        temp_dbos_scheduler,
    ):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        schedule_input["schedule"] = "0 * * * *"
        existing_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
        )
        existing_schedule["last_fired_at"] = None
        existing_schedule["schedule"] = "0 * * * *"
        anchor = datetime.datetime(2026, 7, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        backfill_end = datetime.datetime(2026, 7, 15, 12, 30, 0, tzinfo=datetime.timezone.utc)
        terminal_workflow_id = (
            f"sched-{schedule_input['schedule_name']}-2026-07-15T11:00:00+00:00"
        )
        missing_workflow_id = (
            f"sched-{schedule_input['schedule_name']}-2026-07-15T12:00:00+00:00"
        )
        success_status = mock.Mock(spec=dbos.WorkflowStatus)
        success_status.status = dbos.WorkflowStatusString.SUCCESS.value
        mock_logger = mock.Mock()
        datetime_class_mock = mock.Mock(wraps=datetime.datetime)
        datetime_class_mock.now.return_value = backfill_end
        mock_handles = []
        for workflow_id in (terminal_workflow_id, missing_workflow_id):
            mock_handle = mock.Mock()
            mock_handle.get_workflow_id.return_value = workflow_id
            mock_handles.append(mock_handle)

        async def get_workflow_status_side_effect(requested_workflow_id: str):
            if requested_workflow_id == terminal_workflow_id:
                return success_status
            return None

        async def backfill_to_thread_side_effect(func, *args, **kwargs):
            return func(*args, **kwargs)

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos_cleanup_workflow.get_schedule_input",
            return_value=schedule_input,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            new_callable=mock.AsyncMock,
            return_value=existing_schedule,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.create_schedule_async",
            new_callable=mock.AsyncMock,
        ), mock.patch(
            "octobot_node.scheduler.schedules._get_logger",
            return_value=mock_logger,
        ), mock.patch.object(
            temp_dbos_scheduler.INSTANCE,
            "apply_schedules_async",
            new_callable=mock.AsyncMock,
        ), mock.patch(
            "octobot_node.scheduler.schedules.get_backfill_schedule_default_anchor",
            return_value=anchor,
        ), mock.patch(
            "octobot_node.scheduler.schedules.datetime",
            mock.Mock(
                datetime=datetime_class_mock,
                timezone=datetime.timezone,
                timedelta=datetime.timedelta,
            ),
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_workflow_status_async",
            side_effect=get_workflow_status_side_effect,
        ), mock.patch(
            "octobot_node.scheduler.schedules.asyncio.to_thread",
            side_effect=backfill_to_thread_side_effect,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.backfill_schedule",
            return_value=mock_handles,
        ) as backfill_schedule_mock:
            await schedules_module.register_schedules(temp_dbos_scheduler)

        backfill_schedule_mock.assert_called_once()
        mock_logger.info.assert_any_call(
            "Startup backfill enqueued schedule %s workflow %s",
            schedule_input["schedule_name"],
            missing_workflow_id,
        )
        mock_logger.info.assert_any_call(
            "Startup backfill left schedule %s workflow %s unchanged (already %s)",
            schedule_input["schedule_name"],
            terminal_workflow_id,
            dbos.WorkflowStatusString.SUCCESS.value,
        )
        mock_logger.info.assert_any_call(
            "Startup backfill finished for schedule %s: %s enqueued, %s unchanged",
            schedule_input["schedule_name"],
            1,
            1,
        )

    async def test_skips_backfill_when_last_fired_at_set(
        self,
        dbos_cleanup_workflow_module,
        temp_dbos_scheduler,
    ):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        existing_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
        )

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos_cleanup_workflow.get_schedule_input",
            return_value=schedule_input,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            new_callable=mock.AsyncMock,
            return_value=existing_schedule,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.create_schedule_async",
            new_callable=mock.AsyncMock,
        ), mock.patch(
            "octobot_node.scheduler.schedules._get_logger",
            return_value=mock.Mock(),
        ), mock.patch.object(
            temp_dbos_scheduler.INSTANCE,
            "apply_schedules_async",
            new_callable=mock.AsyncMock,
        ), mock.patch(
            "octobot_node.scheduler.schedules.asyncio.to_thread",
            new_callable=mock.AsyncMock,
        ) as backfill_to_thread_mock:
            await schedules_module.register_schedules(temp_dbos_scheduler)

        backfill_to_thread_mock.assert_not_awaited()

    async def test_skips_backfill_when_automatic_backfill_false(
        self,
        dbos_cleanup_workflow_module,
        temp_dbos_scheduler,
    ):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        schedule_input["automatic_backfill"] = False
        existing_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
            automatic_backfill=False,
        )
        existing_schedule["last_fired_at"] = None

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos_cleanup_workflow.get_schedule_input",
            return_value=schedule_input,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            new_callable=mock.AsyncMock,
            return_value=existing_schedule,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.create_schedule_async",
            new_callable=mock.AsyncMock,
        ), mock.patch(
            "octobot_node.scheduler.schedules._get_logger",
            return_value=mock.Mock(),
        ), mock.patch.object(
            temp_dbos_scheduler.INSTANCE,
            "apply_schedules_async",
            new_callable=mock.AsyncMock,
        ), mock.patch(
            "octobot_node.scheduler.schedules.asyncio.to_thread",
            new_callable=mock.AsyncMock,
        ) as backfill_to_thread_mock:
            await schedules_module.register_schedules(temp_dbos_scheduler)

        backfill_to_thread_mock.assert_not_awaited()
