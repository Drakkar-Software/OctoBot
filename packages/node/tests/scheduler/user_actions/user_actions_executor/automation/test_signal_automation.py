import datetime
import time

import mock
import pytest

pytest.importorskip("octobot_flow")

import octobot_copy.constants as copy_constants
import octobot_flow.entities as flow_entities
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.automation.signal_automation as signal_automation_executor

from .. import provider_assertions


_TEST_WALLET_ADDRESS = "0xaaabbbcccddd"
_TEST_AUTOMATION_ID = "00000000-0000-4000-8000-000000000099"


def _wrap(configuration_payload) -> protocol_models.UserActionConfiguration:
    return protocol_models.UserActionConfiguration.from_json(configuration_payload.to_json())


def _signal_payload_wrapper(actual_instance) -> protocol_models.SignalAutomationConfigurationSignalPayload:
    return protocol_models.SignalAutomationConfigurationSignalPayload(actual_instance=actual_instance)


def _signal_configuration(
    *,
    automation_id: str = _TEST_AUTOMATION_ID,
    signal_type: protocol_models.AutomationSignalType,
    signal_payload: protocol_models.SignalAutomationConfigurationSignalPayload | None = None,
) -> protocol_models.SignalAutomationConfiguration:
    return protocol_models.SignalAutomationConfiguration(
        action_type=protocol_models.UserActionType.AUTOMATION_SIGNAL,
        automation_id=automation_id,
        signal_type=signal_type,
        signal_payload=signal_payload,
    )


def _user_action_signal(
    *,
    user_action_id: str,
    signal_type: protocol_models.AutomationSignalType,
    signal_payload: protocol_models.SignalAutomationConfigurationSignalPayload | None = None,
    automation_id: str = _TEST_AUTOMATION_ID,
) -> protocol_models.UserAction:
    configuration_inner = _signal_configuration(
        automation_id=automation_id,
        signal_type=signal_type,
        signal_payload=signal_payload,
    )
    return protocol_models.UserAction(id=user_action_id, configuration=_wrap(configuration_inner))


def _minimal_trading_signal_dict() -> dict:
    return flow_entities.TradingSignal(
        strategy_id="test-strategy-id",
        account=protocol_models.CopiedAccount(
            version=copy_constants.COPIED_ACCOUNT_VERSION,
            updated_at=time.time(),
            copied_assets=[],
        ),
    ).to_dict(include_default_values=False)


class Test_parse_actions_payload:
    def test_list_returns_same_list(self):
        actions = [{"id": "action_1", "dsl_script": "stop_automation()"}]
        parsed = signal_automation_executor._parse_actions_payload(actions)
        assert parsed == actions

    def test_dict_with_actions_key_returns_nested_list(self):
        actions = [{"id": "action_1", "dsl_script": "noop()"}]
        parsed = signal_automation_executor._parse_actions_payload({"actions": actions})
        assert parsed == actions

    def test_lone_action_dict_wraps_single_element_list(self):
        action = {"id": "action_1", "dsl_script": "noop()"}
        parsed = signal_automation_executor._parse_actions_payload(action)
        assert parsed == [action]

    def test_none_raises_invalid_payload(self):
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="required"):
            signal_automation_executor._parse_actions_payload(None)

    def test_invalid_type_raises_invalid_payload(self):
        with pytest.raises(node_errors.InvalidUserActionPayloadError):
            signal_automation_executor._parse_actions_payload("not-a-payload")


class Test_parse_trading_signal_payload:
    def test_dict_returns_trading_signal(self):
        payload = _minimal_trading_signal_dict()
        parsed = signal_automation_executor._parse_trading_signal_payload(payload)
        assert isinstance(parsed, flow_entities.TradingSignal)
        assert parsed.strategy_id == "test-strategy-id"

    def test_one_element_list_returns_trading_signal(self):
        payload = _minimal_trading_signal_dict()
        parsed = signal_automation_executor._parse_trading_signal_payload([payload])
        assert parsed.strategy_id == "test-strategy-id"

    def test_empty_list_raises_invalid_payload(self):
        with pytest.raises(node_errors.InvalidUserActionPayloadError):
            signal_automation_executor._parse_trading_signal_payload([])

    def test_none_raises_invalid_payload(self):
        with pytest.raises(node_errors.InvalidUserActionPayloadError, match="required"):
            signal_automation_executor._parse_trading_signal_payload(None)


class TestSignalAutomationActionExecutor_execute:
    @pytest.mark.asyncio
    async def test_execute_forced_trigger_calls_send_forced_trigger_to_active_automation(self):
        user_action = _user_action_signal(
            user_action_id="ua-signal-forced",
            signal_type=protocol_models.AutomationSignalType.FORCED_TRIGGER,
        )
        executor = signal_automation_executor.SignalAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with (
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.signal_automation.scheduler_module.is_initialized",
                return_value=True,
            ),
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.signal_automation.scheduler_tasks.send_forced_trigger_to_active_automation",
                new_callable=mock.AsyncMock,
            ) as send_forced_trigger_mock,
        ):
            await executor.execute(user_action)

        send_forced_trigger_mock.assert_awaited_once_with(_TEST_AUTOMATION_ID, _TEST_WALLET_ADDRESS)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="automation",
            expect_error_details=False,
        )

    @pytest.mark.asyncio
    async def test_execute_actions_calls_send_actions_to_active_automation(self):
        actions = [{"id": "action_1", "dsl_script": "noop()"}]
        user_action = _user_action_signal(
            user_action_id="ua-signal-actions",
            signal_type=protocol_models.AutomationSignalType.ACTIONS,
            signal_payload=_signal_payload_wrapper(actions),
        )
        executor = signal_automation_executor.SignalAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with (
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.signal_automation.scheduler_module.is_initialized",
                return_value=True,
            ),
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.signal_automation.scheduler_tasks.send_actions_to_active_automation",
                new_callable=mock.AsyncMock,
            ) as send_actions_mock,
        ):
            await executor.execute(user_action)

        send_actions_mock.assert_awaited_once_with(_TEST_AUTOMATION_ID, _TEST_WALLET_ADDRESS, actions)
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="automation",
            expect_error_details=False,
        )

    @pytest.mark.asyncio
    async def test_execute_trading_signal_calls_trigger_copier_automation(self):
        trading_signal_dict = _minimal_trading_signal_dict()
        user_action = _user_action_signal(
            user_action_id="ua-signal-trading",
            signal_type=protocol_models.AutomationSignalType.TRADING_SIGNAL,
            signal_payload=_signal_payload_wrapper(trading_signal_dict),
        )
        executor = signal_automation_executor.SignalAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with (
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.signal_automation.scheduler_module.is_initialized",
                return_value=True,
            ),
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.signal_automation.scheduler_tasks.trigger_copier_automation",
                new_callable=mock.AsyncMock,
            ) as trigger_copier_mock,
        ):
            await executor.execute(user_action)

        trigger_copier_mock.assert_awaited_once()
        call_args = trigger_copier_mock.await_args
        assert call_args.args[0] == _TEST_AUTOMATION_ID
        assert isinstance(call_args.args[1], flow_entities.TradingSignal)
        assert call_args.args[1].strategy_id == "test-strategy-id"
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.COMPLETED,
            result_channel="automation",
            expect_error_details=False,
        )

    @pytest.mark.asyncio
    async def test_execute_raises_active_automation_workflow_not_found_when_no_workflow_resolves(self):
        user_action = _user_action_signal(
            user_action_id="ua-signal-missing",
            signal_type=protocol_models.AutomationSignalType.FORCED_TRIGGER,
        )
        executor = signal_automation_executor.SignalAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with (
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.signal_automation.scheduler_module.is_initialized",
                return_value=True,
            ),
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.signal_automation.scheduler_tasks.send_forced_trigger_to_active_automation",
                new_callable=mock.AsyncMock,
                side_effect=node_errors.ActiveAutomationWorkflowNotFoundError("missing"),
            ) as send_forced_trigger_mock,
        ):
            with pytest.raises(node_errors.ActiveAutomationWorkflowNotFoundError):
                await executor.execute(user_action)

        send_forced_trigger_mock.assert_awaited_once()
        provider_assertions.assert_user_action_terminal_state(
            user_action=user_action,
            expected_status=protocol_models.UserActionStatus.FAILED,
            result_channel="automation",
            expect_error_details=True,
            expected_error_message=protocol_models.AutomationActionResultErrorMessage.AUTOMATION_NOT_FOUND,
        )

    @pytest.mark.asyncio
    async def test_execute_raises_when_scheduler_not_initialized(self):
        user_action = _user_action_signal(
            user_action_id="ua-signal-no-scheduler",
            signal_type=protocol_models.AutomationSignalType.FORCED_TRIGGER,
        )
        executor = signal_automation_executor.SignalAutomationActionExecutor(_TEST_WALLET_ADDRESS)
        with mock.patch(
            "octobot_node.scheduler.user_actions.user_actions_executor.automation.signal_automation.scheduler_module.is_initialized",
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
        wrong = protocol_models.StopAutomationConfiguration(
            id="auto-stop",
            action_type=protocol_models.UserActionType.AUTOMATION_STOP,
        )
        user_action = protocol_models.UserAction(id="ua-bad-signal", configuration=_wrap(wrong))
        executor = signal_automation_executor.SignalAutomationActionExecutor(_TEST_WALLET_ADDRESS)

        with (
            mock.patch(
                "octobot_node.scheduler.user_actions.user_actions_executor.automation.signal_automation.scheduler_module.is_initialized",
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
