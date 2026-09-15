import contextlib
import mock
import time

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.str_util as str_util

import octobot_flow.enums as flow_enums
import octobot_flow.jobs
import octobot_flow.parsers.signal_script_resolver as signal_script_resolver
import octobot_flow.repositories.exchange
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums

import tentacles.Trading.Mode.dca_trading_mode.dca_trading as dca_trading

import tests.functionnal_tests as functionnal_tests
import tests.functionnal_tests.tentacle_test_configs as tentacle_test_configs
from tests.functionnal_tests import automation_state_dict, current_time, resolved_actions
from tests.functionnal_tests.trading_modes_actions.simulator import test_dca_trading_mode_action as dca_test
from tests.functionnal_tests.trading_modes_actions.simulator import test_grid_trading_mode_action as grid_test

_DCA_TRADING_MODE_DSL_OPERATOR = str_util.camel_to_snake(dca_trading.DCATradingMode.get_name())
BTC_ONLY_DCA_CONFIG = tentacle_test_configs.binanceus_dca_tentacle_config(
    **{
        dca_trading.DCATradingMode.TRADING_PAIRS: [dca_test.BTC_USDC],
    }
)


def cross_symbol_stable_close_by_symbol() -> dict[str, float]:
    return {
        dca_test.BTC_USDC: dca_test._FIXED_BTC_USDC_CLOSE,
        dca_test.ETH_USDC: dca_test._FIXED_ETH_USDC_CLOSE,
    }


@contextlib.contextmanager
def patch_cross_symbol_simulator_exchange_prices():
    close_by_symbol = cross_symbol_stable_close_by_symbol()
    with dca_test.patch_dca_simulator_exchange_prices(
        lambda symbol: close_by_symbol[symbol],
    ) as exchange_price_mock_calls:
        yield exchange_price_mock_calls


def btc_only_dca_action(dependency_action: dict) -> dict:
    config_parts = ", ".join(
        f"{key}={dsl_interpreter.format_parameter_value(value)}"
        for key, value in BTC_ONLY_DCA_CONFIG.items()
    )
    return {
        "id": "action_dca",
        "dsl_script": f"{_DCA_TRADING_MODE_DSL_OPERATOR}({config_parts})",
        "dependencies": [{"action_id": dependency_action["id"]}],
    }


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


def limit_buy_below_market_priority_action(
    action_id: str = "priority_limit_buy",
    *,
    symbol: str = dca_test.BTC_USDC,
    volume: float = 0.01,
    price_offset_percent: str = "-20%",
) -> dict:
    return priority_action(
        action_id,
        f"limit('buy', '{symbol}', {volume}, '{price_offset_percent}')",
    )


def stop_automation_priority_action(*, cancel_orders: bool = False) -> dict:
    if cancel_orders:
        return priority_action("priority_stop", "stop_automation(cancel_orders=True)")
    return priority_action("priority_stop", "stop_automation()")


def eth_buy_with_take_profit_priority_action(action_id: str = "priority_eth_buy_tp") -> dict:
    eth_buy_dsl = resolved_signal_dsl(
        "SYMBOL=ETH/USDC\nSIGNAL=buy\nVOLUME=0.01\nTAKE_PROFIT_PRICE=10%",
    )
    return priority_action(action_id, eth_buy_dsl)


@contextlib.contextmanager
def patch_limit_buy_simulator_exchange_prices():
    patched_fetch_tickers = grid_test.tickers_repository_fetch_tickers_btc_usdc_close_override(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE,
    )
    patched_fetch_ohlcv = grid_test.fetch_ohlcv_side_effect_for_close_price(
        lambda: grid_test._FIXED_BTC_USDC_CLOSE,
    )
    with (
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
        yield


@contextlib.contextmanager
def patch_cross_symbol_fill_prices(close_by_symbol: dict[str, float] | None = None):
    close_by_symbol = close_by_symbol or cross_symbol_stable_close_by_symbol()
    with dca_test.patch_dca_simulator_exchange_prices(
        lambda symbol: close_by_symbol[symbol],
    ):
        yield close_by_symbol


def assert_recall_when_relevant_for_context_scheduled_seconds(
    automation_dump: dict,
    expected_seconds: float,
    *,
    tolerance: float = 0.5,
    reference_time: float | None = None,
) -> None:
    reference_time = current_time if reference_time is None else reference_time
    execution = automation_dump["automation"]["execution"]["current_execution"]
    scheduled_to = execution["scheduled_to"]
    recall_when_relevant_for_context_action = automation_dump["automation"]["actions_dag"]["actions"][1]
    recall_result = recall_when_relevant_for_context_action.get("previous_execution_result", {})
    recall_inner = recall_result.get("ReCallingOperatorResult", {}).get("last_execution_result", {})
    scheduled_delta = scheduled_to - reference_time
    assert expected_seconds - tolerance <= scheduled_delta <= expected_seconds + tolerance, (
        f"expected scheduled_to ~{expected_seconds}s from reference time, got {scheduled_delta}s; "
        f"waiting_time={recall_inner.get('waiting_time')}"
    )
    assert recall_inner.get("waiting_time") == expected_seconds


async def run_automation_job_on_dump(
    automation_dump: dict,
    priority_actions: list | None = None,
    *,
    execution_time: float | None = None,
) -> tuple[octobot_flow.jobs.AutomationJob, dict, list]:
    priority_actions = priority_actions or []
    patched_time = current_time if execution_time is None else execution_time
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
        mock.patch.object(time, "time", return_value=patched_time),
    ):
        async with octobot_flow.jobs.AutomationJob(
            automation_dump,
            priority_actions,
            [],
            {},
        ) as automation_job:
            executed_actions = await automation_job.run()
        return automation_job, automation_job.dump(), executed_actions


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


def open_order_symbols_from_dump(automation_dump: dict) -> set[str]:
    exchange_elements = automation_dump["automation"]["exchange_account_elements"]
    order_symbols = set()
    orders = exchange_elements["orders"]
    for wrapped_order in list(orders["open_orders"]) + list(orders.get("missing_orders", [])):
        order_details = wrapped_order.get(trading_constants.STORAGE_ORIGIN_VALUE, wrapped_order)
        symbol = order_details.get(trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value)
        if symbol:
            order_symbols.add(symbol)
    return order_symbols


def assert_open_order_symbols_include(
    automation_dump: dict,
    expected_symbols: set[str],
) -> None:
    order_symbols = open_order_symbols_from_dump(automation_dump)
    assert expected_symbols.issubset(order_symbols), (
        f"expected open order symbols {expected_symbols}, got {order_symbols}"
    )


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


def signal_bot_recall_when_relevant_for_context_action(dependency_action: dict) -> dict:
    return {
        "id": "action_recall_when_relevant_for_context",
        "dsl_script": (
            "recall_when_relevant_for_context(with_open_trades_seconds=5, without_open_trades_seconds=10, "
            "return_remaining_time=True)"
        ),
        "dependencies": [{"action_id": dependency_action["id"]}],
    }


async def run_signal_bot_bootstrap(init_action_dict: dict) -> dict:
    recall_when_relevant_for_context_action = signal_bot_recall_when_relevant_for_context_action(init_action_dict)
    all_actions = [init_action_dict, recall_when_relevant_for_context_action]
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
        mock.patch.object(time, "time", return_value=current_time),
    ):
        automation_state = automation_state_dict(resolved_actions(all_actions))
        async with octobot_flow.jobs.AutomationJob(automation_state, [], [], {}) as init_automation_job:
            await init_automation_job.run()
        after_init_execution_dump = init_automation_job.dump()
        async with octobot_flow.jobs.AutomationJob(after_init_execution_dump, [], [], {}) as signal_bot_job:
            await signal_bot_job.run()
        return signal_bot_job.dump()


async def run_simulator_dca_bootstrap(init_action_dict: dict) -> dict:
    # Run init + BTC-only DCA actions; caller must apply patch_cross_symbol_simulator_exchange_prices().
    dca_action = btc_only_dca_action(init_action_dict)
    all_actions = [init_action_dict, dca_action]
    with (
        functionnal_tests.mocked_community_authentication(),
        functionnal_tests.mocked_community_repository(),
        mock.patch.object(time, "time", return_value=current_time),
    ):
        automation_state = automation_state_dict(resolved_actions(all_actions))
        async with octobot_flow.jobs.AutomationJob(automation_state, [], [], {}) as init_automation_job:
            await init_automation_job.run()
        after_init_execution_dump = init_automation_job.dump()
        async with octobot_flow.jobs.AutomationJob(after_init_execution_dump, [], [], {}) as dca_automation_job:
            await dca_automation_job.run()
        return dca_automation_job.dump()


def assert_open_orders_are_btc_usdc_only(automation_dump: dict) -> None:
    exchange_elements = automation_dump["automation"]["exchange_account_elements"]
    for wrapped_order in exchange_elements["orders"]["open_orders"]:
        order_details = wrapped_order.get(trading_constants.STORAGE_ORIGIN_VALUE, wrapped_order)
        assert order_details[trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value] == dca_test.BTC_USDC
