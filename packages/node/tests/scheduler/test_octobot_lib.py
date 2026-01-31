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

import octobot_node.scheduler.octobot_lib as octobot_lib
import octobot_commons.constants as common_constants
RUN_TESTS = True
try:
    import octobot_trading.constants
    import octobot_trading.errors

    import octobot_wrapper.keywords.internal.overrides.custom_action_trading_mode as custom_action_trading_mode
    import octobot_wrapper.keywords.internal.constants as kw_constants
    import octobot_wrapper.keywords.internal.enums as kw_enums

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
def create_limit_and_cancel_order_action(limit_order_action, cancel_order_action):
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
                "MIN_DELAY": 0.1,
                "MAX_DELAY": 0.15,
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
        # step 1: configure the task
        job = octobot_lib.OctoBotActionsJob(market_order_action)
        result = await job.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == kw_enums.CustomActionExclusiveFormattedContentConfigKeys.APPLY_CONFIGURATION.value
        pre_trade_portfolio = job.after_execution_state.bots[0].exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 1,
            common_constants.PORTFOLIO_TOTAL: 1,
        }

        # step 2: run the trade action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        assert len(next_actions_description.immediate_actions) == 1
        assert next_actions_description.immediate_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.BUY_SIGNAL
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.BUY_SIGNAL
        assert len(result.get_created_orders()) == 1
        order = result.get_created_orders()[0]
        assert order["symbol"] == "ETH/BTC"
        assert order["amount"] == 1
        assert order["type"] == "market"
        assert order["side"] == "buy"
        assert result.next_actions_description is None # no more actions to execute

        # ensure deposit is successful
        post_deposit_portfolio = job2.after_execution_state.bots[0].exchange_account_elements.portfolio.content
        assert post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE] < pre_trade_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE]
        assert post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_TOTAL] < pre_trade_portfolio["BTC"][common_constants.PORTFOLIO_TOTAL]

        # bought ETH - fees
        assert post_deposit_portfolio["ETH"][common_constants.PORTFOLIO_AVAILABLE] == 0.999
        assert post_deposit_portfolio["ETH"][common_constants.PORTFOLIO_TOTAL] == 0.999

    async def test_run_limit_order_action(self, limit_order_action):
        # step 1: configure the task
        job = octobot_lib.OctoBotActionsJob(limit_order_action)
        result = await job.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == kw_enums.CustomActionExclusiveFormattedContentConfigKeys.APPLY_CONFIGURATION.value
        pre_trade_portfolio = job.after_execution_state.bots[0].exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 1,
            common_constants.PORTFOLIO_TOTAL: 1,
        }

        # step 2: run the trade action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        assert len(next_actions_description.immediate_actions) == 1
        assert next_actions_description.immediate_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.BUY_SIGNAL
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.BUY_SIGNAL
        assert len(result.get_created_orders()) == 1
        order = result.get_created_orders()[0]
        assert order["symbol"] == "ETH/BTC"
        assert order["amount"] == 1
        assert 0.001 < order["limit_price"] < 0.2
        assert order["type"] == "limit"
        assert order["side"] == "buy"
        assert result.next_actions_description is None # no more actions to execute

    async def test_run_stop_loss_order_action(self, stop_loss_order_action):
        # step 1: configure the task
        job = octobot_lib.OctoBotActionsJob(stop_loss_order_action)
        result = await job.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == kw_enums.CustomActionExclusiveFormattedContentConfigKeys.APPLY_CONFIGURATION.value
        pre_trade_portfolio = job.after_execution_state.bots[0].exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["ETH"] == {
            common_constants.PORTFOLIO_AVAILABLE: 1,
            common_constants.PORTFOLIO_TOTAL: 1,
        }

        # step 2: run the trade action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        assert len(next_actions_description.immediate_actions) == 1
        assert next_actions_description.immediate_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.SELL_SIGNAL
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.SELL_SIGNAL
        assert len(result.get_created_orders()) == 1
        order = result.get_created_orders()[0]
        assert order["symbol"] == "ETH/BTC"
        assert order["amount"] == 0.1 # 10% of 1 ETH
        assert 0.001 < order["limit_price"] < 0.2
        assert order["type"] == "stop_loss"
        assert order["side"] == "sell"
        assert result.next_actions_description is None # no more actions to execute

    async def test_run_cancel_limit_order_action(self, create_limit_and_cancel_order_action):
        # step 1: configure the task
        job = octobot_lib.OctoBotActionsJob(create_limit_and_cancel_order_action)
        result = await job.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == kw_enums.CustomActionExclusiveFormattedContentConfigKeys.APPLY_CONFIGURATION.value
        pre_trade_portfolio = job.after_execution_state.bots[0].exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 1,
            common_constants.PORTFOLIO_TOTAL: 1,
        }

        # step 2: run the trade action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        assert len(next_actions_description.immediate_actions) == 1
        assert next_actions_description.immediate_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.BUY_SIGNAL
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.BUY_SIGNAL
        assert len(result.get_created_orders()) == 1
        order = result.get_created_orders()[0]
        assert order["symbol"] == "ETH/BTC"
        assert order["amount"] == 1
        assert 0.001 < order["limit_price"] < 0.2
        assert order["type"] == "limit"
        assert order["side"] == "buy"
        assert result.next_actions_description is not None

        # step 3: run the cancel action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        assert len(next_actions_description.immediate_actions) == 1
        assert next_actions_description.immediate_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.CANCEL_SIGNAL
        job3 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job3.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.CANCEL_SIGNAL
        assert result.processed_actions[0].result["cancelled_orders_count"] == 1
        assert result.next_actions_description is None # no more actions to execute

    async def test_polymarket_trade_action(self, polymarket_order_action): # TODO: update once polymarket is fullly supported
        # step 1: configure the task
        job = octobot_lib.OctoBotActionsJob(polymarket_order_action)
        result = await job.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == kw_enums.CustomActionExclusiveFormattedContentConfigKeys.APPLY_CONFIGURATION.value
        pre_trade_portfolio = job.after_execution_state.bots[0].exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["USDC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 100,
            common_constants.PORTFOLIO_TOTAL: 100,
        }

        # step 2: run the trade action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        assert len(next_actions_description.immediate_actions) == 1
        assert next_actions_description.immediate_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.BUY_SIGNAL
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        with pytest.raises(octobot_trading.errors.FailedRequest): # TODO: update once supported
            result = await job2.run()
            assert len(result.processed_actions) == 1
            assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.BUY_SIGNAL
            assert len(result.get_created_orders()) == 1
            order = result.get_created_orders()[0]
            assert order["symbol"] == "what-price-will-bitcoin-hit-in-january-2026/USDC:USDC-260131-0-YES"
            assert order["amount"] == 1
            assert order["type"] == "market"
            assert order["side"] == "buy"

    async def test_run_deposit_action(self, deposit_action):
        # step 1: configure the task
        job = octobot_lib.OctoBotActionsJob(deposit_action)
        result = await job.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == kw_enums.CustomActionExclusiveFormattedContentConfigKeys.APPLY_CONFIGURATION.value
        pre_deposit_portfolio = job.after_execution_state.bots[0].exchange_account_elements.portfolio.content
        assert pre_deposit_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 0.01,
            common_constants.PORTFOLIO_TOTAL: 0.01,
        }

        # step 2: run the deposit action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        assert len(next_actions_description.immediate_actions) == 1
        assert next_actions_description.immediate_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.TRANSFER_FUNDS_SIGNAL
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.TRANSFER_FUNDS_SIGNAL
        assert result.next_actions_description is None # no more actions to execute

        # ensure deposit is successful
        post_deposit_portfolio = job2.after_execution_state.bots[0].exchange_account_elements.portfolio.content
        assert post_deposit_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: pre_deposit_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE] + deposit_action["params"]["BLOCKCHAIN_FROM_AMOUNT"],
            common_constants.PORTFOLIO_TOTAL: pre_deposit_portfolio["BTC"][common_constants.PORTFOLIO_TOTAL] + deposit_action["params"]["BLOCKCHAIN_FROM_AMOUNT"],
        }

    async def test_run_withdraw_action(self, withdraw_action):
        # step 1: configure the task
        job = octobot_lib.OctoBotActionsJob(withdraw_action)
        result = await job.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == kw_enums.CustomActionExclusiveFormattedContentConfigKeys.APPLY_CONFIGURATION.value
        pre_withdraw_portfolio = job.after_execution_state.bots[0].exchange_account_elements.portfolio.content
        assert pre_withdraw_portfolio["ETH"] == {
            common_constants.PORTFOLIO_AVAILABLE: 2,
            common_constants.PORTFOLIO_TOTAL: 2,
        }

        # step 2: run the withdraw action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        assert len(next_actions_description.immediate_actions) == 1
        assert next_actions_description.immediate_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.WITHDRAW_FUNDS_SIGNAL
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.WITHDRAW_FUNDS_SIGNAL
        assert result.next_actions_description is None # no more actions to execute

        # ensure withdraw is successful
        post_withdraw_portfolio = job2.after_execution_state.bots[0].exchange_account_elements.portfolio.content
        assert post_withdraw_portfolio == {}  # portfolio should now be empty

    async def test_run_multiple_actions_bundle_no_wait(self, multiple_actions_bundle_no_wait):
        # step 1: configure the task
        job = octobot_lib.OctoBotActionsJob(multiple_actions_bundle_no_wait)
        result = await job.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == kw_enums.CustomActionExclusiveFormattedContentConfigKeys.APPLY_CONFIGURATION.value
        pre_trade_portfolio = job.after_execution_state.bots[0].exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 1,
            common_constants.PORTFOLIO_TOTAL: 1,
        }

        # step 2: run the deposit and trade actions
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        assert len(next_actions_description.immediate_actions) == 2
        assert next_actions_description.immediate_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.TRANSFER_FUNDS_SIGNAL
        assert next_actions_description.immediate_actions[1].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.BUY_SIGNAL
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 2
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.TRANSFER_FUNDS_SIGNAL
        assert result.processed_actions[0].result["amount"] == 1
        assert result.processed_actions[1].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.BUY_SIGNAL
        assert len(result.get_created_orders()) == 1
        limit_order = result.get_created_orders()[0]
        assert limit_order["symbol"] == "ETH/BTC"
        assert limit_order["amount"] == 1
        assert limit_order["type"] == "limit"
        assert limit_order["side"] == "buy"
        assert result.next_actions_description is None # no more actions to execute

        # ensure trades are taken into account in portfolio
        post_deposit_portfolio = job2.after_execution_state.bots[0].exchange_account_elements.portfolio.content

        assert "ETH" not in post_deposit_portfolio # ETH order has not been executed (still open)

        assert post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_TOTAL] == 2
        # created a buy order but not executed: locked BTC in portfolio
        assert post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE] < post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_TOTAL]


    async def test_run_multiple_actions_bundle_with_wait(self, multiple_action_bundle_with_wait):
        # step 1: configure the task
        job = octobot_lib.OctoBotActionsJob(multiple_action_bundle_with_wait)
        result = await job.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == kw_enums.CustomActionExclusiveFormattedContentConfigKeys.APPLY_CONFIGURATION.value
        pre_trade_portfolio = job.after_execution_state.bots[0].exchange_account_elements.portfolio.content
        assert pre_trade_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 1,
            common_constants.PORTFOLIO_TOTAL: 1,
        }

        # step 2: run the deposit action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        assert len(next_actions_description.immediate_actions) == 1
        assert next_actions_description.immediate_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.TRANSFER_FUNDS_SIGNAL
        job2 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job2.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.TRANSFER_FUNDS_SIGNAL
        assert result.processed_actions[0].result["amount"] == 1
        assert result.next_actions_description is not None
        assert len(result.next_actions_description.immediate_actions) == 1
        assert result.next_actions_description.immediate_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.BUY_SIGNAL
        post_deposit_portfolio = job2.after_execution_state.bots[0].exchange_account_elements.portfolio.content
        assert post_deposit_portfolio["BTC"] == {
            common_constants.PORTFOLIO_AVAILABLE: 2,
            common_constants.PORTFOLIO_TOTAL: 2,
        }

        # step 3: run the trade action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        assert len(next_actions_description.immediate_actions) == 1
        assert next_actions_description.immediate_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.BUY_SIGNAL
        job3 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job3.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.BUY_SIGNAL
        assert len(result.get_created_orders()) == 1
        post_trade_portfolio = job3.after_execution_state.bots[0].exchange_account_elements.portfolio.content
        assert post_trade_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE] < post_deposit_portfolio["BTC"][common_constants.PORTFOLIO_AVAILABLE]
        assert post_trade_portfolio["ETH"] == {
            common_constants.PORTFOLIO_AVAILABLE: 0.999,
            common_constants.PORTFOLIO_TOTAL: 0.999,
        }

        # step 4: run the withdraw action
        next_actions_description = result.next_actions_description
        assert next_actions_description is not None
        assert len(next_actions_description.immediate_actions) == 1
        assert next_actions_description.immediate_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.WITHDRAW_FUNDS_SIGNAL
        job4 = octobot_lib.OctoBotActionsJob(
            next_actions_description.to_dict(include_default_values=False)
        )
        result = await job4.run()
        assert len(result.processed_actions) == 1
        assert result.processed_actions[0].config[kw_constants.CUSTOM_ACTION_OPEN_SOURCE_FORMAT_KEY][custom_action_trading_mode.CustomActionTradingMode.SIGNAL_KEY] == custom_action_trading_mode.CustomActionTradingMode.WITHDRAW_FUNDS_SIGNAL
        assert result.processed_actions[0].result["amount"] == 0.999
        post_withdraw_portfolio = job4.after_execution_state.bots[0].exchange_account_elements.portfolio.content
        assert post_withdraw_portfolio["BTC"] == post_trade_portfolio["BTC"]
        assert "ETH" not in post_withdraw_portfolio
        assert result.next_actions_description is None # no more actions to execute
