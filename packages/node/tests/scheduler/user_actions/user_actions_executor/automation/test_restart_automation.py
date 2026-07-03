import json
import datetime
import mock
import pytest
import dbos

import octobot_flow.entities as flow_entities
import octobot_flow.enums as flow_enums
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.models as models_module
import octobot_node.scheduler as scheduler_module
import octobot_node.scheduler.workflows.params as workflow_params_module
import octobot_node.scheduler.user_actions.user_actions_executor.automation.restart_automation as restart_automation_executor

from .. import provider_assertions


_TEST_WALLET_ADDRESS = "0xaaabbbcccddd"
_PARENT_AUTOMATION_ID = "00000000-0000-4000-8000-000000000001"


def _wrap(configuration_payload) -> protocol_models.UserActionConfiguration:
    return protocol_models.UserActionConfiguration.from_json(configuration_payload.to_json())


def _user_action_restart(*, user_action_id: str, automation_parent_id: str) -> protocol_models.UserAction:
    restart_payload = protocol_models.RestartAutomationConfiguration(
        id=automation_parent_id,
        action_type=protocol_models.UserActionType.AUTOMATION_RESTART,
    )
    return protocol_models.UserAction(id=user_action_id, configuration=_wrap(restart_payload))


def _stopped_automation_state_dict(*, stop_automation: bool = True) -> dict:
    return {
        "automation": {
            "metadata": {"automation_id": _PARENT_AUTOMATION_ID},
            "actions_dag": {
                "actions": [
                    {
                        "id": "action_init",
                        "action": flow_enums.ActionType.APPLY_CONFIGURATION.value,
                        "executed_at": 1.0,
                    },
                    {
                        "id": "action_run",
                        "dsl_script": "run_octobot_process('auto')",
                        "dependencies": [{"action_id": "action_init"}],
                        "executed_at": 2.0,
                        "result": {"pid": 42},
                    },
                ]
            },
            "post_actions": {"stop_automation": stop_automation},
            "execution": {
                "previous_execution": {"triggered_at": 1.0},
                "current_execution": {"triggered_at": 2.0},
            },
        },
        "exchange_account_details": {
            "exchange_details": {"internal_name": "binanceus"},
        },
    }


def _terminal_workflow_with_output(
    *,
    parent_id: str = _PARENT_AUTOMATION_ID,
    stop_automation: bool = True,
) -> mock.Mock:
    state_dict = _stopped_automation_state_dict(stop_automation=stop_automation)
    task_content = json.dumps({"state": state_dict})
    task = models_module.Task(
        name="restart-test-automation",
        content=task_content,
        type=models_module.TaskType.EXECUTE_ACTIONS.value,
    )
    encoded_inputs = workflow_params_module.AutomationWorkflowInputs(task=task).to_dict(
        include_default_values=False
    )
    workflow_status = mock.Mock(spec=dbos.WorkflowStatus)
    workflow_status.workflow_id = parent_id
    workflow_status.updated_at = 100
    workflow_status.input = {"args": [encoded_inputs], "kwargs": {}}
    workflow_status.output = json.dumps(
        workflow_params_module.AutomationWorkflowOutput(state=task_content).to_dict(
            include_default_values=False
        )
    )
    return workflow_status


class TestPrepareAutomationStateForRestart:
    def test_clears_stop_automation_and_resets_main_action(self):
        automation_state = flow_entities.AutomationState.from_dict(
            _stopped_automation_state_dict(stop_automation=True)
        )
        prepared_state = restart_automation_executor.prepare_automation_state_for_restart(automation_state)
        assert prepared_state.automation.post_actions.stop_automation is False
        run_action = prepared_state.automation.actions_dag.get_actions_by_id()["action_run"]
        assert run_action.executed_at is None
        assert run_action.previous_execution_result == {"pid": 42}
        init_action = prepared_state.automation.actions_dag.get_actions_by_id()["action_init"]
        assert init_action.executed_at == 1.0


class TestRestartAutomationActionExecutor:
    @pytest.mark.asyncio
    async def test_execute_enqueues_task_from_latest_output(self):
        user_action = _user_action_restart(
            user_action_id="ua-restart-1",
            automation_parent_id=_PARENT_AUTOMATION_ID,
        )
        terminal_workflow = _terminal_workflow_with_output()
        executor = restart_automation_executor.RestartAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with (
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.restart_automation.scheduler_module.is_initialized",
                return_value=True,
            ),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "list_user_actions",
                new_callable=mock.AsyncMock,
                return_value=[],
            ),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "resolve_active_automation_workflow_ids_for_parent_id",
                new_callable=mock.AsyncMock,
                return_value=[],
            ),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "resolve_latest_terminal_automation_workflow_for_parent_id",
                new_callable=mock.AsyncMock,
                return_value=terminal_workflow,
            ),
        ):
            await executor.execute(user_action)

        scheduled_task = executor.post_actions.to_create_automation_task
        assert scheduled_task is not None
        assert scheduled_task.id == f"{_PARENT_AUTOMATION_ID}_1"
        assert scheduled_task.name == "restart-test-automation"
        assert scheduled_task.user_id == _TEST_WALLET_ADDRESS
        task_payload = json.loads(scheduled_task.content)
        assert task_payload["state"]["automation"]["post_actions"]["stop_automation"] is False
        run_action = task_payload["state"]["automation"]["actions_dag"]["actions"][1]
        assert run_action["executed_at"] is None
        assert run_action["previous_execution_result"] == {"pid": 42}
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="automation",
            expect_error_details=False,
        )
        inner = user_action.result.actual_instance
        assert inner.created_automation_id == _PARENT_AUTOMATION_ID

    @pytest.mark.asyncio
    async def test_raises_unrestartable_when_id_binds_to_user_action(self):
        user_action = _user_action_restart(
            user_action_id="ua-restart-2",
            automation_parent_id=_PARENT_AUTOMATION_ID,
        )
        bound_user_action = protocol_models.UserAction(id=_PARENT_AUTOMATION_ID)
        executor = restart_automation_executor.RestartAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with (
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.restart_automation.scheduler_module.is_initialized",
                return_value=True,
            ),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "list_user_actions",
                new_callable=mock.AsyncMock,
                return_value=[bound_user_action],
            ),
            pytest.raises(node_errors.UnrestartableAutomationError),
        ):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="automation",
            expect_error_details=True,
            expected_error_message=protocol_models.AutomationActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_raises_unrestartable_when_automation_still_running(self):
        user_action = _user_action_restart(
            user_action_id="ua-restart-3",
            automation_parent_id=_PARENT_AUTOMATION_ID,
        )
        executor = restart_automation_executor.RestartAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with (
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.restart_automation.scheduler_module.is_initialized",
                return_value=True,
            ),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "list_user_actions",
                new_callable=mock.AsyncMock,
                return_value=[],
            ),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "resolve_active_automation_workflow_ids_for_parent_id",
                new_callable=mock.AsyncMock,
                return_value=[f"{_PARENT_AUTOMATION_ID}_1"],
            ),
            pytest.raises(node_errors.UnrestartableAutomationError),
        ):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="automation",
            expect_error_details=True,
            expected_error_message=protocol_models.AutomationActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_raises_unrestartable_when_no_prior_execution(self):
        user_action = _user_action_restart(
            user_action_id="ua-restart-4",
            automation_parent_id=_PARENT_AUTOMATION_ID,
        )
        executor = restart_automation_executor.RestartAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with (
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.restart_automation.scheduler_module.is_initialized",
                return_value=True,
            ),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "list_user_actions",
                new_callable=mock.AsyncMock,
                return_value=[],
            ),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "resolve_active_automation_workflow_ids_for_parent_id",
                new_callable=mock.AsyncMock,
                return_value=[],
            ),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "resolve_latest_terminal_automation_workflow_for_parent_id",
                new_callable=mock.AsyncMock,
                return_value=None,
            ),
            pytest.raises(node_errors.UnrestartableAutomationError),
        ):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="automation",
            expect_error_details=True,
            expected_error_message=protocol_models.AutomationActionResultErrorMessage.INVALID_CONFIGURATION,
        )

    @pytest.mark.asyncio
    async def test_raises_when_scheduler_not_initialized(self):
        user_action = _user_action_restart(
            user_action_id="ua-restart-5",
            automation_parent_id=_PARENT_AUTOMATION_ID,
        )
        executor = restart_automation_executor.RestartAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with mock.patch(
            "octobot_node.scheduler.user_actions.user_actions_executor.automation.restart_automation.scheduler_module.is_initialized",
            return_value=False,
        ):
            with pytest.raises(RuntimeError, match="Scheduler is not initialized"):
                await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="automation",
            expect_error_details=True,
            expected_error_message=protocol_models.AutomationActionResultErrorMessage.INTERNAL_ERROR,
        )

    @pytest.mark.asyncio
    async def test_invalid_payload_raises_invalid_user_action_payload(self):
        wrong = protocol_models.CreateAccountConfiguration(
            action_type=protocol_models.UserActionType.ACCOUNT_CREATE,
            configuration=protocol_models.Account(
                id="a",
                name="n",
                is_simulated=True,
                created_at=datetime.datetime(2026, 6, 1, 12, 0, 0, tzinfo=datetime.UTC),
                updated_at=datetime.datetime(2026, 6, 1, 13, 0, 0, tzinfo=datetime.UTC),
                specifics=protocol_models.AccountSpecifics(
                    actual_instance=protocol_models.ExchangeAccount(
                        account_type=protocol_models.AccountType.EXCHANGE,
                        remote_account_id="r",
                        exchange_config_ids=["test-exchange-config-id"],
                    )
                ),
            ),
        )
        user_action = protocol_models.UserAction(id="ua-bad", configuration=_wrap(wrong))
        executor = restart_automation_executor.RestartAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with (
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.restart_automation.scheduler_module.is_initialized",
                return_value=True,
            ),
            pytest.raises(node_errors.InvalidUserActionPayloadError),
        ):
            await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="automation",
            expect_error_details=True,
            expected_error_message=protocol_models.AutomationActionResultErrorMessage.INVALID_CONFIGURATION,
        )
