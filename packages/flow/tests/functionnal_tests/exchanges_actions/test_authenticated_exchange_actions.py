import pytest
import os


import octobot_commons.constants as common_constants
import octobot_trading.enums as trading_enums


import octobot_flow
import octobot_flow.entities
import octobot_flow.enums

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    current_time,
    EXCHANGE_INTERNAL_NAME,
    actions_with_create_limit_orders,
    actions_with_cancel_limit_orders,
    resolved_actions,
    automation_state_dict,
)



@pytest.fixture
def init_action():
    if not os.environ.get("BINANCE_KEY") or not os.environ.get("BINANCE_SECRET"):
        pytest.skip("BINANCE_KEY and BINANCE_SECRET must be set in the .env file to run this test, skipping...")
    return {
        "id": "action_init",
        "action": octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value,
        "config": {
            "automation": {
                "metadata": {"automation_id": "automation_1"},
                "client_exchange_account_elements": {
                    "portfolio": {"content": {}},
                },
            },
            "exchange_account_details": {
                "exchange_details": {
                    "internal_name": EXCHANGE_INTERNAL_NAME,
                },
                "auth_details": {
                    "api_key": os.environ["BINANCE_KEY"],
                    "api_secret": os.environ["BINANCE_SECRET"],
                },
                "portfolio": {},
            },
        },
    }


@pytest.mark.asyncio
async def test_execute_actions_with_limit_orders_and_empty_state(
    init_action: dict, actions_with_create_limit_orders: list[dict], actions_with_cancel_limit_orders: list[dict]
):
    all_actions = [init_action]
    with (
        functionnal_tests.mocked_community_authentication() as login_mock,
        functionnal_tests.mocked_community_repository() as insert_bot_logs_mock,
    ):
        automation_state = automation_state_dict(resolved_actions(all_actions))
        async with octobot_flow.AutomationJob(automation_state, [], {}) as automations_job:
            await automations_job.run()

        # check bot actions execution
        assert len(automations_job.automation_state.automation.actions_dag.actions) == len(all_actions)
        for action in automations_job.automation_state.automation.actions_dag.actions:
            assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
            assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
            assert action.executed_at and action.executed_at >= current_time
            assert action.result is None

        after_execution_dump = automations_job.dump()
        exchange_account_details = after_execution_dump["exchange_account_details"]
        exchange_details = exchange_account_details["exchange_details"]
        dump_auth_details = exchange_account_details["auth_details"]
        portfolio = exchange_account_details["portfolio"]
        assert "automation" in after_execution_dump
        automation_execution = after_execution_dump["automation"]["execution"]
        # assert exchange account details init
        assert exchange_details["internal_name"] == EXCHANGE_INTERNAL_NAME
        assert dump_auth_details["api_key"] == os.environ["BINANCE_KEY"]
        assert dump_auth_details["api_secret"] == os.environ["BINANCE_SECRET"]
        assert portfolio["content"] == []
        assert portfolio["unit"] == ""
        # assert automation portfolio (not fetched yet)
        portfolio_content = after_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
        assert portfolio_content == {}
        # reported next execution time to the current execution triggered_at
        assert automation_execution["previous_execution"]["triggered_at"] >= current_time
        # no next execution time scheduled: trigger immediately
        assert automation_execution["current_execution"]["scheduled_to"] == 0
        # communit auth is not used in this context
        login_mock.assert_not_called()
        insert_bot_logs_mock.assert_not_called()

        # 2. second call: execute received limit/cancel orders actions
        actions_to_execute = actions_with_create_limit_orders + actions_with_cancel_limit_orders
        state = after_execution_dump
        other_actions = resolved_actions(actions_to_execute)
        automation_id = after_execution_dump["automation"]["metadata"]["automation_id"]
        async with octobot_flow.AutomationJob(state, [], {}) as automations_job:
            automations_job.automation_state.update_automation_actions(other_actions)
            await automations_job.run()

        # check bot actions execution
        actions = automations_job.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_to_execute) + len(all_actions)
        # Skip init action at index 0, check limit/cancel actions
        create_limit_action = actions[1]
        cancel_action = actions[2]
        assert isinstance(create_limit_action, octobot_flow.entities.AbstractActionDetails)
        assert create_limit_action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
        assert isinstance(create_limit_action.result, dict)
        assert "created_orders" in create_limit_action.result
        order = create_limit_action.result["created_orders"][0]
        assert order[trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value] == "BTC/USDC"
        assert 0 < order[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value] < 0.001
        assert order[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] == "limit"
        assert order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == "buy"
        assert 5_000 < order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value] < 10_000_000

        assert isinstance(cancel_action, octobot_flow.entities.AbstractActionDetails)
        assert cancel_action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
        assert isinstance(cancel_action.result, dict)
        assert "cancelled_orders" in cancel_action.result
        cancelled = cancel_action.result["cancelled_orders"]
        assert len(cancelled) == 1
        assert len(cancelled[0]) > 2  # id of the cancelled order

        after_execution_dump = automations_job.dump()
        after_execution_portfolio_content = after_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
        assert "USDC" in after_execution_portfolio_content
        for asset_type in [common_constants.PORTFOLIO_AVAILABLE, common_constants.PORTFOLIO_TOTAL]:
            assert 5 <= after_execution_portfolio_content["USDC"][asset_type] < 10_000_000

        # reported next execution time to the current execution scheduled to
        automation_execution = after_execution_dump["automation"]["execution"]
        assert automation_execution["previous_execution"]["triggered_at"] >= current_time
        # communit auth is not used in this test
        login_mock.assert_not_called()
        insert_bot_logs_mock.assert_not_called()