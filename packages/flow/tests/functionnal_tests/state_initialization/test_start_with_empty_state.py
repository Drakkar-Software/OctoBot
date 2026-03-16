import pytest

import octobot_commons.constants as common_constants

import octobot_flow
import octobot_flow.entities
import octobot_flow.enums

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import current_time, EXCHANGE_INTERNAL_NAME, actions_with_market_orders, auth_details, resolved_actions, automation_state_dict


@pytest.fixture
def init_action():
    return {
        "id": "action_init",
        "action": octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value,
        "config": {
            "automation": {
                "metadata": {
                    "automation_id": "automation_1",
                },
                "client_exchange_account_elements": {
                    "portfolio": {
                        "content": {
                            "USDT": {
                                "available": 1000.0,
                                "total": 1000.0,
                            },
                            "ETH": {
                                "available": 0.1,
                                "total": 0.1,
                            },
                        },
                    },
                },
            },
            "exchange_account_details": {
                "exchange_details": {
                    "internal_name": EXCHANGE_INTERNAL_NAME,
                },
                "auth_details": {},
                "portfolio": {},
            },
        },
    }



@pytest.mark.asyncio
async def test_start_with_empty_state_and_reschedule_no_community_auth(init_action: dict):
    all_actions = [init_action]
    with (
        functionnal_tests.mocked_community_authentication() as login_mock,
        functionnal_tests.mocked_community_repository() as insert_bot_logs_mock,
    ):
        automation_state = automation_state_dict(resolved_actions(all_actions))
        async with octobot_flow.AutomationJob(automation_state, [], {}) as automation_job:
            await automation_job.run()

        # check bot actions execution
        assert len(automation_job.automation_state.automation.actions_dag.actions) == len(all_actions)
        for action in automation_job.automation_state.automation.actions_dag.actions:
            assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
            assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
            assert action.executed_at and action.executed_at >= current_time
            assert action.result is None

        after_execution_dump = automation_job.dump()
        exchange_account_details = after_execution_dump["exchange_account_details"]
        exchange_details = exchange_account_details["exchange_details"]
        dump_auth_details = exchange_account_details["auth_details"]
        portfolio = exchange_account_details["portfolio"]
        assert "automation" in after_execution_dump
        automation_execution = after_execution_dump["automation"]["execution"]
        # assert exchange account details init
        assert exchange_details["internal_name"] == EXCHANGE_INTERNAL_NAME
        assert dump_auth_details["api_key"] == ""
        assert dump_auth_details["api_secret"] == ""
        assert portfolio["content"] == []
        assert portfolio["unit"] == ""
        # assert automation portfolio
        portfolio_content = after_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
        assert portfolio_content == {
            "USDT": {
                "available": 1000.0,
                "total": 1000.0,
            },
            "ETH": {
                "available": 0.1,
                "total": 0.1,
            },
        }
        # reported next execution time to the current execution triggered_at
        assert automation_execution["previous_execution"]["triggered_at"] >= current_time
        # no next execution time scheduled: trigger immediately
        assert automation_execution["current_execution"]["scheduled_to"] == 0
        # communit auth is not used in this context
        login_mock.assert_not_called()
        insert_bot_logs_mock.assert_not_called()



@pytest.mark.asyncio
async def test_start_with_empty_state_action_followed_by_market_orders_no_community_auth(
    init_action: dict, actions_with_market_orders: list[dict]
):
    init_actions = [init_action]
    with (
        functionnal_tests.mocked_community_authentication() as login_mock,
        functionnal_tests.mocked_community_repository() as insert_bot_logs_mock,
    ):
        # 1. initialize bot with configuration
        automation_state = automation_state_dict(resolved_actions(init_actions))
        async with octobot_flow.AutomationJob(automation_state, [], {}) as init_automation_job:
            await init_automation_job.run()
        # check actions execution
        assert len(init_automation_job.automation_state.automation.actions_dag.actions) == len(init_actions)
        for action in init_automation_job.automation_state.automation.actions_dag.actions:
            assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
            assert action.executed_at and action.executed_at >= current_time
            assert action.result is None
        # check portfolio content
        after_config_execution_dump = init_automation_job.dump()
        assert after_config_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"] == {
            "USDT": {
                "available": 1000.0,
                "total": 1000.0,
            },
            "ETH": {
                "available": 0.1,
                "total": 0.1,
            },
        }
        # communit auth is not used in this test
        login_mock.assert_not_called()
        insert_bot_logs_mock.assert_not_called()

        # 2. second call: execute received market orders bot actions
        state = after_config_execution_dump
        other_actions = resolved_actions(actions_with_market_orders)
        async with octobot_flow.AutomationJob(state, [], {}) as automation_job:
            automation_job.automation_state.update_automation_actions(
                other_actions
            )
            await automation_job.run()

        # check bot actions execution
        assert len(automation_job.automation_state.automation.actions_dag.actions) == len(actions_with_market_orders) + len(init_actions)
        for index, action in enumerate(automation_job.automation_state.automation.actions_dag.actions):
            if index == 0:
                assert action.id == init_actions[0]["id"]
            else:
                assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
                assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
                assert action.executed_at and action.executed_at >= current_time
                assert isinstance(action.result, dict)
                assert "created_orders" in action.result
                created_order = action.result["created_orders"][0]
                assert created_order["symbol"] == "BTC/USDT"
                assert created_order["side"] == "buy"
                assert created_order["type"] == "market"

        after_execution_dump = automation_job.dump()
        after_execution_portfolio_content = after_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
        assert list(sorted(after_execution_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]
        for asset_type in [common_constants.PORTFOLIO_AVAILABLE, common_constants.PORTFOLIO_TOTAL]:
            assert 950 < after_execution_portfolio_content["USDT"][asset_type] < 1000 # spent some USDT to buy BTC
            assert after_execution_portfolio_content["ETH"][asset_type] == 0.1  # did not touch ETH
            assert 0.0001 < after_execution_portfolio_content["BTC"][asset_type] < 0.001 # bought BTC
        
        # reported next execution time to the current execution triggered_at
        automation_execution = after_execution_dump["automation"]["execution"]
        assert automation_execution["previous_execution"]["triggered_at"] >= current_time
        # no next execution time scheduled: trigger immediately
        assert automation_execution["current_execution"]["scheduled_to"] == 0
        # communit auth is not used in this test
        login_mock.assert_not_called()
        insert_bot_logs_mock.assert_not_called()
