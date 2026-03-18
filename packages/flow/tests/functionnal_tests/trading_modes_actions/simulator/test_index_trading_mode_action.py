import pytest
import logging
import json

import octobot_commons.enums as common_enums
import octobot_commons.constants as common_constants
import octobot_flow
import octobot_flow.entities
import octobot_flow.enums

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import current_time, resolved_actions, automation_state_dict

import tentacles.Trading.Mode.index_trading_mode.index_distribution as index_distribution

index_content = [
    {
        index_distribution.DISTRIBUTION_NAME: "BTC",
        index_distribution.DISTRIBUTION_VALUE: 1,
    },
    {
        index_distribution.DISTRIBUTION_NAME: "ETH",
        index_distribution.DISTRIBUTION_VALUE: 1,
    },
]


def index_trading_mode_action(dependency_action: dict):
    return {
        "id": "action_1",
        "dsl_script": f"index_trading_mode(index_content={json.dumps(index_content)}, rebalance_trigger_min_percent=5)",
        "dependencies": [{"action_id": dependency_action["id"]}],
    }


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
                        },
                    },
                },
            },
            "exchange_account_details": {
                "exchange_details": {
                    "internal_name": functionnal_tests.EXCHANGE_INTERNAL_NAME,
                },
                "auth_details": {},
                "portfolio": {
                    "unit": "USDT",
                },
            },
        },
    }


@pytest.mark.asyncio
async def test_simulator_index_init_from_empty_state(init_action: dict):
    all_actions = [init_action, index_trading_mode_action(init_action)]
    automation_state = automation_state_dict(resolved_actions(all_actions))

    # 1. run init action
    async with octobot_flow.AutomationJob(automation_state, [], {}) as automation_job:
        await automation_job.run()
    after_init_execution_dump = automation_job.dump()

    # check bot actions execution
    assert len(automation_job.automation_state.automation.actions_dag.actions) == len(all_actions)
    for index, action in enumerate(automation_job.automation_state.automation.actions_dag.actions):
        assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
        assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
        assert action.result is None
        if index == 0:
            assert action.executed_at and action.executed_at >= current_time
            assert action.previous_execution_result is None
        else:
            assert action.executed_at is None
            assert action.previous_execution_result is None

    # 2. run index trading mode action
    async with octobot_flow.AutomationJob(after_init_execution_dump, [], {}) as automation_job:
        await automation_job.run()
    after_initial_rebalance_execution_dump = automation_job.dump()
    assert len(automation_job.automation_state.automation.actions_dag.actions) == len(all_actions)
    for index, action in enumerate(automation_job.automation_state.automation.actions_dag.actions):
        assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
        assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
        assert action.result is None
        if index == 0:
            assert action.executed_at is not None
            assert action.previous_execution_result is None
        else:
            # action is reset: this is a trading mode action: it will be executed again at the next execution
            assert action.executed_at is None
            assert isinstance(action.previous_execution_result, dict)
    
    # scheduled next execution time at 1h after the current execution (1h is the default time when unspecified)
    assert after_initial_rebalance_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"] >= current_time
    one_hour = common_enums.TimeFramesMinutes[common_enums.TimeFrames.ONE_HOUR] * common_constants.MINUTE_TO_SECONDS
    allowed_execution_time = 20
    schedule_delay = (
        after_initial_rebalance_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
        - after_initial_rebalance_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
    )
    assert one_hour - allowed_execution_time < schedule_delay < one_hour + allowed_execution_time
    # check portfolio content
    after_initial_rebalance_portfolio_content = after_initial_rebalance_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
    assert isinstance(after_initial_rebalance_execution_dump, dict)
    assert list(sorted(after_initial_rebalance_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]
    assert 0 < after_initial_rebalance_portfolio_content["USDT"]["available"] < 5
    assert 0.1 < after_initial_rebalance_portfolio_content["ETH"]["available"] < 0.4
    assert 0.001 < after_initial_rebalance_portfolio_content["BTC"]["available"] < 0.01
    logging.getLogger("test_update_simulated_basket_bot").info(f"after_execution_portfolio_content: {after_initial_rebalance_portfolio_content}")


    # 3. trigger again: nothing to do
    async with octobot_flow.AutomationJob(after_initial_rebalance_execution_dump, [], {}) as automation_job:
        await automation_job.run()
    after_second_call_execution_dump = automation_job.dump()
    assert len(automation_job.automation_state.automation.actions_dag.actions) == len(all_actions)
    for index, action in enumerate(automation_job.automation_state.automation.actions_dag.actions):
        assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
        assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
        assert action.result is None
        if index == 0:
            assert action.executed_at is not None
            assert action.previous_execution_result is None
        else:
            # action is reset: this is a trading mode action: it will be executed again at the next execution
            assert action.executed_at is None
            assert isinstance(action.previous_execution_result, dict)

    # ensure schedule delay is the same as the first call
    schedule_delay = (
        after_second_call_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
        - after_second_call_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
    )
    assert one_hour - allowed_execution_time < schedule_delay < one_hour + allowed_execution_time

    # portfolio already follows the index content: ensure portfolio content is the same as the first call
    after_second_call_portfolio_content = after_second_call_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
    assert after_second_call_portfolio_content == after_initial_rebalance_portfolio_content
