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
import json
import functools
import mock
import pytest
import time
import typing
import tempfile
import dbos

import octobot_trading.constants

import octobot_node.scheduler
import octobot_node.scheduler.workflows
import octobot_node.errors as errors
import octobot_node.models
import octobot_node.scheduler.workflows.params as params
import octobot_node.scheduler.octobot_flow_client as octobot_flow_client
import octobot_node.scheduler.task_context as task_context


from tests.scheduler import temp_dbos_scheduler, init_and_destroy_scheduler


IMPORTED_octobot_flow = True
AUTOMATION_WORKFLOW_IMPORTED = False
try:
    import octobot_flow.entities
    import octobot_flow.enums

except ImportError:
    IMPORTED_octobot_flow = False


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
    )

def required_imports(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not IMPORTED_octobot_flow:
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
        # 1. No delay: calls iteration and stops when _should_continue returns False
        inputs = parsed_inputs.to_dict(include_default_values=False)
        iter_result = params.AutomationWorkflowIterationResult(
            progress_status=iteration_result.progress_status,
            next_iteration_description=None,
        )
        mock_iteration = mock.AsyncMock(return_value=iter_result.to_dict(include_default_values=False))
        mock_should_continue = mock.Mock(return_value=False)
        mock_process = mock.AsyncMock()

        with mock.patch.object(
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
            mock_iteration.assert_called_once_with(inputs, [])
            mock_should_continue.assert_called_once()
            mock_process.assert_not_called()

        # 2. With delay: waits, calls iteration, _process_pending not called
        parsed_inputs.execution_time = time.time() + 100
        inputs = parsed_inputs.to_dict(include_default_values=False)
        mock_wait = mock.AsyncMock(return_value=[])
        mock_iteration = mock.AsyncMock(return_value=iteration_result.to_dict(include_default_values=False))
        mock_should_continue = mock.Mock(return_value=False)
        mock_process = mock.AsyncMock()

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_priority_actions",
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
            mock_wait.assert_called_once()
            mock_iteration.assert_called_once_with(inputs, [])
            mock_process.assert_not_called()

        # 3. With delay, _should_continue True: _process_pending called
        inputs = parsed_inputs.to_dict(include_default_values=False)
        mock_wait = mock.AsyncMock(return_value=[])
        mock_iteration = mock.AsyncMock(return_value=iteration_result.to_dict(include_default_values=False))
        mock_should_continue = mock.Mock(return_value=True)
        mock_process = mock.AsyncMock(return_value=True)

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_priority_actions",
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
            mock_wait.assert_called_once()
            mock_iteration.assert_called_once_with(inputs, [])
            mock_should_continue.assert_called_once()
            mock_process.assert_awaited_once_with(parsed_inputs, iteration_result)

        # 4. Priority actions passed to iteration
        inputs = parsed_inputs.to_dict(include_default_values=False)
        priority_actions = [{"action": "stop"}]
        mock_wait = mock.AsyncMock(return_value=priority_actions)
        mock_iteration = mock.AsyncMock(return_value=iteration_result.to_dict(include_default_values=False))
        mock_should_continue = mock.Mock(return_value=False)
        mock_process = mock.AsyncMock()

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_priority_actions",
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
            mock_iteration.assert_called_once_with(inputs, priority_actions)
            mock_process.assert_not_called()

        # 5. Exception is caught and logged
        parsed_inputs.execution_time = 0
        inputs = parsed_inputs.to_dict(include_default_values=False)
        mock_iteration = mock.AsyncMock(side_effect=ValueError("test error"))
        mock_logger = mock.Mock()
        mock_process = mock.AsyncMock()

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "execute_iteration",
            mock_iteration,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_should_continue_workflow",
            mock.Mock(return_value=False),
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "get_logger",
            mock.Mock(return_value=mock_logger),
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
            mock_logger.exception.assert_called_once()
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
        mock_job = mock.Mock()
        mock_job.run = mock.AsyncMock(return_value=mock_result)

        with mock.patch.object(task_context, "encrypted_task", mock.MagicMock()) as mock_encrypted:
            mock_encrypted.return_value.__enter__ = mock.Mock(return_value=None)
            mock_encrypted.return_value.__exit__ = mock.Mock(return_value=None)
            with mock.patch.object(
                octobot_flow_client,
                "OctoBotActionsJob",
                mock.Mock(return_value=mock_job),
            ):
                result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_iteration(inputs, [])

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
                await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_iteration(inputs, [])

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

        mock_result = octobot_flow_client.OctoBotActionsJobResult(
            processed_actions=[action],
            next_actions_description=None,
            actions_dag=None,
            should_stop=False,
        )
        mock_job = mock.Mock()
        mock_job.run = mock.AsyncMock(return_value=mock_result)

        with mock.patch.object(task_context, "encrypted_task", mock.MagicMock()) as mock_encrypted:
            mock_encrypted.return_value.__enter__ = mock.Mock(return_value=None)
            mock_encrypted.return_value.__exit__ = mock.Mock(return_value=None)
            with mock.patch.object(
                octobot_flow_client,
                "OctoBotActionsJob",
                mock.Mock(return_value=mock_job),
            ):
                result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_iteration(inputs, [])

        parsed_progress_status = params.ProgressStatus.model_validate(result["progress_status"])
        assert parsed_progress_status.error == "some_error"


class TestWaitAndTriggerOnPriorityActions:
    @pytest.mark.asyncio
    async def test_wait_and_trigger_returns_empty_when_no_actions(self, import_automation_workflow, parsed_inputs):
        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.SCHEDULER.INSTANCE,
            "recv_async",
            mock.AsyncMock(return_value=[]),
        ):
            result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._wait_and_trigger_on_priority_actions(
                parsed_inputs, 0
            )
        assert result == []

    @pytest.mark.asyncio
    async def test_wait_and_trigger_returns_actions_when_received(self, import_automation_workflow, parsed_inputs):
        priority_actions = [{"action": "stop"}]
        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.SCHEDULER.INSTANCE,
            "recv_async",
            mock.AsyncMock(return_value=priority_actions),
        ):
            result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._wait_and_trigger_on_priority_actions(
                parsed_inputs, 0
            )
        assert result == priority_actions


class TestProcessPendingPriorityActionsAndReschedule:
    @pytest.mark.asyncio
    async def test_process_pending_returns_false_when_no_next_iteration(self, import_automation_workflow, parsed_inputs, iteration_result):
        iteration_result.next_iteration_description = None
        result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._process_pending_priority_actions_and_reschedule(
            parsed_inputs, iteration_result
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_process_pending_schedules_next_when_no_priority_actions(
        self, import_automation_workflow, parsed_inputs, iteration_result
    ):
        mock_wait = mock.AsyncMock(return_value=[])
        mock_schedule = mock.AsyncMock()

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_priority_actions",
            mock_wait,
        ), mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_schedule_next_iteration",
            mock_schedule,
        ):
            result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._process_pending_priority_actions_and_reschedule(
                parsed_inputs, iteration_result
            )
        assert result is True
        mock_wait.assert_awaited_once_with(parsed_inputs, 0)
        mock_schedule.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_pending_returns_false_when_should_stop(self, import_automation_workflow, parsed_inputs, iteration_result):
        iteration_result.progress_status.should_stop = True
        mock_wait = mock.AsyncMock(return_value=[])

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_priority_actions",
            mock_wait,
        ):
            result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._process_pending_priority_actions_and_reschedule(
                parsed_inputs, iteration_result
            )
        assert result is True

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
            next_iteration_description=None,
        )
        mock_wait = mock.AsyncMock(side_effect=[[{"action": "stop"}], []])
        mock_iteration = mock.AsyncMock(
            return_value=result_without_next.to_dict(include_default_values=False)
        )

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_priority_actions",
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
        )
        mock_wait = mock.AsyncMock(side_effect=[[{"action": "stop"}], []])
        mock_iteration = mock.AsyncMock(
            return_value=result_with_next.to_dict(include_default_values=False)
        )
        mock_schedule = mock.AsyncMock()

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow,
            "_wait_and_trigger_on_priority_actions",
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
            result = await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._process_pending_priority_actions_and_reschedule(
                parsed_inputs, iteration_result
            )

        assert result is True
        mock_wait.assert_awaited()
        mock_iteration.assert_called_once()
        mock_schedule.assert_called_once()


class TestScheduleNextIteration:
    @pytest.mark.asyncio
    async def test_schedule_next_iteration_enqueues_workflow(self, import_automation_workflow, parsed_inputs, iteration_result):
        mock_enqueue = mock.AsyncMock()
        next_desc = iteration_result.next_iteration_description

        with mock.patch.object(
            octobot_node.scheduler.workflows.automation_workflow.SCHEDULER.AUTOMATION_WORKFLOW_QUEUE,
            "enqueue_async",
            mock_enqueue,
        ):
            await octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow._schedule_next_iteration(
                parsed_inputs, next_desc, iteration_result.progress_status
            )
        mock_enqueue.assert_called_once()
        call_args = mock_enqueue.call_args
        assert call_args[0][0] == octobot_node.scheduler.workflows.automation_workflow.AutomationWorkflow.execute_automation
        assert "inputs" in call_args[1]


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

    def teardown_method(self):
        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = False

    @pytest.mark.asyncio
    @required_imports
    async def test_execute_automation_full_workflow_three_iterations( #todo
        self,
        import_automation_workflow,
        temp_dbos_scheduler,
    ):
        init_action = {
            "id": "action_init",
            "action": octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value,
            "config": {
                "automation": {"metadata": {"automation_id": "automation_1"}},
                "client_exchange_account_elements": {
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
        state_dict["automation"]["client_exchange_account_elements"] = {
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

        
        completed = [w for w in workflows if w.status == dbos.WorkflowStatusString.SUCCESS.value]
        assert len(completed) >= 3, f"Expected at least 3 completed workflows, got {len(completed)}"
