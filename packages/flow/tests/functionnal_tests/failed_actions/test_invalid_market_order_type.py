import mock
import pytest

import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.personal_data.orders.order_factory as order_factory_module

import octobot_flow.jobs
import octobot_flow.entities
import octobot_flow.enums

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    current_time,
    global_state,
    auth_details,
    resolved_actions,
    EXCHANGE_INTERNAL_NAME,
)


@pytest.fixture
def actions_with_market_order_unsupported_stop_loss_type():
    return [
        {
            "id": "action_1",
            "dsl_script": "market('buy', 'BTC/USDT', '20q', stop_loss_price='-10%')",
        },
    ]


_original_ensure_supported_order_type = (
    order_factory_module.OrderFactory._ensure_supported_order_type
)


def _ensure_supported_order_type_without_stop_loss(self, order_type):
    if order_type == trading_enums.TraderOrderType.STOP_LOSS:
        raise trading_errors.NotSupportedOrderTypeError(
            f"{order_type.name} orders are not supported on {self.exchange_manager.exchange_name}",
            order_type,
        )
    return _original_ensure_supported_order_type(self, order_type)


@pytest.mark.asyncio
async def test_market_order_fails_with_unsupported_stop_loss_type(
    global_state: dict,
    auth_details: octobot_flow.entities.UserAuthentication,
    actions_with_market_order_unsupported_stop_loss_type: list[dict],
):
    expected_error_message = (
        f"{trading_enums.TraderOrderType.STOP_LOSS.name} orders are not supported on {EXCHANGE_INTERNAL_NAME}"
    )
    with (
        mock.patch.object(
            order_factory_module.OrderFactory,
            "_ensure_supported_order_type",
            _ensure_supported_order_type_without_stop_loss,
        ),
        functionnal_tests.mocked_community_authentication() as login_mock,
        functionnal_tests.mocked_community_repository() as insert_bot_logs_mock,
    ):
        automation_state = octobot_flow.entities.AutomationState.from_dict(global_state)
        automation_state.upsert_automation_actions(
            resolved_actions(actions_with_market_order_unsupported_stop_loss_type)
        )
        async with octobot_flow.jobs.AutomationJob(automation_state, [], [], auth_details) as automations_job:
            await automations_job.run()

        actions = automations_job.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_with_market_order_unsupported_stop_loss_type)
        action = actions[0]
        assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
        assert action.error_status == octobot_flow.enums.ActionErrorStatus.UNSUPPORTED_STOP_ORDER.value
        assert action.error_message == expected_error_message
        assert action.result is None
        assert action.executed_at and action.executed_at >= current_time

        login_mock.assert_called_once()
        insert_bot_logs_mock.assert_called_once()
