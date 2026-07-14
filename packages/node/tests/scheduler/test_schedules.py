#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import mock
import pytest

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


class TestRegisterSchedules:
    @pytest.fixture
    def dbos_cleanup_workflow_module(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow_module_loaded

        yield dbos_cleanup_workflow_module_loaded

    def test_creates_schedule_when_missing(self, dbos_cleanup_workflow_module, temp_dbos_scheduler):
        import octobot_node.scheduler.schedules as schedules_module

        schedule_input = _configured_cleanup_schedule_input(dbos_cleanup_workflow_module)
        mock_logger = mock.Mock()

        with mock.patch(
            "octobot_node.scheduler.schedules.dbos_cleanup_workflow.get_schedule_input",
            return_value=schedule_input,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule",
            return_value=None,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.create_schedule",
        ) as create_schedule_mock, mock.patch(
            "octobot_node.scheduler.schedules.logging.getLogger",
            return_value=mock_logger,
        ), mock.patch.object(
            temp_dbos_scheduler.INSTANCE,
            "apply_schedules",
        ) as apply_schedules_mock:
            schedules_module.register_schedules(temp_dbos_scheduler)

        create_schedule_mock.assert_called_once_with(
            schedule_name=schedule_input["schedule_name"],
            workflow_fn=schedule_input["workflow_fn"],
            schedule=schedule_input["schedule"],
            context=schedule_input.get("context"),
            automatic_backfill=schedule_input.get("automatic_backfill", False),
            cron_timezone=schedule_input.get("cron_timezone"),
            queue_name=schedule_input.get("queue_name"),
        )
        apply_schedules_mock.assert_not_called()
        mock_logger.info.assert_called_once_with(
            "Creating schedule %s (%s)",
            schedule_input["schedule_name"],
            schedule_input["schedule"],
        )

    def test_keeps_schedule_when_config_matches(self, dbos_cleanup_workflow_module, temp_dbos_scheduler):
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
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule",
            return_value=existing_schedule,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.create_schedule",
        ) as create_schedule_mock, mock.patch(
            "octobot_node.scheduler.schedules.logging.getLogger",
            return_value=mock_logger,
        ), mock.patch.object(
            temp_dbos_scheduler.INSTANCE,
            "apply_schedules",
        ) as apply_schedules_mock:
            schedules_module.register_schedules(temp_dbos_scheduler)

        create_schedule_mock.assert_not_called()
        apply_schedules_mock.assert_not_called()
        mock_logger.info.assert_called_once_with(
            "Keeping existing schedule %s (%s)",
            schedule_input["schedule_name"],
            schedule_input["schedule"],
        )

    def test_recreates_schedule_when_config_differs(self, dbos_cleanup_workflow_module, temp_dbos_scheduler):
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
            "octobot_node.scheduler.schedules.dbos.DBOS.get_schedule",
            return_value=existing_schedule,
        ), mock.patch(
            "octobot_node.scheduler.schedules.dbos.DBOS.create_schedule",
        ) as create_schedule_mock, mock.patch(
            "octobot_node.scheduler.schedules.logging.getLogger",
            return_value=mock_logger,
        ), mock.patch.object(
            temp_dbos_scheduler.INSTANCE,
            "apply_schedules",
        ) as apply_schedules_mock:
            schedules_module.register_schedules(temp_dbos_scheduler)

        create_schedule_mock.assert_not_called()
        apply_schedules_mock.assert_called_once_with([schedule_input])
        mock_logger.info.assert_called_once_with(
            "Updating schedule %s (%s): configuration changed",
            schedule_input["schedule_name"],
            schedule_input["schedule"],
        )
