import pytest

import octobot_commons.constants as common_constants
import octobot_trading.enums as trading_enums

import octobot_flow
import octobot_flow.entities
import octobot_flow.enums

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    current_time,
    global_state,
    btc_usdc_global_state,
    auth_details,
    actions_with_market_orders,
    resolved_actions,
    actions_with_create_limit_orders,
    actions_with_cancel_limit_orders,
)


ADDED_COIN_SYMBOL = "BTC"


@pytest.mark.asyncio
async def test_exchange_actions_reset_executing_market_order_twice(
    global_state: dict, auth_details: octobot_flow.entities.UserAuthentication, actions_with_market_orders: list[dict]
):
    assert len(actions_with_market_orders) == 2
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
    ):
        # 1. execute market order actions
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
            if isinstance(action, octobot_flow.entities.DSLScriptActionDetails):
                assert action.resolved_dsl_script is None
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
        
        # 2. reset the first market order action
        post_first_buy_state = automations_job.automation_state
        post_first_buy_state.automation.actions_dag.reset_to(post_first_buy_state.automation.actions_dag.actions[0].id)
        # action 1 has been reset
        assert post_first_buy_state.automation.actions_dag.actions[0].executed_at is None
        # action 2 has NOT been reset (it's not dependent on the first action)
        assert post_first_buy_state.automation.actions_dag.actions[1].executed_at is not None

        # 3. execute market order actions again
        async with octobot_flow.AutomationJob(post_first_buy_state, [], auth_details) as automations_job_2:
            await automations_job_2.run()

        # check bot actions execution
        actions = automations_job_2.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_with_market_orders)
        for action in actions:
            # action has been executed again
            assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
            assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
            assert action.executed_at and action.executed_at >= current_time
            assert isinstance(action.result, dict)
            assert "created_orders" in action.result
            created_order = action.result["created_orders"][0]
            assert created_order["symbol"] == "BTC/USDT"
            assert created_order["side"] == "buy"
            assert created_order["type"] == "market"

        after_execution_dump_2 = automations_job_2.dump()
        # reported next execution time to the current execution triggered_at
        assert after_execution_dump_2["automation"]["execution"]["previous_execution"]["triggered_at"] >= current_time
        # no next execution time scheduled: trigger immediately
        assert after_execution_dump_2["automation"]["execution"]["current_execution"]["scheduled_to"] == 0
        # check portfolio content
        after_execution_portfolio_content_2 = after_execution_dump_2["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
        for asset_type in [common_constants.PORTFOLIO_AVAILABLE, common_constants.PORTFOLIO_TOTAL]:
            # spent some more USDT to buy BTC
            assert after_execution_portfolio_content_2["USDT"][asset_type] < after_execution_portfolio_content["USDT"][asset_type]
            # bought BTC
            assert after_execution_portfolio_content_2["BTC"][asset_type] > after_execution_portfolio_content["BTC"][asset_type]
            assert after_execution_portfolio_content_2["ETH"][asset_type] == 0.1  # did not touch ETH


@pytest.mark.asyncio
async def test_exchange_actions_reset_creating_and_cancelling_limit_order_twice(
    btc_usdc_global_state: dict, auth_details: octobot_flow.entities.UserAuthentication,
    actions_with_create_limit_orders: list[dict], actions_with_cancel_limit_orders: list[dict]
):
    actions_with_cancel_limit_orders[0]["id"] = "action_cancel"
    actions_with_cancel_limit_orders[0]["dependencies"] = [{"action_id": actions_with_create_limit_orders[0]["id"]}]
    actions_to_execute = actions_with_create_limit_orders + actions_with_cancel_limit_orders
    assert len(actions_to_execute) == 2
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
    ):
        # 1. execute create limit order action
        automation_state = octobot_flow.entities.AutomationState.from_dict(btc_usdc_global_state)
        automation_state.update_automation_actions(
resolved_actions(actions_to_execute),
        )
        async with octobot_flow.AutomationJob(automation_state, [], auth_details) as automations_job:
            await automations_job.run()

        # check bot actions execution
        actions = automations_job.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_to_execute)
        create_limit_action = actions[0]
        cancel_action = actions[1]
        assert create_limit_action.executed_at is not None and create_limit_action.executed_at > 0 # create order action has been executed
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

        # cancel action has not been executed yet (it depends on the create action)
        assert cancel_action.executed_at is None
        assert isinstance(cancel_action, octobot_flow.entities.AbstractActionDetails)

        # 2. execute cancel limit order action
        automation_state_2 = automations_job.automation_state
        async with octobot_flow.AutomationJob(automation_state_2, [], auth_details) as automations_job_2:
            await automations_job_2.run()

        # check bot actions execution
        actions = automations_job_2.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_to_execute)
        create_limit_action = actions[0]
        assert create_limit_action.executed_at is not None and create_limit_action.executed_at > 0
        cancel_action = actions[1]
        assert cancel_action.executed_at is not None and cancel_action.executed_at > 0
        assert cancel_action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
        assert isinstance(cancel_action.result, dict)
        assert "cancelled_orders" in cancel_action.result
        cancelled = cancel_action.result["cancelled_orders"]
        assert len(cancelled) == 1
        assert len(cancelled[0]) > 2  # id of the cancelled order

        after_execution_dump = automations_job_2.dump()
        after_execution_portfolio_content = after_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
        assert "USDC" in after_execution_portfolio_content
        for asset_type in [common_constants.PORTFOLIO_AVAILABLE, common_constants.PORTFOLIO_TOTAL]:
            assert 5 <= after_execution_portfolio_content["USDC"][asset_type] < 10_000_000

        # reported next execution time to the current execution scheduled to
        automation_execution = after_execution_dump["automation"]["execution"]
        assert automation_execution["previous_execution"]["triggered_at"] >= current_time

        # 3. reset the create limit order action
        limit_order_state_3 = automations_job_2.automation_state
        limit_order_state_3.automation.actions_dag.reset_to(
            limit_order_state_3.automation.actions_dag.actions[0].id
        )
        for action in limit_order_state_3.automation.actions_dag.actions:
            assert action.executed_at is None
            assert action.result is None
        
        # 4. execute create limit order action again
        async with octobot_flow.AutomationJob(limit_order_state_3, [], auth_details) as automations_job_3:
            await automations_job_3.run()

        # check bot actions execution
        actions = automations_job_3.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_to_execute)
        create_limit_action = actions[0]
        cancel_action = actions[1]
        assert create_limit_action.executed_at is not None and create_limit_action.executed_at > 0 # create order action has been executed
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

        # cancel action has not been executed yet (it depends on the create action)
        assert cancel_action.executed_at is None
        assert isinstance(cancel_action, octobot_flow.entities.AbstractActionDetails)

        # 5. execute cancel limit order action
        automation_state_4 = automations_job_3.automation_state
        async with octobot_flow.AutomationJob(automation_state_4, [], auth_details) as automations_job_4:
            await automations_job_4.run()

        # check bot actions execution
        actions = automations_job_4.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_to_execute)
        create_limit_action = actions[0]
        assert create_limit_action.executed_at is not None and create_limit_action.executed_at > 0
        cancel_action = actions[1]
        assert cancel_action.executed_at is not None and cancel_action.executed_at > 0
        assert cancel_action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
        assert isinstance(cancel_action.result, dict)
        assert "cancelled_orders" in cancel_action.result
        cancelled = cancel_action.result["cancelled_orders"]
        assert len(cancelled) == 1
        assert len(cancelled[0]) > 2  # id of the cancelled order

        after_execution_dump = automations_job_4.dump()
        after_execution_portfolio_content = after_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
        assert "USDC" in after_execution_portfolio_content
        for asset_type in [common_constants.PORTFOLIO_AVAILABLE, common_constants.PORTFOLIO_TOTAL]:
            assert 5 <= after_execution_portfolio_content["USDC"][asset_type] < 10_000_000