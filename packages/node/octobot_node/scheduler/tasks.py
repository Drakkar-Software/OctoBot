#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import functools
import datetime
import asyncio
import json
import logging
import time


from octobot_node.scheduler import SCHEDULER
from octobot_node.scheduler.task_context import encrypted_task
from tentacles.Services.Interfaces.node_api.models import Task, TaskType
from tentacles.Services.Interfaces.node_api.enums import TaskResultKeys
from tentacles.Services.Interfaces.node_api.models import TaskStatus

import octobot_node.scheduler.octobot_lib as octobot_lib


def async_task(func):
    """
    Decorator to ensure that the function it wraps is a non-async function that can then use asyncio.run(), e.g. Huey tasks.
    Huey tasks will be called in one of 2 contexts: either they are the top-level function(ish) in the process, and there is no loop yet, or we are running tests in an an async context already and we need to re-use the current loop.
    """

    @functools.wraps(func)
    def wrapper_decorator(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        task = loop.create_task(func(*args, **kwargs))
        return loop.run_until_complete(task)

    return wrapper_decorator


@SCHEDULER.INSTANCE.task()
def start_octobot(task: Task):
    with encrypted_task(task):
        # TODO
        task.result = "ok"
    return {
        TaskResultKeys.STATUS.value: TaskStatus.COMPLETED.value,
        TaskResultKeys.RESULT.value: task.result, 
        TaskResultKeys.METADATA.value: task.result_metadata,
        TaskResultKeys.TASK.value: {"name": task.name},
        TaskResultKeys.ERROR.value: None
    }


def _reshedule_octobot_execution(
    task: Task, next_actions_description: octobot_lib.OctoBotActionsJobDescription
):
    task.content = json.dumps(next_actions_description.to_dict(include_default_values=False))
    next_execution_time = next_actions_description.get_next_execution_time()
    now_time = time.time()
    if next_execution_time == 0 or next_execution_time < now_time:
        delay = 0
    else:
        delay = next_execution_time - now_time
    logging.getLogger("octobot_node.scheduler.tasks").info(
        f"Scheduling task '{task.name}' for execution in {delay} seconds"
    )
    return execute_octobot.schedule(args=[task], delay=delay)


@SCHEDULER.INSTANCE.task()
@async_task
async def execute_octobot(task: Task):
    with encrypted_task(task):
        if task.type == TaskType.EXECUTE_ACTIONS.value:
            logging.getLogger("octobot_node.scheduler.tasks").info(f"Executing task '{task.name}' with content: {task.content} ...")
            result: octobot_lib.OctoBotActionsJobResult = await octobot_lib.OctoBotActionsJob(
                task.content
            ).run()
            task.result = {
                "orders": result.get_created_orders(),
                "transfers": result.get_deposit_and_withdrawal_details(),
            }
            if result.next_actions_description:
                _reshedule_octobot_execution(task, result.next_actions_description)
        else:
            raise ValueError(f"Invalid task type: {task.type}")
    return {
        TaskResultKeys.STATUS.value: TaskStatus.COMPLETED.value,
        TaskResultKeys.RESULT.value: task.result, 
        TaskResultKeys.METADATA.value: task.result_metadata,
        TaskResultKeys.TASK.value: {"name": task.name},
        TaskResultKeys.ERROR.value: None
    }


@SCHEDULER.INSTANCE.task()
def stop_octobot(task: Task):
    with encrypted_task(task):
        # TODO
        task.result = "ok"
    return {
        TaskResultKeys.STATUS.value: TaskStatus.COMPLETED.value,
        TaskResultKeys.RESULT.value: task.result, 
        TaskResultKeys.METADATA.value: task.result_metadata,
        TaskResultKeys.TASK.value: {"name": task.name},
        TaskResultKeys.ERROR.value: None
    }

def trigger_task(task: Task) -> bool:
    if task.type == TaskType.START_OCTOBOT.value:
        start_octobot.schedule(args=[task], delay=1)
        return True
    elif task.type == TaskType.STOP_OCTOBOT.value:
        stop_octobot.schedule(args=[task], delay=1)
        return True
    elif task.type == TaskType.EXECUTE_ACTIONS.value:
        execute_octobot.schedule(args=[task], delay=1)
        return True
    else:
        raise ValueError(f"Invalid task type: {task.type}")
