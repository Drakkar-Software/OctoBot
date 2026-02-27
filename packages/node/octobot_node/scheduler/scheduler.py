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

import dbos
import json
import logging
import typing
import decimal
import enum

import octobot_node.config
import octobot_node.enums
import octobot_node.models
import octobot_node.scheduler.workflows.base as workflow_base
try:
    from octobot import VERSION
except ImportError:
    VERSION = "unknown"

DEFAULT_NAME = "octobot_node"

_BASE_CONFIG = dbos.DBOSConfig(
    name=DEFAULT_NAME,
    max_executor_threads=octobot_node.config.settings.SCHEDULER_MAX_EXECUTOR_THREADS,
    application_version=VERSION,
)


def _sanitize(result: typing.Any) -> typing.Any:
    if isinstance(result, decimal.Decimal):
        return float(result)
    if isinstance(result, enum.Enum):
        return result.value
    if isinstance(result, dict):
        return {k: _sanitize(v) for k, v in result.items()}
    elif isinstance(result, list):
        return [_sanitize(v) for v in result]
    return result


def _sanitize(result: typing.Any) -> typing.Any:
    if isinstance(result, decimal.Decimal):
        return float(result)
    if isinstance(result, enum.Enum):
        return result.value
    if isinstance(result, dict):
        return {k: _sanitize(v) for k, v in result.items()}
    elif isinstance(result, list):
        return [_sanitize(v) for v in result]
    return result


class Scheduler:
    INSTANCE: dbos.DBOS = None # type: ignore
    BOT_WORKFLOW_QUEUE: dbos.Queue = None # type: ignore

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def create(self):
        if octobot_node.config.settings.SCHEDULER_POSTGRES_URL:
            self.logger.info(
                f"Initializing scheduler with Postgres backend at {octobot_node.config.settings.SCHEDULER_POSTGRES_URL}",
            )

            self.INSTANCE = dbos.DBOS(config=dbos.DBOSConfig(
                **_BASE_CONFIG,
                **{
                    "system_database_url": octobot_node.config.settings.SCHEDULER_POSTGRES_URL,
                },
            ))
        else:
            self.logger.info(
                f"Initializing scheduler with sqlite backend at {octobot_node.config.settings.SCHEDULER_SQLITE_FILE}",
            )
            # DB not autosaved?
            self.INSTANCE = dbos.DBOS(config=dbos.DBOSConfig(
                **_BASE_CONFIG,
                **{
                    "system_database_url": f"sqlite:///{octobot_node.config.settings.SCHEDULER_SQLITE_FILE}",
                },
            ))

    def is_enabled(self) -> bool:
        # enabled if master mode or consumer only mode
        return (
            octobot_node.config.settings.IS_MASTER_MODE 
            or octobot_node.config.settings.CONSUMER_ONLY
        )

    def start(self):
        if self.INSTANCE:
            self.create_queues()
            self.logger.info("Starting scheduler")
            self.INSTANCE.launch()
            self.logger.info("Scheduler started")
        else:
            self.logger.warning("Scheduler not initialized")

    def stop(self) -> None:
        if self.INSTANCE:
            self.INSTANCE.destroy()
            self.logger.info("Scheduler stopped")
        else:
            self.logger.warning("Scheduler not initialized")

    def create_queues(self):
        self.BOT_WORKFLOW_QUEUE = dbos.Queue(name=octobot_node.enums.SchedulerQueues.BOT_WORKFLOW_QUEUE.value)

    async def get_periodic_tasks(self) -> list[dict]:
        """DBOS scheduled workflows are not easily introspectable; return empty list."""
        return [] # TODO

    async def get_pending_tasks(self) -> list[dict]:
        if not self.INSTANCE:
            return []
        tasks: list[dict] = []
        try:
            workflows = await self.INSTANCE.list_workflows_async(status=["ENQUEUED", "PENDING"])
            for w in workflows or []:
                try:
                    task_dict = self._parse_workflow_status(w, octobot_node.models.TaskStatus.PENDING, f"Pending task: {w.name}")
                    tasks.append(task_dict)
                except Exception as e:
                    self.logger.warning(f"Failed to process pending workflow {w.name}: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to list pending workflows: {e}")
        return tasks

    async def get_scheduled_tasks(self) -> list[dict]:
        """DBOS has no direct 'scheduled for later' queue; return empty list."""
        return []

    async def get_results(self) -> list[dict]:
        if not self.INSTANCE:
            return []
        tasks: list[dict] = []
        try:
            workflows = await self.INSTANCE.list_workflows_async(status=["SUCCESS", "ERROR"], load_output=True)
            for w in workflows or []:
                try:
                    wf_status = w.status
                    if wf_status == "SUCCESS":
                        if step := await workflow_base.get_current_step(w.workflow_id):
                            description = f"{step.previous_step_details}"
                        else:
                            description = "Task completed"
                        status = octobot_node.models.TaskStatus.COMPLETED
                        result_obj = w.output
                        if isinstance(result_obj, dict):
                            result = result_obj.get(octobot_node.enums.TaskResultKeys.RESULT.value)
                            metadata = result_obj.get(octobot_node.enums.TaskResultKeys.METADATA.value)
                        else:
                            result = result_obj
                            metadata = ""
                    else:
                        description = "Task failed"
                        status = octobot_node.models.TaskStatus.FAILED
                        result = ""
                        metadata = ""
                        result_obj = None

                    tasks.append({
                        "id": w.workflow_id,
                        "name": self.get_task_name(result_obj, w.workflow_id),
                        "description": description,
                        "status": status,
                        "result": json.dumps(_sanitize(result)) if result is not None else "",
                        "result_metadata": metadata,
                        "scheduled_at": w.created_at,
                        "started_at": None,
                        "completed_at": w.updated_at,
                    })
                except Exception as e:
                    self.logger.warning(f"Failed to process result workflow {w.workflow_id}: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to list result workflows: {e}")
        return tasks

    def _parse_workflow_status(
        self,
        w: typing.Any,
        status: octobot_node.models.TaskStatus,
        description: typing.Optional[str] = None,
    ) -> dict:
        """Map DBOS WorkflowStatus to octobot_node.models.Task dict."""
        task_id = str(w.workflow_id)
        task_name = w.name if hasattr(w, "name") else str(w.workflow_id)
        task_type = None
        task_actions = None
        if hasattr(w, "input") and w.input:
            inp = w.input
            if isinstance(inp, (list, tuple)) and inp:
                first = inp[0]
                if hasattr(first, "type"):
                    task_type = first.type
                elif isinstance(first, dict):
                    task_type = first.get("type")
                    task_actions = first.get("actions")

        return {
            "id": task_id,
            "name": task_name,
            "description": description,
            "actions": task_actions,
            "type": task_type,
            "status": status,
            "retries": 0,
            "retry_delay": 0,
            "priority": 0,
            "expires": None,
            "expires_resolved": None,
            "scheduled_at": None,
            "started_at": None,
            "completed_at": None,
        }

    def get_task_name(self, task_data: dict | octobot_node.models.Task | None, default_value: typing.Optional[str] = None) -> typing.Optional[str]:
        if isinstance(task_data, octobot_node.models.Task):
            return task_data.name
        elif isinstance(task_data, dict):
            return task_data.get(octobot_node.enums.TaskResultKeys.TASK.value, {}).get("name", default_value)
        else:
            return default_value
