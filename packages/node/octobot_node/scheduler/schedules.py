#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import logging

import dbos

import octobot_node.scheduler.scheduler as scheduler_module
import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow


def _existing_schedule_matches_configured(
    existing: dbos.WorkflowSchedule,
    schedule_input: dbos.ScheduleInput,
) -> bool:
    return (
        existing["schedule"] == schedule_input["schedule"]
        and bool(existing.get("automatic_backfill"))
        == schedule_input.get("automatic_backfill", False)
        and existing.get("cron_timezone") == schedule_input.get("cron_timezone")
        and existing.get("queue_name") == schedule_input.get("queue_name")
    )


def _ensure_schedule(
    scheduler: scheduler_module.Scheduler,
    schedule_input: dbos.ScheduleInput,
) -> None:
    logger = logging.getLogger("schedules")
    schedule_name = schedule_input["schedule_name"]
    schedule_cron = schedule_input["schedule"]
    existing_schedule = dbos.DBOS.get_schedule(schedule_name)
    if existing_schedule is None:
        logger.info("Creating schedule %s (%s)", schedule_name, schedule_cron)
        dbos.DBOS.create_schedule(
            schedule_name=schedule_name,
            workflow_fn=schedule_input["workflow_fn"],
            schedule=schedule_cron,
            context=schedule_input.get("context"),
            automatic_backfill=schedule_input.get("automatic_backfill", False),
            cron_timezone=schedule_input.get("cron_timezone"),
            queue_name=schedule_input.get("queue_name"),
        )
        return
    if _existing_schedule_matches_configured(existing_schedule, schedule_input):
        logger.info("Keeping existing schedule %s (%s)", schedule_name, schedule_cron)
        return
    logger.info(
        "Updating schedule %s (%s): configuration changed",
        schedule_name,
        schedule_cron,
    )
    scheduler.INSTANCE.apply_schedules([schedule_input])


def register_schedules(scheduler: scheduler_module.Scheduler) -> None:
    schedule_inputs: list[dbos.ScheduleInput] = [
        dbos_cleanup_workflow.get_schedule_input(),
    ]
    for schedule_input in schedule_inputs:
        _ensure_schedule(scheduler, schedule_input)
