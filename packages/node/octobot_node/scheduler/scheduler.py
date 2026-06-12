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

import contextlib
import datetime
import dbos
import json
import logging
import typing
import decimal
import enum
import sqlalchemy

import octobot_commons.logging
import octobot_commons.timestamp_util as timestamp_util
import octobot_protocol.models as protocol_models
import octobot_node.config
import octobot_node.enums
import octobot_node.models
import octobot_node.constants
import octobot_node.scheduler.workflows_util as workflows_util
import octobot_node.scheduler.workflows.params as workflow_params
import octobot_node.scheduler.user_actions.user_action_util as user_action_util
import octobot_node.scheduler.encryption as encryption
import octobot_node.scheduler.task_context as task_context
import octobot_node.protocol.automations as automations_protocol

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
    USER_ACTION_QUEUE: dbos.Queue = None # type: ignore

    @staticmethod
    def _wallet_filter_queue(queue_names: typing.Optional[list[str]]) -> octobot_node.enums.SchedulerQueues:
        if queue_names == [octobot_node.enums.SchedulerQueues.USER_ACTION_QUEUE.value]:
            return octobot_node.enums.SchedulerQueues.USER_ACTION_QUEUE
        return octobot_node.enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def SetWorkflowID(workflow_id: str) -> dbos.SetWorkflowID:
        return dbos.SetWorkflowID(workflow_id)

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
        self.USER_ACTION_QUEUE = dbos.Queue(name=octobot_node.enums.SchedulerQueues.USER_ACTION_QUEUE.value)

    async def get_periodic_tasks(self, wallet_address: typing.Optional[str] = None) -> list[octobot_node.models.Execution]:
        """DBOS scheduled workflows are not easily introspectable; return empty list."""
        return [] # TODO

    async def get_pending_tasks(self, wallet_address: typing.Optional[str] = None) -> list[octobot_node.models.Execution]:
        if not self.INSTANCE:
            return []
        executions: list[octobot_node.models.Execution] = []
        try:
            pending_workflow_statuses = await self._list_workflows(
                wallet_address,
                [
                    dbos.WorkflowStatusString.ENQUEUED, dbos.WorkflowStatusString.PENDING
                ],
                queue_names=[octobot_node.enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE.value],
                load_output=False
            )
            for pending_workflow_status in pending_workflow_statuses:
                try:
                    task = workflows_util.get_automation_input_task(pending_workflow_status)
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

    async def _list_workflows(
        self,
        wallet_address: typing.Optional[str], 
        statuses: typing.Optional[list[dbos.WorkflowStatusString]],
        queue_names: typing.Optional[list[str]],
        load_output: bool
    ) -> list[dbos.WorkflowStatus]:
        workflows = await self.INSTANCE.list_workflows_async(
            status=[status.value for status in statuses] if statuses else None,
            queue_name=queue_names,
            load_output=load_output
        )
        if wallet_address:
            workflows = workflows_util.filter_by_wallet(
                workflows,
                wallet_address,
                self._wallet_filter_queue(queue_names),
            )
        return workflows

    async def _get_parent_and_children_automation_workflow_ids(
        self,
        wallet_address: typing.Optional[str],
        workflow_ids: list[str],
        statuses: list[dbos.WorkflowStatusString],
        load_output: bool = False
    ) -> list[str]:
        all_workflows = await self._list_workflows(
            wallet_address, statuses, [octobot_node.enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE.value], load_output
        )
        parent_workflow_ids = set(
            workflow_id[:octobot_node.constants.PARENT_WORKFLOW_ID_LENGTH]
            for workflow_id in workflow_ids
        )
        return [
            workflow.workflow_id
            for workflow in all_workflows
            if workflow.workflow_id[:octobot_node.constants.PARENT_WORKFLOW_ID_LENGTH] in parent_workflow_ids
        ]

    async def resolve_active_automation_workflow_ids_for_parent_id(
        self,
        wallet_address: typing.Optional[str],
        parent_id: str,
    ) -> list[str]:
        """
        Return DBOS workflow ids for pending/enqueued automations whose parent id prefix matches ``parent_id``.

        Delegates to :meth:`_get_parent_and_children_automation_workflow_ids` with a single seed. For stop-automation user
        actions, ``parent_id`` is :attr:`octobot_protocol.models.StopAutomationConfiguration.id` (a workflow / parent
        id seed compatible with :const:`octobot_node.constants.PARENT_WORKFLOW_ID_LENGTH`).
        """
        return await self._get_parent_and_children_automation_workflow_ids(
            wallet_address,
            [parent_id],
            [
                dbos.WorkflowStatusString.ENQUEUED,
                dbos.WorkflowStatusString.PENDING,
            ],
            load_output=False,
        )

    async def _get_latest_workflow_for_each_automation(
        self,
        wallet_address: typing.Optional[str],
        statuses: typing.Optional[list[dbos.WorkflowStatusString]],
        load_output: bool = False,
    ) -> list[dbos.WorkflowStatus]:
        workflows = await self._list_workflows(
            wallet_address, statuses, [octobot_node.enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE.value], load_output=load_output
        )
        by_parent = workflows_util.get_workflows_by_parent_id(workflows)
        return [
            workflows_util.get_latest_workflow(workflows)
            for workflows in by_parent.values()
        ]

    async def cancel_workflows(self, workflow_ids: list[str]) -> list[str]:
        try:
            to_cancel = await self._get_parent_and_children_automation_workflow_ids(
                None,
                workflow_ids,
                [
                    dbos.WorkflowStatusString.ENQUEUED, dbos.WorkflowStatusString.PENDING
                ]
            )
            self.logger.info(f"Cancelling {len(to_cancel)} workflows {to_cancel}")
            await self.INSTANCE.cancel_workflows_async(to_cancel)
            self.logger.info(f"{len(to_cancel)} workflows {to_cancel} cancelled")
            return to_cancel
        except Exception as e:
            self.logger.exception(e, True, f"Failed to cancel workflows {workflow_ids}: {e}")
            return []

    async def delete_workflows(self, to_delete_workflow_ids: list[str]):
        self.logger.info(f"Deleting {len(to_delete_workflow_ids)} workflows")
        merged_to_delete_workflow_ids = await self._get_parent_and_children_automation_workflow_ids(
            None,
            to_delete_workflow_ids,
            [
                dbos.WorkflowStatusString.SUCCESS, dbos.WorkflowStatusString.ERROR,
                dbos.WorkflowStatusString.CANCELLED, dbos.WorkflowStatusString.MAX_RECOVERY_ATTEMPTS_EXCEEDED
            ]
        )
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
            completed_workflow_statuses = await self._list_workflows(wallet_address, [
                    dbos.WorkflowStatusString.SUCCESS, dbos.WorkflowStatusString.ERROR
                ], [octobot_node.enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE.value], load_output=True)
            for completed_workflow_status in completed_workflow_statuses:
                try:
                    task = workflows_util.get_automation_input_task(completed_workflow_status)
                    error_message = None
                    if completed_workflow_status.status == dbos.WorkflowStatusString.SUCCESS.value:
                        output_error = None
                        if completed_workflow_status.output:
                            try:
                                output = workflow_params.AutomationWorkflowOutput.from_dict(
                                    json.loads(completed_workflow_status.output)
                                )
                                output_error = output.error
                                error_message = output.error_message
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
                            error_message = None
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
                        error_message=error_message,
                        wallet_address=task.wallet_address if task else None,
                    ))
                except Exception as e:
                    self.logger.exception(e, True, f"Failed to process result workflow {completed_workflow_status.workflow_id}: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to list result workflows: {e}")
        return executions

    def _parse_output_and_task_from_workflow_output(
        self,
        workflow_status: dbos.WorkflowStatus,
    ) -> tuple[workflow_params.AutomationWorkflowOutput, octobot_node.models.Task]:
        output = (
            workflows_util.parse_automation_workflow_output(workflow_status)
            or workflow_params.AutomationWorkflowOutput()
        )
        resolved_task = workflows_util.get_resolved_automation_task(workflow_status)
        if resolved_task is not None:
            return output, resolved_task
        input_task = workflows_util.get_automation_input_task(workflow_status)
        task_name = input_task.name if input_task is not None else None
        return output, octobot_node.models.Task(
            name=task_name,
            content=output.state,
            content_metadata=output.state_metadata,
            type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
        )

    def _build_export_result_from_status(
        self,
        workflow_status: dbos.WorkflowStatus,
        user_rsa_public_key: typing.Optional[bytes],
    ) -> dict[str, str]:
        try:
            output, result_task = self._parse_output_and_task_from_workflow_output(workflow_status)
        except Exception as e:
            self.logger.warning(f"Failed to parse output for workflow {workflow_status.workflow_id}: {e}")
            output = workflow_params.AutomationWorkflowOutput()
        if not output.state:
            return {"result": "", "result_metadata": ""}
        with task_context.encrypted_task(result_task):
            if (result_task.content == output.state and output.state_metadata
                    and octobot_node.config.settings.TASKS_SERVER_RSA_PRIVATE_KEY):
                raise encryption.EncryptionTaskError("Internal state decryption silently failed")
            user_rsa_key = user_rsa_public_key or octobot_node.config.settings.TASKS_USER_RSA_PUBLIC_KEY
            if not user_rsa_key or not octobot_node.config.settings.TASKS_SERVER_ECDSA_PRIVATE_KEY:
                return {
                    "result": result_task.content, # type: ignore
                    "result_metadata": "",
                }
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
        completed = await self._list_workflows(None, [
            dbos.WorkflowStatusString.SUCCESS,
            dbos.WorkflowStatusString.ERROR,
        ], [octobot_node.enums.SchedulerQueues.AUTOMATION_WORKFLOW_QUEUE.value], load_output=True)

        by_parent = workflows_util.get_workflows_by_parent_id(completed)
        out: dict[str, dict[str, str]] = {}
        for task_id in task_ids:
            try:
                group = by_parent.get(task_id)
                if not group:
                    out[task_id] = {"error": "not found"}
                    continue
                task = next(
                    (t for t in (workflows_util.get_automation_input_task(w) for w in group) if t is not None),
                    None,
                )
                if wallet_address is not None and (task is None or task.wallet_address != wallet_address):
                    out[task_id] = {"error": "forbidden"}
                    continue
                result_workflows = [
                    w for w in group
                    if w.status == dbos.WorkflowStatusString.SUCCESS.value and w.output
                ]
                chosen = workflows_util.get_latest_workflow(result_workflows) if result_workflows else None
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
            if task := workflows_util.get_automation_input_task(workflow_status):
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

    async def get_automation_states(self, wallet_address: typing.Optional[str]) -> list[protocol_models.AutomationState]:
        workflows = await self._get_latest_workflow_for_each_automation(
            wallet_address, None, load_output=True
        )
        sources: list[automations_protocol.AutomationStateSource] = []
        for workflow in workflows:
            workflow_output = workflows_util.parse_automation_workflow_output(workflow)
            task = workflows_util.get_resolved_automation_task(workflow)
            if task:
                task.id = workflow.workflow_id[:octobot_node.constants.PARENT_WORKFLOW_ID_LENGTH]
                sources.append(automations_protocol.AutomationStateSource(
                    task=task,
                    workflow_status=workflow.status,
                    workflow_output=workflow_output,
                    workflow_error=str(workflow.error) if workflow.error else None,
                ))
        with contextlib.ExitStack() as exit_stack:
            for source in sources:
                exit_stack.enter_context(task_context.encrypted_task(source.task))
            return automations_protocol.to_protocol_automations_state(sources)

    @staticmethod
    def _user_action_list_sort_key(
        user_action: protocol_models.UserAction,
        workflow_status: dbos.WorkflowStatus,
    ) -> tuple[int, str, str]:
        workflow_identifier = str(workflow_status.workflow_id or "")
        return (workflow_status.created_at or 0, user_action.id, workflow_identifier)

    def _parse_user_action_from_workflow_output(
        self,
        workflow_status: dbos.WorkflowStatus,
    ) -> typing.Optional[protocol_models.UserAction]:
        if not workflow_status.output:
            return None
        try:
            output = workflow_params.UserActionWorkflowOutput.from_dict(workflow_status.output)
        except (json.JSONDecodeError, TypeError, ValueError) as err:
            self.logger.warning(
                "Failed to parse user action workflow output for %s: %s",
                getattr(workflow_status, "workflow_id", None),
                err,
            )
            return None
        if output is None or output.updated_user_action is None:
            return None
        return output.updated_user_action

    def _workflow_updated_at(self, workflow_status: dbos.WorkflowStatus) -> datetime.datetime:
        return timestamp_util.utc_datetime_from_timestamp(
            (workflow_status.created_at or 0) / 1000
        )

    def _failed_user_action_from_parsed_inputs(
        self,
        workflow_status: dbos.WorkflowStatus,
        ua_inputs: workflow_params.UserActionWorkflowInputs,
    ) -> protocol_models.UserAction:
        user_action = ua_inputs.user_action
        user_action.status = protocol_models.UserActionStatus.FAILED
        error_text = str(workflow_status.error) if workflow_status.error else "Workflow finished without usable output."
        updated_at = self._workflow_updated_at(workflow_status)
        result_type = user_action_util.resolve_user_action_result_type(user_action)
        user_action.result = user_action_util.build_synthesized_failure_user_action_result(
            result_type=result_type,
            updated_at=updated_at,
            error_details=error_text[:octobot_node.constants.FAILURE_ERROR_DETAILS_MAX_LENGTH],
        )
        user_action.updated_at = updated_at
        return user_action

    def _minimal_user_action_for_workflow(
        self,
        workflow_status: dbos.WorkflowStatus,
        resolved: workflows_util.ResolvedUserActionWorkflowInputs,
        *,
        terminal: bool,
    ) -> protocol_models.UserAction:
        workflow_identifier = str(workflow_status.workflow_id or "")
        parse_error = resolved.parse_error or "could not parse UserActionWorkflowInputs"
        self.logger.debug(
            "Recovered minimal user action for workflow %s: %s",
            workflow_identifier,
            parse_error,
        )
        return user_action_util.build_minimal_user_action_for_workflow(
            workflow_id=workflow_identifier,
            terminal=terminal,
            updated_at=self._workflow_updated_at(workflow_status),
            parse_error=parse_error,
            partial_user_action_id=resolved.partial_user_action_id,
            workflow_error=str(workflow_status.error) if workflow_status.error else None,
        )

    def _user_action_from_workflow_inputs(
        self,
        workflow_status: dbos.WorkflowStatus,
        *,
        terminal: bool,
    ) -> protocol_models.UserAction:
        resolved = workflows_util.resolve_user_action_workflow_inputs(workflow_status)
        if resolved.inputs is not None and resolved.inputs.user_action is not None:
            if terminal:
                return self._failed_user_action_from_parsed_inputs(workflow_status, resolved.inputs)
            return resolved.inputs.user_action
        return self._minimal_user_action_for_workflow(workflow_status, resolved, terminal=terminal)

    def _user_action_from_terminal_workflow(
        self,
        workflow_status: dbos.WorkflowStatus,
    ) -> protocol_models.UserAction:
        from_output = self._parse_user_action_from_workflow_output(workflow_status)
        if from_output is not None:
            return from_output
        return self._user_action_from_workflow_inputs(workflow_status, terminal=True)

    async def list_user_actions(
        self, wallet_address: typing.Optional[str],
        active_only: bool = True,
    ) -> list[protocol_models.UserAction]:
        # Step: aggregate user actions from USER_ACTION_QUEUE workflows (pending inputs + terminal outputs).
        if not self.INSTANCE:
            return []
        _ = active_only  # Reserved for API; DBOS fetches always use explicit non-terminal / terminal status sets.
        user_action_queue_name = octobot_node.enums.SchedulerQueues.USER_ACTION_QUEUE.value
        loaded: list[tuple[tuple[int, str, str], protocol_models.UserAction]] = []
        input_workflows = await self._list_workflows(
            wallet_address,
            list(workflows_util.get_user_action_input_workflow_statuses()),
            [user_action_queue_name],
            load_output=False,
        )
        for workflow_status in input_workflows:
            user_action_row = self._user_action_from_workflow_inputs(workflow_status, terminal=False)
            sort_key = self._user_action_list_sort_key(user_action_row, workflow_status)
            loaded.append((sort_key, user_action_row))
        terminal_workflows = await self._list_workflows(
            wallet_address,
            list(workflows_util.get_user_action_terminal_workflow_statuses()),
            [user_action_queue_name],
            load_output=True,
        )
        for workflow_status in terminal_workflows:
            user_action_row = self._user_action_from_terminal_workflow(workflow_status)
            sort_key = self._user_action_list_sort_key(user_action_row, workflow_status)
            loaded.append((sort_key, user_action_row))
        loaded.sort(key=lambda row: row[0])
        return [pair[1] for pair in loaded]
