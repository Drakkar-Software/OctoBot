import mock
import pytest
import dbos
import datetime

import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.automation.stop_automation as stop_automation_executor
import octobot_node.scheduler as scheduler_module

from .. import provider_assertions


_TEST_WALLET_ADDRESS = "0xaaabbbcccddd"


def _wrap(configuration_payload) -> protocol_models.UserActionConfiguration:
    return protocol_models.UserActionConfiguration.from_json(configuration_payload.to_json())


def _user_action_stop(*, user_action_id: str, automation_parent_id: str) -> protocol_models.UserAction:
    stop_payload = protocol_models.StopAutomationConfiguration(
        id=automation_parent_id,
        action_type=protocol_models.UserActionType.AUTOMATION_STOP,
    )
    return protocol_models.UserAction(id=user_action_id, configuration=_wrap(stop_payload))


class TestResolveActiveAutomationWorkflowIdsForParentId:
    @pytest.mark.asyncio
    async def test_returns_latest_pending_child_workflow_id(self):
        parent_id = "741ce171-dac9-40be-83dc-b443c0eaf0e2"
        older_child = mock.Mock(spec=dbos.WorkflowStatus)
        older_child.workflow_id = f"{parent_id}_1"
        older_child.updated_at = 10
        older_child.status = dbos.WorkflowStatusString.PENDING.value
        latest_child = mock.Mock(spec=dbos.WorkflowStatus)
        latest_child.workflow_id = f"{parent_id}_2"
        latest_child.updated_at = 20
        latest_child.status = dbos.WorkflowStatusString.ENQUEUED.value
        with mock.patch.object(
            scheduler_module.SCHEDULER,
            "_get_parent_and_children_automation_workflows",
            new_callable=mock.AsyncMock,
            return_value=[older_child, latest_child],
        ) as inner_mock:
            result = await scheduler_module.SCHEDULER.resolve_active_automation_workflow_ids_for_parent_id(
                _TEST_WALLET_ADDRESS,
                parent_id,
            )
        assert result == [f"{parent_id}_2"]
        inner_mock.assert_awaited_once_with(
            _TEST_WALLET_ADDRESS,
            [parent_id],
            [
                dbos.WorkflowStatusString.ENQUEUED,
                dbos.WorkflowStatusString.PENDING,
            ],
            load_output=False,
        )


class TestStopAutomationActionExecutor:
    @pytest.mark.asyncio
    async def test_execute_sends_stop_actions_to_active_automation(self):
        user_action = _user_action_stop(user_action_id="ua-stop-1", automation_parent_id="00000000-0000-4000-8000-000000000001")
        executor = stop_automation_executor.StopAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with (
            mock.patch("octobot_node.scheduler.user_actions.user_actions_executor.automation.stop_automation.scheduler_module.is_initialized", return_value=True),
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.stop_automation.scheduler_tasks.send_actions_to_active_automation",
                new_callable=mock.AsyncMock,
            ) as send_actions_mock,
        ):
            await executor.execute(user_action)

        send_actions_mock.assert_awaited_once_with(
            "00000000-0000-4000-8000-000000000001",
            _TEST_WALLET_ADDRESS,
            [
                {
                    "id": "action_stop_priority_ua-stop-1",
                    "dsl_script": "stop_automation()",
                }
            ],
        )
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="automation",
            expect_error_details=False
        )

    @pytest.mark.asyncio
    async def test_execute_raises_active_automation_workflow_not_found_when_wrapper_returns_empty(self):
        user_action = _user_action_stop(user_action_id="ua-stop-2", automation_parent_id="no-match")
        executor = stop_automation_executor.StopAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with (
            mock.patch("octobot_node.scheduler.user_actions.user_actions_executor.automation.stop_automation.scheduler_module.is_initialized", return_value=True),
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.stop_automation.scheduler_tasks.send_actions_to_active_automation",
                new_callable=mock.AsyncMock,
                side_effect=node_errors.ActiveAutomationWorkflowNotFoundError("no-match"),
            ),
        ):
            with pytest.raises(node_errors.ActiveAutomationWorkflowNotFoundError):
                await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="automation",
            expect_error_details=True,
            expected_error_message=protocol_models.AutomationActionResultErrorMessage.AUTOMATION_NOT_FOUND
        )

    @pytest.mark.asyncio
    async def test_execute_raises_when_scheduler_not_initialized(self):
        user_action = _user_action_stop(user_action_id="ua-stop-4", automation_parent_id="x")
        executor = stop_automation_executor.StopAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with mock.patch(
            "octobot_node.scheduler.user_actions.user_actions_executor.automation.stop_automation.scheduler_module.is_initialized",
            return_value=False,
        ):
            with pytest.raises(RuntimeError, match="Scheduler is not initialized"):
                await executor.execute(user_action)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="automation",
            expect_error_details=True,
            expected_error_message=protocol_models.AutomationActionResultErrorMessage.INTERNAL_ERROR
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
        executor = stop_automation_executor.StopAutomationActionExecutor(_TEST_WALLET_ADDRESS)

        with (
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.stop_automation.scheduler_module.is_initialized",
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
            expected_error_message=protocol_models.AutomationActionResultErrorMessage.INVALID_CONFIGURATION
        )
