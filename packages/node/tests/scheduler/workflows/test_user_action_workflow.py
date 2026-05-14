#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License version 3.0 of the License, or (at your option) any later version.

import mock
import pytest
import pydantic
import dbos

import octobot_protocol.models as protocol_models

import octobot_trading.errors as octobot_trading_errors

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_action_post_actions as user_action_post_actions_module
import octobot_node.scheduler.workflows.params as workflow_params_module

from tests.scheduler import temp_dbos_scheduler


class Test_UserActionWorkflow_should_retry:
    """Classification used by DBOS retry policy for ``UserActionWorkflow``."""

    @pytest.fixture
    def user_action_workflow_module(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.user_action_workflow as user_action_workflow_module_loaded

        yield user_action_workflow_module_loaded

    def test_requeues_runtime_errors_as_retriable(self, user_action_workflow_module):
        assert user_action_workflow_module.UserActionWorkflow._should_retry(RuntimeError("temporary backend fault"))

    def test_skips_retries_for_execution_and_validation_terminal_errors(self, user_action_workflow_module):
        assert not user_action_workflow_module.UserActionWorkflow._should_retry(
            node_errors.WorkflowActionExecutionError(),
        )

        class MinimalModelForValidationTrap(pydantic.BaseModel):
            required_positive_count: int

        with pytest.raises(pydantic.ValidationError) as raised_validation_error_capture:
            MinimalModelForValidationTrap.model_validate({"required_positive_count": "not_integer"})
        assert not user_action_workflow_module.UserActionWorkflow._should_retry(
            raised_validation_error_capture.value,
        )

    def test_skips_retries_for_authentication_errors_and_subclasses(
        self,
        user_action_workflow_module,
    ):
        assert not user_action_workflow_module.UserActionWorkflow._should_retry(
            octobot_trading_errors.AuthenticationError("exchange authentication failed"),
        )
        assert not user_action_workflow_module.UserActionWorkflow._should_retry(
            octobot_trading_errors.InvalidAPIKeyIPWhitelistError("ip not allowed"),
        )

    def test_skips_retries_for_user_action_errors_and_subclasses(
        self,
        user_action_workflow_module,
    ):
        assert not user_action_workflow_module.UserActionWorkflow._should_retry(
            node_errors.UserActionError("generic user action failure"),
        )
        assert not user_action_workflow_module.UserActionWorkflow._should_retry(
            node_errors.InvalidUserActionPayloadError("missing exchange account id"),
        )


class Test_UserActionWorkflow_execute_user_action_step:
    """Runs the internal step callable with collaborator patching."""

    @staticmethod
    def _inputs_dict(*, wallet_address_value: str, user_action_document: protocol_models.UserAction) -> dict:
        return workflow_params_module.UserActionWorkflowInputs(
            wallet_address=wallet_address_value,
            user_action=user_action_document,
        ).to_dict(include_default_values=False)

    @staticmethod
    def _stop_automation_user_action(*, automation_identifier_inner: str) -> protocol_models.UserAction:
        configuration_inner_payload = protocol_models.StopAutomationConfiguration(
            id=automation_identifier_inner,
            action_type=protocol_models.UserActionType.AUTOMATION_STOP,
        )
        wrapped_configuration_payload = protocol_models.UserActionConfiguration.from_json(
            configuration_inner_payload.to_json(),
        )
        return protocol_models.UserAction(
            id="ua-inner-step-parse",
            configuration=wrapped_configuration_payload,
        )

    @pytest.mark.asyncio
    async def test_runs_executor_resolved_via_factory_when_user_action_reparses(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.user_action_workflow as user_action_workflow_module_loaded

        test_wallet_segment = "0xwallet11115555"
        user_action_wire_model = self._stop_automation_user_action(automation_identifier_inner="auto-wire-xyz")
        step_inputs_document = self._inputs_dict(
            wallet_address_value=test_wallet_segment,
            user_action_document=user_action_wire_model,
        )
        reparsed_placeholder = protocol_models.UserAction(id="parsed-roundtrip", configuration=user_action_wire_model.configuration)

        async_execute_mock_tracker = mock.AsyncMock()

        class StubConstructedExecutorShell:
            def __init__(self, wallet_segment: str):
                self.received_wallet_segment = wallet_segment
                self.post_actions = user_action_post_actions_module.UserActionPostActions()

            async def execute(self, *run_arguments, **run_keyword_arguments):
                await async_execute_mock_tracker(*run_arguments, **run_keyword_arguments)

        with mock.patch.object(
            protocol_models.UserAction,
            "from_dict",
            return_value=reparsed_placeholder,
        ), mock.patch.object(
            user_action_workflow_module_loaded.user_actions_executor,
            "user_action_executor_factory",
            return_value=StubConstructedExecutorShell,
        ) as patched_factory_resolver:
            await user_action_workflow_module_loaded.UserActionWorkflow._execute_user_action(step_inputs_document)

        patched_factory_resolver.assert_called_once_with(reparsed_placeholder)
        assert async_execute_mock_tracker.await_args.args[0] is reparsed_placeholder

    @pytest.mark.asyncio
    async def test_input_error_when_user_action_blob_does_not_parse(self, temp_dbos_scheduler):
        import octobot_node.scheduler.workflows.user_action_workflow as user_action_workflow_module_loaded

        user_action_wire_model = self._stop_automation_user_action(automation_identifier_inner="auto-missing-wire")
        step_inputs_document = self._inputs_dict(
            wallet_address_value="0xwallet22227777",
            user_action_document=user_action_wire_model,
        )

        with mock.patch.object(
            protocol_models.UserAction,
            "from_dict",
            return_value=None,
        ):
            with pytest.raises(node_errors.WorkflowInputError, match="No user action found in inputs"):
                await user_action_workflow_module_loaded.UserActionWorkflow._execute_user_action(
                    step_inputs_document,
                )

    @pytest.mark.asyncio
    async def test_execute_user_action_step_retries_on_retriable_failed_request_then_completes(
        self,
        temp_dbos_scheduler,
    ):
        # Step 1: ensure DBOS treats exchange retriables as transient (distinct from WorkflowActionExecutionError).
        # Step 2: start workflow, patch asyncio.sleep so step backoff intervals are instantaneous.
        import octobot_node.scheduler.workflows.user_action_workflow as user_action_workflow_module_loaded

        assert user_action_workflow_module_loaded.UserActionWorkflow._should_retry(
            octobot_trading_errors.RetriableFailedRequest("classification probe"),
        )

        wallet_address_retry_run = "0xwallet_retries_retriable"
        user_action_wire_configuration = self._stop_automation_user_action(
            automation_identifier_inner="auto-retries-retriable",
        )
        workflow_encoded_inputs_bundle = self._inputs_dict(
            wallet_address_value=wallet_address_retry_run,
            user_action_document=user_action_wire_configuration,
        )

        transient_failure_attempt_tracker = {"count": 0}

        async def raise_retriable_failed_request_twice_then_return(
            _logged_user_action_run: protocol_models.UserAction,
        ) -> None:
            transient_failure_attempt_tracker["count"] += 1
            if transient_failure_attempt_tracker["count"] < 3:
                raise octobot_trading_errors.RetriableFailedRequest(
                    "simulated exchange retriable failure",
                )

        executor_execute_invocation_observer = mock.AsyncMock(
            side_effect=raise_retriable_failed_request_twice_then_return,
        )

        class RetryThenSucceedExecutorShell:
            def __init__(self, wallet_segment_from_workflow_inputs: str):
                self.wallet_segment_from_workflow_inputs = wallet_segment_from_workflow_inputs
                self.post_actions = user_action_post_actions_module.UserActionPostActions()

            async def execute(self, user_action_bundle: protocol_models.UserAction):
                assert self.wallet_segment_from_workflow_inputs == wallet_address_retry_run
                return await executor_execute_invocation_observer(user_action_bundle)

        with mock.patch.object(
            user_action_workflow_module_loaded.user_actions_executor,
            "user_action_executor_factory",
            return_value=RetryThenSucceedExecutorShell,
        ), mock.patch("asyncio.sleep", mock.AsyncMock()):
            workflow_enqueue_handle_record = await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                user_action_workflow_module_loaded.UserActionWorkflow.execute_user_action,
                inputs=workflow_encoded_inputs_bundle,
            )
            workflow_completion_output_blob = await workflow_enqueue_handle_record.get_result()
            workflow_lifetime_status_snapshot = await workflow_enqueue_handle_record.get_status()

        assert workflow_lifetime_status_snapshot.status == dbos.WorkflowStatusString.SUCCESS.value
        assert isinstance(workflow_completion_output_blob, dict)
        assert executor_execute_invocation_observer.await_count == 3
        assert transient_failure_attempt_tracker["count"] == 3

    @pytest.mark.asyncio
    async def test_execute_user_action_step_skips_retries_when_executor_raises_authentication_error(
        self,
        temp_dbos_scheduler,
    ):
        # Executor raises AuthenticationError: _should_retry is false, DBOS runs the step only once despite retries_allowed=True.
        import octobot_node.scheduler.workflows.user_action_workflow as user_action_workflow_module_loaded

        wallet_address_authentication_terminal = "0xwallet_terminal_auth_failure"
        user_action_wire_configuration = self._stop_automation_user_action(
            automation_identifier_inner="auto-auth-non-retriable",
        )
        workflow_encoded_inputs_bundle = self._inputs_dict(
            wallet_address_value=wallet_address_authentication_terminal,
            user_action_document=user_action_wire_configuration,
        )
        reparsed_user_action_stable_reference = protocol_models.UserAction(
            id="auth-failure-ua-stable",
            configuration=user_action_wire_configuration.configuration,
        )

        async def executor_always_reports_authentication_failure(
            _logged_user_action_run: protocol_models.UserAction,
        ) -> None:
            raise octobot_trading_errors.AuthenticationError("simulated bad API credentials")

        executor_execute_single_attempt_observer = mock.AsyncMock(
            side_effect=executor_always_reports_authentication_failure,
        )

        class AuthenticationFailingExecutorShell:
            def __init__(self, wallet_segment_from_workflow_inputs: str):
                self.wallet_segment_from_workflow_inputs = wallet_segment_from_workflow_inputs
                self.post_actions = user_action_post_actions_module.UserActionPostActions()

            async def execute(self, user_action_bundle: protocol_models.UserAction):
                assert self.wallet_segment_from_workflow_inputs == wallet_address_authentication_terminal
                return await executor_execute_single_attempt_observer(user_action_bundle)

        with mock.patch.object(
            protocol_models.UserAction,
            "from_dict",
            return_value=reparsed_user_action_stable_reference,
        ), mock.patch.object(
            user_action_workflow_module_loaded.user_actions_executor,
            "user_action_executor_factory",
            return_value=AuthenticationFailingExecutorShell,
        ), mock.patch("asyncio.sleep", mock.AsyncMock()):
            workflow_enqueue_handle_record = await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                user_action_workflow_module_loaded.UserActionWorkflow.execute_user_action,
                inputs=workflow_encoded_inputs_bundle,
            )
            with pytest.raises(octobot_trading_errors.AuthenticationError, match="simulated bad API credentials"):
                await workflow_enqueue_handle_record.get_result()
            workflow_lifetime_status_snapshot = await workflow_enqueue_handle_record.get_status()

        assert workflow_lifetime_status_snapshot.status != dbos.WorkflowStatusString.SUCCESS.value
        assert executor_execute_single_attempt_observer.await_count == 1
