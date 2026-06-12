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
import json
import time
import typing
import dbos

import octobot_commons.logging

import octobot.community.wallet_backend.errors as wallet_backend_errors
import octobot_trading.errors

import octobot_flow.entities
import octobot_flow.enums
import octobot_flow.errors

import octobot_node.enums
import octobot_node.models
import octobot_node.scheduler.octobot_flow_client as octobot_flow_client
import octobot_node.scheduler.task_context
import octobot_node.constants as constants
import octobot_node.scheduler.workflows.params as params
import octobot_node.scheduler.workflows_util as workflows_util
import octobot_node.errors as errors
import octobot_node.protocol.accounts_trading as accounts_trading_protocol

from octobot_node.scheduler import SCHEDULER  # avoid circular import


@SCHEDULER.INSTANCE.dbos_class()
class AutomationWorkflow:
    # Always use dict as input to parse minimizable dataclasses and facilitate data format updates

    @staticmethod
    @SCHEDULER.INSTANCE.workflow(name="execute_automation")
    async def execute_automation(inputs: dict) -> typing.Optional[str]:
        """
        Automation workflow runner: 
        1. Wait for priority actions (zero timeout when execution_time is already due).
        2. Execute the iteration (received priority action or DAG's executable actions).
        3. Check and process other received priority actions if any.
        4. Either:
            A. Reschedule the next iteration as a child workflow to avoid growing the workflow forever.
            B. Complete the workflow and stop the automation.
        5. If completed, return tthe updated task.content (the automation state) as workflow output
        """
        output: typing.Optional[params.AutomationWorkflowOutput] = None
        iteration_result = None
        try:
            parsed_inputs = params.AutomationWorkflowInputs.from_dict(inputs)
            delay = parsed_inputs.execution_time - time.time()
            delay_str = f" in {delay:.2f} seconds" if delay > 0 else ""
            AutomationWorkflow.get_logger(parsed_inputs).info(f"{AutomationWorkflow.__name__} starting{delay_str}.")
            actions_update = await AutomationWorkflow._wait_and_trigger_on_actions_update(
                parsed_inputs, parsed_inputs.execution_time
            )
            raw_iteration_result = await AutomationWorkflow.execute_iteration(inputs, actions_update)
            iteration_result = params.AutomationWorkflowIterationResult.from_dict(raw_iteration_result)
            continue_workflow = False
            if (
                iteration_result.progress_status.postponed_iteration
                or AutomationWorkflow._should_continue_workflow(
                    parsed_inputs, iteration_result.progress_status, bool(actions_update)
                )
            ):
                # update iteration_result to include the executions of priority actions if any
                continue_workflow, iteration_result = await AutomationWorkflow._process_pending_priority_actions_and_reschedule(
                    parsed_inputs, iteration_result
                )
            if not continue_workflow:
                AutomationWorkflow.get_logger(parsed_inputs).info(
                    f"Stopped workflow (remaining steps: {iteration_result.progress_status.remaining_steps})"
                )
                final_state = iteration_result.next_iteration_description
                final_state_metadata = iteration_result.next_iteration_description_metadata
                final_error = iteration_result.progress_status.error
                if final_state is not None or final_error is not None:
                    output = params.AutomationWorkflowOutput(
                        state=final_state,
                        state_metadata=final_state_metadata,
                        error=final_error,
                        error_message=iteration_result.progress_status.error_message,
                    )
        except Exception as err:
            AutomationWorkflow.get_logger(parsed_inputs).exception(
                err, True, f"Interrupted workflow: unexpected critical error: {err} ({err.__class__.__name__})"
            )
            output = params.AutomationWorkflowOutput(
                # use available iteration result when possible (might be the one of the previous iteration)
                state=iteration_result.next_iteration_description if iteration_result else None,
                state_metadata=iteration_result.next_iteration_description_metadata if iteration_result else None,
                # keep track of the failed iteration
                error=AutomationWorkflow._get_failed_error_status(err),
                error_message=str(err),
            )
        return json.dumps(output.to_dict(include_default_values=False)) if output else None

    @staticmethod
    def _should_retry(error: BaseException) -> bool:
        return not isinstance(error, (
            # workflow stopping errors
            errors.WorkflowError,
            octobot_flow.errors.ConfigurationError,
        ))

    @staticmethod
    @SCHEDULER.INSTANCE.step(
        name="execute_iteration",
        retries_allowed=True,
        interval_seconds=constants.AUTOMATION_WORKFLOW_RETRY_INTERVAL_SECONDS,
        max_attempts=constants.AUTOMATION_WORKFLOW_MAX_ITERATION_RETRIES,
        backoff_rate=constants.AUTOMATION_WORKFLOW_BACKOFF_RATE,
        should_retry=_should_retry,
    )
    async def execute_iteration(inputs: dict, actions_update: typing.Optional[dict]) -> dict:
        """
        Execute an automation iteration: executed actions can be received priority actions or DAG's executable actions.
        In case of priority actions, the returned next scheduled time will be the same as the previous one to respect
        the latest DAG execution time schedule.

        Should be a SCHEDULER.INSTANCE.step to avoid executing actions twice when recovering a workflow 
        that was interrupted while executing priority actions which were received AFTER the initial 
        iteration of the workflow.

        Will retry up to 3 times in case of an unexpected error before failing step.
        """
        parsed_inputs: params.AutomationWorkflowInputs = params.AutomationWorkflowInputs.from_dict(inputs)
        executed_step: str = "no action executed"
        execution_error = next_step = next_step_at = execution_error_message = None
        postponed_iteration = False
        has_next_actions_override: typing.Optional[bool] = None
        next_iteration_description_override: typing.Optional[str] = None
        next_iteration_description_metadata_override: typing.Optional[str] = None
        result = octobot_flow_client.OctoBotActionsJobResult()
        with octobot_node.scheduler.task_context.encrypted_task(parsed_inputs.task, result):
            #### Start of decryped task context ####
            if parsed_inputs.task.type == octobot_node.models.TaskType.EXECUTE_ACTIONS.value:
                user_actions, trading_signals = AutomationWorkflow._parse_actions_update_envelope(actions_update)
                AutomationWorkflow._log_iteration_execution_intent(
                    parsed_inputs, user_actions, trading_signals
                )
                try:
                    await octobot_flow_client.OctoBotActionsJob(
                        parsed_inputs.task.content,
                        user_actions,
                        trading_signals,
                        result,
                        wallet_address=parsed_inputs.task.wallet_address,
                    ).run()
                except octobot_flow.errors.CommunityTradingSignalError as err:
                    execution_error = octobot_flow.enums.ActionErrorStatus.NO_TRADING_SIGNAL.value
                    execution_error_message = str(err)
                except octobot_trading.errors.AuthenticationError as err:
                    AutomationWorkflow.get_logger(parsed_inputs).error(
                        f"Authentication error: {err} ({err.__class__.__name__})"
                    )
                    execution_error = octobot_flow.enums.ActionErrorStatus.AUTHENTICATION_ERROR.value
                    execution_error_message = str(err)
                    postponed_iteration = True
                    next_step_at = time.time() + constants.INVALID_AUTHENTICATION_RETRY_DELAY_SECONDS
                    has_next_actions_override = True
                    next_iteration_description_override = parsed_inputs.task.content
                    next_iteration_description_metadata_override = parsed_inputs.task.content_metadata
                if result.processed_actions:
                    if latest_step := AutomationWorkflow._get_actions_summary(result.processed_actions, minimal=True):
                        executed_step = latest_step
                    for action in result.processed_actions:
                        if action.error_status is not None:
                            AutomationWorkflow.get_logger(parsed_inputs).error(
                                f"Error: {action.error_status} when executing action {action.id}: {action.get_summary()} "
                            )
                            execution_error = action.error_status
                            execution_error_message = action.error_message
            else:
                raise errors.WorkflowInputError(f"Invalid task type: {parsed_inputs.task.type}")
            next_actions = []
            remaining_steps = 0
            if not postponed_iteration:
                if result.has_next_actions:
                    if result.actions_dag:
                        next_actions = result.actions_dag.get_executable_actions()
                        remaining_steps = len(result.actions_dag.get_pending_actions())
                    next_step_at = result.next_actions_description.get_next_execution_time() if result.next_actions_description else None
                next_step = AutomationWorkflow._get_actions_summary(next_actions, minimal=True)
                next_actions_str = f"next immediate actions: {next_actions}" if next_actions else "all actions completed"
                AutomationWorkflow.get_logger(parsed_inputs).info(
                    f"Iteration completed, executed step: '{executed_step}', {next_actions_str}"
                )
                AutomationWorkflow._persist_account_trading_from_iteration_result(
                    parsed_inputs.task.wallet_address,
                    result,
                )
            else:
                AutomationWorkflow.get_logger(parsed_inputs).info(
                    f"Iteration postponed after authentication error, retry scheduled in "
                    f"{constants.INVALID_AUTHENTICATION_RETRY_DELAY_SECONDS:.0f} seconds"
                )
            #### End of decryped task context - no clear data after this point in encrypted context ####

        return params.AutomationWorkflowIterationResult(
            progress_status=params.ProgressStatus(
                latest_step=executed_step,
                next_step=next_step,
                next_step_at=next_step_at,
                remaining_steps=remaining_steps,
                error=execution_error,
                error_message=execution_error_message,
                should_stop=result.should_stop,
                postponed_iteration=postponed_iteration,
            ),
            next_iteration_description=(
                next_iteration_description_override
                if postponed_iteration
                else result.maybe_encrypted_next_actions_description
            ),
            next_iteration_description_metadata=(
                next_iteration_description_metadata_override
                if postponed_iteration
                else result.next_actions_description_encryption_metadata
            ),
            has_next_actions=(
                has_next_actions_override if postponed_iteration else result.has_next_actions
            ),
        ).to_dict(include_default_values=False)

    @staticmethod
    async def _wait_and_trigger_on_actions_update(
        parsed_inputs: params.AutomationWorkflowInputs, resume_execution_time: float
    ) -> typing.Optional[dict]:
        delay = max(0, resume_execution_time - time.time())
        actions_topic = octobot_node.enums.AutomationWorkflowMessageTopics.ACTIONS_UPDATE.value
        if recv_payload := await SCHEDULER.INSTANCE.recv_async(topic=actions_topic, timeout_seconds=delay):
            AutomationWorkflow.get_logger(parsed_inputs).info(f"Received actions updates: {recv_payload}")
            return recv_payload
        return None

    @staticmethod
    def _persist_account_trading_from_iteration_result(
        wallet_address: typing.Optional[str],
        job_result: octobot_flow_client.OctoBotActionsJobResult,
    ) -> None:
        # Temporary: persist trading snapshot locally until the global view system owns this sync.
        if wallet_address is None or job_result.next_actions_description is None:
            return
        automation_state = octobot_flow.entities.AutomationState.from_dict(
            job_result.next_actions_description.state
        )
        exchange_account_elements = automation_state.automation.exchange_account_elements
        exchange_account_details = automation_state.exchange_account_details
        if exchange_account_elements is None or exchange_account_details is None:
            return
        exchange_account_id = exchange_account_details.exchange_details.exchange_account_id
        if not exchange_account_id:
            return
        try:
            accounts_trading_protocol.update_account_trading(
                wallet_address,
                exchange_account_id,
                list(exchange_account_elements.orders.open_orders),
                list(exchange_account_elements.trades),
                [
                    position_details.position
                    for position_details in exchange_account_elements.positions
                ],
            )
        except wallet_backend_errors.WalletNotFoundError:
            # Trading collections are wallet-scoped; skip until the wallet is registered locally.
            octobot_commons.logging.get_logger(AutomationWorkflow.__name__).warning(
                "Skipping account trading persistence for wallet %s: wallet not registered",
                wallet_address,
            )

    @staticmethod
    def _parse_actions_update_envelope(
        actions_update: typing.Optional[dict],
    ) -> tuple[list[dict], list[dict]]:
        if not actions_update:
            return [], []
        envelope = params.AutomationWorkflowActionUpdate.from_dict(actions_update)
        if envelope.actions_type == octobot_node.enums.AutomationWorkflowActionTypes.USER_ACTIONS.value:
            return list(envelope.actions_details), []
        if envelope.actions_type == octobot_node.enums.AutomationWorkflowActionTypes.TRADING_SIGNAL.value:
            return [], list(envelope.actions_details)
        if envelope.actions_type == octobot_node.enums.AutomationWorkflowActionTypes.FORCED_TRIGGER.value:
            return [], []
        return [], []

    @staticmethod
    def _log_iteration_execution_intent(
        parsed_inputs: params.AutomationWorkflowInputs,
        user_actions: list[dict],
        trading_signals: list[dict],
    ) -> None:
        logger = AutomationWorkflow.get_logger(parsed_inputs)
        if user_actions:
            logger.info(f"Executing user actions: {user_actions}")
        if trading_signals:
            logger.info(f"Executing trading signals: {trading_signals}")
        if not user_actions and not trading_signals:
            logger.info(f"Executing {parsed_inputs.task.name} DAG's executable actions")

    @staticmethod
    async def _process_pending_priority_actions_and_reschedule(
        parsed_inputs: params.AutomationWorkflowInputs,
        previous_iteration_result: params.AutomationWorkflowIterationResult
    ) -> tuple[bool, params.AutomationWorkflowIterationResult]:
        if not previous_iteration_result.has_next_actions:
            return False, previous_iteration_result
        # In case new priority actions were sent, execute them now.
        # Any action sent to this workflow will be lost if not processed by it.
        latest_iteration_result: params.AutomationWorkflowIterationResult = previous_iteration_result
        while new_actions_update := await AutomationWorkflow._wait_and_trigger_on_actions_update(
            parsed_inputs, 0
        ):
            extra_iteration_inputs = AutomationWorkflow._create_next_iteration_inputs(
                parsed_inputs, latest_iteration_result.next_iteration_description, 0,
                latest_iteration_result.next_iteration_description_metadata,
            )
            # execute the iteration on the updated state from last iteration
            raw_iteration_result = await AutomationWorkflow.execute_iteration(extra_iteration_inputs, new_actions_update)
            # use the new inputs for the next iteration of this loop
            parsed_inputs = params.AutomationWorkflowInputs.from_dict(extra_iteration_inputs)
            latest_iteration_result = params.AutomationWorkflowIterationResult.from_dict(raw_iteration_result)
            if not AutomationWorkflow._should_continue_workflow(parsed_inputs, latest_iteration_result.progress_status, False):
                return False, latest_iteration_result
            if not latest_iteration_result.has_next_actions:
                raise errors.WorkflowPriorityActionExecutionError(
                    f"Unexpected error: no next iteration description after processing priority actions: {latest_iteration_result}"
                )
        if latest_iteration_result.progress_status.should_stop:
            AutomationWorkflow.get_logger(parsed_inputs).info(
                f"Stopping workflow, should stop: {latest_iteration_result.progress_status.should_stop}"
            )
        else:
            # successful iteration and a new iteration is required, schedule next iteration, don't return anything
            await AutomationWorkflow._schedule_next_iteration(
                parsed_inputs,
                latest_iteration_result.next_iteration_description,  # type: ignore
                latest_iteration_result.progress_status,
                latest_iteration_result.next_iteration_description_metadata,
            )
        return True, latest_iteration_result

    @staticmethod
    async def _schedule_next_iteration(
        parsed_inputs: params.AutomationWorkflowInputs,
        next_iteration_description: str,
        progress_status: params.ProgressStatus,
        next_iteration_description_metadata: typing.Optional[str] = None,
    ):
        next_execution_time = progress_status.next_step_at or 0
        next_iteration_inputs = AutomationWorkflow._create_next_iteration_inputs(
            parsed_inputs, next_iteration_description, next_execution_time, next_iteration_description_metadata
        )
        delay = next_execution_time - time.time()
        delay_str = f", starting in {delay:.2f} seconds" if delay > 0 else ""
        AutomationWorkflow.get_logger(parsed_inputs).info(
            f"Enqueuing next iteration: next step: {progress_status.next_step}, "
            f"remaining steps: {progress_status.remaining_steps}{delay_str}."
        )
        next_workflow_id = AutomationWorkflow._get_next_child_workflow_id()
        with SCHEDULER.SetWorkflowID(next_workflow_id):
            await SCHEDULER.AUTOMATION_WORKFLOW_QUEUE.enqueue_async(
                AutomationWorkflow.execute_automation,
                inputs=next_iteration_inputs
            )

    @staticmethod
    def _get_next_child_workflow_id() -> str:
        workflow_id = dbos.DBOS.workflow_id
        if workflow_id is None:
            raise errors.WorkflowInputError("Missing current workflow ID while scheduling next iteration.")
        parent_workflow_id = workflow_id[:constants.PARENT_WORKFLOW_ID_LENGTH]
        try:
            current_child_id = workflows_util.parse_automation_child_workflow_index(workflow_id)
        except ValueError as error:
            raise errors.WorkflowInputError(str(error)) from error
        next_child_id = current_child_id + 1
        return f"{parent_workflow_id}_{next_child_id}"

    @staticmethod
    def _create_next_iteration_inputs(
        parsed_inputs: params.AutomationWorkflowInputs,
        next_iteration_description: str,
        next_execution_time: float,
        next_iteration_description_metadata: typing.Optional[str] = None,
    ) -> dict:
        # update task.content with the next iteration description containing the automation state
        next_task = parsed_inputs.task
        next_task.content = next_iteration_description
        next_task.content_metadata = next_iteration_description_metadata
        next_execution_time = next_execution_time or 0
        return params.AutomationWorkflowInputs(
            task=parsed_inputs.task, execution_time=next_execution_time
        ).to_dict(include_default_values=False)

    @staticmethod
    def _should_continue_workflow(
        parsed_inputs: params.AutomationWorkflowInputs,
        progress_status: params.ProgressStatus,
        stop_on_error: bool
    ) -> bool:
        if progress_status.error:
            # failed iteration, return global progress where it stopped and exit workflow
            AutomationWorkflow.get_logger(parsed_inputs).error(
                f"Failed iteration: stopping workflow, error: {progress_status.error}. "
                f"Iteration's last step: {progress_status.latest_step}"
            )
            return stop_on_error
        elif progress_status.should_stop:
            AutomationWorkflow.get_logger(parsed_inputs).info(
                f"Workflow stop required: stopping workflow"
            )
            return False
        return True

    @staticmethod
    def _get_actions_summary(actions: list["octobot_flow.entities.AbstractActionDetails"], minimal: bool = False) -> str:
        return ", ".join([action.get_summary(minimal=minimal) for action in actions]) if actions else ""

    @staticmethod
    def _get_failed_error_status(error: Exception) -> str:
        if isinstance(error, errors.WorkflowActionExecutionError):
            return error.ERROR_MESSAGE
        if isinstance(error, dbos.error.DBOSMaxStepRetriesExceeded):
            last_error = error.errors[-1]
            if isinstance(last_error, octobot_flow.errors.InvalidAutomationActionError):
                return octobot_flow.enums.AutomationWorkflowErrorStatus.INVALID_ACTION_CONFIGURATION.value
        return octobot_flow.enums.AutomationWorkflowErrorStatus.EXCEPTION_DURING_ITERATION.value

    @staticmethod
    def get_logger(parsed_inputs: params.AutomationWorkflowInputs) -> octobot_commons.logging.BotLogger:
        return octobot_commons.logging.get_logger(
            parsed_inputs.task.name or AutomationWorkflow.__name__
        )
