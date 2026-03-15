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

import octobot_commons.logging
import octobot_node.config
import octobot_node.enums
import octobot_node.models
import octobot_node.constants
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
    AUTOMATION_WORKFLOW_QUEUE: dbos.Queue = None # type: ignore

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
        if self.INSTANCE and octobot_node.config.settings.USE_DEDICATED_LOG_FILE_PER_AUTOMATION:
            self._setup_workflow_logging()

    def _setup_workflow_logging(self) -> None:
        """Register DBOS workflow ID provider and add workflow file handler for per-workflow log files."""
        octobot_commons.logging.add_context_based_file_handler(
            octobot_node.constants.AUTOMATION_LOGS_FOLDER,
            self._get_dbos_workflow_id
        )

    @staticmethod
    def _get_dbos_workflow_id() -> typing.Optional[str]:
        """Return the current DBOS workflow ID when executing within a step or workflow."""
        if workflow_id := getattr(dbos.DBOS, "workflow_id", None):
            # group children workflows and parent workflows together
            # (a child workflow has the parent's workflow ID as a prefix)
            return workflow_id[:octobot_node.constants.PARENT_WORKFLOW_ID_LENGTH]
        return None

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
        self.AUTOMATION_WORKFLOW_QUEUE = dbos.Queue(name=octobot_node.enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE.value)

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
                    if state := workflows_util.get_automation_state(pending_workflow_status):
                        next_step = ", ".join([
                            action.get_summary()
                            for action in state.automation.actions_dag.get_executable_actions()
                        ])
                        description = f"next steps: {next_step}"
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
            completed_workflow_statuses = await self.INSTANCE.list_workflows_async(status=[
                dbos.WorkflowStatusString.SUCCESS.value, dbos.WorkflowStatusString.ERROR.value
            ], load_output=True)
            for completed_workflow_status in completed_workflow_statuses or []:
                try:
                    wf_status = completed_workflow_status.status
                    task_name = completed_workflow_status.workflow_id
                    metadata = ""
                    result = ""
                    if wf_status == dbos.WorkflowStatusString.SUCCESS.value:
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
                        "result": json.dumps(_sanitize(result.get("history", result))) if isinstance(result, dict) else "", #todo change
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
