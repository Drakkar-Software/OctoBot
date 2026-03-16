import pytest
import mock

import octobot_trading.blockchain_wallets as blockchain_wallets
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

import octobot_flow
import octobot_flow.entities
import octobot_flow.enums

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    current_time,
    global_state,
    auth_details,
    resolved_actions,
)


ADDED_COIN_SYMBOL = "BTC"

@pytest.fixture
def actions_with_blockchain_deposit_and_withdrawal_with_holding_checks():
    wallet_address = "0x1234567890abcdef1234567890abcdef12345678"
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
        "address": wallet_address,
        "private_key": f"{wallet_address}_private_key",
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
            "dsl_script": f"error('{octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value}') if (blockchain_wallet_balance({blockchain_descriptor}, {wallet_descriptor}, '{ADDED_COIN_SYMBOL}') < 1) else 'ok'", # will pass
        },
        {
            "id": "action_2",
            "dsl_script": f"error('{octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value}') if blockchain_wallet_balance({blockchain_descriptor}, {wallet_descriptor}, '{ADDED_COIN_SYMBOL}') < 2500 else 'ok'", # will fail
        },
        {
            "id": "action_3",
            "dsl_script": f"error('{octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value}') if blockchain_wallet_balance({blockchain_descriptor}, {wallet_descriptor}, '{ADDED_COIN_SYMBOL}') < 1 else 'ok'", # will pass
        },
        {
            "id": "action_4",
            "dsl_script": f"blockchain_wallet_transfer({blockchain_descriptor}, {wallet_descriptor}, '{ADDED_COIN_SYMBOL}', 0.1, '{trading_constants.SIMULATED_DEPOSIT_ADDRESS}_{ADDED_COIN_SYMBOL}')",
        },
        {
            "id": "action_5",
            "dsl_script": f"error('{octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value}') if available('{ADDED_COIN_SYMBOL}') < 0.1 else 'ok'",
        },
        {
            "id": "action_6",
            "dsl_script": f"market('sell', 'BTC/USDT', '0.04')",
        },
        {
            "id": "action_7",
            "dsl_script": f"withdraw('{ADDED_COIN_SYMBOL}', '{trading_constants.SIMULATED_BLOCKCHAIN_NETWORK}', '{wallet_address}', 0.05)",
        },
        {
            "id": "action_8",
            "dsl_script": f"error('{octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value}') if blockchain_wallet_balance({blockchain_descriptor}, {wallet_descriptor}, '{ADDED_COIN_SYMBOL}') < 0.95 else 'ok'",
        },
    ]

@pytest.mark.asyncio
async def test_execute_actions_with_blockchain_deposit_and_withdrawal(
    global_state: dict,
    auth_details: octobot_flow.entities.UserAuthentication,
    actions_with_blockchain_deposit_and_withdrawal_with_holding_checks: list[dict]
):
    with (
        functionnal_tests.mocked_community_authentication() as login_mock,
        functionnal_tests.mocked_community_repository() as insert_bot_logs_mock,
        mock.patch.object(trading_constants, 'ALLOW_FUNDS_TRANSFER', True),
    ):
        async with octobot_flow.AutomationJob(global_state, [], auth_details) as automations_job:
            automations_job.automation_state.update_automation_actions(
                resolved_actions(actions_with_blockchain_deposit_and_withdrawal_with_holding_checks),
            )
            await automations_job.run()

        # check bot actions execution
        actions = automations_job.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_with_blockchain_deposit_and_withdrawal_with_holding_checks)
        for index, action in enumerate(actions):
            assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
            if index == 1:
                # only the second action will fail because of not enough funds
                assert action.error_status == octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value
                assert action.result is None
            else:
                assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
                assert isinstance(action.result, dict) or action.result == "ok"
                assert action.result
            assert action.executed_at and action.executed_at >= current_time

        after_execution_dump = automations_job.dump()
        # reported next execution time to the current execution triggered_at
        assert after_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"] >= current_time
        # no next execution time scheduled: trigger immediately
        assert after_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"] == 0
        # check portfolio content
        after_execution_portfolio_content = after_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
        assert isinstance(after_execution_dump, dict)
        assert list(sorted(after_execution_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]  # BTC is now added to the portfolio
        assert after_execution_portfolio_content["USDT"]["available"] > 2000  # sold BTC, therefore added some USDT to the portfolio (initially 1000 USDT)
        assert after_execution_portfolio_content["ETH"]["available"] == 0.1  # did not touch ETH
        assert 0.009 < after_execution_portfolio_content["BTC"]["total"] <= 0.01  # deposited 0.1 BTC, sold 0.04 BTC and withdrew 0.05 BTC
        assert 0.009 < after_execution_portfolio_content["BTC"]["available"] <= 0.01  # deposited 0.1 BTC, sold 0.04 BTC and withdrew 0.05 BTC
        
        # check transactions
        after_execution_transactions = after_execution_dump["automation"]["client_exchange_account_elements"]["transactions"]
        assert isinstance(after_execution_transactions, list)
        assert len(after_execution_transactions) == 2
        # first transaction is the deposit
        assert after_execution_transactions[0][trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == ADDED_COIN_SYMBOL
        assert after_execution_transactions[0][trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == 0.1
        assert after_execution_transactions[0][trading_enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0x123_simulated_deposit_address_BTC"
        assert after_execution_transactions[0][trading_enums.ExchangeConstantsTransactionColumns.NETWORK.value] == trading_constants.SIMULATED_BLOCKCHAIN_NETWORK
        # second transaction is the withdrawal
        assert after_execution_transactions[1][trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == ADDED_COIN_SYMBOL
        assert after_execution_transactions[1][trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == 0.05
        assert after_execution_transactions[1][trading_enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0x1234567890abcdef1234567890abcdef12345678"
        assert after_execution_transactions[1][trading_enums.ExchangeConstantsTransactionColumns.NETWORK.value] == trading_constants.SIMULATED_BLOCKCHAIN_NETWORK

        login_mock.assert_called_once()
        insert_bot_logs_mock.assert_called_once()


@pytest.mark.asyncio
async def test_execute_actions_with_blockchain_deposit_and_withdrawal_with_holding_checks(
    global_state: dict,
    auth_details: octobot_flow.entities.UserAuthentication,
    actions_with_blockchain_deposit_and_withdrawal_with_holding_checks: list[dict]
):
    with (
        functionnal_tests.mocked_community_authentication() as login_mock,
        functionnal_tests.mocked_community_repository() as insert_bot_logs_mock,
        mock.patch.object(trading_constants, 'ALLOW_FUNDS_TRANSFER', True),
    ):
        async with octobot_flow.AutomationJob(global_state, [], auth_details) as automations_job:
            automations_job.automation_state.update_automation_actions(
                resolved_actions(actions_with_blockchain_deposit_and_withdrawal_with_holding_checks),
            )
            await automations_job.run()

        # check bot actions execution
        actions = automations_job.automation_state.automation.actions_dag.actions
        assert len(actions) == len(actions_with_blockchain_deposit_and_withdrawal_with_holding_checks)
        for index, action in enumerate(actions):
            assert isinstance(action, octobot_flow.entities.AbstractActionDetails)
            if index == 1:
                # only the second action will fail because of not enough funds
                assert action.error_status == octobot_flow.enums.ActionErrorStatus.NOT_ENOUGH_FUNDS.value
                assert action.result is None
            else:
                assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
                assert isinstance(action.result, dict) or action.result == "ok"
                assert action.result
            assert action.executed_at and action.executed_at >= current_time

        after_execution_dump = automations_job.dump()
        # reported next execution time to the current execution triggered_at
        assert after_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"] >= current_time
        # no next execution time scheduled: trigger immediately
        assert after_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"] == 0
        # check portfolio content
        after_execution_portfolio_content = after_execution_dump["automation"]["client_exchange_account_elements"]["portfolio"]["content"]
        assert isinstance(after_execution_dump, dict)
        assert list(sorted(after_execution_portfolio_content.keys())) == ["BTC", "ETH", "USDT"]  # BTC is now added to the portfolio
        assert after_execution_portfolio_content["USDT"]["available"] > 2000  # sold BTC, therefore added some USDT to the portfolio (initially 1000 USDT)
        assert after_execution_portfolio_content["ETH"]["available"] == 0.1  # did not touch ETH
        assert 0.009 < after_execution_portfolio_content["BTC"]["total"] <= 0.01  # deposited 0.1 BTC, sold 0.04 BTC and withdrew 0.05 BTC
        assert 0.009 < after_execution_portfolio_content["BTC"]["available"] <= 0.01  # deposited 0.1 BTC, sold 0.04 BTC and withdrew 0.05 BTC
        # check transactions
        after_execution_transactions = after_execution_dump["automation"]["client_exchange_account_elements"]["transactions"]
        assert isinstance(after_execution_transactions, list)
        assert len(after_execution_transactions) == 2
        # first transaction is the deposit
        assert after_execution_transactions[0][trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == ADDED_COIN_SYMBOL
        assert after_execution_transactions[0][trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == 0.1
        assert after_execution_transactions[0][trading_enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0x123_simulated_deposit_address_BTC"
        assert after_execution_transactions[0][trading_enums.ExchangeConstantsTransactionColumns.NETWORK.value] == trading_constants.SIMULATED_BLOCKCHAIN_NETWORK
        # second transaction is the withdrawal
        assert after_execution_transactions[1][trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == ADDED_COIN_SYMBOL
        assert after_execution_transactions[1][trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == 0.05
        assert after_execution_transactions[1][trading_enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0x1234567890abcdef1234567890abcdef12345678"
        assert after_execution_transactions[1][trading_enums.ExchangeConstantsTransactionColumns.NETWORK.value] == trading_constants.SIMULATED_BLOCKCHAIN_NETWORK

        login_mock.assert_called_once()
        insert_bot_logs_mock.assert_called_once()
