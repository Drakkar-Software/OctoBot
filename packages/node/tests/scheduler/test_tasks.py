#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import json
import mock
import pytest

import octobot_protocol.models as protocol_models

import octobot_node.enums as node_enums
import octobot_node.errors as node_errors
import octobot_node.models
import octobot_node.scheduler.tasks
import octobot_node.scheduler.workflows.params as workflow_params_module
import octobot_node.scheduler as scheduler_module

from tests.scheduler import temp_dbos_scheduler

@pytest.fixture
def schedule_task():
    return octobot_node.models.Task(
        name="test_task",
        content=json.dumps(
            {
                "ACTIONS": "trade",
                "EXCHANGE_FROM": "binance",
                "ORDER_SYMBOL": "ETH/BTC",
                "ORDER_AMOUNT": 1,
                "ORDER_TYPE": "market",
                "ORDER_SIDE": "BUY",
                "SIMULATED_PORTFOLIO": {
                    "BTC": 1,
                },
            }
        ),
        type=octobot_node.models.TaskType.EXECUTE_ACTIONS.value,
    )


class TestTriggerTask:
    """Tests for trigger_task function."""

    @pytest.mark.asyncio
    async def test_trigger_all_task_types(self, schedule_task, temp_dbos_scheduler):
        """
        ``execute_actions`` tasks are enqueued on the automation workflow queue when
        ``target_workflow_id`` is omitted (see :func:`octobot_node.scheduler.tasks.trigger_task`).
        """
        expected_workflow_id = "workflow-id-from-test-mock"
        for task_type in octobot_node.models.TaskType:
            schedule_task.type = task_type.value
            with mock.patch.object(
                temp_dbos_scheduler.AUTOMATION_WORKFLOW_QUEUE, "enqueue_async", mock.AsyncMock()
            ) as mock_enqueue_async:
                mock_handle = mock.Mock()
                mock_handle.workflow_id = expected_workflow_id
                mock_enqueue_async.return_value = mock_handle
                result = await octobot_node.scheduler.tasks.trigger_task(schedule_task)
                assert result == expected_workflow_id
                mock_enqueue_async.assert_called_once()
                call_kwargs = mock_enqueue_async.call_args[1]
                assert "inputs" in call_kwargs
                assert len(call_kwargs["inputs"]) == 1
                inputs = call_kwargs["inputs"]
                assert inputs["task"] == schedule_task.model_dump(exclude_defaults=True)
        with pytest.raises(ValueError, match="Unsupported task type"):
            with mock.patch.object(
                temp_dbos_scheduler.AUTOMATION_WORKFLOW_QUEUE, "enqueue_async", mock.AsyncMock()
            ) as mock_enqueue_async:
                schedule_task.type = "invalid_type"
                await octobot_node.scheduler.tasks.trigger_task(schedule_task)
                mock_enqueue_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_trigger_task_execute_actions_with_target_workflow_id_enqueues_automation_queue(
        self,
        schedule_task,
        temp_dbos_scheduler,
    ):
        """
        With ``target_workflow_id``, the same automation queue is used, scoped with
        :meth:`octobot_node.scheduler.scheduler.Scheduler.SetWorkflowID`.
        """
        expected_workflow_id = "workflow-id-from-test-mock"
        target_workflow_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        schedule_task.type = octobot_node.models.TaskType.EXECUTE_ACTIONS.value
        mock_handle = mock.Mock()
        mock_handle.workflow_id = expected_workflow_id
        with (
            mock.patch.object(
                temp_dbos_scheduler.AUTOMATION_WORKFLOW_QUEUE,
                "enqueue_async",
                mock.AsyncMock(return_value=mock_handle),
            ) as mock_enqueue_automation,
            mock.patch.object(
                temp_dbos_scheduler.USER_ACTION_QUEUE,
                "enqueue_async",
                mock.AsyncMock(),
            ) as mock_enqueue_user_action,
        ):
            result = await octobot_node.scheduler.tasks.trigger_task(
                schedule_task,
                target_workflow_id=target_workflow_id,
            )
        assert result == expected_workflow_id
        mock_enqueue_automation.assert_awaited_once()
        mock_enqueue_user_action.assert_not_called()
        call_kwargs = mock_enqueue_automation.call_args[1]
        assert call_kwargs["inputs"]["task"] == schedule_task.model_dump(exclude_defaults=True)


class TestTriggerUserActionWorkflow:
    """Scenario coverage for trigger_user_action_workflow."""

    @staticmethod
    def _minimal_user_action(stop_automation_identifier: str) -> protocol_models.UserAction:
        inner_configuration = protocol_models.StopAutomationConfiguration(
            id=stop_automation_identifier,
            action_type=protocol_models.UserActionType.AUTOMATION_STOP,
        )
        wrapped_configuration = protocol_models.UserActionConfiguration.from_json(inner_configuration.to_json())
        return protocol_models.UserAction(
            id="ua-task-queue",
            configuration=wrapped_configuration,
        )

    @pytest.mark.asyncio
    async def test_raises_when_scheduler_not_initialized(self):
        user_action_payload = self._minimal_user_action(stop_automation_identifier="auto-queue-1")
        test_wallet_address = "0xaaabbbbbccccddddeeeeffff00002222"
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=False):
            with pytest.raises(RuntimeError, match="Scheduler is not initialized"):
                await octobot_node.scheduler.tasks.trigger_user_action_workflow(
                    user_action_payload,
                    test_wallet_address,
                )

    @pytest.mark.asyncio
    async def test_enqueues_execute_user_action_workflow_with_encoded_inputs(self, temp_dbos_scheduler):
        user_action_payload = self._minimal_user_action(stop_automation_identifier="auto-queue-2")
        test_wallet_address = "0xaaabbbbbccccddddeeeeffff00002222"
        expected_workflow_handle_identifier = "user-action-workflow-test-id"
        with mock.patch.object(
            temp_dbos_scheduler.USER_ACTION_QUEUE,
            "enqueue_async",
            mock.AsyncMock(),
        ) as mock_enqueue_async_operation:
            import octobot_node.scheduler.workflows.user_action_workflow as user_action_workflow_module_loaded

            mock_workflow_enqueue_handle = mock.Mock()
            mock_workflow_enqueue_handle.workflow_id = expected_workflow_handle_identifier
            mock_enqueue_async_operation.return_value = mock_workflow_enqueue_handle

            enqueue_function_result = await octobot_node.scheduler.tasks.trigger_user_action_workflow(
                user_action_payload,
                test_wallet_address,
            )

            assert enqueue_function_result == expected_workflow_handle_identifier
            mock_enqueue_async_operation.assert_awaited_once()
            positional_workflow_targets, enqueue_keyword_arguments = mock_enqueue_async_operation.call_args
            assert (
                positional_workflow_targets[0]
                is user_action_workflow_module_loaded.UserActionWorkflow.execute_user_action
            )
            assert list(enqueue_keyword_arguments) == ["inputs"]
            expected_inputs_encoded = workflow_params_module.UserActionWorkflowInputs(
                user_id=test_wallet_address,
                user_action=user_action_payload,
            ).to_dict(include_default_values=False)
            assert enqueue_keyword_arguments["inputs"] == expected_inputs_encoded


class TestSendToActiveAutomationWorkflow:
    _TEST_WALLET_ADDRESS = "0xaaabbbcccddd"
    _TEST_PARENT_AUTOMATION_ID = "00000000-0000-4000-8000-000000000099"
    _TEST_CHILD_WORKFLOW_ID = f"{_TEST_PARENT_AUTOMATION_ID}_2"

    @pytest.mark.asyncio
    async def test_send_actions_to_active_automation_retries_then_sends(self):
        actions = [{"id": "action_1", "dsl_script": "noop()"}]
        mock_dbos_instance = mock.Mock()
        mock_dbos_instance.send_async = mock.AsyncMock()
        resolve_mock = mock.AsyncMock(side_effect=[[], [self._TEST_CHILD_WORKFLOW_ID]])
        with (
            mock.patch("octobot_node.scheduler.is_initialized", return_value=True),
            mock.patch.object(scheduler_module.SCHEDULER, "INSTANCE", mock_dbos_instance),
            mock.patch(
                "octobot_node.scheduler.tasks.asyncio.sleep",
                new_callable=mock.AsyncMock,
            ),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "resolve_active_automation_workflow_ids_for_parent_id",
                resolve_mock,
            ),
        ):
            await octobot_node.scheduler.tasks.send_actions_to_active_automation(
                self._TEST_PARENT_AUTOMATION_ID,
                self._TEST_WALLET_ADDRESS,
                actions,
            )

        assert resolve_mock.await_count >= 2
        mock_dbos_instance.send_async.assert_awaited_once()
        call_args = mock_dbos_instance.send_async.await_args
        assert call_args.args[0] == self._TEST_CHILD_WORKFLOW_ID
        assert call_args.kwargs["topic"] == node_enums.AutomationWorkflowMessageTopics.ACTIONS_UPDATE.value
        payload = workflow_params_module.AutomationWorkflowActionUpdate.from_dict(call_args.args[1])
        assert payload.actions_type == node_enums.AutomationWorkflowActionTypes.USER_ACTIONS.value
        assert payload.actions_details == actions

    @pytest.mark.asyncio
    async def test_send_forced_trigger_to_active_automation_sends_forced_trigger_payload(self):
        mock_dbos_instance = mock.Mock()
        mock_dbos_instance.send_async = mock.AsyncMock()
        with (
            mock.patch("octobot_node.scheduler.is_initialized", return_value=True),
            mock.patch.object(scheduler_module.SCHEDULER, "INSTANCE", mock_dbos_instance),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "resolve_active_automation_workflow_ids_for_parent_id",
                new_callable=mock.AsyncMock,
                return_value=[self._TEST_CHILD_WORKFLOW_ID],
            ),
        ):
            await octobot_node.scheduler.tasks.send_forced_trigger_to_active_automation(
                self._TEST_PARENT_AUTOMATION_ID,
                self._TEST_WALLET_ADDRESS,
            )

        call_args = mock_dbos_instance.send_async.await_args
        payload = workflow_params_module.AutomationWorkflowActionUpdate.from_dict(call_args.args[1])
        assert payload.actions_type == node_enums.AutomationWorkflowActionTypes.FORCED_TRIGGER.value
        assert payload.actions_details == []

    @pytest.mark.asyncio
    async def test_send_to_active_automation_raises_when_no_workflow_found(self):
        with (
            mock.patch("octobot_node.scheduler.is_initialized", return_value=True),
            mock.patch(
                "octobot_node.scheduler.tasks.asyncio.sleep",
                new_callable=mock.AsyncMock,
            ),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "resolve_active_automation_workflow_ids_for_parent_id",
                new_callable=mock.AsyncMock,
                return_value=[],
            ),
        ):
            with pytest.raises(node_errors.ActiveAutomationWorkflowNotFoundError):
                await octobot_node.scheduler.tasks.send_forced_trigger_to_active_automation(
                    self._TEST_PARENT_AUTOMATION_ID,
                    self._TEST_WALLET_ADDRESS,
                )

    @pytest.mark.asyncio
    async def test_send_to_active_automation_raises_when_scheduler_not_initialized(self):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=False):
            with pytest.raises(RuntimeError, match="Scheduler is not initialized"):
                await octobot_node.scheduler.tasks.send_actions_to_active_automation(
                    self._TEST_PARENT_AUTOMATION_ID,
                    self._TEST_WALLET_ADDRESS,
                    [{"id": "action_1", "dsl_script": "noop()"}],
                )
