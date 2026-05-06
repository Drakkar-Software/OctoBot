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

import asyncio
import dbos
import json
import logging
import typing
import decimal
import enum
import sqlalchemy

import octobot_commons.logging
import octobot_node.config
import octobot_node.enums
import octobot_node.models
import octobot_node.constants
import octobot_node.scheduler.workflows_util as workflows_util
import octobot_node.scheduler.workflows.params as workflow_params
import octobot_node.scheduler.encryption as encryption
import octobot_node.scheduler.task_context as task_context
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

    def is_initialized(self) -> bool:
        return self.INSTANCE is not None

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

    async def get_periodic_tasks(self, wallet_address: typing.Optional[str] = None) -> list[octobot_node.models.Execution]:
        """DBOS scheduled workflows are not easily introspectable; return empty list."""
        return [] # TODO

    async def get_pending_tasks(self, wallet_address: typing.Optional[str] = None) -> list[octobot_node.models.Execution]:
        if not self.INSTANCE:
            return []
        executions: list[octobot_node.models.Execution] = []
        try:
            pending_workflow_statuses = workflows_util.filter_by_wallet(
                await self.INSTANCE.list_workflows_async(status=[dbos.WorkflowStatusString.ENQUEUED.value, dbos.WorkflowStatusString.PENDING.value]),
                wallet_address,
            )
            for pending_workflow_status in pending_workflow_statuses:
                try:
                    task = workflows_util.get_input_task(pending_workflow_status)
                    if reader := workflows_util.get_automation_state_reader(pending_workflow_status):
                        next_step = ", ".join([
                            action.get_summary()
                            for action in reader.get_executable_actions()
                        ])
                        description = f"next steps: {next_step}"
                    else:
                        description = f"Pending task: {pending_workflow_status.workflow_id}"
                    execution = self._parse_workflow_status(pending_workflow_status, octobot_node.models.TaskStatus.PENDING, description)
                    executions.append(execution)
                except Exception as e:
                    self.logger.warning(f"Failed to process pending workflow {pending_workflow_status.workflow_id}: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to list pending workflows: {e}")
        return executions

    async def cancel_workflows(self, workflow_ids: list[str]) -> list[str]:
        try:
            self.logger.info(f"Cancelling {len(workflow_ids)} workflows {workflow_ids}")
            await self.INSTANCE.cancel_workflows_async(workflow_ids)
            self.logger.info(f"{len(workflow_ids)} workflows {workflow_ids} cancelled")
            return workflow_ids
        except Exception as e:
            self.logger.exception(e, True, f"Failed to cancel workflows {workflow_ids}: {e}")
            return []

    async def delete_workflows(self, to_delete_workflow_ids: list[str]):
        self.logger.info(f"Deleting {len(to_delete_workflow_ids)} workflows")
        all_completed_workflows = await self.INSTANCE.list_workflows_async(status=[
            dbos.WorkflowStatusString.SUCCESS.value, dbos.WorkflowStatusString.ERROR.value,
            dbos.WorkflowStatusString.CANCELLED.value, dbos.WorkflowStatusString.MAX_RECOVERY_ATTEMPTS_EXCEEDED.value
        ])
        to_delete_parent_workflow_ids = [
            workflow_id[:octobot_node.constants.PARENT_WORKFLOW_ID_LENGTH] for workflow_id in to_delete_workflow_ids
        ]
        children_workflow_ids = [
            workflow.workflow_id for workflow in all_completed_workflows
            if any(workflow.workflow_id.startswith(parent_workflow_id) for parent_workflow_id in to_delete_parent_workflow_ids)
        ]
        merged_to_delete_workflow_ids = list(set(to_delete_workflow_ids + children_workflow_ids))
        self.logger.info(
            f"Including {len(merged_to_delete_workflow_ids) - len(to_delete_workflow_ids)} associated children workflows to delete"
        )
        await self.INSTANCE.delete_workflows_async(merged_to_delete_workflow_ids, delete_children=False)
        self.logger.info(f"Vacuuming database")
        with self.INSTANCE._sys_db.engine.begin() as conn:
            conn.execute(sqlalchemy.text("VACUUM"))
        self.logger.info(f"Database vacuum completed")

    async def get_scheduled_tasks(self, wallet_address: typing.Optional[str] = None) -> list[octobot_node.models.Execution]:
        """DBOS has no direct 'scheduled for later' queue; return empty list."""
        return []

    async def get_results(self, wallet_address: typing.Optional[str] = None) -> list[octobot_node.models.Execution]:
        if not self.INSTANCE:
            return []
        executions: list[octobot_node.models.Execution] = []
        try:
            completed_workflow_statuses = workflows_util.filter_by_wallet(
                await self.INSTANCE.list_workflows_async(status=[
                    dbos.WorkflowStatusString.SUCCESS.value, dbos.WorkflowStatusString.ERROR.value
                ], load_output=True),
                wallet_address,
            )
            for completed_workflow_status in completed_workflow_statuses:
                try:
                    task = workflows_util.get_input_task(completed_workflow_status)
                    if completed_workflow_status.status == dbos.WorkflowStatusString.SUCCESS.value:
                        output_error = None
                        if completed_workflow_status.output:
                            try:
                                output = workflow_params.AutomationWorkflowOutput.from_dict(
                                    json.loads(completed_workflow_status.output)
                                )
                                output_error = output.error
                            except Exception as parse_err:
                                self.logger.warning(
                                    f"Failed to parse output for workflow {completed_workflow_status.workflow_id}: {parse_err}"
                                )
                        if output_error:
                            status = octobot_node.models.TaskStatus.FAILED
                            description = "ERROR"
                            error = output_error
                        else:
                            status = octobot_node.models.TaskStatus.COMPLETED
                            description = "Completed"
                            error = None
                    else:
                        status = octobot_node.models.TaskStatus.FAILED
                        description = "ERROR"
                        error = str(completed_workflow_status.error) if completed_workflow_status.error else "Execution failed"
                    executions.append(octobot_node.models.Execution(
                        id=completed_workflow_status.workflow_id,
                        name=task.name if task else completed_workflow_status.workflow_id,
                        description=description,
                        status=status,
                        is_encrypted=bool(task.content_metadata) if task else False,
                        result="",
                        result_metadata="",
                        scheduled_at=completed_workflow_status.created_at,
                        completed_at=completed_workflow_status.updated_at,
                        error=error,
                        wallet_address=task.wallet_address if task else None,
                    ))
                except Exception as e:
                    self.logger.exception(e, True, f"Failed to process result workflow {completed_workflow_status.workflow_id}: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to list result workflows: {e}")
        return executions

    def _build_export_result_from_status(
        self,
        workflow_status: dbos.WorkflowStatus,
        user_rsa_public_key: typing.Optional[bytes],
    ) -> dict[str, str]:
        raw = workflow_status.output
        try:
            output = (
                workflow_params.AutomationWorkflowOutput.from_dict(json.loads(raw))
                if raw else workflow_params.AutomationWorkflowOutput()
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse output for workflow {workflow_status.workflow_id}: {e}")
            output = workflow_params.AutomationWorkflowOutput()
        if not output.state:
            return {"result": "", "result_metadata": ""}
        result_task = octobot_node.models.Task(
            name="", content=output.state,
            content_metadata=output.state_metadata, type="execute_actions",
        )
        with task_context.encrypted_task(result_task):
            if (result_task.content == output.state and output.state_metadata
                    and octobot_node.config.settings.TASKS_SERVER_RSA_PRIVATE_KEY):
                raise encryption.EncryptionTaskError("Internal state decryption silently failed")
            user_rsa_key = user_rsa_public_key or octobot_node.config.settings.TASKS_USER_RSA_PUBLIC_KEY
            if not user_rsa_key or not octobot_node.config.settings.TASKS_SERVER_ECDSA_PRIVATE_KEY:
                return {"result": result_task.content, "result_metadata": ""}
            result, metadata = encryption.encrypt_task_result(
                result_task.content,
                rsa_public_key=user_rsa_key,
                ecdsa_private_key=octobot_node.config.settings.TASKS_SERVER_ECDSA_PRIVATE_KEY,
            )
        return {"result": result, "result_metadata": metadata}

    async def get_workflows_export_results(
        self,
        task_ids: list[str],
        wallet_address: typing.Optional[str],
        user_rsa_public_key: typing.Optional[str] = None,
    ) -> dict[str, dict[str, str]]:
        if not self.INSTANCE:
            return {}
        completed = await self.INSTANCE.list_workflows_async(status=[
            dbos.WorkflowStatusString.SUCCESS.value,
            dbos.WorkflowStatusString.ERROR.value,
        ], load_output=True) or []

        by_parent: dict[str, list[dbos.WorkflowStatus]] = {}
        for w in completed:
            parent_id = w.workflow_id[:octobot_node.constants.PARENT_WORKFLOW_ID_LENGTH]
            by_parent.setdefault(parent_id, []).append(w)

        out: dict[str, dict[str, str]] = {}
        for task_id in task_ids:
            try:
                group = by_parent.get(task_id)
                if not group:
                    out[task_id] = {"error": "not found"}
                    continue
                task = next(
                    (t for t in (workflows_util.get_input_task(w) for w in group) if t is not None),
                    None,
                )
                if wallet_address is not None and (task is None or task.wallet_address != wallet_address):
                    out[task_id] = {"error": "forbidden"}
                    continue
                chosen = None
                for w in sorted(group, key=lambda w: w.updated_at or 0):
                    if w.status == dbos.WorkflowStatusString.SUCCESS.value and w.output:
                        chosen = w
                if chosen is None:
                    error_ws = [w for w in group if w.status == dbos.WorkflowStatusString.ERROR.value]
                    if error_ws:
                        err = error_ws[-1].error
                        out[task_id] = {
                            "result": "", "result_metadata": "",
                            "error": str(err) if err else "Execution failed",
                        }
                    else:
                        out[task_id] = {"result": "", "result_metadata": ""}
                    continue
                user_rsa = user_rsa_public_key.encode("utf-8") if user_rsa_public_key else None
                out[task_id] = self._build_export_result_from_status(chosen, user_rsa)
            except Exception as e:
                self.logger.warning(f"Failed to export result for {task_id}: {e}")
                out[task_id] = {"error": str(e)}
        return out

    def _parse_workflow_status(
        self,
        workflow_status: dbos.WorkflowStatus,
        status: octobot_node.models.TaskStatus,
        description: typing.Optional[str] = None,
    ) -> octobot_node.models.Execution:
        """Map DBOS WorkflowStatus to octobot_node.models.Execution."""
        task_id = str(workflow_status.workflow_id)
        task_type = None
        task_actions = None
        task = None
        if workflow_status.input:
            if task := workflows_util.get_input_task(workflow_status):
                task_type = task.type
                task_actions = task.content #todo confi

        task_name = task.name if task else workflow_status.name
        task_wallet_address = task.wallet_address if task else None
        return octobot_node.models.Execution(
            id=task_id,
            name=task_name,
            description=description,
            actions=task_actions,
            is_encrypted=bool(task.content_metadata) if task else False,
            type=task_type,
            status=status,
            wallet_address=task_wallet_address,
        )

    def get_task_name(self, task_data: dict | octobot_node.models.Task | None, default_value: typing.Optional[str] = None) -> typing.Optional[str]:
        if isinstance(task_data, octobot_node.models.Task):
            return task_data.name
        elif isinstance(task_data, dict):
            return task_data.get(octobot_node.enums.TaskResultKeys.TASK.value, {}).get("name", default_value)
        else:
            return default_value
