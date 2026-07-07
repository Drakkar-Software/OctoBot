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


def register_schedules(scheduler: scheduler_module.Scheduler) -> None:
    logger = logging.getLogger("schedules")
    schedule_inputs: list[dbos.ScheduleInput] = [
        dbos_cleanup_workflow.get_schedule_input(),
    ]
    for schedule_input in schedule_inputs:
        logger.info(
            "Registering schedule %s (%s)",
            schedule_input["schedule_name"],
            schedule_input["schedule"],
        )
        scheduler.INSTANCE.apply_schedules([schedule_input])
