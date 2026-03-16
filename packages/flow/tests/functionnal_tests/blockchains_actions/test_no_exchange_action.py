import pytest
import mock
import time
import decimal

import octobot_trading.constants as trading_constants
import octobot_trading.blockchain_wallets as blockchain_wallets

import octobot_flow
import octobot_flow.entities
import octobot_flow.enums

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    current_time,
    resolved_actions,
    automation_state_dict,
)


ADDED_COIN_SYMBOL = "BTC"
DESTINATION_ADDRESS = "0xDESTINATION_ADDRESS1234567890abcdef1234567890abcdef12345678"
WALLET_ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"


@pytest.fixture
def init_action():
    return {
        "id": "action_init",
        "action": octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value,
        "config": {
            "automation": {
                "metadata": {"automation_id": "automation_1"},
            },
            # "exchange_account_details": {}, # no exchange account details
        },
    }


@pytest.fixture
def actions_with_blockchain_deposit_and_withdrawal_with_holding_checks():
    blockchain_descriptor = {
        "blockchain": blockchain_wallets.BlockchainWalletSimulator.BLOCKCHAIN,
        "network": trading_constants.SIMULATED_BLOCKCHAIN_NETWORK,
        "native_coin_symbol": ADDED_COIN_SYMBOL,
        "tokens": [
            {
                "symbol": "ETH",
                "decimals": 18,
                "contract_address": "0x1234567890abcdef1234567890abcdef12345678",
            },
        ]
    }
    wallet_descriptor = {
        "address": WALLET_ADDRESS,
        "private_key": f"{WALLET_ADDRESS}_private_key",
        "specific_config": {
            "assets": [
                {
                    "asset": ADDED_COIN_SYMBOL,
                    "amount": 1,
                },
                {
                    "asset": "ETH",
                    "amount": 42,
                },
            ]
        }
    }
    return [
        {
            "id": "action_1",
            "dsl_script": f"error('{octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value}') if blockchain_wallet_balance({blockchain_descriptor}, {wallet_descriptor}, '{ADDED_COIN_SYMBOL}') < 1 else 'ok'",
            "dependencies": [
                {
                    "action_id": "action_init",
                },
            ],
        },
        {
            "id": "action_2",
            "dsl_script": f"blockchain_wallet_transfer({blockchain_descriptor}, {wallet_descriptor}, '{ADDED_COIN_SYMBOL}', 0.1, '{DESTINATION_ADDRESS}')",
            "dependencies": [
                {
                    "action_id": "action_init",
                },
            ],
        },
    ]


@pytest.mark.asyncio
async def test_start_with_empty_state_and_execute_simple_condition_action(
    init_action: dict,
):
    all_actions = [init_action] + [{
        "id": "action_1",
        "dsl_script": "'yes' if 1 == 2 else 'no'",
        "dependencies": [
            {
                "action_id": "action_init",
            },
        ],
    }]
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
        mock.patch.object(time, 'time', return_value=current_time),
    ):
        # 1. initialize with configuration (other actions wont be executed as their dependencies are not met)
        automation_state = automation_state_dict(resolved_actions(all_actions))
        async with octobot_flow.AutomationJob(automation_state, [], {}) as init_automation_job:
            await init_automation_job.run()
        # check actions execution
        assert len(init_automation_job.automation_state.automation.actions_dag.actions) == len(all_actions)
        for index, action in enumerate(init_automation_job.automation_state.automation.actions_dag.actions):
            if index == 0:
                assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
                assert action.executed_at and action.executed_at >= current_time
                assert action.result is None
            else:
                # not yet executed
                assert action.executed_at is None
                assert action.error_status is None
                assert action.result is None
        # check no exchange account details
        after_config_execution_dump = init_automation_job.dump()
        assert after_config_execution_dump["exchange_account_details"]["portfolio"]["content"] == []
        assert "automation" in after_config_execution_dump
        assert "reference_exchange_account_elements" not in after_config_execution_dump["automation"]
        assert "client_exchange_account_elements" not in after_config_execution_dump["automation"]

        # 2. execute simple condition action
        state = after_config_execution_dump
        async with octobot_flow.AutomationJob(state, [], {}) as automation_job:
            await automation_job.run()

        # check bot actions execution
        actions = automation_job.automation_state.automation.actions_dag.actions
        assert len(actions) == len(all_actions)
        for index, action in enumerate(actions):
            assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
            assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
            assert action.executed_at and action.executed_at >= current_time
            if index == 0:
                assert action.result is None
            elif index == 1:
                assert action.result == "no"
                assert action.error_status is None
                assert action.executed_at and action.executed_at >= current_time

        after_execution_dump = automation_job.dump()
        # still no portfolio
        assert after_execution_dump["exchange_account_details"]["portfolio"]["content"] == []
        assert "reference_exchange_account_elements" not in after_execution_dump["automation"]
        assert "client_exchange_account_elements" not in after_execution_dump["automation"]


@pytest.mark.asyncio
async def test_start_with_empty_state_and_execute_blockchain_transfer_without_exchange(
    init_action: dict, actions_with_blockchain_deposit_and_withdrawal_with_holding_checks: list[dict]
):
    all_actions = [init_action] + actions_with_blockchain_deposit_and_withdrawal_with_holding_checks
    with (
        functionnal_tests.mocked_community_authentication() as login_mock,
        functionnal_tests.mocked_community_repository() as insert_bot_logs_mock,
        mock.patch.object(trading_constants, 'ALLOW_FUNDS_TRANSFER', True),
        mock.patch.object(time, 'time', return_value=current_time),
    ):
        # 1. initialize with configuration (other actions wont be executed as their dependencies are not met)
        automation_state = automation_state_dict(resolved_actions(all_actions))
        async with octobot_flow.AutomationJob(automation_state, [], {}) as init_automation_job:
            await init_automation_job.run()
        # check actions execution
        assert len(init_automation_job.automation_state.automation.actions_dag.actions) == len(all_actions)
        for index, action in enumerate(init_automation_job.automation_state.automation.actions_dag.actions):
            if index == 0:
                assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
                assert action.executed_at and action.executed_at >= current_time
                assert action.result is None
            else:
                # not yet executed
                assert action.executed_at is None
                assert action.error_status is None
                assert action.result is None
        # check no exchange account details
        after_config_execution_dump = init_automation_job.dump()
        assert after_config_execution_dump["exchange_account_details"]["portfolio"]["content"] == []
        assert "automation" in after_config_execution_dump
        assert "reference_exchange_account_elements" not in after_config_execution_dump["automation"]
        assert "client_exchange_account_elements" not in after_config_execution_dump["automation"]
        # communit auth is not used in this test
        login_mock.assert_not_called()
        insert_bot_logs_mock.assert_not_called()

        # 2. execute blockchain transfer actions
        state = after_config_execution_dump
        async with octobot_flow.AutomationJob(state, [], {}) as automation_job:
            await automation_job.run()

        # check bot actions execution
        actions = automation_job.automation_state.automation.actions_dag.actions
        assert len(actions) == len(all_actions)
        for index, action in enumerate(actions):
            assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
            assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
            assert action.executed_at and action.executed_at >= current_time
            if index == 0:
                assert action.result is None
            elif index == 1:
                assert action.result == "ok"
            elif index == 2:
                checked = {
                    "timestamp": int(current_time),
                    "address_from": WALLET_ADDRESS,
                    "address_to": DESTINATION_ADDRESS,
                    "network": trading_constants.SIMULATED_BLOCKCHAIN_NETWORK,
                    "currency": ADDED_COIN_SYMBOL,
                    "amount": decimal.Decimal("0.1"),
                    "fee": None,
                    "comment": "",
                    "internal": False,
                }
                assert len(action.result["created_transactions"]) == 1
                for key, value in checked.items():
                    assert action.result["created_transactions"][0][key] == value
            assert action.executed_at and action.executed_at >= current_time

        after_execution_dump = automation_job.dump()
        # still no portfolio
        assert after_execution_dump["exchange_account_details"]["portfolio"]["content"] == []
        assert "reference_exchange_account_elements" not in after_execution_dump["automation"]
        assert "client_exchange_account_elements" not in after_execution_dump["automation"]
        
        # communit auth is not used in this test
        login_mock.assert_not_called()
        insert_bot_logs_mock.assert_not_called()
