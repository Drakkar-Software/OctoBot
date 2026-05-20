import mock
import pytest
import dbos
import datetime

import octobot_protocol.models as protocol_models

import octobot_node.enums as node_enums
import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.stop_automation as stop_automation_executor
import octobot_node.scheduler as scheduler_module
import octobot_node.scheduler.workflows.params as workflow_params

from . import provider_assertions


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
    async def test_delegates_to_get_parent_and_children_workflow_ids(self):
        with mock.patch.object(
            scheduler_module.SCHEDULER,
            "_get_parent_and_children_automation_workflow_ids",
            new_callable=mock.AsyncMock,
        ) as inner_mock:
            inner_mock.return_value = ["workflow-a"]
            result = await scheduler_module.SCHEDULER.resolve_active_automation_workflow_ids_for_parent_id(
                _TEST_WALLET_ADDRESS,
                "parent-seed",
            )
        assert result == ["workflow-a"]
        inner_mock.assert_awaited_once_with(
            _TEST_WALLET_ADDRESS,
            ["parent-seed"],
            [
                dbos.WorkflowStatusString.ENQUEUED,
                dbos.WorkflowStatusString.PENDING,
            ],
            load_output=False,
        )


class TestStopAutomationActionExecutor:
    @pytest.mark.asyncio
    async def test_execute_sends_stop_via_send_async_when_workflow_ids_match(self):
        user_action = _user_action_stop(user_action_id="ua-stop-1", automation_parent_id="00000000-0000-4000-8000-000000000001")
        executor = stop_automation_executor.StopAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        workflow_id = "00000000-0000-4000-8000-000000000001-child-step"

        mock_dbos_instance = mock.Mock()
        mock_dbos_instance.send_async = mock.AsyncMock()
        with (
            mock.patch("octobot_node.scheduler.user_actions.user_actions_executor.stop_automation.scheduler_module.is_initialized", return_value=True),
            mock.patch.object(scheduler_module.SCHEDULER, "INSTANCE", mock_dbos_instance),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "resolve_active_automation_workflow_ids_for_parent_id",
                new_callable=mock.AsyncMock,
                return_value=[workflow_id],
            ),
        ):
            await executor.execute(user_action)

        send_async_mock = mock_dbos_instance.send_async
        send_async_mock.assert_awaited_once()
        call_args = send_async_mock.await_args
        assert call_args.args[0] == workflow_id
        assert call_args.kwargs["topic"] == node_enums.AutomationWorkflowMessageTopics.ACTIONS_UPDATE.value
        payload = call_args.args[1]
        parsed = workflow_params.AutomationWorkflowActionUpdate.from_dict(payload)
        assert parsed.actions_type == node_enums.AutomationWorkflowActionTypes.USER_ACTIONS.value
        assert len(parsed.actions_details) == 1
        assert parsed.actions_details[0]["dsl_script"] == "stop_automation()"
        assert parsed.actions_details[0]["id"] == "action_stop_priority_ua-stop-1"
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

        mock_dbos_instance = mock.Mock()
        mock_dbos_instance.send_async = mock.AsyncMock()
        with (
            mock.patch("octobot_node.scheduler.user_actions.user_actions_executor.stop_automation.scheduler_module.is_initialized", return_value=True),
            mock.patch.object(scheduler_module.SCHEDULER, "INSTANCE", mock_dbos_instance),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "resolve_active_automation_workflow_ids_for_parent_id",
                new_callable=mock.AsyncMock,
                return_value=[],
            ),
        ):
            with pytest.raises(node_errors.ActiveAutomationWorkflowNotFoundError):
                await executor.execute(user_action)

        mock_dbos_instance.send_async.assert_not_called()
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
            "octobot_node.scheduler.user_actions.user_actions_executor.stop_automation.scheduler_module.is_initialized",
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
                        trading_type=protocol_models.TradingType.SPOT,
                        exchange="binanceus",
                        remote_account_id="r",
                    )
                ),
            ),
        )
        user_action = protocol_models.UserAction(id="ua-bad", configuration=_wrap(wrong))
        executor = stop_automation_executor.StopAutomationActionExecutor(_TEST_WALLET_ADDRESS)

        with (
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.stop_automation.scheduler_module.is_initialized",
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

    @pytest.mark.asyncio
    async def test_execute_raises_ambiguous_when_resolve_returns_multiple_workflow_ids(self):
        user_action = _user_action_stop(user_action_id="ua-stop-5", automation_parent_id="00000000-0000-4000-8000-000000000003")
        executor = stop_automation_executor.StopAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        workflow_id_a = "00000000-0000-4000-8000-000000000003-older"
        workflow_id_b = "00000000-0000-4000-8000-000000000003-newer"

        mock_dbos_instance = mock.Mock()
        mock_dbos_instance.send_async = mock.AsyncMock()
        with (
            mock.patch("octobot_node.scheduler.user_actions.user_actions_executor.stop_automation.scheduler_module.is_initialized", return_value=True),
            mock.patch.object(scheduler_module.SCHEDULER, "INSTANCE", mock_dbos_instance),
            mock.patch.object(
                scheduler_module.SCHEDULER,
                "resolve_active_automation_workflow_ids_for_parent_id",
                new_callable=mock.AsyncMock,
                return_value=[workflow_id_a, workflow_id_b],
            ),
        ):
            with pytest.raises(node_errors.AmbiguousActiveAutomationWorkflowError):
                await executor.execute(user_action)

        mock_dbos_instance.send_async.assert_not_called()
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="automation",
            expect_error_details=True,
            expected_error_message=protocol_models.AutomationActionResultErrorMessage.AUTOMATION_NOT_FOUND
        )
