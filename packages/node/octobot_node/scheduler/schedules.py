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
import asyncio
import datetime
import typing

import dbos
import dbos._croniter as dbos_croniter
import zoneinfo

import octobot_commons.logging as logging
import octobot_node.constants as constants
import octobot_node.scheduler.scheduler as scheduler_module
import octobot_node.scheduler.workflows.dbos_cleanup_workflow as dbos_cleanup_workflow
import octobot_node.scheduler.workflows.global_view_workflow as global_view_workflow
import octobot_node.scheduler.workflows.portfolio_history_workflow as portfolio_history_workflow
import octobot_node.scheduler.workflows_retention as workflows_retention


_DATETIME_CLASS = datetime.datetime


def _workflow_status_string(
    workflow_status: dbos.WorkflowStatus | dict[str, typing.Any],
) -> str:
    if isinstance(workflow_status, dict):
        return workflow_status["status"]
    return workflow_status.status


class ScheduleWindowSlotClassification(typing.TypedDict):
    missing: list[str]
    terminal: list[tuple[str, str]]
    in_progress: list[tuple[str, str]]


def get_backfill_schedule_default_anchor() -> datetime.datetime:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=constants.SCHEDULES_DEFAULT_BACKFILL_DAYS)
    )


def build_scheduled_workflow_id(
    schedule_name: str,
    trigger_time: datetime.datetime,
) -> str:
    return f"sched-{schedule_name}-{trigger_time.isoformat()}"


def get_scheduled_workflow_trigger_time(
    workflow_id: str,
    schedule_name: str,
) -> str | None:
    prefix = f"sched-{schedule_name}-"
    if not workflow_id.startswith(prefix):
        return None
    return workflow_id[len(prefix):]


def _enumerate_schedule_workflow_ids_in_window(
    schedule_name: str,
    schedule_input: dbos.ScheduleInput,
    start: datetime.datetime,
    end: datetime.datetime,
) -> list[str]:
    schedule_cron = schedule_input["schedule"]
    cron_timezone = schedule_input.get("cron_timezone")
    tz = zoneinfo.ZoneInfo(cron_timezone) if cron_timezone else datetime.timezone.utc
    if start.tzinfo is None:
        start = start.replace(tzinfo=datetime.timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=datetime.timezone.utc)
    start_in_tz = start.astimezone(tz)
    iterator = dbos_croniter.croniter(schedule_cron, start_in_tz, second_at_beginning=True)
    workflow_ids: list[str] = []
    while True:
        next_time = iterator.get_next(_DATETIME_CLASS)
        if next_time >= end:
            break
        workflow_ids.append(build_scheduled_workflow_id(schedule_name, next_time))
    return workflow_ids


async def _classify_schedule_window_slots(
    workflow_ids: list[str],
) -> ScheduleWindowSlotClassification:
    missing: list[str] = []
    terminal: list[tuple[str, str]] = []
    in_progress: list[tuple[str, str]] = []
    for workflow_id in workflow_ids:
        workflow_status = await dbos.DBOS.get_workflow_status_async(workflow_id)
        if workflow_status is None:
            missing.append(workflow_id)
        elif workflows_retention.is_terminal_workflow(workflow_status):
            terminal.append((workflow_id, _workflow_status_string(workflow_status)))
        else:
            in_progress.append((workflow_id, _workflow_status_string(workflow_status)))
    return {
        "missing": missing,
        "terminal": terminal,
        "in_progress": in_progress,
    }


def _get_latest_schedule_trigger_time_before(
    schedule_input: dbos.ScheduleInput,
    before: datetime.datetime,
) -> datetime.datetime | None:
    schedule_cron = schedule_input["schedule"]
    cron_timezone = schedule_input.get("cron_timezone")
    tz = zoneinfo.ZoneInfo(cron_timezone) if cron_timezone else datetime.timezone.utc
    if before.tzinfo is None:
        before = before.replace(tzinfo=datetime.timezone.utc)
    before_in_tz = before.astimezone(tz)
    iterator = dbos_croniter.croniter(schedule_cron, before_in_tz, second_at_beginning=True)
    return iterator.get_prev(_DATETIME_CLASS)


def _existing_schedule_matches_configured(
    existing: dbos.WorkflowSchedule,
    schedule_input: dbos.ScheduleInput,
) -> bool:
    return (
        existing["schedule"] == schedule_input["schedule"]
        and bool(existing.get("automatic_backfill"))
        == schedule_input.get("automatic_backfill", False)
        and bool(existing.get("catch_up_once_on_startup"))
        == schedule_input.get("catch_up_once_on_startup", False)
        and existing.get("cron_timezone") == schedule_input.get("cron_timezone")
        and existing.get("queue_name") == schedule_input.get("queue_name")
    )


async def _maybe_catch_up_schedule_once_on_startup(
    schedule_name: str,
    schedule_input: dbos.ScheduleInput,
) -> None:
    if not schedule_input.get("catch_up_once_on_startup", False):
        return
    existing_schedule = await dbos.DBOS.get_schedule_async(schedule_name)
    if existing_schedule is None:
        return

    logger = _get_logger()
    now = datetime.datetime.now(datetime.timezone.utc)
    trigger_time = _get_latest_schedule_trigger_time_before(schedule_input, now)
    if trigger_time is None:
        return

    workflow_id = build_scheduled_workflow_id(schedule_name, trigger_time)
    workflow_status = await dbos.DBOS.get_workflow_status_async(workflow_id)
    if workflow_status is not None:
        if workflows_retention.is_terminal_workflow(workflow_status):
            logger.info(
                "Startup catch-up not needed for schedule %s: latest slot %s already %s",
                schedule_name,
                workflow_id,
                _workflow_status_string(workflow_status),
            )
        else:
            logger.info(
                "Startup catch-up skipped for schedule %s: latest slot %s already %s",
                schedule_name,
                workflow_id,
                _workflow_status_string(workflow_status),
            )
        return

    logger.info(
        "Startup catch-up for schedule %s: enqueuing missed latest slot %s",
        schedule_name,
        workflow_id,
    )
    # backfill_schedule uses get_next from start; start one second before the slot
    # so the target trigger_time is the first cron fire in [start, end).
    backfill_start = trigger_time - datetime.timedelta(seconds=1)
    backfill_end = trigger_time + datetime.timedelta(seconds=1)
    await asyncio.to_thread(
        dbos.DBOS.backfill_schedule,
        schedule_name,
        backfill_start,
        backfill_end,
    )


async def _maybe_backfill_schedule_on_startup(
    schedule_name: str,
    schedule_input: dbos.ScheduleInput,
) -> None:
    # DBOS automatic_backfill only runs when last_fired_at is already set (i.e. the
    # cron fired at least once while the node was up). On first install or after long
    # downtime with a NULL last_fired_at, missed executions are never enqueued unless
    # we backfill explicitly here during register_schedules (after SCHEDULER.start()).
    #
    # last_fired_at stays NULL when cleanup only runs via startup backfill (not live
    # cron), so we also check whether expected cron slots already have terminal
    # workflows before calling backfill_schedule.
    if not schedule_input.get("automatic_backfill", False):
        return
    existing_schedule = await dbos.DBOS.get_schedule_async(schedule_name)
    if existing_schedule is None:
        return
    last_fired_at = existing_schedule.get("last_fired_at")
    if last_fired_at:
        # DBOS already backfills on launch when last_fired_at is known.
        return

    logger = _get_logger()
    start = get_backfill_schedule_default_anchor()
    end = datetime.datetime.now(datetime.timezone.utc)
    if start >= end:
        return

    window_workflow_ids = _enumerate_schedule_workflow_ids_in_window(
        schedule_name,
        schedule_input,
        start,
        end,
    )
    if not window_workflow_ids:
        logger.info(
            "Startup backfill not needed for schedule %s: no cron slots in window [%s, %s)",
            schedule_name,
            start.isoformat(),
            end.isoformat(),
        )
        return

    classifications = await _classify_schedule_window_slots(window_workflow_ids)
    if not classifications["missing"] and not classifications["in_progress"]:
        logger.info(
            "Startup backfill not needed for schedule %s: last_fired_at unset but %s cron slot(s) in [%s, %s) already terminal",
            schedule_name,
            len(window_workflow_ids),
            start.isoformat(),
            end.isoformat(),
        )
        for workflow_id, status in classifications["terminal"]:
            logger.info(
                "Schedule %s slot %s already %s",
                schedule_name,
                workflow_id,
                status,
            )
        return

    logger.info(
        "Startup backfill for schedule %s: last_fired_at unset, checking missed cron slots in [%s, %s)",
        schedule_name,
        start.isoformat(),
        end.isoformat(),
    )
    workflow_statuses_before_backfill = await asyncio.gather(
        *[
            dbos.DBOS.get_workflow_status_async(workflow_id)
            for workflow_id in window_workflow_ids
        ],
    )
    statuses_before_backfill = dict(
        zip(window_workflow_ids, workflow_statuses_before_backfill, strict=True),
    )
    workflow_handles = await asyncio.to_thread(
        dbos.DBOS.backfill_schedule,
        schedule_name,
        start,
        end,
    )
    enqueued_count = 0
    unchanged_count = 0
    for workflow_handle in workflow_handles:
        workflow_id = workflow_handle.get_workflow_id()
        status_before = statuses_before_backfill.get(workflow_id)
        if status_before is None:
            enqueued_count += 1
            logger.info(
                "Startup backfill enqueued schedule %s workflow %s",
                schedule_name,
                workflow_id,
            )
        else:
            unchanged_count += 1
            logger.info(
                "Startup backfill left schedule %s workflow %s unchanged (already %s)",
                schedule_name,
                workflow_id,
                _workflow_status_string(status_before),
            )
    logger.info(
        "Startup backfill finished for schedule %s: %s enqueued, %s unchanged",
        schedule_name,
        enqueued_count,
        unchanged_count,
    )


async def _ensure_schedule(
    scheduler: scheduler_module.Scheduler,
    schedule_input: dbos.ScheduleInput,
) -> None:
    logger = _get_logger()
    schedule_name = schedule_input["schedule_name"]
    schedule_cron = schedule_input["schedule"]
    existing_schedule = await dbos.DBOS.get_schedule_async(schedule_name)
    if existing_schedule is None:
        logger.info("Creating schedule %s (%s)", schedule_name, schedule_cron)
        await dbos.DBOS.create_schedule_async(
            schedule_name=schedule_name,
            workflow_fn=schedule_input["workflow_fn"],
            schedule=schedule_cron,
            context=schedule_input.get("context"),
            automatic_backfill=schedule_input.get("automatic_backfill", False),
            cron_timezone=schedule_input.get("cron_timezone"),
            queue_name=schedule_input.get("queue_name"),
        )
    elif _existing_schedule_matches_configured(existing_schedule, schedule_input):
        logger.info("Keeping existing schedule %s (%s)", schedule_name, schedule_cron)
    else:
        logger.info(
            "Updating schedule %s (%s): configuration changed",
            schedule_name,
            schedule_cron,
        )
        await scheduler.INSTANCE.apply_schedules_async([schedule_input])
    await _maybe_backfill_schedule_on_startup(schedule_name, schedule_input)
    await _maybe_catch_up_schedule_once_on_startup(schedule_name, schedule_input)


async def register_schedules(scheduler: scheduler_module.Scheduler) -> None:
    schedule_inputs: list[dbos.ScheduleInput] = [
        dbos_cleanup_workflow.get_schedule_input(),
        global_view_workflow.get_schedule_input(),
        portfolio_history_workflow.get_schedule_input(),
    ]
    for schedule_input in schedule_inputs:
        await _ensure_schedule(scheduler, schedule_input)


async def update_cleanup_schedule_cron(
    scheduler: scheduler_module.Scheduler,
    cron: str,
) -> dict[str, typing.Any]:
    existing_schedule = await dbos.DBOS.get_schedule_async(dbos_cleanup_workflow.SCHEDULE_NAME)
    if existing_schedule is not None and existing_schedule["schedule"] == cron:
        return {"changed": False, "cron": cron}
    schedule_input = dbos_cleanup_workflow.get_schedule_input(cron=cron)
    logger = _get_logger()
    logger.info("Updating cleanup schedule cron to %s", cron)
    await scheduler.INSTANCE.apply_schedules_async([schedule_input])
    return {"changed": True, "cron": cron}


def _get_logger() -> logging.BotLogger:
    return logging.get_logger("schedules")
