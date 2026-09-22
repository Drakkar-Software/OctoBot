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

import datetime
import asyncio
import dbos
import json
import logging
import typing
import decimal
import enum

import octobot_commons.logging
import octobot_commons.timestamp_util as timestamp_util
import octobot_protocol.models as protocol_models
import octobot_node.config
import octobot_node.enums
import octobot_node.models
import octobot_node.constants
import octobot_node.scheduler.automations.automation_states_loader as automation_states_loader
import octobot_node.scheduler.workflows_util as workflows_util
import octobot_node.scheduler.workflows_retention as workflows_retention
import octobot_node.scheduler.workflows.params as workflow_params
import octobot_node.scheduler.user_actions.user_action_util as user_action_util
import octobot_node.scheduler.encryption as encryption
import octobot_node.scheduler.task_context as task_context
import octobot_node.protocol.util.privacy_filter as privacy_filter

DEFAULT_NAME = "octobot_node"

_BASE_CONFIG = dbos.DBOSConfig(
    name=DEFAULT_NAME,
    max_executor_threads=octobot_node.config.settings.SCHEDULER_MAX_EXECUTOR_THREADS,
    application_version=octobot_node.constants.SCHEDULER_APPLICATION_VERSION,
    # executor_id=..., # a constant executor_id is required for DBOS workflow recovery: leave its init to DBOS
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
            self._get_dbos_workflow_id,
            max_file_bytes=octobot_node.constants.AUTOMATION_LOG_FILE_MAX_BYTES,
            trim_lines_fraction=octobot_node.constants.AUTOMATION_LOG_FILE_TRIM_LINES_FRACTION,
        )

    @staticmethod
    def _get_dbos_workflow_id() -> typing.Optional[str]:
        """Return the current DBOS workflow ID when executing within a step or workflow."""
        if workflow_id := getattr(dbos.DBOS, "workflow_id", None):
            # group children workflows and parent workflows together
            # (a child workflow has the parent's workflow ID as a prefix)
            return workflows_util.normalize_parent_automation_id(workflow_id)
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
            self.logger.info("Starting scheduler")
            self.INSTANCE.launch()
            self.logger.info("Scheduler started")
        else:
            self.logger.warning("Scheduler not initialized")

    def stop(self) -> None:
        if not self.INSTANCE:
            return
        self.INSTANCE.destroy()
        self.logger.info("Scheduler stopped")
        Scheduler.INSTANCE = None

    async def get_periodic_tasks(self, user_id: typing.Optional[str] = None) -> list[octobot_node.models.Execution]:
        """DBOS scheduled workflows are not easily introspectable; return empty list."""
        return [] # TODO

    async def get_pending_tasks(self, user_id: typing.Optional[str] = None) -> list[octobot_node.models.Execution]:
        if not self.INSTANCE:
            return []
        executions: list[octobot_node.models.Execution] = []
        try:
            pending_workflow_statuses = await self._list_workflows(
                user_id,
                [
                    dbos.WorkflowStatusString.ENQUEUED, dbos.WorkflowStatusString.PENDING
                ],
                octobot_node.enums.SchedulerWorkflowNames.EXECUTE_AUTOMATION,
                load_output=False,
                load_input=True,
            )
            for pending_workflow_status in pending_workflow_statuses:
                try:
                    task = workflows_util.get_automation_input_task(pending_workflow_status)
                    if reader := automation_states_loader.get_automation_state_reader(pending_workflow_status):
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
        user_id: typing.Optional[str],
        statuses: typing.Optional[list[dbos.WorkflowStatusString]],
        workflow_name: octobot_node.enums.SchedulerWorkflowNames,
        load_output: bool,
        *,
        load_input: bool = False,
        sort_desc: typing.Optional[bool] = None,
        limit: typing.Optional[int] = None,
    ) -> list[dbos.WorkflowStatus]:
        if not self.INSTANCE:
            return []
        return await workflows_util.list_scheduler_workflows_async(
            self.INSTANCE,
            workflow_name,
            statuses,
            user_id,
            load_output=load_output,
            load_input=load_input,
            sort_desc=sort_desc,
            limit=limit,
        )

    async def _get_parent_and_children_automation_workflows(
        self,
        user_id: typing.Optional[str],
        workflow_ids: list[str],
        statuses: list[dbos.WorkflowStatusString],
        load_output: bool = False,
    ) -> list[dbos.WorkflowStatus]:
        all_workflows = await self._list_workflows(
            user_id,
            statuses,
            octobot_node.enums.SchedulerWorkflowNames.EXECUTE_AUTOMATION,
            load_output,
        )
        parent_workflow_ids = set(
            workflows_util.normalize_parent_automation_id(workflow_id)
            for workflow_id in workflow_ids
        )
        return [
            workflow
            for workflow in all_workflows
            if workflows_util.normalize_parent_automation_id(workflow.workflow_id) in parent_workflow_ids
        ]

    async def get_parent_and_children_automation_workflow_ids(
        self,
        wallet_address: typing.Optional[str],
        workflow_ids: list[str],
        statuses: list[dbos.WorkflowStatusString],
        load_output: bool = False
    ) -> list[str]:
        matching_workflows = await self._get_parent_and_children_automation_workflows(
            wallet_address, workflow_ids, statuses, load_output
        )
        return [workflow.workflow_id for workflow in matching_workflows]

    async def _get_user_action_workflow_ids(
        self,
        user_id: typing.Optional[str],
        user_action_ids: list[str],
        statuses: list[dbos.WorkflowStatusString],
        load_output: bool = False
    ) -> list[str]:
        if not user_action_ids:
            return []
        user_action_id_set = set(user_action_ids)
        matching_workflows = await self._list_workflows(
            user_id,
            statuses,
            octobot_node.enums.SchedulerWorkflowNames.EXECUTE_USER_ACTION,
            load_output,
        )
        matched_workflow_ids: list[str] = []
        for workflow in matching_workflows:
            user_action_id = self._user_action_id_from_workflow(workflow, load_output=load_output)
            if user_action_id is not None and user_action_id in user_action_id_set:
                matched_workflow_ids.append(workflow.workflow_id)
        return matched_workflow_ids

    async def resolve_active_automation_workflow_ids_for_parent_id(
        self,
        user_id: typing.Optional[str],
        parent_id: str,
    ) -> list[str]:
        """
        Return the latest pending/enqueued child DBOS workflow id for ``parent_id``.

        For stop-automation user actions, ``parent_id`` is
        :attr:`octobot_protocol.models.StopAutomationConfiguration.id` (a workflow / parent id seed compatible with
        :const:`octobot_node.constants.PARENT_WORKFLOW_ID_LENGTH`).
        """
        matching_workflows = await self._get_parent_and_children_automation_workflows(
            user_id,
            [parent_id],
            [
                dbos.WorkflowStatusString.ENQUEUED,
                dbos.WorkflowStatusString.PENDING,
            ],
            load_output=False,
        )
        if not matching_workflows:
            return []
        latest_workflow = workflows_util.get_latest_child_workflow(matching_workflows)
        return [latest_workflow.workflow_id]

    async def resolve_automation_owner_user_id(
        self,
        parent_id: str,
    ) -> typing.Optional[str]:
        """
        Return the Starfish ``user_id`` that owns the active automation for ``parent_id``.

        Unlike :meth:`resolve_active_automation_workflow_ids_for_parent_id`, this lookup is not
        wallet-scoped so callers can resolve cross-wallet ownership after API-side authorization.
        """
        matching_workflows = await self._get_parent_and_children_automation_workflows(
            None,
            [parent_id],
            [
                dbos.WorkflowStatusString.ENQUEUED,
                dbos.WorkflowStatusString.PENDING,
            ],
            load_output=False,
        )
        if not matching_workflows:
            return None
        latest_workflow = workflows_util.get_latest_child_workflow(matching_workflows)
        task = workflows_util.get_automation_input_task(latest_workflow)
        if task is None:
            return None
        return task.user_id

    async def resolve_terminal_automation_owner_user_id(
        self,
        parent_id: str,
    ) -> typing.Optional[str]:
        """
        Return the Starfish ``user_id`` that owns the latest terminal automation for ``parent_id``.

        Unlike :meth:`resolve_automation_owner_user_id`, this lookup uses SUCCESS/ERROR workflows
        so restart actions can resolve ownership after the automation has completed or failed.
        """
        terminal_workflow = await self.resolve_latest_terminal_automation_workflow_for_parent_id(
            None,
            parent_id,
        )
        if terminal_workflow is None:
            return None
        task = workflows_util.get_automation_input_task(terminal_workflow)
        if task is None:
            return None
        return task.user_id

    async def resolve_latest_terminal_automation_workflow_for_parent_id(
        self,
        user_id: typing.Optional[str],
        parent_id: str,
    ) -> typing.Optional[dbos.WorkflowStatus]:
        """
        Return the latest terminal (SUCCESS/ERROR) child workflow for ``parent_id`` that has
        resolvable automation task content (workflow output state or input fallback), or None
        when no prior execution exists.
        """
        matching_workflows = await self._get_parent_and_children_automation_workflows(
            user_id,
            [parent_id],
            [
                dbos.WorkflowStatusString.SUCCESS,
                dbos.WorkflowStatusString.ERROR,
            ],
            load_output=True,
        )
        if not matching_workflows:
            return None
        sorted_workflows = sorted(
            matching_workflows,
            key=workflows_util._automation_child_workflow_sort_key,
            reverse=True,
        )
        for workflow_status in sorted_workflows:
            if workflows_util.get_resolved_automation_task(workflow_status) is not None:
                return workflow_status
        return None

    async def _get_latest_workflow_for_each_automation(
        self,
        user_id: typing.Optional[str],
        statuses: typing.Optional[list[dbos.WorkflowStatusString]],
        load_output: bool = False,
    ) -> list[dbos.WorkflowStatus]:
        workflows = await self._list_workflows(
            user_id,
            statuses,
            octobot_node.enums.SchedulerWorkflowNames.EXECUTE_AUTOMATION,
            load_output,
            load_input=True,
        )
        by_parent = workflows_util.get_workflows_by_parent_id(workflows)
        return [
            workflows_util.get_latest_workflow(workflows)
            for workflows in by_parent.values()
        ]

    async def cancel_workflows(self, workflow_ids: list[str]) -> list[str]:
        try:
            to_cancel = await self.get_parent_and_children_automation_workflow_ids(
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
        merged_to_delete_workflow_ids = await workflows_retention.get_workflows_to_delete(
            self,
            to_delete_workflow_ids,
        )
        self.logger.info(
            f"Including {len(merged_to_delete_workflow_ids) - len(to_delete_workflow_ids)} associated children workflows to delete"
        )
        await workflows_retention.delete_workflows_and_vacuum(
            self.INSTANCE,
            merged_to_delete_workflow_ids,
        )

    async def get_scheduled_tasks(self, user_id: typing.Optional[str] = None) -> list[octobot_node.models.Execution]:
        """DBOS has no direct 'scheduled for later' queue; return empty list."""
        return []

    async def _list_terminal_automation_workflows(
        self,
        user_id: typing.Optional[str],
        *,
        load_output: bool,
    ) -> list[dbos.WorkflowStatus]:
        return await self._list_workflows(
            user_id,
            list(workflows_util.DBOS_TERMINAL_WORKFLOW_STATUSES),
            octobot_node.enums.SchedulerWorkflowNames.EXECUTE_AUTOMATION,
            load_output,
            load_input=True,
        )

    @staticmethod
    def _automation_input_wallet_and_encryption(
        latest_input_task: typing.Optional[octobot_node.models.Task],
    ) -> tuple[typing.Optional[str], bool]:
        if latest_input_task is None:
            return None, False
        return latest_input_task.user_id, bool(latest_input_task.content_metadata)

    @staticmethod
    def _automation_execution_display_name(
        latest_input_task: typing.Optional[octobot_node.models.Task],
        workflow_id: str,
        *,
        is_latest_child: bool,
    ) -> typing.Optional[str]:
        if not is_latest_child:
            return None
        if latest_input_task and latest_input_task.name:
            return latest_input_task.name
        return str(workflow_id)

    def _executions_for_automation_group(
        self,
        group: list[dbos.WorkflowStatus],
        latest: dbos.WorkflowStatus,
        latest_input_task: typing.Optional[octobot_node.models.Task],
    ) -> list[octobot_node.models.Execution]:
        """
        Build tasks API Execution rows for one parent automation's terminal children.

        When the latest child is CANCELLED, return only that row (hide prior SUCCESS/ERROR),
        matching workflows_util.resolve_automation_result_for_group export semantics.
        """
        if latest.status == dbos.WorkflowStatusString.CANCELLED.value:
            return [
                self._execution_from_automation_child_row(
                    latest,
                    latest_input_task=latest_input_task,
                    is_latest_child=True,
                )
            ]
        group_executions: list[octobot_node.models.Execution] = []
        for terminal_workflow_status in group:
            if terminal_workflow_status.status not in (
                dbos.WorkflowStatusString.SUCCESS.value,
                dbos.WorkflowStatusString.ERROR.value,
            ):
                continue
            is_latest_child = terminal_workflow_status.workflow_id == latest.workflow_id
            group_executions.append(
                self._execution_from_automation_child_row(
                    terminal_workflow_status,
                    latest_input_task=latest_input_task,
                    is_latest_child=is_latest_child,
                )
            )
        return group_executions

    def _execution_from_automation_child_row(
        self,
        workflow_status: dbos.WorkflowStatus,
        *,
        latest_input_task: typing.Optional[octobot_node.models.Task],
        is_latest_child: bool,
    ) -> octobot_node.models.Execution:
        """
        Map one terminal child workflow row to a tasks API Execution.

        Wallet, display name, and base encryption come from the parent's latest child input
        (`latest_input_task`), including for older SUCCESS/ERROR rows in the same group.
        Row status, errors, and output-derived encryption come from this child's DBOS row;
        output parsing applies only when `is_latest_child` and status is SUCCESS.
        """
        parent_user_id, parent_is_encrypted = self._automation_input_wallet_and_encryption(
            latest_input_task
        )
        workflow_identifier = str(workflow_status.workflow_id)
        display_name = self._automation_execution_display_name(
            latest_input_task,
            workflow_identifier,
            is_latest_child=is_latest_child,
        )

        error_message: typing.Optional[str] = None
        if workflow_status.status == dbos.WorkflowStatusString.CANCELLED.value:
            if not is_latest_child:
                raise ValueError(
                    f"CANCELLED workflow row must be latest child: {workflow_identifier!r}"
                )
            return octobot_node.models.Execution(
                id=workflow_identifier,
                name=display_name,
                description="Cancelled",
                status=octobot_node.models.TaskStatus.CANCELLED,
                is_encrypted=parent_is_encrypted,
                result="",
                result_metadata="",
                scheduled_at=workflow_status.created_at,
                completed_at=workflow_status.updated_at,
                error=None,
                error_message=None,
                user_id=parent_user_id,
            )
        if workflow_status.status == dbos.WorkflowStatusString.SUCCESS.value:
            if is_latest_child:
                output_error = None
                if workflow_status.output:
                    try:
                        raw_output = workflow_status.output
                        if isinstance(raw_output, str):
                            raw_output = json.loads(raw_output)
                        output = workflow_params.AutomationWorkflowOutput.from_dict(raw_output)
                        output_error = output.error
                        error_message = output.error_message
                    except Exception as parse_err:
                        self.logger.warning(
                            f"Failed to parse output for workflow {workflow_identifier}: {parse_err}"
                        )
                if output_error:
                    row_status = octobot_node.models.TaskStatus.FAILED
                    description = "ERROR"
                    error = output_error
                else:
                    row_status = octobot_node.models.TaskStatus.COMPLETED
                    description = "Completed"
                    error = None
                    error_message = None
                if workflow_status.output:
                    parsed_output = workflows_util.parse_automation_workflow_output(workflow_status)
                    row_is_encrypted = bool(
                        parsed_output.state_metadata if parsed_output else None
                    ) or parent_is_encrypted
                else:
                    row_is_encrypted = parent_is_encrypted
            else:
                row_status = octobot_node.models.TaskStatus.COMPLETED
                description = "Completed"
                error = None
                error_message = None
                row_is_encrypted = parent_is_encrypted
        elif workflow_status.status == dbos.WorkflowStatusString.ERROR.value:
            row_status = octobot_node.models.TaskStatus.FAILED
            description = "ERROR"
            error = (
                str(workflow_status.error)
                if workflow_status.error
                else "Execution failed"
            )
            row_is_encrypted = parent_is_encrypted
        else:
            raise ValueError(f"Unexpected terminal workflow status for execution row: {workflow_status.status!r}")

        return octobot_node.models.Execution(
            id=workflow_identifier,
            name=display_name,
            description=description,
            status=row_status,
            is_encrypted=row_is_encrypted,
            result="",
            result_metadata="",
            scheduled_at=workflow_status.created_at,
            completed_at=workflow_status.updated_at,
            error=error,
            error_message=error_message,
            user_id=parent_user_id,
        )

    async def get_results(self, user_id: typing.Optional[str] = None) -> list[octobot_node.models.Execution]:
        """
        List terminal automation workflow executions for the tasks API.

        Uses a cheap metadata scan, then hydrates each parent's latest child
        (input and output) in one request.
        """
        if not self.INSTANCE:
            return []
        executions: list[octobot_node.models.Execution] = []
        try:
            # Step 1 — Terminal workflows without input/output payloads.
            metadata_rows = await workflows_util.list_scheduler_workflows_async(
                self.INSTANCE,
                octobot_node.enums.SchedulerWorkflowNames.EXECUTE_AUTOMATION,
                list(workflows_util.DBOS_TERMINAL_WORKFLOW_STATUSES),
                None,
                load_output=False,
                load_input=False,
            )
            # Step 2 — Group by parent automation id; latest child per group.
            by_parent = workflows_util.get_workflows_by_parent_id(metadata_rows)
            if not by_parent:
                return executions

            latest_by_parent: dict[str, dbos.WorkflowStatus] = {
                parent_id: workflows_util.get_latest_workflow(group)
                for parent_id, group in by_parent.items()
            }
            all_metadata_rows: list[dbos.WorkflowStatus] = []
            for group in by_parent.values():
                all_metadata_rows.extend(group)

            # Step 3 — Hydrate each parent's latest child (input and output) in one request.
            latest_workflow_ids = [
                latest_workflow.workflow_id for latest_workflow in latest_by_parent.values()
            ]
            if latest_workflow_ids:
                await workflows_util.hydrate_scheduler_workflows_async(
                    self.INSTANCE,
                    octobot_node.enums.SchedulerWorkflowNames.EXECUTE_AUTOMATION,
                    all_metadata_rows,
                    latest_workflow_ids,
                    load_input=True,
                    load_output=True,
                )

            # Step 4 — Wallet filter and build Execution rows per parent group.
            for parent_id, group in list(by_parent.items()):
                latest = latest_by_parent[parent_id]
                try:
                    latest_input_task = workflows_util.get_automation_input_task(latest)
                    if (
                        user_id is not None
                        and latest_input_task is not None
                        and latest_input_task.user_id
                        and latest_input_task.user_id != user_id
                    ):
                        continue
                    executions.extend(
                        self._executions_for_automation_group(group, latest, latest_input_task)
                    )
                except Exception as e:
                    self.logger.exception(e, True, f"Failed to process result workflow group: {e}")
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
            return {"result": "", "result_metadata": ""}
        # Latest run: export persisted output.state when present, else workflow input task content.
        if not output.state and not result_task.content:
            return {"result": "", "result_metadata": ""}
        with task_context.encrypted_task(result_task):
            if (result_task.content == output.state and output.state_metadata
                    and octobot_node.config.settings.TASKS_SERVER_RSA_PRIVATE_KEY):
                raise encryption.EncryptionTaskError("Internal state decryption silently failed")
            user_rsa_key = user_rsa_public_key or octobot_node.config.settings.TASKS_USER_RSA_PUBLIC_KEY
            if not user_rsa_key or not octobot_node.config.settings.TASKS_SERVER_ECDSA_PRIVATE_KEY:
                # Node-side decrypt only; return plaintext state (typical dev / tests).
                return {
                    "result": result_task.content, # type: ignore
                    "result_metadata": "",
                }
            # Re-encrypt for the requesting user's RSA key (export to client).
            result, metadata = encryption.encrypt_task_result(
                result_task.content,
                rsa_public_key=user_rsa_key,
                ecdsa_private_key=octobot_node.config.settings.TASKS_SERVER_ECDSA_PRIVATE_KEY,
            )
        return {"result": result, "result_metadata": metadata}

    async def get_workflows_export_results(
        self,
        task_ids: list[str],
        user_id: typing.Optional[str],
        user_rsa_public_key: typing.Optional[str] = None,
    ) -> dict[str, dict[str, str]]:
        """
        Batch-export automation state for parent task IDs.

        Per task_id the value is one of:
        - ``{"error": "not found" | "forbidden" | ...}`` — request/lookup failure.
        - ``{"result", "result_metadata"}`` — decrypted or re-encrypted state (may be empty strings).
        - ``{"result": "", "result_metadata": "", "error": "..."}`` — chosen row is ERROR with no
          persisted output.state; empty result fields mean nothing to export, ``error`` is the run failure.
        """
        if not self.INSTANCE:
            return {}
        completed = await self._list_terminal_automation_workflows(None, load_output=True)

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
                if user_id is not None and (task is None or task.user_id != user_id):
                    out[task_id] = {"error": "forbidden"}
                    continue
                export_workflow = workflows_util.get_latest_workflow(group)
                user_rsa = user_rsa_public_key.encode("utf-8") if user_rsa_public_key else None
                built = self._build_export_result_from_status(export_workflow, user_rsa)
                if built.get("result") or built.get("result_metadata"):
                    # SUCCESS/ERROR with output.state, or CANCELLED with input task content.
                    out[task_id] = built
                    continue
                if export_workflow.status == dbos.WorkflowStatusString.ERROR.value:
                    # ERROR without persisted state: same empty payload as above, plus workflow error.
                    err = export_workflow.error
                    out[task_id] = {
                        "result": "",
                        "result_metadata": "",
                        "error": str(err) if err else "Execution failed",
                    }
                else:
                    # CANCELLED (or other) with no input content — legitimately empty export.
                    out[task_id] = built
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
        task_wallet_address = task.user_id if task else None
        return octobot_node.models.Execution(
            id=task_id,
            name=task_name,
            description=description,
            actions=task_actions,
            is_encrypted=bool(task.content_metadata) if task else False,
            type=task_type,
            status=status,
            user_id=task_wallet_address,
        )

    def get_task_name(self, task_data: dict | octobot_node.models.Task | None, default_value: typing.Optional[str] = None) -> typing.Optional[str]:
        if isinstance(task_data, octobot_node.models.Task):
            return task_data.name
        elif isinstance(task_data, dict):
            return task_data.get(octobot_node.enums.TaskResultKeys.TASK.value, {}).get("name", default_value)
        else:
            return default_value

    async def get_automation_states(
        self,
        user_id: typing.Optional[str],
        statuses: typing.Optional[list[dbos.WorkflowStatusString]] = None,
    ) -> list[protocol_models.AutomationState]:
        return await automation_states_loader.load_protocol_automation_states(user_id, statuses)

    @staticmethod
    def _user_action_list_sort_key(
        user_action: protocol_models.UserAction,
        workflow_status: dbos.WorkflowStatus,
    ) -> tuple[int, str, str]:
        workflow_identifier = str(workflow_status.workflow_id or "")
        return (workflow_status.created_at or 0, user_action.id, workflow_identifier)

    def _user_action_id_from_workflow(
        self,
        workflow_status: dbos.WorkflowStatus,
        *,
        load_output: bool,
    ) -> typing.Optional[str]:
        if load_output and workflow_status.output:
            from_output = self._parse_user_action_from_workflow_output(workflow_status)
            if from_output is not None:
                return from_output.id
        resolved = workflows_util.resolve_user_action_workflow_inputs(workflow_status)
        if resolved.inputs is not None and resolved.inputs.user_action is not None:
            return resolved.inputs.user_action.id
        return resolved.partial_user_action_id

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
        self, user_id: typing.Optional[str],
        active_only: bool = True,
    ) -> list[protocol_models.UserAction]:
        # Step: aggregate user actions from USER_ACTION_QUEUE workflows (pending inputs + terminal outputs).
        if not self.INSTANCE:
            return []
        _ = active_only  # Reserved for API; DBOS fetches always use explicit non-terminal / terminal status sets.
        loaded: list[tuple[tuple[int, str, str], protocol_models.UserAction]] = []
        input_workflows = await self._list_workflows(
            user_id,
            list(workflows_util.get_user_action_input_workflow_statuses()),
            octobot_node.enums.SchedulerWorkflowNames.EXECUTE_USER_ACTION,
            load_output=False,
            load_input=True,
        )
        for workflow_status in input_workflows:
            user_action_row = self._user_action_from_workflow_inputs(workflow_status, terminal=False)
            sort_key = self._user_action_list_sort_key(user_action_row, workflow_status)
            loaded.append((sort_key, user_action_row))
        terminal_workflows = await self._list_workflows(
            user_id,
            list(workflows_util.DBOS_TERMINAL_WORKFLOW_STATUSES),
            octobot_node.enums.SchedulerWorkflowNames.EXECUTE_USER_ACTION,
            load_output=True,
            load_input=True,
        )
        for workflow_status in terminal_workflows:
            user_action_row = self._user_action_from_terminal_workflow(workflow_status)
            sort_key = self._user_action_list_sort_key(user_action_row, workflow_status)
            loaded.append((sort_key, user_action_row))
        loaded.sort(key=lambda row: row[0])
        return [
            privacy_filter.to_protocol_user_action(user_action)
            for _, user_action in loaded
        ]
