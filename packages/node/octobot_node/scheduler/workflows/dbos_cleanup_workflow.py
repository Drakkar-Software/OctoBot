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
import datetime
import typing

import dbos

import octobot_commons.logging as logging
import octobot_node.enums
import octobot_node.scheduler.workflows_retention as workflows_retention

from octobot_node.scheduler import SCHEDULER  # avoid circular import

WORKFLOW_NAME = "dbos_cleanup"
SCHEDULE_NAME = "dbos_cleanup_daily"
SCHEDULE_CRON = "0 0 * * *"  # daily at midnight UTC


@SCHEDULER.INSTANCE.dbos_class()
class DbosCleanupWorkflow:
    @staticmethod
    @SCHEDULER.INSTANCE.workflow(name=WORKFLOW_NAME)
    async def dbos_cleanup(
        scheduled_time: datetime.datetime,
        context: typing.Any,
    ) -> dict[str, typing.Any]:
        return await DbosCleanupWorkflow._cleanup_outdated_automation_executions(
            scheduled_time,
        )

    @staticmethod
    @SCHEDULER.INSTANCE.step(name="cleanup_outdated_automation_executions")
    async def _cleanup_outdated_automation_executions(
        scheduled_time: datetime.datetime,
    ) -> dict[str, typing.Any]:
        logger = logging.get_logger(DbosCleanupWorkflow.__name__)
        if workflows_retention.should_skip_retention_cleanup_on_this_node():
            logger.info("dbos_cleanup skipped: consumer-only node")
            return dict(workflows_retention.EMPTY_CLEANUP_SUMMARY)
        if await workflows_retention.should_skip_retention_cleanup_for_scheduled_time(
            SCHEDULER,
            scheduled_time,
        ):
            logger.info(
                "dbos_cleanup skipped for scheduled_time %s: latest completed cleanup is newer",
                scheduled_time.isoformat(),
            )
            return dict(workflows_retention.EMPTY_CLEANUP_SUMMARY)
        return await workflows_retention.cleanup_outdated_automation_executions(SCHEDULER)


def get_schedule_input() -> dbos.ScheduleInput:
    return {
        "schedule_name": SCHEDULE_NAME,
        "workflow_fn": DbosCleanupWorkflow.dbos_cleanup,
        "schedule": SCHEDULE_CRON,
        "context": None,
        "automatic_backfill": True,
        "queue_name": octobot_node.enums.SchedulerQueues.DBOS_CLEANUP_QUEUE.value,
    }
