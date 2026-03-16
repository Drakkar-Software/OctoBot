import pytest
import logging
import mock

import octobot_commons.constants as common_constants
import octobot_trading.blockchain_wallets as blockchain_wallets
import octobot_trading.constants as trading_constants

import octobot_flow
import octobot_flow.entities
import octobot_flow.enums

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    current_time,
    global_state,
    auth_details,
    actions_with_market_orders,
    resolved_actions,
)


ADDED_COIN_SYMBOL = "BTC"


@pytest.mark.asyncio
async def test_execute_actions_with_market_orders_and_existing_state(
    global_state: dict, auth_details: octobot_flow.entities.UserAuthentication, actions_with_market_orders: list[dict]
):
    with (
        functionnal_tests.mocked_community_authentication() as login_mock,
        functionnal_tests.mocked_community_repository() as insert_bot_logs_mock,
    ):
        # test with parsed global state
        automation_state = octobot_flow.entities.AutomationState.from_dict(global_state)
        automation_state.update_automation_actions(resolved_actions(actions_with_market_orders))
        async with octobot_flow.AutomationJob(automation_state, [], auth_details) as automations_job:
            await automations_job.run()

        # check bot actions execution
        actions = automations_job.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_with_market_orders)
        for action in actions:
            assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
            assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
            assert action.executed_at and action.executed_at >= current_time
            assert isinstance(action.result, dict)
            assert "created_orders" in action.result
            created_order = action.result["created_orders"][0]
            assert created_order["symbol"] == "BTC/USDT"
            assert created_order["side"] == "buy"
            assert created_order["type"] == "market"

        after_execution_dump = automations_job.dump()
        # reported next execution time to the current execution triggered_at
        assert after_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"] >= current_time
        # no next execution time scheduled: trigger immediately
        assert after_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"] == 0
        # check portfolio content
        after_execution_portfolio_content = after_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
        assert isinstance(after_execution_dump, dict)
        assert list(sorted(after_execution_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]
        for asset_type in [common_constants.PORTFOLIO_AVAILABLE, common_constants.PORTFOLIO_TOTAL]:
            assert 950 < after_execution_portfolio_content["USDT"][asset_type] < 1000  # spent some USDT to buy BTC
            assert after_execution_portfolio_content["ETH"][asset_type] == 0.1  # did not touch ETH
            assert 0.0001 < after_execution_portfolio_content["BTC"][asset_type] < 0.001  # bought BTC
        logging.getLogger("test_execute_actions_with_market_orders").info(
            f"after_execution_portfolio_content: {after_execution_portfolio_content}"
        )
        # check bot actions
        login_mock.assert_called_once()
        insert_bot_logs_mock.assert_called_once()
