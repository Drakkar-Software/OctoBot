import pytest

import octobot_commons.enums as common_enums
import octobot_commons.constants as common_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_flow
import octobot_flow.entities
import octobot_flow.enums

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import current_time, resolved_actions, automation_state_dict

import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading

increment = 200
spread = 600
grid_pair_settings = [
    grid_trading.GridTradingMode.get_default_pair_config(
        "BTC/USDC",
        spread,
        increment,
        2,
        2,
        False,
        False,
        False,
    )
]


def grid_trading_mode_action(dependency_action: dict):
    return {
        "id": "action_1",
        "dsl_script": (
            f"grid_trading_mode(pair_settings={dsl_interpreter.format_parameter_value(grid_pair_settings)})"
        ),
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
                            "USDC": {
                                "available": 1000.0,
                                "total": 1000.0,
                            }
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
                    "unit": "USDC",
                },
            },
        },
    }


@pytest.mark.asyncio
async def test_simulator_grid_init_from_empty_state(init_action: dict):
    all_actions = [init_action, grid_trading_mode_action(init_action)]
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

    # 2. run grid trading mode action
    async with octobot_flow.AutomationJob(after_init_execution_dump, [], {}) as automation_job:
        await automation_job.run()
    after_grid_execution_dump = automation_job.dump()
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
    assert after_grid_execution_dump["automation"]["execution"]["previous_execution"][
        "triggered_at"
    ] >= current_time
    one_hour = (
        common_enums.TimeFramesMinutes[common_enums.TimeFrames.ONE_HOUR]
        * common_constants.MINUTE_TO_SECONDS
    )
    allowed_execution_time = 20
    schedule_delay = (
        after_grid_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
        - after_grid_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
    )
    assert one_hour - allowed_execution_time < schedule_delay < one_hour + allowed_execution_time

    # check portfolio and open grid orders
    after_grid_portfolio_content = after_grid_execution_dump["automation"][
        "client_exchange_account_elements"
    ]["portfolio"]["content"]
    assert isinstance(after_grid_execution_dump, dict)
    assert list(sorted(after_grid_portfolio_content.keys())) == ["BTC", "USDC"]
    # applied portfolio optimizations and created grid open orders
    assert 450 < after_grid_portfolio_content["USDC"]["total"] < 550 # USDC holding split in half
    assert after_grid_portfolio_content["USDC"]["available"] < 100
    assert 0.001 < after_grid_portfolio_content["BTC"]["total"] < 0.02
    assert after_grid_portfolio_content["BTC"]["available"] < 0.001

    open_orders_origin_values = [
        order[trading_constants.STORAGE_ORIGIN_VALUE]
        for order in after_grid_execution_dump["automation"]["client_exchange_account_elements"]["orders"][
            "open_orders"
        ]
    ] 
    buy_orders = sorted([
        o for o in open_orders_origin_values if o[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.BUY.value
    ], key=lambda o: o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value])
    sell_orders = sorted([
        o for o in open_orders_origin_values if o[trading_enums.ExchangeConstantsOrderColumns.SIDE.value] == trading_enums.TradeOrderSide.SELL.value
    ], key=lambda o: o[trading_enums.ExchangeConstantsOrderColumns.PRICE.value])
    assert len(buy_orders) == len(sell_orders) == 2
    # check order prices are according to the grid settings
    lowest_buy_price = buy_orders[0][trading_enums.ExchangeConstantsOrderColumns.PRICE.value]
    assert buy_orders[1][trading_enums.ExchangeConstantsOrderColumns.PRICE.value] == lowest_buy_price + increment
    assert sell_orders[0][trading_enums.ExchangeConstantsOrderColumns.PRICE.value] == lowest_buy_price + increment + spread
    assert sell_orders[1][trading_enums.ExchangeConstantsOrderColumns.PRICE.value] == lowest_buy_price + increment + spread + increment

    # 3. trigger again: nothing to do
    async with octobot_flow.AutomationJob(after_grid_execution_dump, [], {}) as automation_job:
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
            assert action.executed_at is None
            assert isinstance(action.previous_execution_result, dict)

    schedule_delay = (
        after_second_call_execution_dump["automation"]["execution"]["current_execution"]["scheduled_to"]
        - after_second_call_execution_dump["automation"]["execution"]["previous_execution"]["triggered_at"]
    )
    assert one_hour - allowed_execution_time < schedule_delay < one_hour + allowed_execution_time

    after_second_call_portfolio_content = after_second_call_execution_dump["automation"][
        "client_exchange_account_elements"
    ]["portfolio"]["content"]
    assert after_second_call_portfolio_content == after_grid_portfolio_content
