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

import asyncio
import contextlib
import json
import os
import functools
import mock
import pytest
import time
import typing
import tempfile
import dbos

import octobot_trading.constants
import octobot_trading.errors as octobot_trading_errors
import octobot_commons.cryptography

import octobot_copy.constants as copy_constants
import octobot_protocol.models as protocol_models
import octobot_node.config
import octobot_node.constants
import octobot_node.enums
import octobot_node.scheduler
import octobot_node.scheduler.workflows
import octobot_node.errors as errors
import octobot_node.models
import octobot_node.scheduler.workflows.params as params
import octobot_node.scheduler.octobot_flow_client as octobot_flow_client
import octobot_node.scheduler.encryption.task_inputs as task_inputs_encryption
import octobot_node.scheduler.task_context as task_context


from tests.scheduler import temp_dbos_scheduler, init_and_destroy_scheduler, init_scheduler


IMPORTED_OCTOBOT_FLOW = True
AUTOMATION_WORKFLOW_IMPORTED = False
try:
    import octobot_flow.entities
    import octobot_flow.enums
    import octobot_flow.errors

except ImportError:
    IMPORTED_OCTOBOT_FLOW = False


@pytest.fixture
def import_automation_workflow():
    global AUTOMATION_WORKFLOW_IMPORTED
    if not AUTOMATION_WORKFLOW_IMPORTED:
        with tempfile.NamedTemporaryFile() as temp_file:
            init_and_destroy_scheduler(temp_file.name)
        import octobot_node.scheduler.workflows.automation_workflow
    AUTOMATION_WORKFLOW_IMPORTED = True


def _automation_state_dict(actions: list[dict[str, typing.Any]]) -> dict[str, typing.Any]:
    """Build automation state dict with raw action dicts (JSON-serializable)."""
    return {
        "automation": {
            "metadata": {"automation_id": "automation_1"},
            "actions_dag": {"actions": actions},
        }
    }


def _parse_automation_workflow_output(
    workflow_output: str,
) -> params.AutomationWorkflowOutput:
    """
    Parse a completed automation workflow result (``get_result()`` string or dict-shaped DBOS output)
    into ``AutomationWorkflowOutput``. ``AutomationWorkflowOutput.state`` is always a str (JSON
    document text); use ``json.loads(parsed.state)`` for a dict tree.
    """
    payload = json.loads(workflow_output)
    return params.AutomationWorkflowOutput.from_dict(payload)


def _expected_automation_workflow_envelope_json(
    state_document: str,
    error: str | None = None,
    error_message: str | None = None,
) -> str:
    """Mirror ``execute_automation`` return: ``json.dumps(AutomationWorkflowOutput.to_dict(...))``."""
    return json.dumps(
        params.AutomationWorkflowOutput(
            state=state_document,
            error=error,
            error_message=error_message,
        ).to_dict(include_default_values=False)
    )


def _dbos_step_retries_exhausted_error_message(step_name: str, max_attempts: int) -> str:
    return f"DBOS Error 7: Step {step_name} has exceeded its maximum of {max_attempts} retries"


def _job_description_dict_from_output(parsed: params.AutomationWorkflowOutput) -> dict[str, typing.Any]:
    """Decode ``parsed.state`` (OctoBotActionsJobDescription JSON text)."""
    assert isinstance(parsed.state, str)
    return json.loads(parsed.state)


def _apply_octobot_actions_job_result_template(
    target: octobot_flow_client.OctoBotActionsJobResult,
    template: octobot_flow_client.OctoBotActionsJobResult,
) -> None:
    """Copy fields from ``template`` onto ``target`` (real ``run()`` mutates ``OctoBotActionsJob.result`` in place)."""
    target.processed_actions = template.processed_actions
    target.next_actions_description = template.next_actions_description
    target.has_next_actions = template.has_next_actions
    target.actions_dag = template.actions_dag
    target.should_stop = template.should_stop


def _assert_iteration_job_errors_logged(
    mock_logger: mock.Mock,
    raised_exception: BaseException,
    *,
    iteration_failure_count: int,
    expect_workflow_interrupted_log: bool = False,
) -> None:
    expected_call_count = iteration_failure_count + (1 if expect_workflow_interrupted_log else 0)
    assert mock_logger.exception.call_count == expected_call_count
    for call_index in range(iteration_failure_count):
        logged_exception, publish_error, error_message = mock_logger.exception.call_args_list[call_index][0]
        assert isinstance(logged_exception, type(raised_exception))
        assert str(logged_exception) == str(raised_exception)
        assert publish_error is True
        assert error_message == f"Error while running automation job: {logged_exception}"
    if expect_workflow_interrupted_log:
        assert "Interrupted workflow: unexpected critical error: " in str(
            mock_logger.exception.call_args_list[-1][0][2]
        )


def _octobot_actions_job_mock_class(
    *,
    run_on_result: typing.Callable[[octobot_flow_client.OctoBotActionsJobResult], typing.Any] | None = None,
    run_side_effect: typing.Any = None,
    latest_result_ref: list[octobot_flow_client.OctoBotActionsJobResult | None] | None = None,
) -> tuple[mock.Mock, mock.AsyncMock | None]:
    """
    Patch target for ``OctoBotActionsJob``: each constructor call receives ``result`` at index 3.

    Use ``run_on_result`` to mutate that object like production ``run()`` (one ``run`` mock per job instance).

    Use ``run_side_effect`` with a **shared** ``run`` mock so ``await_count`` aggregates across job instances
    (exceptions, retries, or repeated failures). When ``run_side_effect`` needs the current ``OctoBotActionsJobResult``,
    pass ``latest_result_ref=[None]`` and assign ``latest_result_ref[0] = args[3]`` on each construction.
    """
    if (run_on_result is None) == (run_side_effect is None):
        raise ValueError("Pass exactly one of run_on_result or run_side_effect")

    if run_side_effect is not None:
        run_mock = mock.AsyncMock(side_effect=run_side_effect)

        def mock_job_factory(*args, **kwargs):
            if latest_result_ref is not None:
                latest_result_ref[0] = args[3]
            return mock.Mock(run=run_mock)

        return mock.Mock(side_effect=mock_job_factory), run_mock

    def mock_job_factory(*args, **kwargs):
        result_ref = args[3]

        async def assign_result(*args, **kwargs):
            outcome = run_on_result(result_ref)
            if asyncio.iscoroutine(outcome):
                await outcome

        return mock.Mock(run=mock.AsyncMock(side_effect=assign_result))

    return mock.Mock(side_effect=mock_job_factory), None


def _user_actions_update_envelope(user_action_dicts: list[dict]) -> dict[str, typing.Any]:
    return params.AutomationWorkflowActionUpdate(
        actions_type=octobot_node.enums.AutomationWorkflowActionTypes.USER_ACTIONS.value,
        actions_details=user_action_dicts,
    ).to_dict(include_default_values=False)


def _trading_signal_update_envelope(signal_dicts: list[dict]) -> dict[str, typing.Any]:
    return params.AutomationWorkflowActionUpdate(
        actions_type=octobot_node.enums.AutomationWorkflowActionTypes.TRADING_SIGNAL.value,
        actions_details=signal_dicts,
    ).to_dict(include_default_values=False)


@pytest.fixture
def parsed_inputs():
    task = octobot_node.models.Task(
        name="test_task",
        content="{}",
        type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
    )
    return params.AutomationWorkflowInputs(task=task, execution_time=0)


@pytest.fixture
def task():
    return octobot_node.models.Task(
        name="test_task",
        content="{}",
        type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
    )


@pytest.fixture
def iteration_result():
    return params.AutomationWorkflowIterationResult(
        progress_status=params.ProgressStatus(
            latest_step="action_1",
            next_step="action_2",
            next_step_at=0.0,
            remaining_steps=1,
            error=None,
            should_stop=False,
        ),
        next_iteration_description='{"state": {"automation": {}}}',
        has_next_actions=True,
    )

def required_imports(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not IMPORTED_OCTOBOT_FLOW:
            pytest.skip(reason="octobot_flow is not installed")
        return await func(*args, **kwargs)
    return wrapper


class TestExecuteAutomation:
    # use a minimal amount of tests to avoid wasting time initializing the scheduler
    @pytest.mark.asyncio
    @required_imports
    async def test_execute_automation(
        self, temp_dbos_scheduler, parsed_inputs, iteration_result
    ):
        # 1. execution_time due: initial zero-timeout wait, then iteration; stops when _should_continue is False
        inputs = parsed_inputs.to_dict(include_default_values=False)
        iter_result = params.AutomationWorkflowIterationResult(
            progress_status=iteration_result.progress_status,
            next_iteration_description=None,
            has_next_actions=False,
        )
        mock_wait = mock.AsyncMock(return_value=None)
        mock_iteration = mock.AsyncMock(return_value=iter_result.to_dict(include_default_values=False))
        mock_should_continue = mock.Mock(return_value=False)
        mock_process = mock.AsyncMock()

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_actions_update",
            mock_wait,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "execute_iteration",
            mock_iteration,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_should_continue_workflow",
            mock_should_continue,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_process_pending_priority_actions_and_reschedule",
            mock_process,
        ):
            handle = await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation,
                inputs=inputs,
            )
            assert await handle.get_result() is None # next_iteration_description.next_actions_description is None
            mock_wait.assert_awaited_once_with(parsed_inputs, 0)
            mock_iteration.assert_called_once_with(inputs, None)
            mock_should_continue.assert_called_once()
            mock_process.assert_not_called()

        # 2. With delay: waits, calls iteration, _process_pending not called
        parsed_inputs.execution_time = time.time() + 100
        inputs = parsed_inputs.to_dict(include_default_values=False)
        mock_wait = mock.AsyncMock(return_value=None)
        iteration_result.next_iteration_description = json.dumps({"state": {"automation": {}}})
        mock_iteration = mock.AsyncMock(return_value=iteration_result.to_dict(include_default_values=False))
        mock_should_continue = mock.Mock(return_value=False)
        mock_process = mock.AsyncMock()

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_actions_update",
            mock_wait,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "execute_iteration",
            mock_iteration,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_should_continue_workflow",
            mock_should_continue,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_process_pending_priority_actions_and_reschedule",
            mock_process,
        ):
            handle = await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation,
                inputs=inputs,
            )
            assert await handle.get_result() == _expected_automation_workflow_envelope_json(
                r'{"state": {"automation": {}}}'
            )  # next_iteration_description.next_actions_description is not None
            mock_wait.assert_called_once()
            mock_iteration.assert_called_once_with(inputs, None)
            mock_process.assert_not_called()

        # 3. With delay, _should_continue True: _process_pending called
        inputs = parsed_inputs.to_dict(include_default_values=False)
        mock_wait = mock.AsyncMock(return_value=None)
        mock_iteration = mock.AsyncMock(return_value=iteration_result.to_dict(include_default_values=False))
        mock_should_continue = mock.Mock(return_value=True)
        mock_process = mock.AsyncMock(return_value=(True, iteration_result))

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_actions_update",
            mock_wait,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "execute_iteration",
            mock_iteration,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_should_continue_workflow",
            mock_should_continue,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_process_pending_priority_actions_and_reschedule",
            mock_process,
        ):
            handle = await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation,
                inputs=inputs,
            )
            assert await handle.get_result() is None # _should_continue_workflow is True
            mock_wait.assert_called_once()
            mock_iteration.assert_called_once_with(inputs, None)
            mock_should_continue.assert_called_once()
            mock_process.assert_awaited_once_with(parsed_inputs, iteration_result)

        # 4. Priority actions passed to iteration (raw actions_update envelope dict)
        inputs = parsed_inputs.to_dict(include_default_values=False)
        actions_update = _user_actions_update_envelope([{"action": "stop"}])
        mock_wait = mock.AsyncMock(return_value=actions_update)
        mock_iteration = mock.AsyncMock(return_value=iteration_result.to_dict(include_default_values=False))
        mock_should_continue = mock.Mock(return_value=False)
        mock_process = mock.AsyncMock()

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_actions_update",
            mock_wait,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "execute_iteration",
            mock_iteration,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_should_continue_workflow",
            mock_should_continue,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_process_pending_priority_actions_and_reschedule",
            mock_process,
        ):
            handle = await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation,
                inputs=inputs,
            )
            assert await handle.get_result() == _expected_automation_workflow_envelope_json(
                r'{"state": {"automation": {}}}'
            )
            mock_iteration.assert_called_once_with(inputs, actions_update)
            mock_process.assert_not_called()

        # 5. Exceptions are caught and mapped to workflow error statuses
        parsed_inputs.execution_time = 0
        inputs = parsed_inputs.to_dict(include_default_values=False)
        max_attempts = octobot_node.constants.AUTOMATION_WORKFLOW_MAX_ITERATION_RETRIES
        dbos_retries_exhausted_message = _dbos_step_retries_exhausted_error_message(
            "execute_iteration",
            max_attempts,
        )
        failure_cases = [
            (
                ValueError("test error"),
                octobot_flow.enums.AutomationWorkflowErrorStatus.EXCEPTION_DURING_ITERATION.value,
                dbos_retries_exhausted_message,
                max_attempts,
            ),
            (
                octobot_flow.errors.InvalidAutomationActionError("invalid action config"), # non retryable ConfigurationError
                octobot_flow.enums.AutomationWorkflowErrorStatus.EXCEPTION_DURING_ITERATION.value,
                "invalid action config",
                1, # only 1 attempt: this raises a non retryable error
            ),
            (
                errors.WorkflowInputError("invalid action config"), # non retryable WorkflowError
                octobot_flow.enums.AutomationWorkflowErrorStatus.EXCEPTION_DURING_ITERATION.value,
                "invalid action config",
                1, # only 1 attempt: this raises a non retryable error
            ),
        ]
        for (
            raised_exception,
            expected_error_status,
            expected_error_message,
            expected_run_await_count,
        ) in failure_cases:
            mock_logger = mock.Mock()
            mock_process = mock.AsyncMock()
            mock_octobot_actions_job_class, run_mock = _octobot_actions_job_mock_class(
                run_side_effect=raised_exception
            )
            with mock.patch(
                "asyncio.sleep", mock.AsyncMock()
            ), mock.patch.object(
                octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
                "_should_continue_workflow",
                mock.Mock(return_value=False),
            ), mock.patch.object(
                octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
                "get_logger",
                mock.Mock(return_value=mock_logger),
            ), mock.patch.object(
                octobot_flow_client,
                "OctoBotActionsJob",
                mock_octobot_actions_job_class,
            ), mock.patch.object(
                octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
                "_process_pending_priority_actions_and_reschedule",
                mock_process,
            ):
                handle = await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                    octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation,
                    inputs=inputs,
                )
                workflow_result = await handle.get_result()
                assert workflow_result == json.dumps(
                    params.AutomationWorkflowOutput(
                        error=expected_error_status,
                        error_message=expected_error_message,
                    ).to_dict(include_default_values=False)
                )
                parsed_output = _parse_automation_workflow_output(workflow_result)
                assert parsed_output.state is None
                assert parsed_output.error == expected_error_status
                assert parsed_output.error_message == expected_error_message
                assert run_mock.await_count == expected_run_await_count
                if expected_run_await_count > 1:
                    _assert_iteration_job_errors_logged(
                        mock_logger,
                        raised_exception,
                        iteration_failure_count=expected_run_await_count,
                        expect_workflow_interrupted_log=True,
                    )
                else:
                    _assert_iteration_job_errors_logged(
                        mock_logger,
                        raised_exception,
                        iteration_failure_count=1,
                        expect_workflow_interrupted_log=True,
                    )
                mock_process.assert_not_called()


class TestExecuteIteration:
    def setup_method(self):
        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = True

    def teardown_method(self):
        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = False

    @pytest.mark.asyncio
    @required_imports
    async def test_execute_iteration_returns_iteration_result(self, import_automation_workflow, task):
        task.content = json.dumps({"params": {"ACTIONS": "trade", "EXCHANGE_FROM": "binance",
            "ORDER_SYMBOL": "ETH/BTC", "ORDER_AMOUNT": 1, "ORDER_TYPE": "market",
            "ORDER_SIDE": "BUY", "SIMULATED_PORTFOLIO": {"BTC": 1}}})
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(include_default_values=False)

        action = octobot_flow.entities.ConfiguredActionDetails(
            id="action_1",
            action="trade",
        )

        mock_result = octobot_flow_client.OctoBotActionsJobResult(
            processed_actions=[action],
            next_actions_description=None,
            actions_dag=None,
            should_stop=False,
        )
        mock_octobot_actions_job_class, _ = _octobot_actions_job_mock_class(
            run_on_result=lambda result_ref: _apply_octobot_actions_job_result_template(result_ref, mock_result),
        )

        with mock.patch.object(
            octobot_flow_client,
            "OctoBotActionsJob",
            mock_octobot_actions_job_class,
        ):
            result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_iteration(inputs, None)

        assert "progress_status" in result
        assert "next_iteration_description" in result
        parsed_progress_status = params.ProgressStatus.model_validate(result["progress_status"])
        assert parsed_progress_status.latest_step == "trade"
        assert parsed_progress_status.error is None
        assert parsed_progress_status.should_stop is False

    @pytest.mark.asyncio
    async def test_execute_iteration_invalid_task_type_raises_workflow_input_error(self, import_automation_workflow, task):
        task.type = "invalid_type"
        task.content = "{}"
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(include_default_values=False)

        with mock.patch.object(task_context, "encrypted_task", mock.MagicMock()) as mock_encrypted:
            mock_encrypted.return_value.__enter__ = mock.Mock(return_value=None)
            mock_encrypted.return_value.__exit__ = mock.Mock(return_value=None)
            with pytest.raises(errors.WorkflowInputError, match="Invalid task type"):
                await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_iteration(inputs, None)

    @pytest.mark.asyncio
    @required_imports
    async def test_execute_iteration_execution_error_sets_progress_error(self, import_automation_workflow, task):
        task.content = json.dumps({"params": {"ACTIONS": "trade", "EXCHANGE_FROM": "binance",
            "ORDER_SYMBOL": "ETH/BTC", "ORDER_AMOUNT": 1, "ORDER_TYPE": "market",
            "ORDER_SIDE": "BUY", "SIMULATED_PORTFOLIO": {"BTC": 1}}})
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(include_default_values=False)

        action = octobot_flow.entities.ConfiguredActionDetails(
            id="action_1",
            action="trade",
            error_status="some_error",
        )
        template_result = octobot_flow_client.OctoBotActionsJobResult(processed_actions=[action])
        mock_octobot_actions_job_class, _ = _octobot_actions_job_mock_class(
            run_on_result=lambda result_ref: _apply_octobot_actions_job_result_template(result_ref, template_result),
        )

        with mock.patch.object(
            octobot_flow_client,
            "OctoBotActionsJob",
            mock_octobot_actions_job_class,
        ):
            result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_iteration(inputs, None)

        parsed_progress_status = params.ProgressStatus.model_validate(result["progress_status"])
        assert parsed_progress_status.error == "some_error"

    @pytest.mark.asyncio
    @required_imports
    async def test_execute_iteration_missing_trading_signal_sets_no_trading_signal_error(
        self, import_automation_workflow, task
    ):
        task.content = json.dumps({"params": {"ACTIONS": "trade", "EXCHANGE_FROM": "binance",
            "ORDER_SYMBOL": "ETH/BTC", "ORDER_AMOUNT": 1, "ORDER_TYPE": "market",
            "ORDER_SIDE": "BUY", "SIMULATED_PORTFOLIO": {"BTC": 1}}})
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(include_default_values=False)
        error_message = "No trading signal available for strategy 9192736c-test"
        mock_octobot_actions_job_class, _ = _octobot_actions_job_mock_class(
            run_side_effect=octobot_flow.errors.CommunityTradingSignalError(error_message),
        )

        with mock.patch.object(
            octobot_flow_client,
            "OctoBotActionsJob",
            mock_octobot_actions_job_class,
        ):
            result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_iteration(
                inputs, None
            )

        parsed_progress_status = params.ProgressStatus.model_validate(result["progress_status"])
        assert parsed_progress_status.error == octobot_flow.enums.ActionErrorStatus.NO_TRADING_SIGNAL.value
        assert parsed_progress_status.error_message == error_message

    @pytest.mark.asyncio
    @required_imports
    async def test_execute_iteration_logs_and_reraises_when_octobot_actions_job_fails(
        self, import_automation_workflow, task
    ):
        task.content = json.dumps({"params": {"ACTIONS": "trade", "EXCHANGE_FROM": "binance",
            "ORDER_SYMBOL": "ETH/BTC", "ORDER_AMOUNT": 1, "ORDER_TYPE": "market",
            "ORDER_SIDE": "BUY", "SIMULATED_PORTFOLIO": {"BTC": 1}}})
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(include_default_values=False)
        run_error = RuntimeError("automation failed")
        mock_octobot_actions_job_class, _ = _octobot_actions_job_mock_class(
            run_side_effect=run_error,
        )
        mock_logger = mock.Mock()
        automation_workflow = octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow

        with mock.patch.object(
            octobot_flow_client,
            "OctoBotActionsJob",
            mock_octobot_actions_job_class,
        ), mock.patch.object(
            automation_workflow,
            "get_logger",
            return_value=mock_logger,
        ):
            with pytest.raises(RuntimeError, match="automation failed"):
                await automation_workflow.execute_iteration(inputs, None)

        mock_logger.exception.assert_called_once_with(
            run_error,
            True,
            f"Error while running automation job: {run_error}",
        )

    @pytest.mark.asyncio
    @required_imports
    async def test_execute_iteration_authentication_error_sets_postponed_iteration(
        self, import_automation_workflow, task
    ):
        task_content = json.dumps({"params": {"ACTIONS": "trade", "EXCHANGE_FROM": "binance",
            "ORDER_SYMBOL": "ETH/BTC", "ORDER_AMOUNT": 1, "ORDER_TYPE": "market",
            "ORDER_SIDE": "BUY", "SIMULATED_PORTFOLIO": {"BTC": 1}}})
        task.content = task_content
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(include_default_values=False)
        authentication_error_message = "Invalid API credentials"
        mock_octobot_actions_job_class, _ = _octobot_actions_job_mock_class(
            run_side_effect=octobot_trading_errors.AuthenticationError(authentication_error_message),
        )
        fixed_now = 1000.0

        with mock.patch.object(
            octobot_flow_client,
            "OctoBotActionsJob",
            mock_octobot_actions_job_class,
        ), mock.patch(
            "octobot_node.scheduler.workflows.automation_workflow.time.time",
            return_value=fixed_now,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.accounts_trading_protocol,
            "update_account_trading",
        ) as update_account_trading_mock:
            result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_iteration(
                inputs, None
            )

        update_account_trading_mock.assert_not_called()
        parsed_progress_status = params.ProgressStatus.model_validate(result["progress_status"])
        assert parsed_progress_status.error == octobot_flow.enums.ActionErrorStatus.AUTHENTICATION_ERROR.value
        assert parsed_progress_status.error_message == authentication_error_message
        assert parsed_progress_status.postponed_iteration is True
        assert parsed_progress_status.next_step_at == (
            fixed_now + octobot_node.constants.INVALID_AUTHENTICATION_RETRY_DELAY_SECONDS
        )
        assert result["has_next_actions"] is True
        assert result["next_iteration_description"] == task_content

    @pytest.mark.asyncio
    @required_imports
    async def test_execute_iteration_passes_trading_signals_to_octobot_actions_job(
        self, import_automation_workflow, task
    ):
        task.content = json.dumps({"params": {"ACTIONS": "trade", "EXCHANGE_FROM": "binance",
            "ORDER_SYMBOL": "ETH/BTC", "ORDER_AMOUNT": 1, "ORDER_TYPE": "market",
            "ORDER_SIDE": "BUY", "SIMULATED_PORTFOLIO": {"BTC": 1}}})
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(include_default_values=False)

        signal = octobot_flow.entities.TradingSignal(
            account=protocol_models.CopiedAccount(
                version=copy_constants.COPIED_ACCOUNT_VERSION,
                updated_at=time.time(),
                copied_assets=[],
            ),
            strategy_id="test-strategy-id",
        )
        signal_dict = signal.to_dict(include_default_values=False)
        actions_update = _trading_signal_update_envelope([signal_dict])

        action = octobot_flow.entities.ConfiguredActionDetails(id="action_1", action="trade")
        mock_result = octobot_flow_client.OctoBotActionsJobResult(
            processed_actions=[action],
            next_actions_description=None,
            actions_dag=None,
            should_stop=False,
        )
        mock_octobot_actions_job_class, _ = _octobot_actions_job_mock_class(
            run_on_result=lambda result_ref: _apply_octobot_actions_job_result_template(result_ref, mock_result),
        )

        with mock.patch.object(task_context, "encrypted_task", mock.MagicMock()) as mock_encrypted:
            mock_encrypted.return_value.__enter__ = mock.Mock(return_value=None)
            mock_encrypted.return_value.__exit__ = mock.Mock(return_value=None)
            with mock.patch.object(
                octobot_flow_client,
                "OctoBotActionsJob",
                mock_octobot_actions_job_class,
            ) as mock_job_factory:
                await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_iteration(
                    inputs, actions_update
                )

        assert mock_job_factory.call_args[0][2] == [signal_dict]

    @pytest.mark.asyncio
    @required_imports
    async def test_execute_iteration_persists_open_orders_to_account_trading(
        self, import_automation_workflow, task
    ):
        import octobot_trading.enums as trading_enums

        task.user_id = "0xwallet-trading-sync"
        task.content = json.dumps({"params": {"ACTIONS": "trade", "EXCHANGE_FROM": "binance",
            "ORDER_SYMBOL": "ETH/BTC", "ORDER_AMOUNT": 1, "ORDER_TYPE": "market",
            "ORDER_SIDE": "BUY", "SIMULATED_PORTFOLIO": {"BTC": 1}}})
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(include_default_values=False)
        order_columns = trading_enums.ExchangeConstantsOrderColumns
        open_order = {
            order_columns.EXCHANGE_ID.value: "open-order-1",
            order_columns.SYMBOL.value: "BTC/USDT",
        }
        missing_order = {
            order_columns.EXCHANGE_ID.value: "missing-order-1",
            order_columns.SYMBOL.value: "ETH/USDT",
        }
        elements = octobot_flow.entities.ExchangeAccountElements()
        elements.orders.open_orders = [open_order]
        elements.orders.missing_orders = [missing_order]
        exchange_details = octobot_flow.entities.ExchangeAccountDetails()
        exchange_details.exchange_details.exchange_account_id = "acc-sync-1"
        automation_state = octobot_flow.entities.AutomationState(
            automation=octobot_flow.entities.AutomationDetails(
                metadata=octobot_flow.entities.AutomationMetadata(automation_id="automation_1"),
            ),
            exchange_account_details=exchange_details,
        )
        automation_state.automation.exchange_account_elements = elements
        next_actions_description = octobot_flow_client.OctoBotActionsJobDescription(
            state=automation_state.to_dict(include_default_values=False),
        )
        action = octobot_flow.entities.ConfiguredActionDetails(id="action_1", action="trade")
        mock_result = octobot_flow_client.OctoBotActionsJobResult(
            processed_actions=[action],
            next_actions_description=next_actions_description,
            has_next_actions=True,
            actions_dag=None,
            should_stop=False,
        )
        mock_octobot_actions_job_class, _ = _octobot_actions_job_mock_class(
            run_on_result=lambda result_ref: _apply_octobot_actions_job_result_template(result_ref, mock_result),
        )

        with mock.patch.object(
            octobot_flow_client,
            "OctoBotActionsJob",
            mock_octobot_actions_job_class,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.accounts_trading_protocol,
            "update_account_trading",
        ) as update_account_trading_mock:
            await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_iteration(
                inputs, None
            )

        update_account_trading_mock.assert_called_once_with(
            task.user_id,
            "acc-sync-1",
            [open_order],
            [],
            [],
        )

    @pytest.mark.asyncio
    @required_imports
    async def test_execute_iteration_continues_when_trading_persistence_wallet_missing(
        self, import_automation_workflow, task
    ):
        import octobot.community.wallet_backend.errors as wallet_backend_errors_module
        import octobot_trading.enums as trading_enums

        task.user_id = "0xwallet-trading-sync"
        task.content = json.dumps({"params": {"ACTIONS": "trade", "EXCHANGE_FROM": "binance",
            "ORDER_SYMBOL": "ETH/BTC", "ORDER_AMOUNT": 1, "ORDER_TYPE": "market",
            "ORDER_SIDE": "BUY", "SIMULATED_PORTFOLIO": {"BTC": 1}}})
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(include_default_values=False)
        order_columns = trading_enums.ExchangeConstantsOrderColumns
        open_order = {
            order_columns.EXCHANGE_ID.value: "open-order-1",
            order_columns.SYMBOL.value: "BTC/USDT",
        }
        elements = octobot_flow.entities.ExchangeAccountElements()
        elements.orders.open_orders = [open_order]
        exchange_details = octobot_flow.entities.ExchangeAccountDetails()
        exchange_details.exchange_details.exchange_account_id = "acc-sync-1"
        automation_state = octobot_flow.entities.AutomationState(
            automation=octobot_flow.entities.AutomationDetails(
                metadata=octobot_flow.entities.AutomationMetadata(automation_id="automation_1"),
            ),
            exchange_account_details=exchange_details,
        )
        automation_state.automation.exchange_account_elements = elements
        next_actions_description = octobot_flow_client.OctoBotActionsJobDescription(
            state=automation_state.to_dict(include_default_values=False),
        )
        action = octobot_flow.entities.ConfiguredActionDetails(id="action_1", action="trade")
        mock_result = octobot_flow_client.OctoBotActionsJobResult(
            processed_actions=[action],
            next_actions_description=next_actions_description,
            has_next_actions=False,
            actions_dag=None,
            should_stop=False,
        )
        mock_octobot_actions_job_class, _ = _octobot_actions_job_mock_class(
            run_on_result=lambda result_ref: _apply_octobot_actions_job_result_template(result_ref, mock_result),
        )

        with mock.patch.object(
            octobot_flow_client,
            "OctoBotActionsJob",
            mock_octobot_actions_job_class,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.accounts_trading_protocol,
            "update_account_trading",
            side_effect=wallet_backend_errors_module.WalletNotFoundError("Wallet not found"),
        ):
            result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_iteration(
                inputs, None
            )

        parsed_progress_status = params.ProgressStatus.model_validate(result["progress_status"])
        assert parsed_progress_status.error is None


class TestExecuteAutomationPostponedIteration:
    @pytest.mark.asyncio
    @required_imports
    async def test_execute_automation_reschedules_on_postponed_iteration(
        self, temp_dbos_scheduler, import_automation_workflow, parsed_inputs
    ):
        postponed_iteration_result = params.AutomationWorkflowIterationResult(
            progress_status=params.ProgressStatus(
                latest_step="no action executed",
                next_step_at=time.time() + octobot_node.constants.INVALID_AUTHENTICATION_RETRY_DELAY_SECONDS,
                error=octobot_flow.enums.ActionErrorStatus.AUTHENTICATION_ERROR.value,
                error_message="Invalid API credentials",
                postponed_iteration=True,
                should_stop=False,
            ),
            next_iteration_description='{"state": {"automation": {}}}',
            has_next_actions=True,
        )
        inputs = parsed_inputs.to_dict(include_default_values=False)
        mock_wait = mock.AsyncMock(return_value=None)
        mock_iteration = mock.AsyncMock(
            return_value=postponed_iteration_result.to_dict(include_default_values=False)
        )
        mock_should_continue = mock.Mock(return_value=False)
        mock_process = mock.AsyncMock(return_value=(True, postponed_iteration_result))

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_actions_update",
            mock_wait,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "execute_iteration",
            mock_iteration,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_should_continue_workflow",
            mock_should_continue,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_process_pending_priority_actions_and_reschedule",
            mock_process,
        ):
            handle = await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation,
                inputs=inputs,
            )
            assert await handle.get_result() is None

        mock_should_continue.assert_not_called()
        mock_process.assert_awaited_once_with(parsed_inputs, postponed_iteration_result)


class TestWaitAndTriggerOnActionsUpdate:
    @pytest.mark.asyncio
    async def test_wait_and_trigger_returns_empty_when_no_actions(self, import_automation_workflow, parsed_inputs):
        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.SCHEDULER.INSTANCE,
            "recv_async",
            mock.AsyncMock(return_value=[]),
        ):
            result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._wait_and_trigger_on_actions_update(
                parsed_inputs, 0
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_wait_and_trigger_returns_envelopes_when_received(self, import_automation_workflow, parsed_inputs):
        envelope = _user_actions_update_envelope([{"action": "stop"}])
        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.SCHEDULER.INSTANCE,
            "recv_async",
            mock.AsyncMock(return_value=envelope),
        ):
            result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._wait_and_trigger_on_actions_update(
                parsed_inputs, 0
            )
        assert result == envelope


class TestProcessPendingPriorityActionsAndReschedule:
    @pytest.mark.asyncio
    async def test_process_pending_returns_false_when_no_next_iteration(self, import_automation_workflow, parsed_inputs, iteration_result):
        iteration_result.has_next_actions = False
        should_continue, updated_result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._process_pending_priority_actions_and_reschedule(
            parsed_inputs, iteration_result
        )
        assert should_continue is False
        assert updated_result is iteration_result

    @pytest.mark.asyncio
    async def test_process_pending_schedules_next_when_no_priority_actions(
        self, import_automation_workflow, parsed_inputs, iteration_result
    ):
        mock_wait = mock.AsyncMock(return_value=None)
        mock_schedule = mock.AsyncMock()

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_actions_update",
            mock_wait,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_schedule_next_iteration",
            mock_schedule,
        ):
            should_continue, _ = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._process_pending_priority_actions_and_reschedule(
                parsed_inputs, iteration_result
            )
        assert should_continue is True
        mock_wait.assert_awaited_once_with(parsed_inputs, 0)
        mock_schedule.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_pending_returns_false_when_should_stop(self, import_automation_workflow, parsed_inputs, iteration_result):
        iteration_result.progress_status.should_stop = True
        mock_wait = mock.AsyncMock(return_value=None)

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_actions_update",
            mock_wait,
        ):
            should_continue, _ = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._process_pending_priority_actions_and_reschedule(
                parsed_inputs, iteration_result
            )
        assert should_continue is True

    @pytest.mark.asyncio
    async def test_process_pending_raises_when_no_next_iteration_after_priority_actions(
        self, import_automation_workflow, parsed_inputs, iteration_result
    ):
        result_without_next = params.AutomationWorkflowIterationResult(
            progress_status=params.ProgressStatus(
                latest_step="done",
                next_step=None,
                next_step_at=None,
                remaining_steps=0,
                error=None,
                should_stop=False,
            ),
            next_iteration_description=json.dumps({"state": {"automation": {}}}),
            has_next_actions=False,
        )
        mock_wait = mock.AsyncMock(
            side_effect=[
                _user_actions_update_envelope([{"action": "stop"}]),
                None,
            ]
        )
        mock_iteration = mock.AsyncMock(
            return_value=result_without_next.to_dict(include_default_values=False)
        )

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_actions_update",
            mock_wait,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "execute_iteration",
            mock_iteration,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_should_continue_workflow",
            mock.Mock(return_value=True),
        ):
            with pytest.raises(
                errors.WorkflowPriorityActionExecutionError,
                match="no next iteration description after processing priority actions",
            ):
                await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._process_pending_priority_actions_and_reschedule(
                    parsed_inputs, iteration_result
                )

    @pytest.mark.asyncio
    async def test_process_pending_with_priority_actions_schedules_next_when_iteration_has_next(
        self, import_automation_workflow, parsed_inputs, iteration_result
    ):
        result_with_next = params.AutomationWorkflowIterationResult(
            progress_status=params.ProgressStatus(
                latest_step="step_1",
                next_step="step_2",
                next_step_at=0.0,
                remaining_steps=1,
                error=None,
                should_stop=False,
            ),
            next_iteration_description='{"state": {"automation": {}}}',
            has_next_actions=True,
        )
        mock_wait = mock.AsyncMock(
            side_effect=[
                _user_actions_update_envelope([{"action": "stop"}]),
                None,
            ]
        )
        mock_iteration = mock.AsyncMock(
            return_value=result_with_next.to_dict(include_default_values=False)
        )
        mock_schedule = mock.AsyncMock()

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_actions_update",
            mock_wait,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "execute_iteration",
            mock_iteration,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_should_continue_workflow",
            mock.Mock(return_value=True),
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_schedule_next_iteration",
            mock_schedule,
        ):
            should_continue, _ = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._process_pending_priority_actions_and_reschedule(
                parsed_inputs, iteration_result
            )

        assert should_continue is True
        mock_wait.assert_awaited()
        mock_iteration.assert_called_once()
        mock_schedule.assert_called_once()


class TestScheduleNextIteration:
    @pytest.mark.asyncio
    async def test_schedule_next_iteration_enqueues_workflow(self, import_automation_workflow, parsed_inputs, iteration_result):
        mock_enqueue = mock.AsyncMock()
        set_workflow_id_context = contextlib.nullcontext()
        mock_set_workflow_id = mock.Mock(return_value=set_workflow_id_context)
        next_desc = iteration_result.next_iteration_description
        parent_workflow_id = "12345678-1234-1234-1234-123456789012"

        with mock.patch.object(dbos.DBOS, "workflow_id", parent_workflow_id), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.SCHEDULER,
            "SetWorkflowID",
            mock_set_workflow_id,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.SCHEDULER.AUTOMATION_WORKFLOW_QUEUE,
            "enqueue_async",
            mock_enqueue,
        ):
            await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._schedule_next_iteration(
                parsed_inputs, next_desc, iteration_result.progress_status
            )
        mock_enqueue.assert_called_once()
        mock_set_workflow_id.assert_called_once_with(f"{parent_workflow_id}_1")
        call_args = mock_enqueue.call_args
        assert call_args[0][0] == octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation
        assert "inputs" in call_args[1]

    @pytest.mark.asyncio
    async def test_schedule_next_iteration_increments_existing_child_workflow_id(
        self, import_automation_workflow, parsed_inputs, iteration_result
    ):
        mock_enqueue = mock.AsyncMock()
        set_workflow_id_context = contextlib.nullcontext()
        mock_set_workflow_id = mock.Mock(return_value=set_workflow_id_context)
        next_desc = iteration_result.next_iteration_description
        current_workflow_id = "12345678-1234-1234-1234-123456789012_2"

        with mock.patch.object(dbos.DBOS, "workflow_id", current_workflow_id), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.SCHEDULER,
            "SetWorkflowID",
            mock_set_workflow_id,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.SCHEDULER.AUTOMATION_WORKFLOW_QUEUE,
            "enqueue_async",
            mock_enqueue,
        ):
            await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._schedule_next_iteration(
                parsed_inputs, next_desc, iteration_result.progress_status
            )

        mock_set_workflow_id.assert_called_once_with("12345678-1234-1234-1234-123456789012_3")
        mock_enqueue.assert_called_once()


class TestCreateNextIterationInputs:
    def test_create_next_iteration_inputs_returns_correct_dict(self, import_automation_workflow, task):
        parsed_inputs = params.AutomationWorkflowInputs(task=task, execution_time=0)
        next_iteration_description = '{"state": {}}'
        next_execution_time = 123.0

        result = octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._create_next_iteration_inputs(
            parsed_inputs, next_iteration_description, next_execution_time
        )
        assert "task" in result
        parsed_result = params.AutomationWorkflowInputs.from_dict(result)
        task = parsed_result.task
        content = task.get("content") if isinstance(task, dict) else task.content
        assert content == next_iteration_description
        assert parsed_result.execution_time == 123.0

    def test_create_next_iteration_inputs_uses_zero_when_execution_time_none(self, import_automation_workflow, task): #todo
        parsed_inputs = params.AutomationWorkflowInputs(task=task, execution_time=0)
        result = octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._create_next_iteration_inputs(
            parsed_inputs, "{}", None
        )
        result = params.AutomationWorkflowInputs.from_dict(result)
        assert result.execution_time == 0


class TestShouldContinueWorkflow:
    def test_should_continue_returns_stop_on_error_when_error(self, import_automation_workflow, parsed_inputs):
        progress = params.ProgressStatus(error="some_error", should_stop=False)
        assert octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._should_continue_workflow(
            parsed_inputs, progress, True
        ) is True
        assert octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._should_continue_workflow(
            parsed_inputs, progress, False
        ) is False

    def test_should_continue_returns_false_when_should_stop(self, import_automation_workflow, parsed_inputs):
        progress = params.ProgressStatus(error=None, should_stop=True)
        assert octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._should_continue_workflow(
            parsed_inputs, progress, True
        ) is False
        assert octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._should_continue_workflow(
            parsed_inputs, progress, False
        ) is False

    def test_should_continue_returns_true_by_no_reason_to_stop(self, import_automation_workflow, parsed_inputs):
        progress = params.ProgressStatus(error=None, should_stop=False)
        assert octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._should_continue_workflow(
            parsed_inputs, progress, True
        ) is True
        assert octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._should_continue_workflow(
            parsed_inputs, progress, False
        ) is True


class TestGetActionsSummary:
    def test_get_actions_summary_empty_returns_empty_string(self, import_automation_workflow):
        assert octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._get_actions_summary([]) == ""

    @pytest.mark.asyncio
    @required_imports
    async def test_get_actions_summary_joins_action_summaries(self, import_automation_workflow):
        action1 = octobot_flow.entities.ConfiguredActionDetails(id="action_1", action="action_1")
        action2 = octobot_flow.entities.DSLScriptActionDetails(id="action_2", dsl_script="action_2('plop')")
        result = octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._get_actions_summary([action1, action2])
        assert result == "action_1, action_2('plop')"
        
        # with minimal=True, only the first operator name is returned
        result = octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._get_actions_summary([action1, action2], minimal=True)
        assert result == "action_1, action_2"

    def test_get_actions_summary_minimal_calls_get_summary_with_minimal(self, import_automation_workflow):
        mock_action = mock.Mock()
        mock_action.get_summary = mock.Mock(return_value="sum")
        octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._get_actions_summary([mock_action], minimal=True)
        mock_action.get_summary.assert_called_once_with(minimal=True)


class TestGetLogger:
    def test_get_logger_uses_task_name(self, import_automation_workflow, parsed_inputs):
        with mock.patch("octobot_commons.logging.get_logger", mock.Mock()) as mock_get_logger:
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.get_logger(parsed_inputs)
        mock_get_logger.assert_called_once_with("test_task")

    def test_get_logger_uses_class_name_when_task_name_none(self, import_automation_workflow):
        task = octobot_node.models.Task(name=None, content="{}")
        parsed_inputs = params.AutomationWorkflowInputs(task=task, execution_time=0)
        with mock.patch("octobot_commons.logging.get_logger", mock.Mock()) as mock_get_logger:
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.get_logger(parsed_inputs)
        mock_get_logger.assert_called_once_with(octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.__name__)


class TestExecuteAutomationIntegration:
    def setup_method(self):
        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = True
        self._no_encrypt_rsa = mock.patch.object(octobot_node.config.settings, "TASKS_SERVER_RSA_PRIVATE_KEY", None)
        self._no_encrypt_ecdsa = mock.patch.object(octobot_node.config.settings, "TASKS_SERVER_ECDSA_PRIVATE_KEY", None)
        self._no_encrypt_rsa.start()
        self._no_encrypt_ecdsa.start()

    def teardown_method(self):
        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = False
        self._no_encrypt_rsa.stop()
        self._no_encrypt_ecdsa.stop()

    @pytest.mark.asyncio
    @required_imports
    async def test_execute_automation_full_workflow_three_iterations(
        self,
        import_automation_workflow,
        temp_dbos_scheduler,
    ):
        init_action = {
            "id": "action_init",
            "action": octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value,
            "config": {
                "automation": {"metadata": {"automation_id": "automation_1"}},
                "exchange_account_elements": {
                    "portfolio": {
                        "content": {
                            "ETH": {"total": 1, "available": 1},
                        },
                    },
                },
            },
        }
        dsl_action_1 = {
            "id": "action_dsl_1",
            "dsl_script": "1 if True else 2",
            "dependencies": [{"action_id": "action_init"}],
        }
        dsl_action_2 = {
            "id": "action_dsl_2",
            "dsl_script": "1 if True else 2",
            "dependencies": [{"action_id": "action_dsl_1"}],
        }
        all_actions = [init_action, dsl_action_1, dsl_action_2]
        state_dict = _automation_state_dict(all_actions)
        state_dict["automation"]["exchange_account_elements"] = {
            "portfolio": {"content": {"ETH": {"total": 1, "available": 1}}},
        }
        state_dict["automation"]["execution"] = {
            "previous_execution": {
                "trigger_time": time.time() - 600,
                "trigger_reason": "scheduled",
                "strategy_execution_time": time.time() - 590,
            },
            "current_execution": {"trigger_reason": "scheduled"},
        }
        task_content = json.dumps({"state": state_dict})
        task = octobot_node.models.Task(
            name="test_automation",
            content=task_content,
            type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
        )
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(
            include_default_values=False
        )
        inputs["task"] = task.model_dump(exclude_defaults=True)

        recv_path = "octobot_node.scheduler.workflows.automation_workflow.SCHEDULER.INSTANCE.recv_async"
        with mock.patch(recv_path, mock.AsyncMock(return_value=[])):
            await temp_dbos_scheduler.AUTOMATION_WORKFLOW_QUEUE.enqueue_async(
                octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation,
                inputs=inputs,
            )

        max_wait = 30
        poll_interval = 0.5
        elapsed = 0
        while elapsed < max_wait:
            workflows = await temp_dbos_scheduler.INSTANCE.list_workflows_async()
            pending = [w for w in workflows if w.status in (
                dbos.WorkflowStatusString.PENDING.value, dbos.WorkflowStatusString.ENQUEUED.value
            )]
            if not pending and len(workflows) >= 3:
                break
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        assert len(workflows) >= 3, f"Expected at least 3 workflows, got {len(workflows)}"
        assert not pending, f"Expected no pending workflows, got {pending}"
        all_workflow_ids = [workflow_status.workflow_id for workflow_status in workflows]
        assert len(all_workflow_ids) == len(workflows) == 3
        print(f'all_workflow_ids: {all_workflow_ids}')
        parent_workflow_id = all_workflow_ids[0][:octobot_node.constants.PARENT_WORKFLOW_ID_LENGTH]
        child_suffixes: list[int] = []
        for workflow_id in all_workflow_ids:
            assert workflow_id.startswith(parent_workflow_id)
            suffix = workflow_id[octobot_node.constants.PARENT_WORKFLOW_ID_LENGTH:]
            if not suffix:
                continue
            assert suffix.startswith("_"), f"Invalid child suffix format: {workflow_id}"
            child_suffixes.append(int(suffix[1:]))
        assert child_suffixes
        assert sorted(child_suffixes) == list(range(1, len(child_suffixes) + 1))

        
        completed = [w for w in workflows if w.status == dbos.WorkflowStatusString.SUCCESS.value]
        assert len(completed) >= 3, f"Expected at least 3 completed workflows, got {len(completed)}"

        workflow_outputs: list[typing.Optional[str]] = []
        for wf_status in completed:
            handle = await temp_dbos_scheduler.INSTANCE.retrieve_workflow_async(wf_status.workflow_id)
            result = await handle.get_result()
            workflow_outputs.append(result)
            db_status = await handle.get_status()
            assert db_status.status == dbos.WorkflowStatusString.SUCCESS.value
            assert db_status.output == result
        non_none_outputs = [output for output in workflow_outputs if output is not None]
        assert len(non_none_outputs) == 1, (
            f"Expected exactly one completed workflow to expose a final state payload; "
            f"got {len(non_none_outputs)} non-null outputs among {workflow_outputs}"
        )
        parsed_final = _parse_automation_workflow_output(non_none_outputs[0])
        assert parsed_final.error is None
        assert isinstance(parsed_final.state, str)
        state_tree = _job_description_dict_from_output(parsed_final)
        automation_state = state_tree["state"]["automation"]
        assert automation_state["metadata"]["automation_id"] == "automation_1"
        assert "actions_dag" in automation_state
        assert "exchange_account_elements" in automation_state

    @pytest.mark.asyncio
    @required_imports
    async def test_execute_automation_priority_stop_action_stops_workflow(
        self,
        import_automation_workflow,
        temp_dbos_scheduler,
    ):
        """
        After a normal DAG iteration with ``has_next_actions`` set, ``recv_async`` delivers a stop
        priority action; the follow-up iteration must set ``should_stop`` and complete with that
        state as workflow output (no child workflow enqueued).
        """
        task = octobot_node.models.Task(
            name="priority_stop_integration",
            content="{}",
            type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
        )
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(
            include_default_values=False
        )
        inputs["task"] = task.model_dump(exclude_defaults=True)

        action = octobot_flow.entities.ConfiguredActionDetails(id="action_dsl", action="trade")
        dag_state = {
            "automation": {
                "metadata": {"automation_id": "priority_stop_auto"},
                "execution": {"current_execution": {"scheduled_to": 0.0}},
            }
        }
        stop_state = {"automation": {"stopped": True, "by_priority_action": True}}
        dag_iteration_result = octobot_flow_client.OctoBotActionsJobResult(
            processed_actions=[action],
            next_actions_description=octobot_flow_client.OctoBotActionsJobDescription(state=dag_state),
            has_next_actions=True,
            actions_dag=None,
            should_stop=False,
        )
        stop_iteration_result = octobot_flow_client.OctoBotActionsJobResult(
            processed_actions=[action],
            next_actions_description=octobot_flow_client.OctoBotActionsJobDescription(state=stop_state),
            has_next_actions=False,
            actions_dag=None,
            should_stop=True,
        )
        iteration_templates = [dag_iteration_result, stop_iteration_result]
        iteration_index = [0]

        def run_on_iteration_result(result_ref: octobot_flow_client.OctoBotActionsJobResult) -> None:
            _apply_octobot_actions_job_result_template(result_ref, iteration_templates[iteration_index[0]])
            iteration_index[0] += 1

        mock_octobot_actions_job_class, _ = _octobot_actions_job_mock_class(run_on_result=run_on_iteration_result)
        stop_envelope = _user_actions_update_envelope([{"action": "stop"}])
        mock_recv = mock.AsyncMock(side_effect=[[], stop_envelope])

        recv_path = "octobot_node.scheduler.workflows.automation_workflow.SCHEDULER.INSTANCE.recv_async"
        with mock.patch(recv_path, mock_recv), mock.patch(
            "asyncio.sleep", mock.AsyncMock()
        ), mock.patch.object(
            octobot_flow_client,
            "OctoBotActionsJob",
            mock_octobot_actions_job_class,
        ) as mock_job_factory:
            handle = await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation,
                inputs=inputs,
            )
            workflow_result = await handle.get_result()
            expected_state_str = json.dumps(
                stop_iteration_result.next_actions_description.to_dict(include_default_values=False)
            )
            assert workflow_result == _expected_automation_workflow_envelope_json(expected_state_str)
            assert iteration_index[0] == 2
            assert mock_recv.await_count == 2
            stop_user_actions = mock_job_factory.call_args_list[1][0][1]
            assert stop_user_actions == [{"action": "stop"}]
            parsed_output = _parse_automation_workflow_output(workflow_result)
            job_description = _job_description_dict_from_output(parsed_output)
            assert job_description["state"]["automation"]["stopped"] is True # the state of the stop action is returned
            assert job_description["state"]["automation"]["by_priority_action"] is True

        workflows = await temp_dbos_scheduler.INSTANCE.list_workflows_async()
        assert len(workflows) == 1, "Stop must not enqueue a follow-up automation workflow"

    @pytest.mark.asyncio
    @required_imports
    async def test_cancel_workflow_async_cancels_running_automation_workflow(
        self,
        import_automation_workflow,
        temp_dbos_scheduler,
    ):
        task = octobot_node.models.Task(
            name="cancel_running_workflow_test",
            content="{}",
            type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
        )
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(
            include_default_values=False
        )
        inputs["task"] = task.model_dump(exclude_defaults=True)
        entered_iteration_event = asyncio.Event()

        async def wait_forever_in_iteration(*args, **kwargs):
            entered_iteration_event.set()
            await asyncio.Future()

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "execute_iteration",
            mock.AsyncMock(side_effect=wait_forever_in_iteration),
        ):
            await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation,
                inputs=inputs,
            )
            await asyncio.wait_for(entered_iteration_event.wait(), timeout=5)
            active_workflows = await temp_dbos_scheduler.INSTANCE.list_workflows_async(
                status=[dbos.WorkflowStatusString.ENQUEUED.value, dbos.WorkflowStatusString.PENDING.value]
            )
            assert len(active_workflows) == 1
            automation_workflow_id = active_workflows[0].workflow_id
            await temp_dbos_scheduler.INSTANCE.cancel_workflow_async(automation_workflow_id)

            cancelled_status = None
            for _attempt_index in range(10):
                workflow_handle = await temp_dbos_scheduler.INSTANCE.retrieve_workflow_async(automation_workflow_id)
                cancelled_status = await workflow_handle.get_status()
                if cancelled_status.status == dbos.WorkflowStatusString.CANCELLED.value:
                    break
                await asyncio.sleep(0.1)

            assert cancelled_status is not None
            assert cancelled_status.status == dbos.WorkflowStatusString.CANCELLED.value

    @pytest.mark.asyncio
    @required_imports
    async def test_cancel_workflow_async_during_iteration_retries_stops_further_job_attempts(
        self,
        import_automation_workflow,
        temp_dbos_scheduler,
    ):
        """
        DBOS retries the ``execute_iteration`` step when the iteration body raises a retriable error.
        Here ``OctoBotActionsJob.run()`` raises ``RuntimeError`` on the first attempt (retriable per
        ``AutomationWorkflow._should_retry``), so the step retries. After the first retry attempt has
        started, cancelling the workflow must not schedule further runs (no third ``run()`` call despite
        ``AUTOMATION_WORKFLOW_MAX_ITERATION_RETRIES``). Once the workflow is ``CANCELLED``, the blocked
        retry ``run()`` must observe ``CancelledError`` when the pending wait is cancelled (DBOS may defer
        asyncio teardown; cancelling the shared ``Future`` finishes the assertion). No further iteration
        runs after cancellation: ``OctoBotActionsJob.run()`` stays at two awaits (initial failure plus one
        retry); DBOS retries the ``execute_iteration`` step internally without extra workflow-level calls.
        """
        task = octobot_node.models.Task(
            name="cancel_during_retry_test",
            content="{}",
            type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
        )
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(
            include_default_values=False
        )
        inputs["task"] = task.model_dump(exclude_defaults=True)
        first_retry_entered = asyncio.Event()
        retry_run_block_future: dict[str, asyncio.Future | None] = {"f": None}
        blocked_retry_run_got_cancelled_error = [False]
        attempt_number = [0]

        async def fail_once_then_block_until_cancel(*args, **kwargs):
            attempt_number[0] += 1
            if attempt_number[0] == 1:
                raise RuntimeError("simulated retriable iteration failure")
            first_retry_entered.set()
            loop = asyncio.get_running_loop()
            retry_run_block_future["f"] = loop.create_future()
            try:
                await retry_run_block_future["f"]
            except asyncio.CancelledError:
                blocked_retry_run_got_cancelled_error[0] = True
                raise

        mock_octobot_actions_job_class, run_mock = _octobot_actions_job_mock_class(
            run_side_effect=fail_once_then_block_until_cancel,
        )
        recv_path = "octobot_node.scheduler.workflows.automation_workflow.SCHEDULER.INSTANCE.recv_async"
        with mock.patch(recv_path, mock.AsyncMock(return_value=[])), mock.patch.object(
            octobot_flow_client,
            "OctoBotActionsJob",
            mock_octobot_actions_job_class,
        ):
            with mock.patch("asyncio.sleep", mock.AsyncMock()):
                await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                    octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation,
                    inputs=inputs,
                )
                await asyncio.wait_for(first_retry_entered.wait(), timeout=5)
                active_workflows = await temp_dbos_scheduler.INSTANCE.list_workflows_async(
                    status=[dbos.WorkflowStatusString.ENQUEUED.value, dbos.WorkflowStatusString.PENDING.value]
                )
                assert len(active_workflows) == 1
                automation_workflow_id = active_workflows[0].workflow_id
                await temp_dbos_scheduler.INSTANCE.cancel_workflow_async(automation_workflow_id)

                cancelled_status = None
                for _attempt_index in range(10):
                    workflow_handle = await temp_dbos_scheduler.INSTANCE.retrieve_workflow_async(automation_workflow_id)
                    cancelled_status = await workflow_handle.get_status()
                    if cancelled_status.status == dbos.WorkflowStatusString.CANCELLED.value:
                        break
                    await asyncio.sleep(0.1)

                assert cancelled_status is not None
                assert cancelled_status.status == dbos.WorkflowStatusString.CANCELLED.value

            blocked_future = retry_run_block_future["f"]
            assert blocked_future is not None
            await asyncio.sleep(1)
            if not blocked_retry_run_got_cancelled_error[0] and not blocked_future.done():
                blocked_future.cancel()
            for _yield_index in range(1000):
                if blocked_retry_run_got_cancelled_error[0]:
                    break
                await asyncio.sleep(0)
            assert blocked_retry_run_got_cancelled_error[0], (
                "blocked retry OctoBotActionsJob.run() must observe CancelledError when cancelled"
            )
            assert run_mock.await_count == 2

        await asyncio.sleep(0.2)
        assert run_mock.await_count == 2

    @pytest.mark.asyncio
    @required_imports
    async def test_cancel_workflow_async_during_retry_backoff_sleep_skips_step_retry(
        self,
        import_automation_workflow,
        temp_dbos_scheduler,
    ):
        """
        After a retriable failure, DBOS waits ``interval_seconds * backoff**attempt`` before
        re-invoking the step (via ``asyncio.sleep``). Patch
        ``octobot_node.constants.AUTOMATION_WORKFLOW_RETRY_INTERVAL_SECONDS`` to a long interval,
        cancel the workflow during that wait, and ensure ``OctoBotActionsJob.run()`` is not awaited
        again (no retry execution after cancellation).
        """
        task = octobot_node.models.Task(
            name="cancel_during_retry_backoff_test",
            content="{}",
            type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
        )
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(
            include_default_values=False
        )
        inputs["task"] = task.model_dump(exclude_defaults=True)
        first_attempt_failed = asyncio.Event()
        run_call_counter = [0]

        async def fail_retriable_every_call(*args, **kwargs):
            run_call_counter[0] += 1
            if run_call_counter[0] == 1:
                first_attempt_failed.set()
            raise RuntimeError("simulated retriable iteration failure")

        mock_octobot_actions_job_class, run_mock = _octobot_actions_job_mock_class(
            run_side_effect=fail_retriable_every_call,
        )
        recv_path = "octobot_node.scheduler.workflows.automation_workflow.SCHEDULER.INSTANCE.recv_async"
        long_retry_interval_seconds = 3.0
        with mock.patch(recv_path, mock.AsyncMock(return_value=[])), mock.patch.object(
            octobot_flow_client,
            "OctoBotActionsJob",
            mock_octobot_actions_job_class,
        ), mock.patch.object(
            octobot_node.constants,
            "AUTOMATION_WORKFLOW_RETRY_INTERVAL_SECONDS",
            long_retry_interval_seconds,
        ):
            await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation,
                inputs=inputs,
            )
            await asyncio.wait_for(first_attempt_failed.wait(), timeout=5)
            await asyncio.sleep(0.5)
            active_workflows = await temp_dbos_scheduler.INSTANCE.list_workflows_async(
                status=[dbos.WorkflowStatusString.ENQUEUED.value, dbos.WorkflowStatusString.PENDING.value]
            )
            assert len(active_workflows) == 1
            automation_workflow_id = active_workflows[0].workflow_id
            await temp_dbos_scheduler.INSTANCE.cancel_workflow_async(automation_workflow_id)

            cancelled_status = None
            for _attempt_index in range(30):
                workflow_handle = await temp_dbos_scheduler.INSTANCE.retrieve_workflow_async(automation_workflow_id)
                cancelled_status = await workflow_handle.get_status()
                if cancelled_status.status == dbos.WorkflowStatusString.CANCELLED.value:
                    break
                await asyncio.sleep(0.1)

            assert cancelled_status is not None
            assert cancelled_status.status == dbos.WorkflowStatusString.CANCELLED.value
            assert run_mock.await_count == 1
            assert run_call_counter[0] == 1

        await asyncio.sleep(0.2)
        assert run_mock.await_count == 1
        assert run_call_counter[0] == 1

    @pytest.mark.asyncio
    @required_imports
    async def test_execute_automation_execute_iteration_retries_octobot_actions_job_then_succeeds_and_returns_action_error(
        self,
        import_automation_workflow,
        temp_dbos_scheduler,
    ):
        """
        DBOS execute_iteration is configured with max_attempts=AUTOMATION_WORKFLOW_MAX_ITERATION_RETRIES.
        When OctoBotActionsJob.run() fails on early attempts then succeeds, the step should
        retry and eventually complete without failing the workflow. A processed action may still
        report an error_status; that value is copied to AutomationWorkflowOutput.error on completion.
        """
        max_attempts = octobot_node.constants.AUTOMATION_WORKFLOW_MAX_ITERATION_RETRIES
        task = octobot_node.models.Task(
            name="retry_policy_test",
            content="{}",
            type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
        )
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(
            include_default_values=False
        )
        inputs["task"] = task.model_dump(exclude_defaults=True)

        dag_action_error = octobot_flow.enums.ActionErrorStatus.INVALID_ORDER.value
        action = octobot_flow.entities.ConfiguredActionDetails(
            id="action_1",
            action="trade",
            error_status=dag_action_error,
        )
        success_result = octobot_flow_client.OctoBotActionsJobResult(
            processed_actions=[action],
            next_actions_description=octobot_flow_client.OctoBotActionsJobDescription(state={"automation": {}}),
            has_next_actions=False,
            actions_dag=None,
            should_stop=False,
        )
        latest_result: list[octobot_flow_client.OctoBotActionsJobResult | None] = [None]
        attempt = [0]

        async def run_with_retries_then_apply_success(*args, **kwargs) -> None:
            attempt[0] += 1
            if attempt[0] < max_attempts:
                raise RuntimeError("simulated transient failure")
            assert latest_result[0] is not None
            _apply_octobot_actions_job_result_template(latest_result[0], success_result)

        mock_octobot_actions_job_class, run_mock = _octobot_actions_job_mock_class(
            run_side_effect=run_with_retries_then_apply_success,
            latest_result_ref=latest_result,
        )
        mock_logger = mock.Mock()

        recv_path = "octobot_node.scheduler.workflows.automation_workflow.SCHEDULER.INSTANCE.recv_async"
        with mock.patch(recv_path, mock.AsyncMock(return_value=[])), mock.patch(
            "asyncio.sleep", mock.AsyncMock()
        ), mock.patch.object(
            octobot_flow_client,
            "OctoBotActionsJob",
            mock_octobot_actions_job_class,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "get_logger",
            mock.Mock(return_value=mock_logger),
        ):
            handle = await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation,
                inputs=inputs,
            )
            workflow_result = await handle.get_result()
            expected_inner_state = r'{"state": {"automation": {}}}'
            assert workflow_result == _expected_automation_workflow_envelope_json(
                expected_inner_state,
                error=dag_action_error,
            )
            parsed_output = _parse_automation_workflow_output(workflow_result)
            assert parsed_output.error == dag_action_error
            assert isinstance(parsed_output.state, str)
            job_description = _job_description_dict_from_output(parsed_output)
            assert job_description["state"]["automation"] == {}
            wf_status = await handle.get_status()
            assert wf_status.status == dbos.WorkflowStatusString.SUCCESS.value
            assert wf_status.output == workflow_result
            assert parsed_output == _parse_automation_workflow_output(wf_status.output)

        assert run_mock.await_count == max_attempts
        _assert_iteration_job_errors_logged(
            mock_logger,
            RuntimeError("simulated transient failure"),
            iteration_failure_count=max_attempts - 1,
        )

    @pytest.mark.asyncio
    @required_imports
    async def test_execute_automation_execute_iteration_exhausts_retries_when_octobot_actions_job_always_fails(
        self,
        import_automation_workflow,
        temp_dbos_scheduler,
    ):
        """After AUTOMATION_WORKFLOW_MAX_ITERATION_RETRIES failed OctoBotActionsJob.run() calls, the step must stop retrying."""
        max_attempts = octobot_node.constants.AUTOMATION_WORKFLOW_MAX_ITERATION_RETRIES
        task = octobot_node.models.Task(
            name="retry_exhausted_test",
            content="{}",
            type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
        )
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0).to_dict(
            include_default_values=False
        )
        inputs["task"] = task.model_dump(exclude_defaults=True)

        mock_octobot_actions_job_class, run_mock = _octobot_actions_job_mock_class(
            run_side_effect=RuntimeError("persistent failure")
        )
        mock_logger = mock.Mock()

        recv_path = "octobot_node.scheduler.workflows.automation_workflow.SCHEDULER.INSTANCE.recv_async"
        with mock.patch(recv_path, mock.AsyncMock(return_value=[])), mock.patch(
            "asyncio.sleep", mock.AsyncMock()
        ), mock.patch.object(
            octobot_flow_client,
            "OctoBotActionsJob",
            mock_octobot_actions_job_class,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "get_logger",
            mock.Mock(return_value=mock_logger),
        ):
            handle = await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation,
                inputs=inputs,
            )
            workflow_result = await handle.get_result()
            expected_error_message = _dbos_step_retries_exhausted_error_message(
                "execute_iteration",
                max_attempts,
            )
            assert workflow_result == json.dumps(
                params.AutomationWorkflowOutput(
                    error=octobot_flow.enums.AutomationWorkflowErrorStatus.EXCEPTION_DURING_ITERATION.value,
                    error_message=expected_error_message,
                ).to_dict(include_default_values=False)
            )
            parsed_output = _parse_automation_workflow_output(workflow_result)
            assert parsed_output.state is None
            assert (
                parsed_output.error
                == octobot_flow.enums.AutomationWorkflowErrorStatus.EXCEPTION_DURING_ITERATION.value
            )
            assert parsed_output.error_message == expected_error_message
            wf_status = await handle.get_status()
            assert wf_status.status == dbos.WorkflowStatusString.SUCCESS.value
            assert wf_status.output == workflow_result

        assert run_mock.await_count == max_attempts
        _assert_iteration_job_errors_logged(
            mock_logger,
            RuntimeError("persistent failure"),
            iteration_failure_count=max_attempts,
            expect_workflow_interrupted_log=True,
        )

    @pytest.mark.asyncio
    @required_imports
    async def test_encrypted_task_decrypts_for_octobot_actions_job_and_encrypts_iteration_and_workflow_outputs(
        self,
        import_automation_workflow,
        temp_dbos_scheduler,
    ):
        """
        With node-side encryption keys set:

        - ``execute_iteration`` receives tasks whose ``content`` is ciphertext; ``encrypted_task`` decrypts
          before ``OctoBotActionsJob`` is constructed, so the mock must see plaintext ``task.content``.
        - Iteration outputs expose ``next_iteration_description`` / metadata as encrypted when enabled.
        - ``execute_automation`` returns encrypted ``state`` / ``state_metadata`` when the run stops with
          a next-state payload; rescheduling passes encrypted ``task.content`` / ``content_metadata`` to
        ``enqueue_async``.
        """
        # --- Keys: real RSA/ECDSA material so encrypt_task_content / decrypt_task_content and
        #     encrypted_task use the same crypto path as production (settings.is_node_side_encryption_enabled).
        rsa_private_key, rsa_public_key = octobot_commons.cryptography.generate_rsa_key_pair(2048)
        ecdsa_private_key, ecdsa_public_key = octobot_commons.cryptography.generate_ecdsa_key_pair()

        # Plaintext task.content as stored client-side before upload (what decrypt must reproduce).
        plain_task_content = json.dumps({"params": {"ACTIONS": "trade", "EXCHANGE_FROM": "binance",
            "ORDER_SYMBOL": "ETH/BTC", "ORDER_AMOUNT": 1, "ORDER_TYPE": "market",
            "ORDER_SIDE": "BUY", "SIMULATED_PORTFOLIO": {"BTC": 1}}})

        # Clear derived-key caches so patched settings take effect immediately.
        task_inputs_encryption._server_rsa_public_key_bytes.cache_clear()
        task_inputs_encryption._server_ecdsa_public_key_bytes.cache_clear()

        # Patch all four encryption keys on settings for the duration of each block below.
        encryption_patches = (
            mock.patch.object(
                octobot_node.config.settings, "TASKS_SERVER_RSA_PRIVATE_KEY", rsa_private_key
            ),
            mock.patch.object(
                octobot_node.config.settings, "TASKS_SERVER_ECDSA_PRIVATE_KEY", ecdsa_private_key
            ),
            mock.patch.object(
                octobot_node.config.settings, "TASKS_USER_RSA_PUBLIC_KEY", rsa_public_key
            ),
            mock.patch.object(
                octobot_node.config.settings, "TASKS_USER_ECDSA_PUBLIC_KEY", ecdsa_public_key
            ),
        )

        with encryption_patches[0], encryption_patches[1], encryption_patches[2], encryption_patches[3]:
            assert octobot_node.config.settings.is_node_side_encryption_enabled is True

            # Simulate API/CSV: task content is ciphertext + metadata (inputs remain encrypted at rest).
            encrypted_task_content, task_content_metadata = task_inputs_encryption.encrypt_task_content(
                plain_task_content
            )
            assert encrypted_task_content != plain_task_content

        # OctoBotActionsJob result templates applied by mocks (mutate job.result like real run()).
        next_state_for_stop = {
            "automation": {
                "metadata": {"automation_id": "encryption_integration"},
                "stopped": True,
                "by_encryption_test": True,
            }
        }
        next_state_for_schedule = {
            "automation": {
                "metadata": {"automation_id": "encryption_integration"},
                "execution": {"current_execution": {"scheduled_to": 0.0}},
            }
        }

        stop_result_template = octobot_flow_client.OctoBotActionsJobResult(
            processed_actions=[],
            next_actions_description=octobot_flow_client.OctoBotActionsJobDescription(
                state=next_state_for_stop
            ),
            has_next_actions=False,
            actions_dag=None,
            should_stop=True,
        )

        schedule_result_template = octobot_flow_client.OctoBotActionsJobResult(
            processed_actions=[],
            next_actions_description=octobot_flow_client.OctoBotActionsJobDescription(
                state=next_state_for_schedule
            ),
            has_next_actions=True,
            actions_dag=None,
            should_stop=False,
        )

        # Stop path: one iteration then workflow completes with AutomationWorkflowOutput.
        mock_octobot_actions_job_class_stop, _ = _octobot_actions_job_mock_class(
            run_on_result=lambda result_ref: _apply_octobot_actions_job_result_template(
                result_ref, stop_result_template
            ),
        )

        # Schedule path: one iteration with has_next_actions True so _schedule_next_iteration enqueues child workflow.
        mock_octobot_actions_job_class_schedule, _ = _octobot_actions_job_mock_class(
            run_on_result=lambda result_ref: _apply_octobot_actions_job_result_template(
                result_ref, schedule_result_template
            ),
        )

        def _encrypted_description_raw_json(template: octobot_flow_client.OctoBotActionsJobResult) -> str:
            assert template.next_actions_description is not None
            return json.dumps(
                template.next_actions_description.to_dict(include_default_values=False)
            )

        recv_path = "octobot_node.scheduler.workflows.automation_workflow.SCHEDULER.INSTANCE.recv_async"
        automation_wf = octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow

        # Step 1 — execute_iteration: encrypted_task decrypts before OctoBotActionsJob; exit encrypts next state.
        # Assert mock sees plaintext description arg; iteration dict carries ciphertext + metadata.
        with encryption_patches[0], encryption_patches[1], encryption_patches[2], encryption_patches[3]:
            enc_task = octobot_node.models.Task(
                name="encryption_integration",
                content=encrypted_task_content,
                content_metadata=task_content_metadata,
                type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
            )
            inputs_dict = params.AutomationWorkflowInputs(task=enc_task, execution_time=0).to_dict(
                include_default_values=False
            )
            inputs_dict["task"] = enc_task.model_dump(exclude_defaults=True)

            with mock.patch.object(
                octobot_flow_client,
                "OctoBotActionsJob",
                mock_octobot_actions_job_class_stop,
            ) as mock_job_cls:
                iteration_payload = await automation_wf.execute_iteration(inputs_dict, None)

            mock_job_cls.assert_called_once()
            job_ctor_content_arg = mock_job_cls.call_args[0][0]
            assert job_ctor_content_arg == plain_task_content

            iteration_model = params.AutomationWorkflowIterationResult.from_dict(iteration_payload)
            raw_stop_description_json = _encrypted_description_raw_json(stop_result_template)
            assert iteration_model.next_iteration_description != raw_stop_description_json
            assert isinstance(iteration_model.next_iteration_description, str)
            assert isinstance(iteration_model.next_iteration_description_metadata, str) 
            decrypted_iteration_state = task_inputs_encryption.decrypt_task_content(
                iteration_model.next_iteration_description,
                iteration_model.next_iteration_description_metadata,
            )
            assert json.loads(decrypted_iteration_state) == json.loads(raw_stop_description_json)

        # Step 2 — execute_automation (should_stop): final workflow JSON uses encrypted state/metadata;
        # decrypt rounds back to the same next-actions description JSON as the mock template.
        with encryption_patches[0], encryption_patches[1], encryption_patches[2], encryption_patches[3]:
            enc_task_wf = octobot_node.models.Task(
                name="encryption_integration_wf_stop",
                content=encrypted_task_content,
                content_metadata=task_content_metadata,
                type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
            )
            wf_inputs = params.AutomationWorkflowInputs(task=enc_task_wf, execution_time=0).to_dict(
                include_default_values=False
            )
            wf_inputs["task"] = enc_task_wf.model_dump(exclude_defaults=True)

            with mock.patch(recv_path, mock.AsyncMock(return_value=[])), mock.patch(
                "asyncio.sleep", mock.AsyncMock()
            ), mock.patch.object(
                octobot_flow_client,
                "OctoBotActionsJob",
                mock_octobot_actions_job_class_stop,
            ):
                handle = await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                    automation_wf.execute_automation,
                    inputs=wf_inputs,
                )
                workflow_result = await handle.get_result()

            assert isinstance(workflow_result, str)
            parsed_final = _parse_automation_workflow_output(workflow_result)
            assert isinstance(parsed_final.state, str)
            assert isinstance(parsed_final.state_metadata, str)
            raw_final_json = _encrypted_description_raw_json(stop_result_template)
            assert parsed_final.state != raw_final_json
            decrypted_final = task_inputs_encryption.decrypt_task_content(
                parsed_final.state, parsed_final.state_metadata
            )
            assert json.loads(decrypted_final) == json.loads(raw_final_json)

        # Step 3 — execute_automation (reschedule): _schedule_next_iteration calls enqueue_async with
        # next_iteration_description as task.content (and metadata) as encrypted values
        enqueue_mock = mock.AsyncMock(return_value=None)
        with encryption_patches[0], encryption_patches[1], encryption_patches[2], encryption_patches[3]:
            enc_task_sched = octobot_node.models.Task(
                name="encryption_integration_enqueue",
                content=encrypted_task_content,
                content_metadata=task_content_metadata,
                type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
            )
            sched_inputs = params.AutomationWorkflowInputs(task=enc_task_sched, execution_time=0).to_dict(
                include_default_values=False
            )
            sched_inputs["task"] = enc_task_sched.model_dump(exclude_defaults=True)

            with mock.patch(recv_path, mock.AsyncMock(return_value=[])), mock.patch(
                "asyncio.sleep", mock.AsyncMock()
            ), mock.patch.object(
                octobot_flow_client,
                "OctoBotActionsJob",
                mock_octobot_actions_job_class_schedule,
            ), mock.patch.object(
                octobot_node.scheduler.SCHEDULER.AUTOMATION_WORKFLOW_QUEUE,
                "enqueue_async",
                enqueue_mock,
            ):
                schedule_handle = await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                    automation_wf.execute_automation,
                    inputs=sched_inputs,
                )
                await schedule_handle.get_result()

            enqueue_mock.assert_called_once()
            assert len(enqueue_mock.call_args.args) == 1 # function to call
            assert len(enqueue_mock.call_args.kwargs) == 1 # inputs
            enqueued_inputs = enqueue_mock.call_args.kwargs["inputs"]
            schedule_plaintext_state = _encrypted_description_raw_json(schedule_result_template)
            assert enqueued_inputs["task"]["content"] != schedule_plaintext_state
            assert isinstance(enqueued_inputs["task"]["content_metadata"], str)
            decrypted_enqueued = task_inputs_encryption.decrypt_task_content(
                enqueued_inputs["task"]["content"], enqueued_inputs["task"]["content_metadata"]
            )
            assert json.loads(decrypted_enqueued) == json.loads(schedule_plaintext_state)


class TestExecuteAutomationInitialWait:
    @pytest.mark.asyncio
    @required_imports
    async def test_execute_automation_always_calls_initial_wait_when_execution_time_is_due(
        self,
        temp_dbos_scheduler,
        parsed_inputs,
        iteration_result,
    ):
        """
        When execution_time is already due, execute_automation must still call the initial
        recv_async wait (zero timeout) so DBOS function ids stay aligned on replay.
        """
        parsed_inputs.execution_time = 0
        inputs = parsed_inputs.to_dict(include_default_values=False)
        iter_result = params.AutomationWorkflowIterationResult(
            progress_status=iteration_result.progress_status,
            next_iteration_description=None,
            has_next_actions=False,
        )
        mock_wait = mock.AsyncMock(return_value=None)
        mock_iteration = mock.AsyncMock(return_value=iter_result.to_dict(include_default_values=False))

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_actions_update",
            mock_wait,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "execute_iteration",
            mock_iteration,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_should_continue_workflow",
            mock.Mock(return_value=False),
        ):
            handle = await temp_dbos_scheduler.INSTANCE.start_workflow_async(
                octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation,
                inputs=inputs,
            )
            assert await handle.get_result() is None

        mock_wait.assert_awaited_once_with(parsed_inputs, 0)
        mock_iteration.assert_awaited_once_with(inputs, None)


class TestExecuteAutomationReplayRecvDeterminism:
    @staticmethod
    def _dbos_recv_sleep_mismatch_message() -> str:
        return "DBOS.sleep was recorded when DBOS.recv was expected"

    @staticmethod
    def _wait_calls_include_scheduled_execution_time(
        wait_mock: mock.AsyncMock,
        scheduled_execution_time: float,
    ) -> bool:
        for call in wait_mock.await_args_list:
            resume_execution_time = call.args[1]
            if abs(resume_execution_time - scheduled_execution_time) < 0.001:
                return True
        return False

    @pytest.mark.asyncio
    @required_imports
    async def test_recv_step_order_stable_when_execution_time_becomes_past_on_recovery(
        self,
        import_automation_workflow,
    ):
        """
        Record recv+sleep at workflow start (future execution_time), interrupt during
        execute_iteration, then recover after execution_time is due.

        On recovery the workflow body runs again from the top. Skipping the initial wait
        when delay <= 0 shifts the next recv onto the sleep function id (DBOS Error 11).
        The initial wait must always run so recv ids stay aligned on replay.
        """
        automation_wf = octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow
        scheduled_delay_seconds = 0.3
        future_execution_time = time.time() + scheduled_delay_seconds
        task = octobot_node.models.Task(
            name="replay_recv_determinism",
            content="{}",
            type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
        )
        inputs = params.AutomationWorkflowInputs(
            task=task, execution_time=future_execution_time
        ).to_dict(include_default_values=False)
        inputs["task"] = task.model_dump(exclude_defaults=True)

        iteration_result = params.AutomationWorkflowIterationResult(
            progress_status=params.ProgressStatus(
                latest_step="action_1",
                next_step="action_2",
                next_step_at=0.0,
                remaining_steps=1,
                error=None,
                should_stop=False,
            ),
            next_iteration_description='{"state": {"automation": {}}}',
            has_next_actions=True,
        )
        iteration_result_dict = iteration_result.to_dict(include_default_values=False)
        iteration_started = asyncio.Event()

        async def hang_execute_iteration(inputs_dict: dict, actions_update: typing.Optional[dict]) -> dict:
            iteration_started.set()
            await asyncio.Future()

        mock_schedule = mock.AsyncMock()
        dbos_error_fragment = self._dbos_recv_sleep_mismatch_message()
        wait_path = (
            "octobot_node.scheduler.workflows.automation_workflow."
            "AutomationWorkflow._wait_and_trigger_on_actions_update"
        )

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            db_file_name = temp_file.name

        workflow_id: str | None = None
        try:
            init_scheduler(db_file_name)
            octobot_node.scheduler.SCHEDULER.INSTANCE.reset_system_database()
            octobot_node.scheduler.SCHEDULER.INSTANCE.launch()

            with mock.patch(
                wait_path,
                mock.AsyncMock(
                    wraps=automation_wf._wait_and_trigger_on_actions_update
                ),
            ) as wait_mock, mock.patch.object(
                automation_wf, "execute_iteration", hang_execute_iteration
            ), mock.patch.object(
                automation_wf, "_schedule_next_iteration", mock_schedule
            ):
                handle = await octobot_node.scheduler.SCHEDULER.INSTANCE.start_workflow_async(
                    automation_wf.execute_automation,
                    inputs=inputs,
                )
                workflow_id = handle.get_workflow_id()
                await asyncio.wait_for(
                    iteration_started.wait(),
                    timeout=scheduled_delay_seconds + 3.0,
                )

            octobot_node.scheduler.SCHEDULER.INSTANCE.destroy()
            await asyncio.sleep(scheduled_delay_seconds + 0.1)

            init_scheduler(db_file_name)
            octobot_node.scheduler.SCHEDULER.INSTANCE.launch()

            mock_iteration = mock.AsyncMock(return_value=iteration_result_dict)
            with mock.patch(
                wait_path,
                mock.AsyncMock(
                    wraps=automation_wf._wait_and_trigger_on_actions_update
                ),
            ) as recovery_wait_mock, mock.patch.object(
                automation_wf, "execute_iteration", mock_iteration
            ), mock.patch.object(
                automation_wf, "_schedule_next_iteration", mock_schedule
            ):
                recovery_handle = await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(
                    workflow_id
                )
                workflow_result = await recovery_handle.get_result()

            assert self._wait_calls_include_scheduled_execution_time(
                recovery_wait_mock, future_execution_time
            ), (
                "Recovery must re-run the scheduled initial wait (resume_execution_time equals "
                f"stored execution_time={future_execution_time}), not only the post-iteration poll "
                f"with resume_execution_time=0 (calls={recovery_wait_mock.await_args_list})"
            )
            if workflow_result is not None:
                parsed_output = _parse_automation_workflow_output(workflow_result)
                assert dbos_error_fragment not in (parsed_output.error_message or ""), (
                    f"DBOS recv/sleep step order mismatch on recovery: {parsed_output.error_message}"
                )
                assert parsed_output.error is None
            recovery_status = await recovery_handle.get_status()
            assert recovery_status.status == dbos.WorkflowStatusString.SUCCESS.value
        finally:
            if octobot_node.scheduler.SCHEDULER.INSTANCE is not None:
                with contextlib.suppress(Exception):
                    octobot_node.scheduler.SCHEDULER.INSTANCE.destroy()
            with contextlib.suppress(OSError):
                os.unlink(db_file_name)
