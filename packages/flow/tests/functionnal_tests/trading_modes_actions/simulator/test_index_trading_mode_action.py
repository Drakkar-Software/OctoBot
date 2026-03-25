import pytest
import logging
import json
import mock

import octobot_commons.enums as common_enums
import octobot_commons.constants as common_constants
import octobot_trading.dsl as trading_dsl
import octobot_trading.exchanges.exchange_channels as exchange_channels
import octobot_copy.rebalancing as rebalancing
import octobot_flow
import octobot_flow.entities
import octobot_flow.enums

import tentacles.Trading.Mode.index_trading_mode as index_trading_mode

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import current_time, resolved_actions, automation_state_dict, set_init_action_run_mode

import octobot_copy.enums as rebalancer_enums

index_content = [
    {
        rebalancer_enums.DistributionKeys.NAME: "BTC",
        rebalancer_enums.DistributionKeys.VALUE: 1,
    },
    {
        rebalancer_enums.DistributionKeys.NAME: "ETH",
        rebalancer_enums.DistributionKeys.VALUE: 1,
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
@pytest.mark.parametrize("run_mode", [
    octobot_flow.enums.AutomationRunMode.UPDATE_CLIENT_EXCHANGE_ACCOUNT_ONLY,
    octobot_flow.enums.AutomationRunMode.UPDATE_REFERENCE_EXCHANGE_ACCOUNT_AND_COPY,
])
async def test_simulator_index_init_from_empty_state(init_action: dict, run_mode: octobot_flow.enums.AutomationRunMode):
    all_actions = [set_init_action_run_mode(init_action, run_mode), index_trading_mode_action(init_action)]
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
    # both run modes should result in the same client portfolio
    after_initial_rebalance_portfolio_content = after_initial_rebalance_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
    assert isinstance(after_initial_rebalance_execution_dump, dict)
    assert list(sorted(after_initial_rebalance_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]
    assert 0 < after_initial_rebalance_portfolio_content["USDT"]["available"] < 5
    assert 0.1 < after_initial_rebalance_portfolio_content["ETH"]["available"] < 0.4
    assert 0.001 < after_initial_rebalance_portfolio_content["BTC"]["available"] < 0.01
    logging.getLogger("test_update_simulated_basket_bot").info(f"after_execution_portfolio_content: {after_initial_rebalance_portfolio_content}")
    if run_mode == octobot_flow.enums.AutomationRunMode.UPDATE_REFERENCE_EXCHANGE_ACCOUNT_AND_COPY:
        # check reference account portfolio content
        after_initial_rebalance_reference_account_portfolio_content = after_initial_rebalance_execution_dump["automation"]["reference_exchange_account_elements"]["portfolio"]["content"]
        assert isinstance(after_initial_rebalance_reference_account_portfolio_content, dict)
        assert list(sorted(after_initial_rebalance_reference_account_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]
        assert 0 < after_initial_rebalance_reference_account_portfolio_content["USDT"]["available"] < 5
        assert 0.1 < after_initial_rebalance_reference_account_portfolio_content["ETH"]["available"] < 0.4
        assert 0.001 < after_initial_rebalance_reference_account_portfolio_content["BTC"]["available"] < 0.01
    else:
        # reference account should not be updated
        assert "reference_exchange_account_elements" not in after_initial_rebalance_execution_dump["automation"]


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
    if run_mode == octobot_flow.enums.AutomationRunMode.UPDATE_REFERENCE_EXCHANGE_ACCOUNT_AND_COPY:
        after_second_call_reference_account_portfolio_content = after_second_call_execution_dump["automation"]["reference_exchange_account_elements"]["portfolio"]["content"]
        assert after_second_call_reference_account_portfolio_content == after_initial_rebalance_reference_account_portfolio_content
    else:
        assert "reference_exchange_account_elements" not in after_second_call_execution_dump["automation"]


@pytest.mark.asyncio
@pytest.mark.parametrize("run_mode", [
    octobot_flow.enums.AutomationRunMode.UPDATE_CLIENT_EXCHANGE_ACCOUNT_ONLY,
    octobot_flow.enums.AutomationRunMode.UPDATE_REFERENCE_EXCHANGE_ACCOUNT_AND_COPY,
])
async def test_simulator_index_with_added_traded_pairs(init_action: dict, run_mode: octobot_flow.enums.AutomationRunMode):
    all_actions = [set_init_action_run_mode(init_action, run_mode), index_trading_mode_action(init_action)]
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
    with (
        mock.patch.object(
            index_trading_mode.IndexTradingMode, "get_dsl_dependencies",
            # ETH/USDT won't be identified as dependency but is in index config: it will be added dynamically
            return_value=[trading_dsl.SymbolDependency(symbol="BTC/USDT")]
        ) as mock_get_dsl_dependencies,
        mock.patch.object(
            rebalancing.RebalanceActionsPlanner, "_get_supported_distribution",
            return_value=rebalancing.get_uniform_distribution(["BTC", "ETH"])
        ) as mock_get_supported_distribution,
        mock.patch.object(
            rebalancing.RebalanceActionsPlanner, "_get_filtered_traded_coins",
            return_value=["BTC", "ETH"]
        ) as mock_get_filtered_traded_coins,
        mock.patch.object(
            exchange_channels, "create_minimal_dynamic_symbols_env_producers_if_needed",
            mock.AsyncMock(wraps=exchange_channels.create_minimal_dynamic_symbols_env_producers_if_needed)
        ) as mock_create_minimal_dynamic_symbols_env_producers_if_needed,
    ):
        async with octobot_flow.AutomationJob(after_init_execution_dump, [], {}) as automation_job:
            await automation_job.run()
        assert mock_get_dsl_dependencies.call_count > 1
        # ensure the ETH/USDC pairs is really added as a dynamic symbol
        mock_create_minimal_dynamic_symbols_env_producers_if_needed.assert_awaited_once()
        expected_call_count = 2 if run_mode == octobot_flow.enums.AutomationRunMode.UPDATE_REFERENCE_EXCHANGE_ACCOUNT_AND_COPY else 1
        assert mock_get_supported_distribution.call_count == expected_call_count
        assert mock_get_filtered_traded_coins.call_count == expected_call_count
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
    
    # both run modes should result in the same client portfolio
    after_initial_rebalance_portfolio_content = after_initial_rebalance_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
    assert isinstance(after_initial_rebalance_execution_dump, dict)
    assert list(sorted(after_initial_rebalance_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]
    assert 0 < after_initial_rebalance_portfolio_content["USDT"]["available"] < 5
    assert 0.1 < after_initial_rebalance_portfolio_content["ETH"]["available"] < 0.4
    assert 0.001 < after_initial_rebalance_portfolio_content["BTC"]["available"] < 0.01
    if run_mode == octobot_flow.enums.AutomationRunMode.UPDATE_REFERENCE_EXCHANGE_ACCOUNT_AND_COPY:
        # check reference account portfolio content
        after_initial_rebalance_reference_account_portfolio_content = after_initial_rebalance_execution_dump["automation"]["reference_exchange_account_elements"]["portfolio"]["content"]
        assert isinstance(after_initial_rebalance_reference_account_portfolio_content, dict)
        assert list(sorted(after_initial_rebalance_reference_account_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]
        assert 0 < after_initial_rebalance_reference_account_portfolio_content["USDT"]["available"] < 5
        assert 0.1 < after_initial_rebalance_reference_account_portfolio_content["ETH"]["available"] < 0.4
        assert 0.001 < after_initial_rebalance_reference_account_portfolio_content["BTC"]["available"] < 0.01
    else:
        assert "reference_exchange_account_elements" not in after_initial_rebalance_execution_dump["automation"]
