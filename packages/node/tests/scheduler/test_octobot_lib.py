#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import pytest
import decimal
import time
import mock

import octobot_commons.constants as common_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.constants
import octobot_trading.errors
import octobot_trading.enums as trading_enums
import octobot_node.scheduler.octobot_lib as octobot_lib

RUN_TESTS = True


try:
    import mini_octobot.entities
    import mini_octobot.enums

    import tentacles.Meta.DSL_operators as DSL_operators

    BLOCKCHAIN = octobot_trading.constants.SIMULATED_BLOCKCHAIN_NETWORK
except ImportError:
    # tests will be skipped if octobot_trading or octobot_wrapper are not installed
    RUN_TESTS = False
    BLOCKCHAIN = "unavailable"


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def market_order_action():
    return {
        "params": {
            "ACTIONS": "trade",
            "EXCHANGE_FROM": "binance",
            "ORDER_SYMBOL": "ETH/BTC",
            "ORDER_AMOUNT": 1,
            "ORDER_TYPE": "market",
            "ORDER_SIDE": "BUY",
            "SIMULATED_PORTFOLIO": {
                "BTC": 1,
            },
        }
    }


@pytest.fixture
def limit_order_action():
    return {
        "params": {
            "ACTIONS": "trade",
            "EXCHANGE_FROM": "binance",
            "ORDER_SYMBOL": "ETH/BTC",
            "ORDER_AMOUNT": 1,
            "ORDER_PRICE": "-10%",
            "ORDER_TYPE": "limit",
            "ORDER_SIDE": "BUY",
            "SIMULATED_PORTFOLIO": {
                "BTC": 1,
            },
        }
    }


@pytest.fixture
def stop_loss_order_action():
    return {
        "params": {
            "ACTIONS": "trade",
            "EXCHANGE_FROM": "binance",
            "ORDER_SYMBOL": "ETH/BTC",
            "ORDER_TYPE": "stop",
            "ORDER_AMOUNT": "10%",
            "ORDER_SIDE": "SELL",
            "ORDER_STOP_PRICE": "-10%",
            "SIMULATED_PORTFOLIO": {
                "ETH": 1,
            },
        }
    }


@pytest.fixture
def cancel_order_action():
    return {
        "params": {
            "ACTIONS": "cancel",
            "EXCHANGE_FROM": "binance",
            "ORDER_SYMBOL": "ETH/BTC",
            "ORDER_SIDE": "BUY",
        }
    }


@pytest.fixture
def polymarket_order_action():
    return {
        "params": {
            "ACTIONS": "trade",
            "EXCHANGE_FROM": "polymarket",
            "ORDER_SYMBOL": "what-price-will-bitcoin-hit-in-january-2026/USDC:USDC-260131-0-YES",
            "ORDER_AMOUNT": 1,
            "ORDER_TYPE": "market",
            "ORDER_SIDE": "BUY",
            "SIMULATED_PORTFOLIO": {
                "USDC": 100,
            },
        }
    }


@pytest.fixture
def deposit_action():
    return {
        "params": {
            "ACTIONS": "deposit",
            "EXCHANGE_TO": "binance",
            "BLOCKCHAIN_FROM_ASSET": "BTC",
            "BLOCKCHAIN_FROM_AMOUNT": 1,
            "BLOCKCHAIN_FROM": BLOCKCHAIN,
            "SIMULATED_PORTFOLIO": {
                "BTC": 0.01,
            },
        }
    }


@pytest.fixture
def transfer_blockchain_action():
    return {
        "params": {
            "ACTIONS": "transfer",
            "BLOCKCHAIN_FROM_ASSET": "BTC",
            "BLOCKCHAIN_FROM_AMOUNT": 1,
            "BLOCKCHAIN_FROM": BLOCKCHAIN,
            "BLOCKCHAIN_TO": BLOCKCHAIN,
            "BLOCKCHAIN_TO_ASSET": "BTC",
            "BLOCKCHAIN_TO_ADDRESS": "0x123_simulated_transfer_to_address_BTC",
        }
    }


@pytest.fixture
def withdraw_action():
    return {
        "params": {
            "ACTIONS": "withdraw",
            "EXCHANGE_FROM": "binance",
            "BLOCKCHAIN_TO": "ethereum",
            "BLOCKCHAIN_TO_ASSET": "ETH",
            "BLOCKCHAIN_TO_ADDRESS": "0x1234567890123456789012345678901234567890",
            "SIMULATED_PORTFOLIO": {
                "ETH": 2,
            },
        },
    }


@pytest.fixture
def create_limit_instant_wait_and_cancel_order_action(limit_order_action, cancel_order_action):
    all = {
        "params": {
            **limit_order_action["params"],
            **cancel_order_action["params"],
            **{
                "MIN_DELAY": 0,
                "MAX_DELAY": 0,
            }
        }
    }
    all["params"]["SIMULATED_PORTFOLIO"] = {
        "BTC": 1,
    }
    all["params"]["ACTIONS"] = "trade,wait,cancel"
    return all


@pytest.fixture
def multiple_actions_bundle_no_wait(deposit_action, limit_order_action):
    all = {
        "params": {
            **deposit_action["params"],
            **limit_order_action["params"],
        }
    }
    all["params"]["SIMULATED_PORTFOLIO"] = {
        "BTC": 1,
    }
    all["params"]["ACTIONS"] = "deposit,trade"
    return all


@pytest.fixture
def multiple_action_bundle_with_wait(deposit_action, market_order_action, withdraw_action):
    all = {
        "params": {
            **deposit_action["params"],
            **market_order_action["params"],
            **withdraw_action["params"],
            **{
                "MIN_DELAY": 100,
                "MAX_DELAY": 150,
            }
        }
    }
    all["params"]["SIMULATED_PORTFOLIO"] = {
        "BTC": 1,
    }
    all["params"]["ACTIONS"] = "deposit,wait,trade,wait,withdraw"
    return all


def misses_required_octobot_lib_import():
    try:
        if not RUN_TESTS:
            return "OctoBot dependencies are not installed"
        import mini_octobot
        return None
    except ImportError:
        return "octobot_lib is not installed"

class TestOctoBotActionsJob:

    def setup_method(self):
        if message := misses_required_octobot_lib_import():
            pytest.skip(reason=message)
        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = True

    def teardown_method(self):
        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = False

    async def test_run_market_order_action(self, market_order_action):
        # step 1: configure the job
        job = octobot_lib.OctoBotActionsJob(market_order_action)
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == mini_octobot.enums.ActionType.APPLY_CONFIGURATION.value
        assert processed_actions[0].config is not None
        assert "automation" in processed_actions[0].config
        assert isinstance(processed_actions[0].config["exchange_account_details"], dict)
        pre_trade_portfolio = job.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 1,
            common_constants.PORTFOLIO_TOTAL: 1,
        }

        # step 2: run the trade action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script == "market('buy', 'ETH/BTC', 1)"
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script == "market('buy', 'ETH/BTC', 1)"
        assert len(result.get_created_orders()) == 1
        order = result.get_created_orders()[0]
        assert order["symbol"] == "ETH/BTC"
        assert order["amount"] == 1
        assert order["type"] == "market"
        assert order["side"] == "buy"
        assert result.next_actions_description is None # no more actions to execute

        # ensure deposit is successful
        post_deposit_portfolio = job2.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE] < pre_trade_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE]
        assert post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_TOTAL] < pre_trade_portfolio["BTC"][common_constants.PORTFOLIO_TOTAL]

        # bought ETH - fees
        assert post_deposit_portfolio["ETH"][common_constants.PORTFOLIO_AVAILABLE] == 0.999
        assert post_deposit_portfolio["ETH"][common_constants.PORTFOLIO_TOTAL] == 0.999

    async def test_run_limit_order_action(self, limit_order_action):
        # step 1: configure the job
        job = octobot_lib.OctoBotActionsJob(limit_order_action)
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == mini_octobot.enums.ActionType.APPLY_CONFIGURATION.value
        assert processed_actions[0].config is not None
        assert "automation" in processed_actions[0].config
        assert isinstance(processed_actions[0].config["exchange_account_details"], dict)
        pre_trade_portfolio = job.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 1,
            common_constants.PORTFOLIO_TOTAL: 1,
        }

        # step 2: run the trade action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script == "limit('buy', 'ETH/BTC', 1, '-10%')"
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script == "limit('buy', 'ETH/BTC', 1, '-10%')"
        assert len(result.get_created_orders()) == 1
        order = result.get_created_orders()[0]
        assert order["symbol"] == "ETH/BTC"
        assert order["amount"] == decimal.Decimal("1")
        assert decimal.Decimal("0.001") < order["price"] < decimal.Decimal("0.2")
        assert order["type"] == "limit"
        assert order["side"] == "buy"
        assert result.next_actions_description is None # no more actions to execute

    async def test_run_stop_loss_order_action(self, stop_loss_order_action):
        # step 1: configure the job
        job = octobot_lib.OctoBotActionsJob(stop_loss_order_action)
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == mini_octobot.enums.ActionType.APPLY_CONFIGURATION.value
        assert processed_actions[0].config is not None
        assert "automation" in processed_actions[0].config
        assert isinstance(processed_actions[0].config["exchange_account_details"], dict)
        pre_trade_portfolio = job.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["ETH"] == {
            common_constants.PORTFOLIO_AVAILABLE: 1,
            common_constants.PORTFOLIO_TOTAL: 1,
        }

        # step 2: run the trade action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("stop_loss('sell', 'ETH/BTC', '10%', '-10%')")
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("stop_loss('sell', 'ETH/BTC', '10%', '-10%')")
        assert len(result.get_created_orders()) == 1
        order = result.get_created_orders()[0]
        assert order["symbol"] == "ETH/BTC"
        assert order["amount"] == decimal.Decimal("0.1") # 10% of 1 ETH
        assert decimal.Decimal("0.001") < order["price"] < decimal.Decimal("0.2")
        assert order["type"] == "stop_loss"
        assert order["side"] == "sell"
        assert result.next_actions_description is None # no more actions to execute

    async def test_run_cancel_limit_order_after_instant_wait_action(self, create_limit_instant_wait_and_cancel_order_action):
        # step 1: configure the job
        job = octobot_lib.OctoBotActionsJob(create_limit_instant_wait_and_cancel_order_action)
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == mini_octobot.enums.ActionType.APPLY_CONFIGURATION.value
        assert processed_actions[0].config is not None
        assert "automation" in processed_actions[0].config
        assert isinstance(processed_actions[0].config["exchange_account_details"], dict)
        pre_trade_portfolio = job.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 1,
            common_constants.PORTFOLIO_TOTAL: 1,
        }

        # step 2: run the trade action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script == "limit('buy', 'ETH/BTC', 1, '-10%')"
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("limit(")
        assert len(result.get_created_orders()) == 1
        order = result.get_created_orders()[0]
        assert order["symbol"] == "ETH/BTC"
        assert order["amount"] == decimal.Decimal("1")
        assert decimal.Decimal("0.001") < order["price"] < decimal.Decimal("0.2")
        assert order["type"] == "limit"
        assert order["side"] == "buy"
        assert result.next_actions_description is not None

        # step 3: run the wait action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("wait(")
        job3 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job3.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("wait(")
        # wait is waiting 0 seconds, so it should be executed immediately
        assert processed_actions[0].executed_at is not None and processed_actions[0].executed_at > 0 
        
        # step 4: run the cancel action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script == "cancel_order('ETH/BTC', side='buy')"
        job4 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job4.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("cancel_order(")
        assert processed_actions[0].result is not None
        assert len(processed_actions[0].result[DSL_operators.CANCELLED_ORDERS_KEY]) == len(result.get_cancelled_orders()) == 1
        assert result.next_actions_description is None # no more actions to execute

    @pytest.mark.skip(reason="restore once polymarket is fully supported")
    async def test_polymarket_trade_action(self, polymarket_order_action): # TODO: update once polymarket is fullly supported
        # step 1: configure the job
        job = octobot_lib.OctoBotActionsJob(polymarket_order_action)
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == mini_octobot.enums.ActionType.APPLY_CONFIGURATION.value
        assert processed_actions[0].config is not None
        assert "automation" in processed_actions[0].config
        assert isinstance(processed_actions[0].config["exchange_account_details"], dict)
        pre_trade_portfolio = job.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["USDC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 100,
            common_constants.PORTFOLIO_TOTAL: 100,
        }

        # step 2: run the trade action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("market(")
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        with pytest.raises(octobot_trading.errors.FailedRequest): # TODO: update once supported
            result = await job2.run()
            assert len(result.processed_actions) == 1
            processed_actions = result.processed_actions
            assert len(processed_actions) == 1
            assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
            assert processed_actions[0].dsl_script.startswith("market(")
            assert len(result.get_created_orders()) == 1
            order = result.get_created_orders()[0]
            assert order["symbol"] == "what-price-will-bitcoin-hit-in-january-2026/USDC:USDC-260131-0-YES"
            assert order["amount"] == decimal.Decimal("1")
            assert order["type"] == "market"
            assert order["side"] == "buy"

    async def test_run_transfer_blockchain_only_action(self, transfer_blockchain_action):
        # step 1: configure the job
        job = octobot_lib.OctoBotActionsJob(transfer_blockchain_action)
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == mini_octobot.enums.ActionType.APPLY_CONFIGURATION.value
        assert processed_actions[0].config is not None
        assert "automation" in processed_actions[0].config
        assert job.after_execution_state.automation.reference_exchange_account_elements is None
        assert job.after_execution_state.automation.client_exchange_account_elements.portfolio.content is None

        # step 2: run the transfer action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in next_actions[0].dsl_script
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in processed_actions[0].dsl_script
        assert result.next_actions_description is None # no more actions to execute

        assert processed_actions[0].result is not None
        assert len(processed_actions[0].result[DSL_operators.CREATED_TRANSACTIONS_KEY]) == len(result.get_deposit_and_withdrawal_details()) == 1
        assert len(result.get_deposit_and_withdrawal_details()) == 1
        transaction = result.get_deposit_and_withdrawal_details()[0]
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == "BTC"
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == decimal.Decimal("1")
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.NETWORK.value] == BLOCKCHAIN
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0x123_simulated_transfer_to_address_BTC"



    async def test_run_deposit_action(self, deposit_action):
        # step 1: configure the job
        job = octobot_lib.OctoBotActionsJob(deposit_action)
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == mini_octobot.enums.ActionType.APPLY_CONFIGURATION.value
        assert processed_actions[0].config is not None
        assert "automation" in processed_actions[0].config
        assert isinstance(processed_actions[0].config["exchange_account_details"], dict)
        pre_deposit_portfolio = job.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert pre_deposit_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 0.01,
            common_constants.PORTFOLIO_TOTAL: 0.01,
        }

        # step 2: run the deposit action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in next_actions[0].dsl_script
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in processed_actions[0].dsl_script
        assert result.next_actions_description is None # no more actions to execute

        # ensure deposit is successful
        post_deposit_portfolio = job2.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert post_deposit_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: pre_deposit_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE] + deposit_action["params"]["BLOCKCHAIN_FROM_AMOUNT"],
            common_constants.PORTFOLIO_TOTAL: pre_deposit_portfolio["BTC"][common_constants.PORTFOLIO_TOTAL] + deposit_action["params"]["BLOCKCHAIN_FROM_AMOUNT"],
        }

    async def test_run_withdraw_action(self, withdraw_action):
        # step 1: configure the job
        job = octobot_lib.OctoBotActionsJob(withdraw_action)
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == mini_octobot.enums.ActionType.APPLY_CONFIGURATION.value
        assert processed_actions[0].config is not None
        assert "automation" in processed_actions[0].config
        assert isinstance(processed_actions[0].config["exchange_account_details"], dict)
        pre_withdraw_portfolio = job.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert pre_withdraw_portfolio["ETH"] == {
            common_constants.PORTFOLIO_AVAILABLE: 2,
            common_constants.PORTFOLIO_TOTAL: 2,
        }

        # step 2: run the withdraw action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("withdraw(")
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("withdraw(")
        assert result.next_actions_description is None # no more actions to execute

        # ensure withdraw is successful
        post_withdraw_portfolio = job2.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert post_withdraw_portfolio == {}  # portfolio should now be empty

    async def test_run_multiple_actions_bundle_no_wait(self, multiple_actions_bundle_no_wait):
        # step 1: configure the job
        job = octobot_lib.OctoBotActionsJob(multiple_actions_bundle_no_wait)
        # ensure wait keywords have been considered
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == mini_octobot.enums.ActionType.APPLY_CONFIGURATION.value
        assert processed_actions[0].config is not None
        assert "automation" in processed_actions[0].config
        assert isinstance(processed_actions[0].config["exchange_account_details"], dict)
        pre_trade_portfolio = job.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 1,
            common_constants.PORTFOLIO_TOTAL: 1,
        }

        # step 2: run the deposit action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1 # only the deposit action should be executable as the trade action depends on it
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in next_actions[0].dsl_script
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in processed_actions[0].dsl_script
        assert processed_actions[0].result is not None
        assert len(processed_actions[0].result[DSL_operators.CREATED_TRANSACTIONS_KEY]) == len(result.get_deposit_and_withdrawal_details()) == 1
        assert len(result.get_deposit_and_withdrawal_details()) == 1
        transaction = result.get_deposit_and_withdrawal_details()[0]
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == "BTC"
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == decimal.Decimal("1")
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.NETWORK.value] == BLOCKCHAIN
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0x123_simulated_deposit_address_BTC"


        # step 3: run the trade action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1 # only the trade action should be executable now: all others have been executed already
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("limit(")
        job3 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job3.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("limit(")
        assert len(result.get_created_orders()) == 1
        limit_order = result.get_created_orders()[0]
        assert limit_order["symbol"] == "ETH/BTC"
        assert limit_order["amount"] == decimal.Decimal("1")
        assert limit_order["type"] == "limit"
        assert limit_order["side"] == "buy"
        assert result.next_actions_description is None # no more actions to execute

        # ensure trades are taken into account in portfolio
        post_deposit_portfolio = job3.after_execution_state.automation.client_exchange_account_elements.portfolio.content

        assert "ETH" not in post_deposit_portfolio # ETH order has not been executed (still open)

        assert post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_TOTAL] == 2
        # created a buy order but not executed: locked BTC in portfolio
        assert post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE] < post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_TOTAL]


    async def test_run_multiple_actions_bundle_with_wait(self, multiple_action_bundle_with_wait):
        # step 1: configure the job
        job = octobot_lib.OctoBotActionsJob(multiple_action_bundle_with_wait)
        # ensure wait keywords have been considered
        automation = job.description.state["automation"]
        dag = automation["actions_dag"]
        assert len(dag["actions"]) == 6 # 6 actions: init, deposit, wait, trade, wait, withdraw
        dsl_scripts = [action["dsl_script"] for action in dag["actions"][1:]]
        assert all(
            dsl_script.startswith(keyword)
            for dsl_script, keyword in zip(dsl_scripts, ["blockchain_wallet_transfer", "wait", "market", "wait", "withdraw"])
        )
        # run the job
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == mini_octobot.enums.ActionType.APPLY_CONFIGURATION.value
        assert processed_actions[0].config is not None
        assert "automation" in processed_actions[0].config
        assert isinstance(processed_actions[0].config["exchange_account_details"], dict)
        pre_trade_portfolio = job.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 1,
            common_constants.PORTFOLIO_TOTAL: 1,
        }

        # step 2: run the deposit action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in next_actions[0].dsl_script
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        next_actions_description = result.next_actions_description
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in processed_actions[0].dsl_script
        assert processed_actions[0].result is not None
        assert len(processed_actions[0].result[DSL_operators.CREATED_TRANSACTIONS_KEY]) == len(result.get_deposit_and_withdrawal_details()) == 1
        transaction = processed_actions[0].result[DSL_operators.CREATED_TRANSACTIONS_KEY][0]
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == "BTC"
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == decimal.Decimal("1")
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.NETWORK.value] == BLOCKCHAIN
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0x123_simulated_deposit_address_BTC"
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("wait(")

        # step 3.A: run the wait action
        job3 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job3.run()
        next_actions_description = result.next_actions_description
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("wait(")
        # next action is wait again: waiting time has not been reached yet
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("wait(")
        waiting_time = next_actions[0].previous_execution_result[dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY][dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value]
        
        # step 3.B: complete the wait action
        with mock.patch.object(time, "time", mock.Mock(return_value=time.time() + waiting_time)):
            job4 = octobot_lib.OctoBotActionsJob(
                next_actions_description.to_dict(include_default_values=False)
            )
            result = await job4.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("wait(")
        assert processed_actions[0].executed_at is not None and processed_actions[0].executed_at > 0 

        next_actions_description = result.next_actions_description
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("market(")
        post_deposit_portfolio = job2.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert post_deposit_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 2,
            common_constants.PORTFOLIO_TOTAL: 2,
        }

        # step 4: run the trade action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("market(")
        job5 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job5.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("market(")
        assert processed_actions[0].result is not None
        assert len(processed_actions[0].result[DSL_operators.CREATED_ORDERS_KEY]) == len(result.get_created_orders()) == 1
        post_trade_portfolio = job5.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert post_trade_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE] < post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE]
        assert post_trade_portfolio["ETH"] == {
            common_constants.PORTFOLIO_AVAILABLE: 0.999,
            common_constants.PORTFOLIO_TOTAL: 0.999,
        }
        # step 5.A: run the wait action
        next_actions_description = result.next_actions_description
        job6 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job6.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("wait(")
        waiting_time = processed_actions[0].previous_execution_result[dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY][dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value]
        
        # step 5.B: complete the wait action
        next_actions_description = result.next_actions_description
        with mock.patch.object(time, "time", mock.Mock(return_value=time.time() + waiting_time)):
            job7 = octobot_lib.OctoBotActionsJob(
                next_actions_description.to_dict(include_default_values=False)
            )
            result = await job7.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("wait(")
        assert processed_actions[0].executed_at is not None and processed_actions[0].executed_at > 0 



        # step 6: run the withdraw action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = mini_octobot.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("withdraw(")
        job8 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job8.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], mini_octobot.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("withdraw(")
        assert processed_actions[0].result is not None
        assert len(processed_actions[0].result[DSL_operators.CREATED_WITHDRAWALS_KEY]) == len(result.get_deposit_and_withdrawal_details()) == 1
        transaction = processed_actions[0].result[DSL_operators.CREATED_WITHDRAWALS_KEY][0]
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == "ETH"
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == decimal.Decimal("0.999")
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.NETWORK.value] == "ethereum"
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0x1234567890123456789012345678901234567890"
        post_withdraw_portfolio = job8.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert post_withdraw_portfolio["BTC"] == post_trade_portfolio["BTC"]
        assert "ETH" not in post_withdraw_portfolio
        assert result.next_actions_description is None # no more actions to execute
