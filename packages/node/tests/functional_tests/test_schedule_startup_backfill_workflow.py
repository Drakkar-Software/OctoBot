#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import asyncio
import datetime
import tempfile
import time

import dbos
import mock
import pytest

import octobot_node.scheduler

import tests.scheduler as scheduler_tests

_BLANK_WORKFLOW_NAME = "blank_backfill_test"
_BLANK_SCHEDULE_NAME = "blank_backfill_test_daily"
_BLANK_QUEUE_NAME = "blank_backfill_test_queue"
_TEST_APP_VERSION = "functional-test-app-version"
_STALE_APP_VERSION = "stale-hash-version"
_WORKFLOW_RESULT_TIMEOUT_SECONDS = 30.0
_STUCK_POLL_SECONDS = 5.0

blank_backfill_test_runs: list[datetime.datetime] = []

pytestmark = pytest.mark.xdist_group("schedule_backfill_functional")


def _register_blank_backfill_workflow():
    @octobot_node.scheduler.SCHEDULER.INSTANCE.workflow(name=_BLANK_WORKFLOW_NAME)
    async def blank_backfill_test(scheduled_time, context):
        blank_backfill_test_runs.append(scheduled_time)
        return {"ran": True}

    return blank_backfill_test


def _blank_schedule_input(blank_workflow_fn) -> dbos.ScheduleInput:
    return {
        "schedule_name": _BLANK_SCHEDULE_NAME,
        "workflow_fn": blank_workflow_fn,
        "schedule": "0 * * * *",
        "context": None,
        "automatic_backfill": True,
        "queue_name": _BLANK_QUEUE_NAME,
    }


async def _run_startup_backfill(
    schedule_input: dbos.ScheduleInput,
    *,
    backfill_anchor: datetime.datetime,
    backfill_end: datetime.datetime,
) -> None:
    import octobot_node.scheduler.schedules as schedules_module

    datetime_class_mock = mock.Mock(wraps=datetime.datetime)
    datetime_class_mock.now.return_value = backfill_end
    with mock.patch.object(
        schedules_module,
        "get_backfill_schedule_default_anchor",
        return_value=backfill_anchor,
    ), mock.patch.object(
        schedules_module,
        "datetime",
        mock.Mock(
            datetime=datetime_class_mock,
            timezone=datetime.timezone,
            timedelta=datetime.timedelta,
        ),
    ):
        await schedules_module._maybe_backfill_schedule_on_startup(
            schedule_input["schedule_name"],
            schedule_input,
        )


async def _assert_workflow_stays_enqueued(workflow_id: str, poll_seconds: float) -> None:
    poll_deadline = time.monotonic() + poll_seconds
    while time.monotonic() < poll_deadline:
        workflow_status = await dbos.DBOS.get_workflow_status_async(workflow_id)
        assert workflow_status is not None
        assert workflow_status.status == dbos.WorkflowStatusString.ENQUEUED.value
        await asyncio.sleep(0.2)


def _seed_stale_latest_application_version(stale_version_name: str) -> None:
    import dbos._dbos as dbos_internals

    dbos_internals._get_dbos_instance()._sys_db.create_application_version(
        stale_version_name,
    )


def _get_or_create_registry_queue(queue_name: str, **queue_options) -> dbos.Queue:
    # destroy_launched_dbos() keeps the global registry; reuse an existing Queue
    # declaration when this fixture runs more than once on the same xdist worker.
    import dbos._dbos as dbos_internals

    registry = dbos_internals._get_or_create_dbos_registry()
    existing_queue = registry.queue_info_map.get(queue_name)
    if existing_queue is not None:
        return existing_queue
    return dbos.Queue(name=queue_name, **queue_options)


@pytest.fixture
def temp_dbos_scheduler_backfill():
    blank_backfill_test_runs.clear()
    with tempfile.NamedTemporaryFile() as temp_file:
        scheduler_tests.destroy_launched_dbos()
        dbos_runtime = scheduler_tests.init_scheduler_with_app_version(
            temp_file.name,
            _TEST_APP_VERSION,
        )
        _get_or_create_registry_queue(_BLANK_QUEUE_NAME, concurrency=1)
        blank_workflow_fn = _register_blank_backfill_workflow()
        dbos_runtime.reset_system_database()
        dbos_runtime.launch()
        try:
            yield blank_workflow_fn
        finally:
            scheduler_tests.destroy_launched_dbos()


@pytest.mark.asyncio
class TestScheduleBackfillFunctional:
    async def test_blank_workflow_runs_after_startup_backfill(
        self,
        temp_dbos_scheduler_backfill,
    ):
        blank_workflow_fn = temp_dbos_scheduler_backfill
        schedule_input = _blank_schedule_input(blank_workflow_fn)
        backfill_anchor = datetime.datetime(
            2026, 7, 15, 11, 0, 0, tzinfo=datetime.timezone.utc,
        )
        backfill_end = datetime.datetime(
            2026, 7, 15, 12, 30, 0, tzinfo=datetime.timezone.utc,
        )
        expected_scheduled_time = datetime.datetime(
            2026, 7, 15, 12, 0, 0, tzinfo=datetime.timezone.utc,
        )
        expected_workflow_id = (
            f"sched-{_BLANK_SCHEDULE_NAME}-{expected_scheduled_time.isoformat()}"
        )

        dbos.DBOS.create_schedule(
            schedule_name=schedule_input["schedule_name"],
            workflow_fn=schedule_input["workflow_fn"],
            schedule=schedule_input["schedule"],
            context=schedule_input.get("context"),
            automatic_backfill=schedule_input.get("automatic_backfill", False),
            queue_name=schedule_input.get("queue_name"),
        )
        existing_schedule = dbos.DBOS.get_schedule(_BLANK_SCHEDULE_NAME)
        assert existing_schedule is not None
        assert existing_schedule.get("last_fired_at") is None

        await _run_startup_backfill(
            schedule_input,
            backfill_anchor=backfill_anchor,
            backfill_end=backfill_end,
        )

        workflow_status = await dbos.DBOS.get_workflow_status_async(expected_workflow_id)
        assert workflow_status is not None
        assert workflow_status.app_version == dbos.DBOS.application_version

        workflow_handle = await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(
            expected_workflow_id,
        )
        workflow_result = await asyncio.wait_for(
            workflow_handle.get_result(),
            timeout=_WORKFLOW_RESULT_TIMEOUT_SECONDS,
        )
        assert workflow_result == {"ran": True}

        final_workflow_status = await dbos.DBOS.get_workflow_status_async(expected_workflow_id)
        assert final_workflow_status is not None
        assert final_workflow_status.status == dbos.WorkflowStatusString.SUCCESS.value
        assert expected_scheduled_time in blank_backfill_test_runs

    async def test_startup_backfill_skipped_when_slot_already_success(
        self,
        temp_dbos_scheduler_backfill,
    ):
        blank_workflow_fn = temp_dbos_scheduler_backfill
        schedule_input = _blank_schedule_input(blank_workflow_fn)
        backfill_anchor = datetime.datetime(
            2026, 7, 15, 11, 0, 0, tzinfo=datetime.timezone.utc,
        )
        backfill_end = datetime.datetime(
            2026, 7, 15, 12, 30, 0, tzinfo=datetime.timezone.utc,
        )
        expected_scheduled_time = datetime.datetime(
            2026, 7, 15, 12, 0, 0, tzinfo=datetime.timezone.utc,
        )
        expected_workflow_id = (
            f"sched-{_BLANK_SCHEDULE_NAME}-{expected_scheduled_time.isoformat()}"
        )

        dbos.DBOS.create_schedule(
            schedule_name=schedule_input["schedule_name"],
            workflow_fn=schedule_input["workflow_fn"],
            schedule=schedule_input["schedule"],
            context=schedule_input.get("context"),
            automatic_backfill=schedule_input.get("automatic_backfill", False),
            queue_name=schedule_input.get("queue_name"),
        )

        await _run_startup_backfill(
            schedule_input,
            backfill_anchor=backfill_anchor,
            backfill_end=backfill_end,
        )
        workflow_handle = await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(
            expected_workflow_id,
        )
        await asyncio.wait_for(
            workflow_handle.get_result(),
            timeout=_WORKFLOW_RESULT_TIMEOUT_SECONDS,
        )
        assert len(blank_backfill_test_runs) == 1

        await _run_startup_backfill(
            schedule_input,
            backfill_anchor=backfill_anchor,
            backfill_end=backfill_end,
        )

        final_workflow_status = await dbos.DBOS.get_workflow_status_async(expected_workflow_id)
        assert final_workflow_status is not None
        assert final_workflow_status.status == dbos.WorkflowStatusString.SUCCESS.value
        assert len(blank_backfill_test_runs) == 1

    async def test_backfill_stuck_when_db_latest_differs_from_runtime(
        self,
        temp_dbos_scheduler_backfill,
    ):
        blank_workflow_fn = temp_dbos_scheduler_backfill
        schedule_input = _blank_schedule_input(blank_workflow_fn)
        backfill_anchor = datetime.datetime(
            2026, 7, 15, 11, 0, 0, tzinfo=datetime.timezone.utc,
        )
        backfill_end = datetime.datetime(
            2026, 7, 15, 12, 30, 0, tzinfo=datetime.timezone.utc,
        )
        expected_scheduled_time = datetime.datetime(
            2026, 7, 15, 12, 0, 0, tzinfo=datetime.timezone.utc,
        )
        expected_workflow_id = (
            f"sched-{_BLANK_SCHEDULE_NAME}-{expected_scheduled_time.isoformat()}"
        )

        dbos.DBOS.create_schedule(
            schedule_name=schedule_input["schedule_name"],
            workflow_fn=schedule_input["workflow_fn"],
            schedule=schedule_input["schedule"],
            context=schedule_input.get("context"),
            automatic_backfill=schedule_input.get("automatic_backfill", False),
            queue_name=schedule_input.get("queue_name"),
        )

        _seed_stale_latest_application_version(_STALE_APP_VERSION)
        dbos.DBOS.set_latest_application_version(_STALE_APP_VERSION)

        await _run_startup_backfill(
            schedule_input,
            backfill_anchor=backfill_anchor,
            backfill_end=backfill_end,
        )

        workflow_status = await dbos.DBOS.get_workflow_status_async(expected_workflow_id)
        assert workflow_status is not None
        assert workflow_status.app_version == _STALE_APP_VERSION
        assert workflow_status.app_version != dbos.DBOS.application_version

        await _assert_workflow_stays_enqueued(
            expected_workflow_id,
            _STUCK_POLL_SECONDS,
        )

    async def test_backfill_resumes_after_application_version_migration(
        self,
        temp_dbos_scheduler_backfill,
    ):
        blank_workflow_fn = temp_dbos_scheduler_backfill
        schedule_input = _blank_schedule_input(blank_workflow_fn)
        backfill_anchor = datetime.datetime(
            2026, 7, 15, 11, 0, 0, tzinfo=datetime.timezone.utc,
        )
        backfill_end = datetime.datetime(
            2026, 7, 15, 12, 30, 0, tzinfo=datetime.timezone.utc,
        )
        expected_scheduled_time = datetime.datetime(
            2026, 7, 15, 12, 0, 0, tzinfo=datetime.timezone.utc,
        )
        expected_workflow_id = (
            f"sched-{_BLANK_SCHEDULE_NAME}-{expected_scheduled_time.isoformat()}"
        )

        dbos.DBOS.create_schedule(
            schedule_name=schedule_input["schedule_name"],
            workflow_fn=schedule_input["workflow_fn"],
            schedule=schedule_input["schedule"],
            context=schedule_input.get("context"),
            automatic_backfill=schedule_input.get("automatic_backfill", False),
            queue_name=schedule_input.get("queue_name"),
        )

        _seed_stale_latest_application_version(_STALE_APP_VERSION)
        dbos.DBOS.set_latest_application_version(_STALE_APP_VERSION)

        await _run_startup_backfill(
            schedule_input,
            backfill_anchor=backfill_anchor,
            backfill_end=backfill_end,
        )

        workflow_status = await dbos.DBOS.get_workflow_status_async(expected_workflow_id)
        assert workflow_status is not None
        assert workflow_status.app_version == _STALE_APP_VERSION
        assert workflow_status.app_version != dbos.DBOS.application_version

        import dbos._dbos as dbos_internals
        import octobot_node.scheduler.workflows_version_migration as workflows_version_migration

        scheduler_database_url = dbos_internals._get_dbos_instance()._sys_db.engine.url
        assert scheduler_database_url is not None
        assert scheduler_database_url.database is not None

        with mock.patch.object(
            workflows_version_migration.octobot_node.config.settings,
            "SCHEDULER_POSTGRES_URL",
            None,
        ), mock.patch.object(
            workflows_version_migration.octobot_node.config.settings,
            "SCHEDULER_SQLITE_FILE",
            scheduler_database_url.database,
        ):
            workflows_version_migration.migrate_stranded_workflow_versions(
                target_version=dbos.DBOS.application_version,
            )

        workflow_handle = await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(
            expected_workflow_id,
        )
        workflow_result = await asyncio.wait_for(
            workflow_handle.get_result(),
            timeout=_WORKFLOW_RESULT_TIMEOUT_SECONDS,
        )
        assert workflow_result == {"ran": True}

        final_workflow_status = await dbos.DBOS.get_workflow_status_async(expected_workflow_id)
        assert final_workflow_status is not None
        assert final_workflow_status.status == dbos.WorkflowStatusString.SUCCESS.value
        assert expected_scheduled_time in blank_backfill_test_runs
