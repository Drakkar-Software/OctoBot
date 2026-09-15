import pytest
import mock
import time

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_flow.jobs
import octobot_flow.enums
import octobot_flow.repositories.exchange
import octobot_flow.logic.exchange.simulator.simulated_exchange_account_resolver as simulated_exchange_account_resolver

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import (
    current_time,
    resolved_actions,
    automation_state_dict,
)
from tests.functionnal_tests.trading_modes_actions.simulator import test_grid_trading_mode_action as grid_test


def _open_order_counts_from_dump(automation_dump: dict) -> tuple[int, int, int]:
    exchange_elements = automation_dump["automation"]["exchange_account_elements"]
    open_orders = exchange_elements["orders"]["open_orders"]
    buy_count = 0
    sell_count = 0
    for wrapped_order in open_orders:
        order_details = wrapped_order.get(trading_constants.STORAGE_ORIGIN_VALUE, wrapped_order)
        side = order_details[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
        if side == trading_enums.TradeOrderSide.BUY.value:
            buy_count += 1
        elif side == trading_enums.TradeOrderSide.SELL.value:
            sell_count += 1
    trade_count = len(exchange_elements.get("trades", []))
    return buy_count, sell_count, trade_count


async def _run_simulator_grid_bootstrap(init_action: dict) -> dict:
    patched_fetch_tickers = grid_test.tickers_repository_fetch_tickers_btc_usdc_close_override(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    patched_fetch_ohlcv = grid_test.fetch_ohlcv_side_effect_for_close_price(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    grid_action = grid_test.grid_trading_mode_action(init_action)
    all_actions = [init_action, grid_action]
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
        mock.patch.object(time, "time", return_value=current_time),
        mock.patch.object(
            octobot_flow.repositories.exchange.TickersRepository,
            "fetch_tickers",
            new=patched_fetch_tickers,
        ),
        mock.patch.object(
            octobot_flow.repositories.exchange.OhlcvRepository,
            "fetch_ohlcv",
            side_effect=patched_fetch_ohlcv,
        ),
    ):
        automation_state = automation_state_dict(resolved_actions(all_actions))
        async with octobot_flow.jobs.AutomationJob(automation_state, [], [], {}) as init_automation_job:
            await init_automation_job.run()
        after_init_execution_dump = init_automation_job.dump()
        async with octobot_flow.jobs.AutomationJob(after_init_execution_dump, [], [], {}) as grid_automation_job:
            await grid_automation_job.run()
        return grid_automation_job.dump()


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
                "exchange_account_elements": {
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


@pytest.fixture
def stop_automation_action():
    return {
        "id": "action_stop",
        "dsl_script": "stop_automation()",
        "dependencies": [
            {"action_id": "action_init"},
        ],
    }


@pytest.fixture
def random_action():
    return {
        "id": "action_random",
        "dsl_script": "'yes' if 1 == 2 else 'no'",
        "dependencies": [
            {"action_id": "action_init"},
        ],
    }

@pytest.mark.asyncio
async def test_stop_automation_action_sets_post_actions_stop_flag(
    init_action: dict,
    stop_automation_action: dict,
):
    all_actions = [init_action, stop_automation_action]
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
        mock.patch.object(time, "time", return_value=current_time),
    ):
        # 1. Initialize with configuration (only init action is executed)
        automation_state = automation_state_dict(resolved_actions(all_actions))
        async with octobot_flow.jobs.AutomationJob(automation_state, [], [], {}) as init_automation_job:
            await init_automation_job.run()
        assert init_automation_job.automation_state.automation.post_actions.stop_automation is False

        # 2. Run again to execute the stop_automation action
        after_config_execution_dump = init_automation_job.dump()
        state = after_config_execution_dump
        async with octobot_flow.jobs.AutomationJob(state, [], [], {}) as automation_job:
            await automation_job.run()

        # 3. Verify stop_automation action was executed and post_actions.stop_automation is set
        actions = automation_job.automation_state.automation.actions_dag.actions
        assert len(actions) == len(all_actions)
        for action in actions:
            assert action.error_status == octobot_flow.enums.ActionErrorStatus.NO_ERROR.value
            assert action.executed_at and action.executed_at >= current_time

        assert automation_job.automation_state.automation.post_actions.stop_automation is True
        assert automation_job.automation_state.priority_actions == []


@pytest.mark.asyncio
async def test_stop_automation_action_via_priority_actions_sets_post_actions_stop_flag(
    init_action: dict,
    stop_automation_action: dict,
    random_action: dict,
):
    all_actions = [init_action, random_action]
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
        mock.patch.object(time, "time", return_value=current_time),
    ):
        # 1. Initialize with configuration (only init action is executed)
        automation_state = automation_state_dict(resolved_actions(all_actions))
        async with octobot_flow.jobs.AutomationJob(automation_state, [], [], {}) as init_automation_job:
            await init_automation_job.run()
        assert init_automation_job.automation_state.automation.post_actions.stop_automation is False
        # check random action is not executed
        assert init_automation_job.automation_state.automation.actions_dag.actions[1].result is None
        assert init_automation_job.automation_state.automation.actions_dag.actions[1].executed_at is None

        # 2. Run again with stop_automation_action as priority_actions
        after_config_execution_dump = init_automation_job.dump()
        state = after_config_execution_dump
        priority_actions = resolved_actions([stop_automation_action])
        async with octobot_flow.jobs.AutomationJob(state, priority_actions, [], {}) as automation_job:
            await automation_job.run()
        # check random action is not executed
        assert init_automation_job.automation_state.automation.actions_dag.actions[1].result is None
        assert init_automation_job.automation_state.automation.actions_dag.actions[1].executed_at is None

        # check stop_automation action is executed
        assert priority_actions[0].executed_at is not None and priority_actions[0].executed_at >= current_time

        # 3. Verify stop_automation action was executed and post_actions.stop_automation is set
        assert automation_job.automation_state.automation.post_actions.stop_automation is True
        assert automation_job.automation_state.priority_actions == priority_actions
        # ensure priority_actions is added to history


@pytest.mark.asyncio
async def test_stop_automation_cancel_orders_clears_open_orders(init_action: dict):
    after_grid_dump = await _run_simulator_grid_bootstrap(init_action)
    buy_count, sell_count, trade_count = _open_order_counts_from_dump(after_grid_dump)
    assert buy_count >= 2
    assert sell_count >= 2
    assert trade_count == 1

    stop_automation_action_cancel = {
        "id": "action_stop",
        "dsl_script": "stop_automation(cancel_orders=True)",
        "dependencies": [{"action_id": init_action["id"]}],
    }
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
        mock.patch.object(time, "time", return_value=current_time),
        mock.patch.object(
            simulated_exchange_account_resolver.SimulatedExchangeAccountResolver,
            "resolve",
            mock.AsyncMock(),
        ),
    ):
        priority_actions = resolved_actions([stop_automation_action_cancel])
        async with octobot_flow.jobs.AutomationJob(after_grid_dump, priority_actions, [], {}) as automation_job:
            await automation_job.run()

        assert automation_job.automation_state.automation.post_actions.stop_automation is True
        final_buy_count, final_sell_count, final_trade_count = _open_order_counts_from_dump(
            automation_job.dump()
        )
        assert final_buy_count == 0
        assert final_sell_count == 0
        assert final_trade_count == 1


@pytest.mark.asyncio
async def test_stop_automation_cancel_orders_false_preserves_open_orders(init_action: dict):
    after_grid_dump = await _run_simulator_grid_bootstrap(init_action)
    buy_count, sell_count, trade_count = _open_order_counts_from_dump(after_grid_dump)
    assert buy_count >= 2
    assert sell_count >= 2
    assert trade_count == 1

    stop_automation_action_plain = {
        "id": "action_stop",
        "dsl_script": "stop_automation()",
        "dependencies": [{"action_id": init_action["id"]}],
    }
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
        mock.patch.object(time, "time", return_value=current_time),
        mock.patch.object(
            simulated_exchange_account_resolver.SimulatedExchangeAccountResolver,
            "resolve",
            mock.AsyncMock(),
        ),
    ):
        priority_actions = resolved_actions([stop_automation_action_plain])
        async with octobot_flow.jobs.AutomationJob(after_grid_dump, priority_actions, [], {}) as automation_job:
            await automation_job.run()

        assert automation_job.automation_state.automation.post_actions.stop_automation is True
        final_buy_count, final_sell_count, final_trade_count = _open_order_counts_from_dump(
            automation_job.dump()
        )
        assert final_buy_count == buy_count
        assert final_sell_count == sell_count
        assert final_trade_count == trade_count
