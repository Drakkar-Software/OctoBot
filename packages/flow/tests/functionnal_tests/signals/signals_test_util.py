import mock
import time

import octobot_flow.enums as flow_enums
import octobot_flow.jobs
import octobot_flow.parsers.signal_script_resolver as signal_script_resolver
import octobot_flow.repositories.exchange
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

import tests.functionnal_tests as functionnal_tests
from tests.functionnal_tests import automation_state_dict, current_time, resolved_actions
from tests.functionnal_tests.trading_modes_actions.simulator import test_grid_trading_mode_action as grid_test


def init_action() -> dict:
    return {
        "id": "action_init",
        "action": flow_enums.ActionType.APPLY_CONFIGURATION.value,
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


def resolved_signal_dsl(signal_script: str) -> str:
    # Resolve signal keyval/JSON through the real signal_script_resolver.
    return signal_script_resolver.resolve_signal_script(
        signal_script,
        exchange_name=functionnal_tests.EXCHANGE_INTERNAL_NAME,
        exchange_type=trading_enums.ExchangeTypes.SPOT,
        reference_market="USDC",
    )


def priority_action(action_id: str, dsl_script: str) -> dict:
    return {
        "id": action_id,
        "dsl_script": dsl_script,
    }


def assert_historized_priority_actions(
    automation_state,
    expected_priority_actions: list,
    *,
    executed_at_min: float,
    expected_by_id: dict | None = None,
) -> None:
    expected_by_id = expected_by_id or {}
    assert automation_state.priority_actions == expected_priority_actions
    for action in expected_priority_actions:
        action_expectations = expected_by_id.get(action.id, {})
        expected_error_status = action_expectations.get(
            "error_status",
            flow_enums.ActionErrorStatus.NO_ERROR.value,
        )
        assert action.executed_at is not None
        assert action.executed_at >= executed_at_min
        assert action.error_status == expected_error_status
        if "error_message" in action_expectations:
            assert action.error_message == action_expectations["error_message"]
        elif expected_error_status == flow_enums.ActionErrorStatus.NO_ERROR.value:
            assert action.error_message is None
        if "result_is_none" in action_expectations:
            assert (action.result is None) == action_expectations["result_is_none"]


def open_order_counts_from_dump(automation_dump: dict) -> tuple[int, int, int]:
    # Count open buy/sell orders from automation dump storage format.
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


async def run_init_only(init_action_dict: dict) -> dict:
    # Run APPLY_CONFIGURATION init action and return dumped automation state.
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
        mock.patch.object(time, "time", return_value=current_time),
    ):
        automation_state = automation_state_dict(resolved_actions([init_action_dict]))
        async with octobot_flow.jobs.AutomationJob(automation_state, [], [], {}) as automation_job:
            await automation_job.run()
        return automation_job.dump()


async def run_simulator_grid_bootstrap(init_action_dict: dict) -> dict:
    # 1. Patch tickers/OHLCV to fixed BTC/USDC close (grid determinism)
    patched_fetch_tickers = grid_test.tickers_repository_fetch_tickers_btc_usdc_close_override(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    patched_fetch_ohlcv = grid_test.fetch_ohlcv_side_effect_for_close_price(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE
    )
    grid_action = grid_test.grid_trading_mode_action(init_action_dict)
    all_actions = [init_action_dict, grid_action]
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
        # 2. Run init action job
        async with octobot_flow.jobs.AutomationJob(automation_state, [], [], {}) as init_automation_job:
            await init_automation_job.run()
        after_init_execution_dump = init_automation_job.dump()
        # 3. Run grid trading mode action on dumped state
        async with octobot_flow.jobs.AutomationJob(after_init_execution_dump, [], [], {}) as grid_automation_job:
            await grid_automation_job.run()
        # 4. Return final dump with open orders
        return grid_automation_job.dump()
