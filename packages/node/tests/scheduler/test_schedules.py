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


def _configured_global_view_schedule_input(global_view_workflow_module) -> dict:
    return global_view_workflow_module.get_schedule_input()


def _matching_existing_global_view_schedule(global_view_workflow_module) -> dict:
    schedule_input = _configured_global_view_schedule_input(global_view_workflow_module)
    return {
        "schedule_id": "existing-global-view-schedule-id",
        "schedule_name": global_view_workflow_module.SCHEDULE_NAME,
        "workflow_name": "ignored-workflow-name",
        "workflow_class_name": None,
        "schedule": schedule_input["schedule"],
        "status": "ACTIVE",
        "context": None,
        "last_fired_at": "2026-07-13T00:00:00+00:00",
        "automatic_backfill": schedule_input.get("automatic_backfill", False),
        "cron_timezone": schedule_input.get("cron_timezone"),
        "queue_name": schedule_input.get("queue_name"),
    }


def _configured_portfolio_history_schedule_input(portfolio_history_workflow_module) -> dict:
    return portfolio_history_workflow_module.get_schedule_input()


def _matching_existing_portfolio_history_schedule(portfolio_history_workflow_module) -> dict:
    schedule_input = _configured_portfolio_history_schedule_input(portfolio_history_workflow_module)
    return {
        "schedule_id": "existing-portfolio-history-schedule-id",
        "schedule_name": portfolio_history_workflow_module.SCHEDULE_NAME,
        "workflow_name": "ignored-workflow-name",
        "workflow_class_name": None,
        "schedule": schedule_input["schedule"],
        "status": "ACTIVE",
        "context": None,
        "last_fired_at": "2026-07-13T00:00:00+00:00",
        "automatic_backfill": schedule_input.get("automatic_backfill", False),
        "catch_up_once_on_startup": schedule_input.get("catch_up_once_on_startup", False),
        "cron_timezone": schedule_input.get("cron_timezone"),
        "queue_name": schedule_input.get("queue_name"),
    }


def _success_workflow_status():
    success_status = mock.Mock(spec=dbos.WorkflowStatus)
    success_status.status = dbos.WorkflowStatusString.SUCCESS.value
    return success_status


def _enqueued_workflow_status():
    enqueued_status = mock.Mock(spec=dbos.WorkflowStatus)
    enqueued_status.status = dbos.WorkflowStatusString.ENQUEUED.value
    return enqueued_status


def _workflow_status_async_with_portfolio_terminal(
    portfolio_history_workflow_module,
    inner_side_effect=None,
):
    portfolio_prefix = f"sched-{portfolio_history_workflow_module.SCHEDULE_NAME}-"

    async def get_workflow_status_async(workflow_id: str):
        if workflow_id.startswith(portfolio_prefix):
            return _success_workflow_status()
        if inner_side_effect is None:
            return None
        return await inner_side_effect(workflow_id)

    return get_workflow_status_async


def _get_schedule_async_side_effect(
    dbos_cleanup_workflow_module,
    global_view_workflow_module,
    portfolio_history_workflow_module,
    *,
    cleanup_existing: dict | None,
    global_view_existing: dict | None,
    portfolio_history_existing: dict | None,
):
    async def get_schedule_async(schedule_name: str):
        if schedule_name == dbos_cleanup_workflow_module.SCHEDULE_NAME:
            return cleanup_existing
        if schedule_name == global_view_workflow_module.SCHEDULE_NAME:
            return global_view_existing
        if schedule_name == portfolio_history_workflow_module.SCHEDULE_NAME:
            return portfolio_history_existing
        return None

    return get_schedule_async


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

    def test_returns_false_when_catch_up_once_on_startup_differs(self, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module
        import octobot_node.scheduler.workflows.portfolio_history_workflow as portfolio_history_workflow_module

        schedule_input = _configured_portfolio_history_schedule_input(portfolio_history_workflow_module)
        existing_schedule = _matching_existing_portfolio_history_schedule(portfolio_history_workflow_module)
        existing_schedule["catch_up_once_on_startup"] = False

        assert schedules_module._existing_schedule_matches_configured(
            existing_schedule,
            schedule_input,
        ) is False


class TestGetLatestScheduleTriggerTimeBefore:
    def test_daily_cron_returns_latest_slot_before_now(self, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module
        import octobot_node.scheduler.workflows.portfolio_history_workflow as portfolio_history_workflow_module

        schedule_input = _configured_portfolio_history_schedule_input(portfolio_history_workflow_module)
        before = datetime.datetime(2026, 7, 15, 13, 0, 0, tzinfo=datetime.timezone.utc)
        trigger_time = schedules_module._get_latest_schedule_trigger_time_before(
            schedule_input,
            before,
        )
        assert trigger_time == datetime.datetime(2026, 7, 15, 3, 0, 0, tzinfo=datetime.timezone.utc)


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

    @pytest.fixture
    def global_view_workflow_module(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.global_view_workflow as global_view_workflow_module_loaded

        yield global_view_workflow_module_loaded

    @pytest.fixture
    def portfolio_history_workflow_module(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.portfolio_history_workflow as portfolio_history_workflow_module_loaded

        yield portfolio_history_workflow_module_loaded

    async def test_creates_schedule_when_missing(
        self,
        dbos_cleanup_workflow_module,
        global_view_workflow_module,
        portfolio_history_workflow_module,
        temp_dbos_scheduler,
    ):
        import octobot_node.scheduler.schedules as schedules_module

        cleanup_schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        global_view_schedule_input = _configured_global_view_schedule_input(global_view_workflow_module)
        portfolio_history_schedule_input = _configured_portfolio_history_schedule_input(
            portfolio_history_workflow_module,
        )
        mock_logger = mock.Mock()

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos_cleanup_workflow.get_schedule_input",
            return_value=cleanup_schedule_input,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            side_effect=_get_schedule_async_side_effect(
                dbos_cleanup_workflow_module,
                global_view_workflow_module,
                portfolio_history_workflow_module,
                cleanup_existing=None,
                global_view_existing=None,
                portfolio_history_existing=None,
            ),
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

        assert create_schedule_mock.await_count == 3
        create_schedule_mock.assert_any_await(
            schedule_name=cleanup_schedule_input["schedule_name"],
            workflow_fn=cleanup_schedule_input["workflow_fn"],
            schedule=cleanup_schedule_input["schedule"],
            context=cleanup_schedule_input.get("context"),
            automatic_backfill=cleanup_schedule_input.get("automatic_backfill", False),
            cron_timezone=cleanup_schedule_input.get("cron_timezone"),
            queue_name=cleanup_schedule_input.get("queue_name"),
        )
        create_schedule_mock.assert_any_await(
            schedule_name=global_view_schedule_input["schedule_name"],
            workflow_fn=global_view_schedule_input["workflow_fn"],
            schedule=global_view_schedule_input["schedule"],
            context=global_view_schedule_input.get("context"),
            automatic_backfill=global_view_schedule_input.get("automatic_backfill", False),
            cron_timezone=global_view_schedule_input.get("cron_timezone"),
            queue_name=global_view_schedule_input.get("queue_name"),
        )
        create_schedule_mock.assert_any_await(
            schedule_name=portfolio_history_schedule_input["schedule_name"],
            workflow_fn=portfolio_history_schedule_input["workflow_fn"],
            schedule=portfolio_history_schedule_input["schedule"],
            context=portfolio_history_schedule_input.get("context"),
            automatic_backfill=portfolio_history_schedule_input.get("automatic_backfill", False),
            cron_timezone=portfolio_history_schedule_input.get("cron_timezone"),
            queue_name=portfolio_history_schedule_input.get("queue_name"),
        )
        apply_schedules_mock.assert_not_awaited()
        backfill_to_thread_mock.assert_not_awaited()
        mock_logger.info.assert_any_call(
            "Creating schedule %s (%s)",
            cleanup_schedule_input["schedule_name"],
            cleanup_schedule_input["schedule"],
        )
        mock_logger.info.assert_any_call(
            "Creating schedule %s (%s)",
            global_view_schedule_input["schedule_name"],
            global_view_schedule_input["schedule"],
        )
        mock_logger.info.assert_any_call(
            "Creating schedule %s (%s)",
            portfolio_history_schedule_input["schedule_name"],
            portfolio_history_schedule_input["schedule"],
        )

    async def test_keeps_schedule_when_config_matches(
        self,
        dbos_cleanup_workflow_module,
        global_view_workflow_module,
        portfolio_history_workflow_module,
        temp_dbos_scheduler,
    ):
        import octobot_node.scheduler.schedules as schedules_module

        cleanup_schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        global_view_schedule_input = _configured_global_view_schedule_input(global_view_workflow_module)
        existing_cleanup_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
        )
        existing_global_view_schedule = _matching_existing_global_view_schedule(
            global_view_workflow_module,
        )
        existing_portfolio_history_schedule = _matching_existing_portfolio_history_schedule(
            portfolio_history_workflow_module,
        )
        mock_logger = mock.Mock()

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos_cleanup_workflow.get_schedule_input",
            return_value=cleanup_schedule_input,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            side_effect=_get_schedule_async_side_effect(
                dbos_cleanup_workflow_module,
                global_view_workflow_module,
                portfolio_history_workflow_module,
                cleanup_existing=existing_cleanup_schedule,
                global_view_existing=existing_global_view_schedule,
                portfolio_history_existing=existing_portfolio_history_schedule,
            ),
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
            "octobot_node.scheduler.schedules.dbos.DBOS.get_workflow_status_async",
            side_effect=_workflow_status_async_with_portfolio_terminal(
                portfolio_history_workflow_module,
            ),
        ), mock.patch(
            "octobot_node.scheduler.schedules.asyncio.to_thread",
            new_callable=mock.AsyncMock,
        ) as backfill_to_thread_mock:
            await schedules_module.register_schedules(temp_dbos_scheduler)

        create_schedule_mock.assert_not_awaited()
        apply_schedules_mock.assert_not_awaited()
        backfill_to_thread_mock.assert_not_awaited()
        mock_logger.info.assert_any_call(
            "Keeping existing schedule %s (%s)",
            cleanup_schedule_input["schedule_name"],
            cleanup_schedule_input["schedule"],
        )
        mock_logger.info.assert_any_call(
            "Keeping existing schedule %s (%s)",
            global_view_schedule_input["schedule_name"],
            global_view_schedule_input["schedule"],
        )

    async def test_recreates_schedule_when_config_differs(
        self,
        dbos_cleanup_workflow_module,
        global_view_workflow_module,
        portfolio_history_workflow_module,
        temp_dbos_scheduler,
    ):
        import octobot_node.scheduler.schedules as schedules_module

        cleanup_schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        existing_cleanup_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
            automatic_backfill=False,
        )
        existing_global_view_schedule = _matching_existing_global_view_schedule(
            global_view_workflow_module,
        )
        existing_portfolio_history_schedule = _matching_existing_portfolio_history_schedule(
            portfolio_history_workflow_module,
        )
        mock_logger = mock.Mock()

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos_cleanup_workflow.get_schedule_input",
            return_value=cleanup_schedule_input,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            side_effect=_get_schedule_async_side_effect(
                dbos_cleanup_workflow_module,
                global_view_workflow_module,
                portfolio_history_workflow_module,
                cleanup_existing=existing_cleanup_schedule,
                global_view_existing=existing_global_view_schedule,
                portfolio_history_existing=existing_portfolio_history_schedule,
            ),
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
            "octobot_node.scheduler.schedules.dbos.DBOS.get_workflow_status_async",
            side_effect=_workflow_status_async_with_portfolio_terminal(
                portfolio_history_workflow_module,
            ),
        ), mock.patch(
            "octobot_node.scheduler.schedules.asyncio.to_thread",
            new_callable=mock.AsyncMock,
        ) as backfill_to_thread_mock:
            await schedules_module.register_schedules(temp_dbos_scheduler)

        create_schedule_mock.assert_not_awaited()
        apply_schedules_mock.assert_awaited_once_with([cleanup_schedule_input])
        backfill_to_thread_mock.assert_not_awaited()
        mock_logger.info.assert_any_call(
            "Updating schedule %s (%s): configuration changed",
            cleanup_schedule_input["schedule_name"],
            cleanup_schedule_input["schedule"],
        )
        mock_logger.info.assert_any_call(
            "Keeping existing schedule %s (%s)",
            global_view_workflow_module.SCHEDULE_NAME,
            _configured_global_view_schedule_input(global_view_workflow_module)["schedule"],
        )

    async def test_backfills_when_last_fired_at_is_null(
        self,
        dbos_cleanup_workflow_module,
        global_view_workflow_module,
        portfolio_history_workflow_module,
        temp_dbos_scheduler,
    ):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        existing_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
        )
        existing_global_view_schedule = _matching_existing_global_view_schedule(
            global_view_workflow_module,
        )
        existing_portfolio_history_schedule = _matching_existing_portfolio_history_schedule(
            portfolio_history_workflow_module,
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
            side_effect=_get_schedule_async_side_effect(
                dbos_cleanup_workflow_module,
                global_view_workflow_module,
                portfolio_history_workflow_module,
                cleanup_existing=existing_schedule,
                global_view_existing=existing_global_view_schedule,
                portfolio_history_existing=existing_portfolio_history_schedule,
            ),
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
            side_effect=_workflow_status_async_with_portfolio_terminal(
                portfolio_history_workflow_module,
            ),
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
        global_view_workflow_module,
        portfolio_history_workflow_module,
        temp_dbos_scheduler,
    ):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        existing_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
        )
        existing_global_view_schedule = _matching_existing_global_view_schedule(
            global_view_workflow_module,
        )
        existing_portfolio_history_schedule = _matching_existing_portfolio_history_schedule(
            portfolio_history_workflow_module,
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
            side_effect=_get_schedule_async_side_effect(
                dbos_cleanup_workflow_module,
                global_view_workflow_module,
                portfolio_history_workflow_module,
                cleanup_existing=existing_schedule,
                global_view_existing=existing_global_view_schedule,
                portfolio_history_existing=existing_portfolio_history_schedule,
            ),
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
            side_effect=_workflow_status_async_with_portfolio_terminal(
                portfolio_history_workflow_module,
                inner_side_effect=get_workflow_status_side_effect,
            ),
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
        global_view_workflow_module,
        portfolio_history_workflow_module,
        temp_dbos_scheduler,
    ):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        schedule_input["schedule"] = "0 * * * *"
        existing_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
        )
        existing_global_view_schedule = _matching_existing_global_view_schedule(
            global_view_workflow_module,
        )
        existing_portfolio_history_schedule = _matching_existing_portfolio_history_schedule(
            portfolio_history_workflow_module,
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
            side_effect=_get_schedule_async_side_effect(
                dbos_cleanup_workflow_module,
                global_view_workflow_module,
                portfolio_history_workflow_module,
                cleanup_existing=existing_schedule,
                global_view_existing=existing_global_view_schedule,
                portfolio_history_existing=existing_portfolio_history_schedule,
            ),
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
            side_effect=_workflow_status_async_with_portfolio_terminal(
                portfolio_history_workflow_module,
                inner_side_effect=get_workflow_status_side_effect,
            ),
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
        global_view_workflow_module,
        portfolio_history_workflow_module,
        temp_dbos_scheduler,
    ):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        existing_schedule = _matching_existing_schedule(
            dbos_cleanup_workflow_module,
            temp_dbos_scheduler,
        )
        existing_global_view_schedule = _matching_existing_global_view_schedule(
            global_view_workflow_module,
        )
        existing_portfolio_history_schedule = _matching_existing_portfolio_history_schedule(
            portfolio_history_workflow_module,
        )

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos_cleanup_workflow.get_schedule_input",
            return_value=schedule_input,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            side_effect=_get_schedule_async_side_effect(
                dbos_cleanup_workflow_module,
                global_view_workflow_module,
                portfolio_history_workflow_module,
                cleanup_existing=existing_schedule,
                global_view_existing=existing_global_view_schedule,
                portfolio_history_existing=existing_portfolio_history_schedule,
            ),
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
            "octobot_node.scheduler.schedules.dbos.DBOS.get_workflow_status_async",
            side_effect=_workflow_status_async_with_portfolio_terminal(
                portfolio_history_workflow_module,
            ),
        ), mock.patch(
            "octobot_node.scheduler.schedules.asyncio.to_thread",
            new_callable=mock.AsyncMock,
        ) as backfill_to_thread_mock:
            await schedules_module.register_schedules(temp_dbos_scheduler)

        backfill_to_thread_mock.assert_not_awaited()

    async def test_skips_backfill_when_automatic_backfill_false(
        self,
        dbos_cleanup_workflow_module,
        global_view_workflow_module,
        portfolio_history_workflow_module,
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
        existing_global_view_schedule = _matching_existing_global_view_schedule(
            global_view_workflow_module,
        )
        existing_portfolio_history_schedule = _matching_existing_portfolio_history_schedule(
            portfolio_history_workflow_module,
        )
        existing_schedule["last_fired_at"] = None

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos_cleanup_workflow.get_schedule_input",
            return_value=schedule_input,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            side_effect=_get_schedule_async_side_effect(
                dbos_cleanup_workflow_module,
                global_view_workflow_module,
                portfolio_history_workflow_module,
                cleanup_existing=existing_schedule,
                global_view_existing=existing_global_view_schedule,
                portfolio_history_existing=existing_portfolio_history_schedule,
            ),
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.create_schedule_async",
            new_callable=mock.AsyncMock,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_workflow_status_async",
            new_callable=mock.AsyncMock,
            return_value=_success_workflow_status(),
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


class TestMaybeCatchUpScheduleOnceOnStartup:
    pytestmark = pytest.mark.asyncio

    @pytest.fixture
    def portfolio_history_workflow_module(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.portfolio_history_workflow as portfolio_history_workflow_module_loaded

        yield portfolio_history_workflow_module_loaded

    async def test_backfills_latest_slot_when_missing(self, portfolio_history_workflow_module, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_portfolio_history_schedule_input(portfolio_history_workflow_module)
        now = datetime.datetime(2026, 7, 15, 13, 0, 0, tzinfo=datetime.timezone.utc)
        trigger_time = datetime.datetime(2026, 7, 15, 3, 0, 0, tzinfo=datetime.timezone.utc)
        workflow_id = schedules_module.build_scheduled_workflow_id(
            portfolio_history_workflow_module.SCHEDULE_NAME,
            trigger_time,
        )
        mock_handle = mock.Mock()
        mock_handle.get_workflow_id.return_value = workflow_id
        datetime_class_mock = mock.Mock(wraps=datetime.datetime)
        datetime_class_mock.now.return_value = now

        async def backfill_to_thread_side_effect(func, *args, **kwargs):
            return func(*args, **kwargs)

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            new_callable=mock.AsyncMock,
            return_value=_matching_existing_portfolio_history_schedule(portfolio_history_workflow_module),
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_workflow_status_async",
            new_callable=mock.AsyncMock,
            return_value=None,
        ), mock.patch(
            "octobot_node.scheduler.schedules.datetime",
            mock.Mock(
                datetime=datetime_class_mock,
                timezone=datetime.timezone,
                timedelta=datetime.timedelta,
            ),
        ), mock.patch(
            "octobot_node.scheduler.schedules.asyncio.to_thread",
            side_effect=backfill_to_thread_side_effect,
        ) as backfill_to_thread_mock, mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.backfill_schedule",
            return_value=[mock_handle],
        ) as backfill_schedule_mock:
            await schedules_module._maybe_catch_up_schedule_once_on_startup(
                portfolio_history_workflow_module.SCHEDULE_NAME,
                schedule_input,
            )

        backfill_to_thread_mock.assert_awaited_once()
        backfill_schedule_mock.assert_called_once()
        schedule_name, backfill_start, backfill_end = backfill_schedule_mock.call_args[0]
        assert schedule_name == portfolio_history_workflow_module.SCHEDULE_NAME
        assert backfill_start == trigger_time - datetime.timedelta(seconds=1)
        assert backfill_end == trigger_time + datetime.timedelta(seconds=1)

    async def test_skips_when_latest_slot_terminal(self, portfolio_history_workflow_module, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_portfolio_history_schedule_input(portfolio_history_workflow_module)
        now = datetime.datetime(2026, 7, 15, 13, 0, 0, tzinfo=datetime.timezone.utc)
        datetime_class_mock = mock.Mock(wraps=datetime.datetime)
        datetime_class_mock.now.return_value = now

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            new_callable=mock.AsyncMock,
            return_value=_matching_existing_portfolio_history_schedule(portfolio_history_workflow_module),
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_workflow_status_async",
            new_callable=mock.AsyncMock,
            return_value=_success_workflow_status(),
        ), mock.patch(
            "octobot_node.scheduler.schedules.datetime",
            mock.Mock(
                datetime=datetime_class_mock,
                timezone=datetime.timezone,
                timedelta=datetime.timedelta,
            ),
        ), mock.patch(
            "octobot_node.scheduler.schedules.asyncio.to_thread",
            new_callable=mock.AsyncMock,
        ) as backfill_to_thread_mock:
            await schedules_module._maybe_catch_up_schedule_once_on_startup(
                portfolio_history_workflow_module.SCHEDULE_NAME,
                schedule_input,
            )

        backfill_to_thread_mock.assert_not_awaited()

    async def test_skips_when_latest_slot_in_progress(self, portfolio_history_workflow_module, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_portfolio_history_schedule_input(portfolio_history_workflow_module)
        now = datetime.datetime(2026, 7, 15, 13, 0, 0, tzinfo=datetime.timezone.utc)
        datetime_class_mock = mock.Mock(wraps=datetime.datetime)
        datetime_class_mock.now.return_value = now

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            new_callable=mock.AsyncMock,
            return_value=_matching_existing_portfolio_history_schedule(portfolio_history_workflow_module),
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_workflow_status_async",
            new_callable=mock.AsyncMock,
            return_value=_enqueued_workflow_status(),
        ), mock.patch(
            "octobot_node.scheduler.schedules.datetime",
            mock.Mock(
                datetime=datetime_class_mock,
                timezone=datetime.timezone,
                timedelta=datetime.timedelta,
            ),
        ), mock.patch(
            "octobot_node.scheduler.schedules.asyncio.to_thread",
            new_callable=mock.AsyncMock,
        ) as backfill_to_thread_mock:
            await schedules_module._maybe_catch_up_schedule_once_on_startup(
                portfolio_history_workflow_module.SCHEDULE_NAME,
                schedule_input,
            )

        backfill_to_thread_mock.assert_not_awaited()

    async def test_skips_when_flag_disabled(self, portfolio_history_workflow_module, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_portfolio_history_schedule_input(portfolio_history_workflow_module)
        schedule_input["catch_up_once_on_startup"] = False

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            new_callable=mock.AsyncMock,
        ) as get_schedule_mock, mock.patch(
            "octobot_node.scheduler.schedules.asyncio.to_thread",
            new_callable=mock.AsyncMock,
        ) as backfill_to_thread_mock:
            await schedules_module._maybe_catch_up_schedule_once_on_startup(
                portfolio_history_workflow_module.SCHEDULE_NAME,
                schedule_input,
            )

        get_schedule_mock.assert_not_awaited()
        backfill_to_thread_mock.assert_not_awaited()


class TestUpdateCleanupScheduleCron:
    pytestmark = pytest.mark.asyncio

    @pytest.fixture
    def dbos_cleanup_workflow_module(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow_module_loaded

        yield dbos_cleanup_workflow_module_loaded

    async def test_applies_schedule_when_cron_changes(
        self,
        dbos_cleanup_workflow_module,
        temp_dbos_scheduler,
    ):
        import octobot_node.scheduler.schedules as schedules_module

        desired_cron = "0 */6 * * *"
        schedule_input = dbos_cleanup_workflow_module.get_schedule_input(cron=desired_cron)

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            new_callable=mock.AsyncMock,
            return_value={"schedule": "0 0 * * *"},
        ), mock.patch.object(
            temp_dbos_scheduler.INSTANCE,
            "apply_schedules_async",
            new_callable=mock.AsyncMock,
        ) as apply_schedules_mock:
            result = await schedules_module.update_cleanup_schedule_cron(
                temp_dbos_scheduler,
                desired_cron,
            )

        assert result == {"changed": True, "cron": desired_cron}
        apply_schedules_mock.assert_awaited_once_with([schedule_input])

    async def test_skips_apply_when_cron_unchanged(
        self,
        dbos_cleanup_workflow_module,
        temp_dbos_scheduler,
    ):
        import octobot_node.scheduler.schedules as schedules_module

        desired_cron = dbos_cleanup_workflow_module.SCHEDULE_CRON

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule_async",
            new_callable=mock.AsyncMock,
            return_value={"schedule": desired_cron},
        ), mock.patch.object(
            temp_dbos_scheduler.INSTANCE,
            "apply_schedules_async",
            new_callable=mock.AsyncMock,
        ) as apply_schedules_mock:
            result = await schedules_module.update_cleanup_schedule_cron(
                temp_dbos_scheduler,
                desired_cron,
            )

        assert result == {"changed": False, "cron": desired_cron}
        apply_schedules_mock.assert_not_awaited()
