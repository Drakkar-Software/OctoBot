#  Drakkar-Software OctoBot
#  Shared helpers/constants for octobot process functional tests (run_octobot_process, GridTradingMode).

import copy
import decimal
import typing

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import pytest

import octobot_flow
import octobot_flow.entities
import octobot_flow.enums
import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading
import tests.functionnal_tests as functionnal_tests

pytestmark = pytest.mark.asyncio

# --- Timeouts and grid geometry (must match pair_settings spread / increment below) ---
GLOBAL_START_TIMEOUT_SEC = 30.0
SLEEP_BETWEEN_JOB_POLLS_SEC = 2.0
# Grid orders may land after init_state_ok; bounded wait for ≥4 opens in merged automation EAE (job.dump).
GRID_ORDERS_TIMEOUT_SEC = 15.0
GRID_ORDERS_POLL_SEC = 1

GRID_INCREMENT = 200
GRID_SPREAD = 600
D_INCREMENT = decimal.Decimal(str(GRID_INCREMENT))
D_SPREAD = decimal.Decimal(str(GRID_SPREAD))
# After SIGTERM, services may take time to stop; assert on PID instead.
CHILD_STOP_WAIT_SEC = 15.0

# Child dump interval for this test (set via monkeypatch before Popen). Do not use
# octobot.constants.PROCESS_BOT_STATE_DUMP_INTERVAL_SECONDS in the parent for assertions;
# it is fixed at import time and stays 30 unless the interpreter reloads constants.
EXPECTED_PROCESS_BOT_DUMP_INTERVAL_SEC = 5.0

# Same as `waiting_time=` in run_octobot_process(...) DSL for this file's tests.
WAITING_TIME_RUN_OCTOBOT_PROCESS_SEC = 2.0
RECALL_SCHEDULE_TOLERANCE_SEC = 1.5

EXCHANGE_BINANCEUS = "binanceus"

# --- DSL / DAG action ids (fixtures, dependencies, _get_action_by_id) ---
ACTION_ID_INIT = "action_init"
ACTION_ID_RUN_OCTOBOT = "action_run_octobot"
ACTION_ID_STOP_AUTOMATION = "action_stop_automation"

# --- Child profile for run_octobot_process: simulator (trader.enabled False) + GridTradingMode BTC/USDT 2×2 ---
GRID_BINANCEUS_PROFILE_DATA = {
    "profile_details": {"name": "func_test_grid_octoprocess", "id": "func_test_grid_octoprocess"},
    "crypto_currencies": [
        {"trading_pairs": ["BTC/USDT"], "name": "BTC", "enabled": True},
    ],
    "exchanges": [
        {"internal_name": EXCHANGE_BINANCEUS, "exchange_type": "spot"},
    ],
    "trader": {"enabled": False, "load_trade_history": True},
    "trader_simulator": {
        "enabled": True,
        "starting_portfolio": {"USDT": 1000.0, "BTC": 0.01},
        "maker_fees": 0.0,
        "taker_fees": 0.0,
    },
    "trading": {"reference_market": "USDT", "risk": 1.0, "paused": False},
    "tentacles": [
        {
            "name": "GridTradingMode",
            "config": {
                "pair_settings": [
                    grid_trading.GridTradingMode.get_default_pair_config(
                        "BTC/USDT",
                        float(GRID_SPREAD),
                        float(GRID_INCREMENT),
                        2,
                        2,
                        False,
                        False,
                        False,
                    )
                ]
            },
        },
    ],
    "options": {},
    "distribution": "default",
}


# --- Helpers: order ladder checks and ReCallingOperatorResult payload access ---

def _open_orders_origins(open_orders: list[dict]) -> list[dict]:
    return [
        order[trading_constants.STORAGE_ORIGIN_VALUE]
        for order in open_orders
    ]


def _assert_two_by_two_grid_ladder_orders(orders_wrapped: list[dict]) -> None:
    open_orders_origin_values = _open_orders_origins(orders_wrapped)
    buy_orders = sorted(
        [
            order
            for order in open_orders_origin_values
            if order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
            == trading_enums.TradeOrderSide.BUY.value
        ],
        key=lambda order: order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
    )
    sell_orders = sorted(
        [
            order
            for order in open_orders_origin_values
            if order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]
            == trading_enums.TradeOrderSide.SELL.value
        ],
        key=lambda order: order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
    )
    assert len(buy_orders) == len(sell_orders) == 2
    sym = trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value
    for ord_dict in buy_orders + sell_orders:
        assert ord_dict.get(sym) == "BTC/USDT"
    price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
    lowest_buy_price = functionnal_tests.d_order_price(buy_orders[0][price_col])
    assert functionnal_tests.d_order_price(buy_orders[1][price_col]) == lowest_buy_price + D_INCREMENT
    assert functionnal_tests.d_order_price(sell_orders[0][price_col]) == lowest_buy_price + D_INCREMENT + D_SPREAD
    assert functionnal_tests.d_order_price(sell_orders[1][price_col]) == lowest_buy_price + D_INCREMENT + D_SPREAD + D_INCREMENT


def _grid_binanceus_profile_data(buy_orders: int, sell_orders: int) -> dict:
    """Copy of grid simulator profile with configurable GridTradingMode buy/sell counts."""
    data = copy.deepcopy(GRID_BINANCEUS_PROFILE_DATA)
    data["tentacles"] = [
        {
            "name": "GridTradingMode",
            "config": {
                "pair_settings": [
                    grid_trading.GridTradingMode.get_default_pair_config(
                        "BTC/USDT",
                        float(GRID_SPREAD),
                        float(GRID_INCREMENT),
                        buy_orders,
                        sell_orders,
                        False,
                        False,
                        False,
                    )
                ]
            },
        },
    ]
    return data


def _recall_inner_state(run_result: typing.Optional[dict]) -> typing.Optional[dict]:
    if not isinstance(run_result, dict):
        return None
    rec = run_result.get(dsl_interpreter.ReCallingOperatorResult.__name__)
    if not isinstance(rec, dict):
        return None
    inner = rec.get("last_execution_result")
    return inner if isinstance(inner, dict) else None


def _recall_inner_from_dsl_action(
    action: octobot_flow.entities.AbstractActionDetails,
) -> typing.Optional[dict]:
    """
    After a re-calling operator finishes, `ActionsExecutor._reset_dag_to` calls `action.reset()`,
    which moves the result dict to `previous_execution_result` and clears `result`. Read both.
    """
    for run_result in (action.result, action.previous_execution_result):
        inner = _recall_inner_state(run_result) if run_result is not None else None
        if inner is not None:
            return inner
    return None


def _assert_run_octobot_process_recall_scheduled_to_in_dump(
    job_dump: dict[str, typing.Any],
    *,
    expected_waiting_time_sec: float = WAITING_TIME_RUN_OCTOBOT_PROCESS_SEC,
    schedule_tolerance_sec: float = RECALL_SCHEDULE_TOLERANCE_SEC,
    assert_delay_matches_waiting_time: bool = True,
) -> None:
    """
    After a job run where `run_octobot_process` schedules a re-call, the merged automation
    state must expose the next execution time at execution.current_execution.scheduled_to.
    """
    automation = job_dump["automation"]
    execution = automation["execution"]
    current_execution = execution["current_execution"]
    previous_execution = execution["previous_execution"]
    scheduled_to = current_execution["scheduled_to"]
    assert isinstance(scheduled_to, (int, float))
    assert scheduled_to > 0, f"next iteration was not scheduled (scheduled_to={scheduled_to})"
    triggered_at = previous_execution["triggered_at"]
    assert isinstance(triggered_at, (int, float))
    assert triggered_at > 0
    if assert_delay_matches_waiting_time:
        delay_sec = float(scheduled_to) - float(triggered_at)
        assert (
            expected_waiting_time_sec - schedule_tolerance_sec
            < delay_sec
            < expected_waiting_time_sec + schedule_tolerance_sec
        ), (
            f"recall scheduled_to should be ~triggered_at+{expected_waiting_time_sec}s: "
            f"delay={delay_sec}s scheduled_to={scheduled_to} triggered_at={triggered_at}"
        )


def _get_action_by_id(
    job: octobot_flow.AutomationJob, action_id: str
) -> typing.Optional[octobot_flow.entities.AbstractActionDetails]:
    for action in job.automation_state.automation.actions_dag.actions:
        if action.id == action_id:
            return action
    return None


def _make_tracked_spawn_managed_with_forward_terminal_output(
    real_spawn_managed: typing.Callable[..., typing.Any],
    popen_calls: dict[str, int],
) -> typing.Callable[..., typing.Any]:
    def _tracked(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        popen_calls["count"] += 1
        merged_kwargs = dict(kwargs)
        merged_kwargs["forward_terminal_output"] = True
        return real_spawn_managed(*args, **merged_kwargs)

    return _tracked


@pytest.fixture
def init_action():
    # Automation apply_configuration: seed automation state to match expected exchange + portfolio.
    return {
        "id": ACTION_ID_INIT,
        "action": octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value,
        "config": {
            "automation": {
                "metadata": {"automation_id": "automation_1"},
                "exchange_account_elements": {
                    "portfolio": {
                        "content": {
                            "USDT": {"available": 1000.0, "total": 1000.0},
                            "BTC": {"available": 0.01, "total": 0.01},
                        },
                    },
                },
            },
            "exchange_account_details": {
                "exchange_details": {
                    "internal_name": EXCHANGE_BINANCEUS,
                },
                "auth_details": {},
                "portfolio": {},
            },
        },
    }
