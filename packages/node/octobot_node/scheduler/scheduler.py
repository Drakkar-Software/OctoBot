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
import octobot_node.scheduler.workflows_util as workflows_util
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
    AUTOMATIONS_WORKFLOW_QUEUE: dbos.Queue = None # type: ignore

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
        self.AUTOMATIONS_WORKFLOW_QUEUE = dbos.Queue(name=octobot_node.enums.SchedulerQueues.AUTOMATIONS_WORKFLOW_QUEUE.value)

    async def get_periodic_tasks(self) -> list[dict]:
        """DBOS scheduled workflows are not easily introspectable; return empty list."""
        return [] # TODO

    async def get_pending_tasks(self) -> list[dict]:
        if not self.INSTANCE:
            return []
        tasks: list[dict] = []
        try:
            pending_workflow_statuses = await self.INSTANCE.list_workflows_async(status=["ENQUEUED", "PENDING"])
            for pending_workflow_status in pending_workflow_statuses or []:
                try:
                    if progress_status := await workflows_util.get_progress_status(pending_workflow_status.workflow_id):
                        description = f"{progress_status.latest_step_by_automation_id}"
                    else:
                        description = f"Pending task: {pending_workflow_status.workflow_id}"
                    task_dict = self._parse_workflow_status(pending_workflow_status, octobot_node.models.TaskStatus.PENDING, description)
                    tasks.append(task_dict)
                except Exception as e:
                    self.logger.warning(f"Failed to process pending workflow {pending_workflow_status.workflow_id}: {e}")
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
            completed_workflow_statuses = await self.INSTANCE.list_workflows_async(status=["SUCCESS", "ERROR"], load_output=True)
            for completed_workflow_status in completed_workflow_statuses or []:
                try:
                    wf_status = completed_workflow_status.status
                    task_name = completed_workflow_status.workflow_id
                    metadata = ""
                    result = ""
                    if wf_status == "SUCCESS":
                        result = completed_workflow_status.output
                        execution_error = result.get("error") if isinstance(result, dict) else None
                        description = "Error" if execution_error else "Completed" 
                        status = octobot_node.models.TaskStatus.FAILED if execution_error else octobot_node.models.TaskStatus.COMPLETED
                        if task := workflows_util.get_input_task(completed_workflow_status):
                            metadata = task.content_metadata
                            task_name = task.name
                    else:
                        description = "Task failed"
                        status = octobot_node.models.TaskStatus.FAILED

                    tasks.append({
                        "id": completed_workflow_status.workflow_id,
                        "name": task_name,
                        "description": description,
                        "status": status,
                        "result": json.dumps(_sanitize(result.get("history", result))) if isinstance(result, dict) else "",
                        "result_metadata": metadata,
                        "scheduled_at": completed_workflow_status.created_at,
                        "started_at": None,
                        "completed_at": completed_workflow_status.updated_at,
                    })
                except Exception as e:
                    self.logger.exception(e, True, f"Failed to process result workflow {completed_workflow_status.workflow_id}: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to list result workflows: {e}")
        return tasks

    def _parse_workflow_status(
        self,
        workflow_status: dbos.WorkflowStatus,
        status: octobot_node.models.TaskStatus,
        description: typing.Optional[str] = None,
    ) -> dict:
        """Map DBOS WorkflowStatus to octobot_node.models.Task dict."""
        task_id = str(workflow_status.workflow_id)
        task_name = workflow_status.name
        task_type = None
        task_actions = None
        if workflow_status.input:
            if task := workflows_util.get_input_task(workflow_status):
                task_type = task.type
                task_actions = task.content #todo confi

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
