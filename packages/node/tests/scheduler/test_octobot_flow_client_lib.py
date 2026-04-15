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
import typing

import octobot_commons.list_util as list_util
import octobot_commons.constants as common_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.constants
import octobot_trading.errors
import octobot_trading.enums as trading_enums
import octobot_trading.blockchain_wallets.simulator.blockchain_wallet_simulator as blockchain_wallet_simulator
import octobot_trading.personal_data.orders.order_factory as order_factory
import octobot_node.scheduler.octobot_flow_client as octobot_flow_client

RUN_TESTS = True


try:
    import octobot_flow.entities
    import octobot_flow.enums

    import tentacles.Meta.DSL_operators as DSL_operators
    import tentacles.Meta.DSL_operators.exchange_operators.exchange_personal_data_operators.fetch_order_operators as fetch_order_operators_module  # noqa: E501

    BLOCKCHAIN = octobot_trading.constants.SIMULATED_BLOCKCHAIN_NETWORK
except ImportError as err:
    import traceback
    traceback.print_exc()
    print(f"Error importing octobot_flow: {err}")
    # tests will be skipped if octobot_trading or octobot_wrapper are not installed
    RUN_TESTS = False
    BLOCKCHAIN = "unavailable"


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


EXCHANGE_INTERNAL_NAME = "binanceus"


@pytest.fixture
def market_order_action():
    return {
        "params": {
            "ACTIONS": "trade",
            "EXCHANGE_FROM": EXCHANGE_INTERNAL_NAME,
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
            "EXCHANGE_FROM": EXCHANGE_INTERNAL_NAME,
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
            "EXCHANGE_FROM": EXCHANGE_INTERNAL_NAME,
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
            "EXCHANGE_FROM": EXCHANGE_INTERNAL_NAME,
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
            "EXCHANGE_TO": EXCHANGE_INTERNAL_NAME,
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
            "EXCHANGE_FROM": EXCHANGE_INTERNAL_NAME,
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
def trade_transfer_and_check_balance_actions_bundle_no_wait(market_order_action, transfer_blockchain_action):
    check_address = "17ouWjN7nvPWkZKo2svTF81etXL6Qxnty7"
    all = {
        "params": {
            **market_order_action["params"],
            **transfer_blockchain_action["params"],
            **{
                "ORDER_EXTRA_PARAMS": {"address_to": check_address},
                "BLOCKCHAIN_TO_ADDRESS": (
                    "dependency::action_trade_1::created_orders::0::esov::address_from"
                ),
                "BLOCKCHAIN_BALANCE_ADDRESS": "123_balance_address",
                "BLOCKCHAIN_BALANCE_AMOUNT": 1,
                "BLOCKCHAIN_BALANCE": BLOCKCHAIN,
                "BLOCKCHAIN_BALANCE_ASSET": "BTC",
                "LOOP_INTERVAL": 3,
                "LOOP_TIMEOUT": 10,
                "LOOP_MAX_ATTEMPTS": 4,
            },
        }
    }
    all["params"]["SIMULATED_PORTFOLIO"] = {
        "BTC": 1,
    }
    all["params"]["ACTIONS"] = "trade,transfer,loop_until_blockchain_balance"
    return all


@pytest.fixture
def trade_and_loop_until_order_closed(market_order_action):
    all = {
        "params": {
            **market_order_action["params"],
            **{
                "ORDER_EXCHANGE_ID": (
                    "dependency::action_trade_1::created_orders::0::exchange_id"
                ),
                "LOOP_INTERVAL": 3,
                "LOOP_TIMEOUT": 10,
                "LOOP_MAX_ATTEMPTS": 4,
            },
        }
    }
    all["params"]["SIMULATED_PORTFOLIO"] = {
        "BTC": 1,
    }
    all["params"]["ACTIONS"] = "trade,loop_until_order_closed"
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


def misses_required_octobot_flow_client_import():
    try:
        if not RUN_TESTS:
            return "OctoBot dependencies are not installed"
        import octobot_flow
        return None
    except ImportError:
        return "octobot_flow_client is not installed"


def get_failed_actions(actions: list["octobot_flow.entities.AbstractActionDetails"]) -> list[typing.Optional[dict]]:
    return [
        action.result
        for action in actions
        if action.error_status is not octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
    ]

def get_created_orders(actions: list["octobot_flow.entities.AbstractActionDetails"]) -> list[dict]:
    order_lists = [
        action.result.get(DSL_operators.CREATED_ORDERS_KEY, [])
        for action in actions
        if action.result
    ]
    return list_util.flatten_list(order_lists) if order_lists else []

def get_cancelled_orders(actions: list["octobot_flow.entities.AbstractActionDetails"]) -> list[str]:
    cancelled_orders = [
        action.result.get(DSL_operators.CANCELLED_ORDERS_KEY, [])
        for action in actions
        if action.result
    ]
    return list_util.flatten_list(cancelled_orders) if cancelled_orders else []

def get_deposit_and_withdrawal_details(actions: list["octobot_flow.entities.AbstractActionDetails"]) -> list[dict]:
    withdrawal_lists = [
        action.result.get(DSL_operators.CREATED_WITHDRAWALS_KEY, []) + action.result.get(DSL_operators.CREATED_TRANSACTIONS_KEY, [])
        for action in actions
        if action.result and isinstance(action.result, dict) and (
            DSL_operators.CREATED_WITHDRAWALS_KEY in action.result or
            DSL_operators.CREATED_TRANSACTIONS_KEY in action.result
        )
    ]
    return list_util.flatten_list(withdrawal_lists) if withdrawal_lists else []


class TestOctoBotActionsJob:

    def setup_method(self):
        if message := misses_required_octobot_flow_client_import():
            pytest.skip(reason=message)
        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = True

    def teardown_method(self):
        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = False

    async def test_run_market_order_action(self, market_order_action):
        # step 1: configure the job
        job = octobot_flow_client.OctoBotActionsJob(market_order_action, [])
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value
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
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script == "market('buy', 'ETH/BTC', 1)"
        job2 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False), []
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script == "market('buy', 'ETH/BTC', 1)"
        assert len(get_created_orders(processed_actions)) == 1
        order = get_created_orders(processed_actions)[0]
        assert order["symbol"] == "ETH/BTC"
        assert order["amount"] == 1
        assert order["type"] == "market"
        assert order["side"] == "buy"
        assert result.has_next_actions is False # no more actions to execute

        # ensure deposit is successful
        post_deposit_portfolio = job2.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE] < pre_trade_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE]
        assert post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_TOTAL] < pre_trade_portfolio["BTC"][common_constants.PORTFOLIO_TOTAL]

        # bought ETH - fees
        assert 0.990 < post_deposit_portfolio["ETH"][common_constants.PORTFOLIO_AVAILABLE] <= 0.999
        assert 0.990 < post_deposit_portfolio["ETH"][common_constants.PORTFOLIO_TOTAL] <= 0.999

    async def test_run_limit_order_action(self, limit_order_action):
        # step 1: configure the job
        job = octobot_flow_client.OctoBotActionsJob(limit_order_action, [])
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value
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
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script == "limit('buy', 'ETH/BTC', 1, '-10%')"
        job2 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False), []
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script == "limit('buy', 'ETH/BTC', 1, '-10%')"
        assert len(get_created_orders(processed_actions)) == 1
        order = get_created_orders(processed_actions)[0]
        assert order["symbol"] == "ETH/BTC"
        assert order["amount"] == decimal.Decimal("1")
        assert decimal.Decimal("0.001") < order["price"] < decimal.Decimal("0.2")
        assert order["type"] == "limit"
        assert order["side"] == "buy"
        assert result.has_next_actions is False # no more actions to execute

    async def test_run_stop_loss_order_action(self, stop_loss_order_action):
        # step 1: configure the job
        job = octobot_flow_client.OctoBotActionsJob(stop_loss_order_action, [])
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value
        assert processed_actions[0].config is not None
        assert "automation" in processed_actions[0].config
        assert isinstance(processed_actions[0].config["exchange_account_details"], dict)
        pre_trade_portfolio = job.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["ETH"] == {
            common_constants.PORTFOLIO_AVAILABLE: 1,
            common_constants.PORTFOLIO_TOTAL: 1,
        }

        # step 2: run the trade action
        with mock.patch.object(
            # force stop loseses to be supported no matter the exchange
            order_factory.OrderFactory, "_ensure_supported_order_type", mock.Mock()
        ) as _ensure_supported_order_type:
            next_actions_description = result.next_actions_description
            assert next_actions_description is not None
            parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
            next_actions = parsed_state.automation.actions_dag.get_executable_actions()
            assert len(next_actions) == 1
            assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
            assert next_actions[0].dsl_script.startswith("stop_loss('sell', 'ETH/BTC', '10%', '-10%')")
            job2 = octobot_flow_client.OctoBotActionsJob(
                next_actions_description.to_dict(include_default_values=False), []
            )
            result = await job2.run()
            assert len(result.processed_actions) == 1
            processed_actions = result.processed_actions
            assert len(processed_actions) == 1
            assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
            assert processed_actions[0].dsl_script.startswith("stop_loss('sell', 'ETH/BTC', '10%', '-10%')")
            assert processed_actions[0].error_status is None
            assert len(get_created_orders(processed_actions)) == 1
            order = get_created_orders(processed_actions)[0]
            assert order["symbol"] == "ETH/BTC"
            assert order["amount"] == decimal.Decimal("0.1") # 10% of 1 ETH
            assert decimal.Decimal("0.001") < order["price"] < decimal.Decimal("0.2")
            assert order["type"] == "stop_loss"
            assert order["side"] == "sell"
            assert result.has_next_actions is False # no more actions to execute

    async def test_run_cancel_limit_order_after_instant_wait_action(self, create_limit_instant_wait_and_cancel_order_action):
        # step 1: configure the job
        job = octobot_flow_client.OctoBotActionsJob(create_limit_instant_wait_and_cancel_order_action, [])
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value
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
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script == "limit('buy', 'ETH/BTC', 1, '-10%')"
        job2 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False), []
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("limit(")
        assert len(get_created_orders(processed_actions)) == 1
        order = get_created_orders(processed_actions)[0]
        assert order["symbol"] == "ETH/BTC"
        assert order["amount"] == decimal.Decimal("1")
        assert decimal.Decimal("0.001") < order["price"] < decimal.Decimal("0.2")
        assert order["type"] == "limit"
        assert order["side"] == "buy"
        assert result.next_actions_description is not None

        # step 3: run the wait action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("wait(")
        job3 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False), []
        )
        result = await job3.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("wait(")
        # wait is waiting 0 seconds, so it should be executed immediately
        assert processed_actions[0].executed_at is not None and processed_actions[0].executed_at > 0 
        
        # step 4: run the cancel action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script == "cancel_order('ETH/BTC', side='buy')"
        job4 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False), []
        )
        result = await job4.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("cancel_order(")
        assert processed_actions[0].result is not None
        assert len(processed_actions[0].result[DSL_operators.CANCELLED_ORDERS_KEY]) == len(get_cancelled_orders(processed_actions)) == 1
        assert result.has_next_actions is False # no more actions to execute

    @pytest.mark.skip(reason="restore once polymarket is fully supported")
    async def test_polymarket_trade_action(self, polymarket_order_action): # TODO: update once polymarket is fullly supported
        # step 1: configure the job
        job = octobot_flow_client.OctoBotActionsJob(polymarket_order_action, [])
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value
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
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("market(")
        job2 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        with pytest.raises(octobot_trading.errors.FailedRequest): # TODO: update once supported
            result = await job2.run()
            assert len(result.processed_actions) == 1
            processed_actions = result.processed_actions
            assert len(processed_actions) == 1
            assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
            assert processed_actions[0].dsl_script.startswith("market(")
            assert len(get_created_orders(processed_actions)) == 1
            order = get_created_orders(processed_actions)[0]
            assert order["symbol"] == "what-price-will-bitcoin-hit-in-january-2026/USDC:USDC-260131-0-YES"
            assert order["amount"] == decimal.Decimal("1")
            assert order["type"] == "market"
            assert order["side"] == "buy"

    async def test_run_transfer_blockchain_only_action(self, transfer_blockchain_action):
        # step 1: configure the job
        job = octobot_flow_client.OctoBotActionsJob(transfer_blockchain_action, [])
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value
        assert processed_actions[0].config is not None
        assert "automation" in processed_actions[0].config
        assert job.after_execution_state.automation.reference_exchange_account_elements is None
        assert job.after_execution_state.automation.client_exchange_account_elements.portfolio.content == {}

        # step 2: run the transfer action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in next_actions[0].dsl_script
        job2 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in processed_actions[0].dsl_script
        assert result.has_next_actions is False # no more actions to execute

        assert processed_actions[0].result is not None
        assert len(processed_actions[0].result[DSL_operators.CREATED_TRANSACTIONS_KEY]) == len(get_deposit_and_withdrawal_details(processed_actions)) == 1
        assert len(get_deposit_and_withdrawal_details(processed_actions)) == 1
        transaction = get_deposit_and_withdrawal_details(processed_actions)[0]
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == "BTC"
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == decimal.Decimal("1")
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.NETWORK.value] == BLOCKCHAIN
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0x123_simulated_transfer_to_address_BTC"



    async def test_run_deposit_action(self, deposit_action):
        # step 1: configure the job
        job = octobot_flow_client.OctoBotActionsJob(deposit_action, [])
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value
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
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in next_actions[0].dsl_script
        job2 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in processed_actions[0].dsl_script
        assert result.has_next_actions is False # no more actions to execute

        # ensure deposit is successful
        post_deposit_portfolio = job2.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert post_deposit_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: pre_deposit_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE] + deposit_action["params"]["BLOCKCHAIN_FROM_AMOUNT"],
            common_constants.PORTFOLIO_TOTAL: pre_deposit_portfolio["BTC"][common_constants.PORTFOLIO_TOTAL] + deposit_action["params"]["BLOCKCHAIN_FROM_AMOUNT"],
        }

    async def test_run_withdraw_action(self, withdraw_action):
        # step 1: configure the job
        job = octobot_flow_client.OctoBotActionsJob(withdraw_action, [])
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value
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
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("withdraw(")
        job2 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("withdraw(")
        assert result.has_next_actions is False # no more actions to execute

        # ensure withdraw is successful
        post_withdraw_portfolio = job2.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert post_withdraw_portfolio == {}  # portfolio should now be empty

    async def test_run_multiple_actions_bundle_no_wait(self, multiple_actions_bundle_no_wait):
        # step 1: configure the job
        job = octobot_flow_client.OctoBotActionsJob(multiple_actions_bundle_no_wait, [])
        # ensure wait keywords have been considered
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value
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
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1 # only the deposit action should be executable as the trade action depends on it
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in next_actions[0].dsl_script
        job2 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in processed_actions[0].dsl_script
        assert processed_actions[0].result is not None
        assert len(processed_actions[0].result[DSL_operators.CREATED_TRANSACTIONS_KEY]) == len(get_deposit_and_withdrawal_details(processed_actions)) == 1
        assert len(get_deposit_and_withdrawal_details(processed_actions)) == 1
        transaction = get_deposit_and_withdrawal_details(processed_actions)[0]
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == "BTC"
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == decimal.Decimal("1")
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.NETWORK.value] == BLOCKCHAIN
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0x123_simulated_deposit_address_BTC"


        # step 3: run the trade action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1 # only the trade action should be executable now: all others have been executed already
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("limit(")
        job3 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        result = await job3.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("limit(")
        assert len(get_created_orders(processed_actions)) == 1
        limit_order = get_created_orders(processed_actions)[0]
        assert limit_order["symbol"] == "ETH/BTC"
        assert limit_order["amount"] == decimal.Decimal("1")
        assert limit_order["type"] == "limit"
        assert limit_order["side"] == "buy"
        assert result.has_next_actions is False # no more actions to execute

        # ensure trades are taken into account in portfolio
        post_deposit_portfolio = job3.after_execution_state.automation.client_exchange_account_elements.portfolio.content

        assert "ETH" not in post_deposit_portfolio # ETH order has not been executed (still open)

        assert post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_TOTAL] == 2
        # created a buy order but not executed: locked BTC in portfolio
        assert post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE] < post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_TOTAL]

    async def test_run_trade_and_loop_until_order_closed(self, trade_and_loop_until_order_closed):
        # Step 1 — Apply automation config (ACTIONS: trade, loop_until_order_closed).
        # The only runnable action is init/APPLY_CONFIGURATION; portfolio is seeded (e.g. BTC for the later market buy).
        job = octobot_flow_client.OctoBotActionsJob(trade_and_loop_until_order_closed, [])
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value
        assert processed_actions[0].config is not None
        assert "automation" in processed_actions[0].config
        assert isinstance(processed_actions[0].config["exchange_account_details"], dict)
        pre_trade_portfolio = job.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 1,
            common_constants.PORTFOLIO_TOTAL: 1,
        }

        # Step 2 — Run the market trade node (first executable after init). Produces created_orders data the DAG wires
        # into loop_until_order_closed via dependency::action_trade_1::created_orders::0::...
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script is not None and next_actions[0].dsl_script.startswith("market(")
        job2 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script is not None and processed_actions[0].dsl_script.startswith("market(")
        assert processed_actions[0].result is not None
        assert len(get_created_orders(processed_actions)) == 1
        order = get_created_orders(processed_actions)[0]
        assert order["symbol"] == "ETH/BTC"
        assert order["amount"] == 1
        assert order["type"] == "market"
        assert order["side"] == "buy"

        # Step 3 — loop_until_order_closed: DSL polls fetch_order until status != open (simulator reads orders_manager / trades).
        # Sanity-check the generated script before running it.
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        loop_dsl = next_actions[0].dsl_script
        assert loop_dsl is not None
        assert loop_dsl.startswith("loop_until(")
        assert "fetch_order" in loop_dsl
        assert f"!= '{trading_enums.OrderStatus.OPEN.value}'" in loop_dsl
        assert "3, timeout=10, max_attempts=4, return_remaining_time=True)" in loop_dsl
        job3 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        # Step 3a — First automation run: pretend the order is still open on the first fetch_order resolution only.
        # The real loop condition is fetch_order(...)["status"] != "open"; forcing "open" keeps it false once.
        # With return_remaining_time=True, loop_until does not block: it yields a ReCallingOperatorResult and leaves
        # the action pending for a later job run (same pattern as blockchain loop_until tests).
        fetch_resolution_attempt_counter = {"count": 0}
        real_simulated_fetch_resolve = fetch_order_operators_module._resolve_simulated_fetch_order_dict

        def resolve_simulated_order_first_fetch_reports_open_then_real(
            exchange_mgr, symbol_param, exchange_order_param
        ):
            order_dict = real_simulated_fetch_resolve(exchange_mgr, symbol_param, exchange_order_param)
            fetch_resolution_attempt_counter["count"] += 1
            if fetch_resolution_attempt_counter["count"] == 1:
                dict_with_open_status = dict(order_dict)
                dict_with_open_status[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] = (
                    trading_enums.OrderStatus.OPEN.value
                )
                return dict_with_open_status
            return order_dict

        with mock.patch.object(
            fetch_order_operators_module,
            "_resolve_simulated_fetch_order_dict",
            mock.Mock(side_effect=resolve_simulated_order_first_fetch_reports_open_then_real),
        ):
            result = await job3.run()
        # Expect the loop_until action to be re-scheduled, not completed.
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("loop_until(")
        assert processed_actions[0].executed_at is None
        assert processed_actions[0].result is None
        assert dsl_interpreter.ReCallingOperatorResult.is_re_calling_operator_result(
            processed_actions[0].previous_execution_result
        )
        assert result.next_actions_description is not None
        assert result.has_next_actions is True
        # Same loop_until node stays executable; previous_execution_result carries waiting_time for the scheduler.
        parsed_state = octobot_flow.AutomationState.from_dict(result.next_actions_description.state)
        next_actions_after_first_attempt = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions_after_first_attempt) == 1
        assert isinstance(next_actions_after_first_attempt[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions_after_first_attempt[0].dsl_script.startswith("loop_until(")
        assert next_actions_after_first_attempt[0].previous_execution_result
        last_loop_execution_result = dsl_interpreter.ReCallingOperatorResult.from_dict(
            next_actions_after_first_attempt[0].previous_execution_result[
                dsl_interpreter.ReCallingOperatorResult.__name__
            ]
        )
        assert last_loop_execution_result.last_execution_result is not None
        assert last_loop_execution_result.last_execution_result[
            dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value
        ] > 0

        # Step 3b — Second automation run: no patch; fetch_order sees the real status (non-open), condition is true,
        # loop_until completes and the DAG has no further executable actions.
        next_actions_description = result.next_actions_description
        job3b = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        result = await job3b.run()
        # trade is saved
        assert len(job3b.after_execution_state.automation.client_exchange_account_elements.trades) == 1
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("loop_until(")
        assert processed_actions[0].error_status is None
        assert processed_actions[0].result is True
        assert result.next_actions_description
        assert result.has_next_actions is False

    async def test_run_trade_transfer_and_check_balance_actions_bundle_no_wait(self, trade_transfer_and_check_balance_actions_bundle_no_wait):
        # step 1: configure the job (ACTIONS: trade, transfer, wait_for_blockchain_balance)
        job = octobot_flow_client.OctoBotActionsJob(trade_transfer_and_check_balance_actions_bundle_no_wait, [])
        result = await job.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value
        assert processed_actions[0].config is not None
        assert "automation" in processed_actions[0].config
        assert isinstance(processed_actions[0].config["exchange_account_details"], dict)
        pre_trade_portfolio = job.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 1,
            common_constants.PORTFOLIO_TOTAL: 1,
        }

        # step 2: run the market trade action (first executable after init)
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script is not None and next_actions[0].dsl_script.startswith("market(")
        job2 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        _real_create_order_instance = order_factory.create_order_instance

        def _create_order_instance_with_address_from(*args, **kwargs):
            order_instance = _real_create_order_instance(*args, **kwargs)
            order_instance.exchange_specific_order_values = {"address_from": "123_address_from"}
            return order_instance

        with mock.patch.object(
            order_factory, "create_order_instance",
            mock.Mock(side_effect=_create_order_instance_with_address_from),
        ) as create_order_instance_mock:
            result = await job2.run()
        assert len(result.processed_actions) == 1
        create_order_instance_mock.assert_called_once()
        assert create_order_instance_mock.mock_calls[0].kwargs["exchange_creation_params"] == {
            "address_to": "17ouWjN7nvPWkZKo2svTF81etXL6Qxnty7"
        }
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script is not None and processed_actions[0].dsl_script.startswith("market(")
        assert processed_actions[0].result is not None
        trade_result = processed_actions[0].result
        assert isinstance(trade_result, dict)
        assert (
            trade_result[DSL_operators.CREATED_ORDERS_KEY][0]["esov"]["address_from"]
            == "123_address_from"
        )
        assert len(get_created_orders(processed_actions)) == 1
        order = get_created_orders(processed_actions)[0]
        assert order["symbol"] == "ETH/BTC"
        assert order["type"] == "market"
        assert order["side"] == "buy"

        # step 3: transfer uses dependency::action_trade_1::created_orders::0::esov::address_from
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in next_actions[0].dsl_script
        job3 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        result = await job3.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in processed_actions[0].dsl_script
        assert processed_actions[0].result is not None
        assert len(processed_actions[0].result[DSL_operators.CREATED_TRANSACTIONS_KEY]) == 1
        assert len(get_deposit_and_withdrawal_details(processed_actions)) == 1
        transaction = get_deposit_and_withdrawal_details(processed_actions)[0]
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == "BTC"
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == decimal.Decimal("1")
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.NETWORK.value] == BLOCKCHAIN
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "123_address_from"

        # step 4.A: wait_for_blockchain_balance — mocked balance 0 triggers wait (re-call); automation not finished
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script is not None
        assert next_actions[0].dsl_script.startswith("loop_until(")
        assert "blockchain_wallet_balance" in next_actions[0].dsl_script
        assert "123_balance_address" in next_actions[0].dsl_script
        assert "3, timeout=10, max_attempts=4, return_remaining_time=True)" in next_actions[0].dsl_script
        job4 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        zero_btc_portfolio = {
            "BTC": {
                octobot_trading.constants.CONFIG_PORTFOLIO_FREE: decimal.Decimal(0),
                octobot_trading.constants.CONFIG_PORTFOLIO_USED: decimal.Decimal(0),
                octobot_trading.constants.CONFIG_PORTFOLIO_TOTAL: decimal.Decimal(0),
            }
        }
        with mock.patch.object(
            blockchain_wallet_simulator.BlockchainWalletSimulator,
            "get_balance",
            mock.AsyncMock(return_value=zero_btc_portfolio),
        ):
            result = await job4.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        wait_dsl = processed_actions[0].dsl_script
        assert wait_dsl is not None
        assert wait_dsl.startswith("loop_until(")
        assert "blockchain_wallet_balance" in wait_dsl
        # action got reset
        assert processed_actions[0].executed_at is None
        assert processed_actions[0].result is None
        assert dsl_interpreter.ReCallingOperatorResult.is_re_calling_operator_result(
            processed_actions[0].previous_execution_result
        )
        assert result.next_actions_description is not None
        parsed_state = octobot_flow.AutomationState.from_dict(result.next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("loop_until(")
        assert next_actions[0].previous_execution_result
        last_execution_result = dsl_interpreter.ReCallingOperatorResult.from_dict(
            next_actions[0].previous_execution_result[dsl_interpreter.ReCallingOperatorResult.__name__]
        )
        assert last_execution_result.last_execution_result is not None
        assert last_execution_result.last_execution_result[
            dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value
        ] > 0

        # step 4.B: real balance satisfies wait condition — action completes
        next_actions_description = result.next_actions_description
        assert result.has_next_actions is True
        job4b = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        result = await job4b.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("loop_until(value_if(")
        assert processed_actions[0].error_status is None
        assert processed_actions[0].result == 1.0  # return fetched balance
        assert result.next_actions_description
        assert result.has_next_actions is False


    async def test_run_multiple_actions_bundle_with_wait(self, multiple_action_bundle_with_wait):
        # step 1: configure the job
        job = octobot_flow_client.OctoBotActionsJob(multiple_action_bundle_with_wait, [])
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
        assert isinstance(processed_actions[0], octobot_flow.entities.ConfiguredActionDetails)
        assert processed_actions[0].action == octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value
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
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in next_actions[0].dsl_script
        job2 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        result = await job2.run()
        next_actions_description = result.next_actions_description
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script is not None and "blockchain_wallet_transfer" in processed_actions[0].dsl_script
        assert processed_actions[0].result is not None
        assert len(processed_actions[0].result[DSL_operators.CREATED_TRANSACTIONS_KEY]) == len(get_deposit_and_withdrawal_details(processed_actions)) == 1
        transaction = processed_actions[0].result[DSL_operators.CREATED_TRANSACTIONS_KEY][0]
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == "BTC"
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == decimal.Decimal("1")
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.NETWORK.value] == BLOCKCHAIN
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0x123_simulated_deposit_address_BTC"
        assert next_actions_description is not None
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("wait(")

        # step 3.A: run the wait action
        job3 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        result = await job3.run()
        next_actions_description = result.next_actions_description
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("wait(")
        # next action is wait again: waiting time has not been reached yet
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("wait(")
        assert next_actions[0].previous_execution_result
        last_execution_result = dsl_interpreter.ReCallingOperatorResult.from_dict(
            next_actions[0].previous_execution_result[dsl_interpreter.ReCallingOperatorResult.__name__]
        )
        waiting_time = last_execution_result.last_execution_result[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value]

        # step 3.B: complete the wait action
        with mock.patch.object(time, "time", mock.Mock(return_value=time.time() + waiting_time)):
            job4 = octobot_flow_client.OctoBotActionsJob(
                next_actions_description.to_dict(include_default_values=False),
                []
            )
            result = await job4.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("wait(")
        assert processed_actions[0].executed_at is not None and processed_actions[0].executed_at > 0 

        next_actions_description = result.next_actions_description
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("market(")
        post_deposit_portfolio = job2.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert post_deposit_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 2,
            common_constants.PORTFOLIO_TOTAL: 2,
        }

        # step 4: run the trade action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("market(")
        job5 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        result = await job5.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("market(")
        assert processed_actions[0].result is not None
        assert len(processed_actions[0].result[DSL_operators.CREATED_ORDERS_KEY]) == len(get_created_orders(processed_actions)) == 1
        post_trade_portfolio = job5.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert post_trade_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE] < post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE]
        assert 0.990 < post_trade_portfolio["ETH"][common_constants.PORTFOLIO_AVAILABLE] <= 0.999
        assert 0.990 < post_trade_portfolio["ETH"][common_constants.PORTFOLIO_TOTAL] <= 0.999
        # step 5.A: run the wait action
        next_actions_description = result.next_actions_description
        job6 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        result = await job6.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("wait(")
        assert processed_actions[0].previous_execution_result
        last_execution_result = dsl_interpreter.ReCallingOperatorResult.from_dict(
            processed_actions[0].previous_execution_result[dsl_interpreter.ReCallingOperatorResult.__name__]
        )
        waiting_time = last_execution_result.last_execution_result[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value]

        # step 5.B: complete the wait action
        next_actions_description = result.next_actions_description
        with mock.patch.object(time, "time", mock.Mock(return_value=time.time() + waiting_time)):
            job7 = octobot_flow_client.OctoBotActionsJob(
                next_actions_description.to_dict(include_default_values=False),
                []
            )
            result = await job7.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("wait(")
        assert processed_actions[0].executed_at is not None and processed_actions[0].executed_at > 0 



        # step 6: run the withdraw action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        parsed_state = octobot_flow.AutomationState.from_dict(next_actions_description.state)
        next_actions = parsed_state.automation.actions_dag.get_executable_actions()
        assert len(next_actions) == 1
        assert isinstance(next_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert next_actions[0].dsl_script.startswith("withdraw(")
        job8 = octobot_flow_client.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False),
            []
        )
        result = await job8.run()
        assert len(result.processed_actions) == 1
        processed_actions = result.processed_actions
        assert len(processed_actions) == 1
        assert isinstance(processed_actions[0], octobot_flow.entities.DSLScriptActionDetails)
        assert processed_actions[0].dsl_script.startswith("withdraw(")
        assert processed_actions[0].result is not None
        assert len(processed_actions[0].result[DSL_operators.CREATED_WITHDRAWALS_KEY]) == len(get_deposit_and_withdrawal_details(processed_actions)) == 1
        transaction = processed_actions[0].result[DSL_operators.CREATED_WITHDRAWALS_KEY][0]
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == "ETH"
        assert 0.990 < transaction[trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value] <= 0.999
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.NETWORK.value] == "ethereum"
        assert transaction[trading_enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0x1234567890123456789012345678901234567890"
        post_withdraw_portfolio = job8.after_execution_state.automation.client_exchange_account_elements.portfolio.content
        assert post_withdraw_portfolio["BTC"] == post_trade_portfolio["BTC"]
        assert "ETH" not in post_withdraw_portfolio
        assert result.has_next_actions is False # no more actions to execute
