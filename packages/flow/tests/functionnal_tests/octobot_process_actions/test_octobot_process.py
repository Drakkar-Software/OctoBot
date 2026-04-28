#  Drakkar-Software OctoBot
#  Functional test: run_octobot_process + stop_automation (GridTradingMode, binanceus simulator)

import asyncio
import decimal
import json
import os
import shutil
import time
import typing
import uuid

import mock
import octobot.constants as octobot_app_constants
import octobot_commons.constants as common_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.process_util as process_util
import octobot_node.constants as octobot_node_constants
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import pytest

import octobot_flow
import octobot_flow.entities
import octobot_flow.enums

import tests.functionnal_tests as functionnal_tests
import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading

import octobot_flow.entities.accounts.exchange_account_elements as exchange_account_elements_import
import octobot_flow.entities.accounts.process_bot_state as process_bot_state_import  # Metadata only (hybrid: EAE from job.dump)

from tests.functionnal_tests import (
    automation_state_dict,
    d_order_price,
    resolved_actions,
)


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

EXCHANGE_BINANCEUS = "binanceus"

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
    lowest_buy_price = d_order_price(buy_orders[0][price_col])
    assert d_order_price(buy_orders[1][price_col]) == lowest_buy_price + D_INCREMENT
    assert d_order_price(sell_orders[0][price_col]) == lowest_buy_price + D_INCREMENT + D_SPREAD
    assert d_order_price(sell_orders[1][price_col]) == lowest_buy_price + D_INCREMENT + D_SPREAD + D_INCREMENT


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


def _get_action_by_id(
    job: octobot_flow.AutomationJob, action_id: str
) -> typing.Optional[octobot_flow.entities.AbstractActionDetails]:
    for action in job.automation_state.automation.actions_dag.actions:
        if action.id == action_id:
            return action
    return None


@pytest.fixture
def init_action():
    # Automation apply_configuration: seed automation state to match expected exchange + portfolio.
    return {
        "id": "action_init",
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


# --- Main lifecycle: spawn child OctoBot; EAE from job.dump() after merge; metadata from file; recall, stop ---

async def test_run_octobot_process_lifecycle_grid_trading(
    init_action: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    if not os.path.isfile(os.path.join(os.getcwd(), "start.py")):
        pytest.skip("start.py missing: run pytest with cwd set to the OctoBot project root")

    monkeypatch.setenv(octobot_app_constants.ENV_PROCESS_BOT_STATE_DUMP_INTERVAL_SECONDS, "5")

    # --- User folder, DSL scripts, and action DAG wiring ---
    user_folder = f"functionnal_tests/octlife_{uuid.uuid4().hex[:12]}"
    run_dsl = (
        "run_octobot_process("
        f"{user_folder!r}, {repr(GRID_BINANCEUS_PROFILE_DATA)}, "
        "waiting_time=2.0, ping_timeout=30.0)"
    )
    run_action = {
        "id": "action_run_octobot",
        "dsl_script": run_dsl,
        "dependencies": [{"action_id": "action_init"}],
    }
    # Depends only on init so it can run in the same ActionsExecutor pass after run_octobot re-calls;
    # stop_automation() triggers _await_recallable_execution_stops → run_octobot_process(execution_stop).
    stop_automation_action = {
        "id": "action_stop_automation",
        "dsl_script": "stop_automation()",
        "dependencies": [{"action_id": "action_init"}],
    }

    popen_calls = {"count": 0}
    real_spawn_managed = process_util.spawn_managed_subprocess

    def _tracked_spawn_managed(*args, **kwargs):
        popen_calls["count"] += 1
        return real_spawn_managed(*args, **kwargs)

    # Paths used only for teardown (child may create these under cwd).
    user_root_guess = os.path.normpath(
        os.path.join(
            os.getcwd(),
            *common_constants.USER_AUTOMATIONS_FOLDER.split("/"),
            *user_folder.replace("\\", "/").split("/"),
        )
    )
    log_folder_guess = os.path.normpath(
        os.path.join(
            os.getcwd(),
            *octobot_node_constants.AUTOMATION_LOGS_FOLDER.split("/"),
            *[segment for segment in user_folder.replace("\\", "/").split("/") if segment],
        )
    )

    try:
        # Mock community + wrap process_util.spawn_managed_subprocess so we can count child spawns
        # (`EnsureOctobotProcessOperator` calls spawn via mixin instance helper → process_util).
        with (
            functionnal_tests.mocked_community_authentication(),
            functionnal_tests.mocked_community_repository(),
            mock.patch.object(
                process_util,
                "spawn_managed_subprocess",
                side_effect=_tracked_spawn_managed,
            ),
        ):
            # 1) Apply init configuration (automation + exchange account seed).
            state = automation_state_dict(resolved_actions([init_action]))
            async with octobot_flow.AutomationJob(state, [], [], {}) as init_job:
                await init_job.run()
            state = init_job.dump()

            # 2) Register run_octobot_process; poll job until the child reports init_state_ok (live process_bot_state).
            async with octobot_flow.AutomationJob(state, [], [], {}) as job:
                job.automation_state.upsert_automation_actions(resolved_actions([run_action]))
                state = job.dump()

            deadline = time.monotonic() + GLOBAL_START_TIMEOUT_SEC
            inner: typing.Optional[dict] = None
            # Run DSL job once, then optionally poll until recall payload shows init_state_ok.
            async with octobot_flow.AutomationJob(state, [], [], {}) as first_poll:
                await first_poll.run()
            first_run = _get_action_by_id(first_poll, "action_run_octobot")
            assert first_run is not None
            inner = _recall_inner_from_dsl_action(first_run)
            state = first_poll.dump()
            if not (inner and inner.get("init_state_ok") is True):
                while time.monotonic() < deadline:
                    await asyncio.sleep(SLEEP_BETWEEN_JOB_POLLS_SEC)
                    async with octobot_flow.AutomationJob(state, [], [], {}) as poll_job:
                        await poll_job.run()
                    run_details = _get_action_by_id(poll_job, "action_run_octobot")
                    assert run_details is not None
                    inner = _recall_inner_from_dsl_action(run_details)
                    if inner and inner.get("init_state_ok") is True:
                        state = poll_job.dump()
                        break
                    state = poll_job.dump()
                else:
                    pytest.fail(
                        f"OctoBot did not become ready (init_state_ok) within {GLOBAL_START_TIMEOUT_SEC}s"
                    )

            assert inner is not None
            assert inner.get("pid"), "expected child pid in ensure state"
            assert popen_calls["count"] >= 1

            # --- process_bot_state path: must exist before poll (child wrote at least one dump) ---
            state_path = os.path.normpath(
                os.path.join(
                    inner["user_root"],
                    octobot_app_constants.PROCESS_BOT_STATE_FILE_NAME,
                )
            )
            assert os.path.isfile(state_path)

            # 1) Poll AutomationJob + dump() until merge yields ≥4 open orders (EAE from automation snapshot,
            #    not from parsing full process_bot_state on disk).
            orders_deadline = time.monotonic() + GRID_ORDERS_TIMEOUT_SEC
            exchange_account_snapshot: typing.Optional[
                exchange_account_elements_import.ExchangeAccountElements
            ] = None
            last_open_order_count = 0
            while time.monotonic() < orders_deadline:
                async with octobot_flow.AutomationJob(state, [], [], {}) as grid_poll_job:
                    await grid_poll_job.run()
                    job_dump_payload = grid_poll_job.dump()
                automation_dump = job_dump_payload.get("automation")
                exchange_account_snapshot_dict = (
                    automation_dump.get("exchange_account_elements")
                    if isinstance(automation_dump, dict)
                    else None
                )
                state = job_dump_payload
                if exchange_account_snapshot_dict is not None:
                    exchange_account_snapshot = (
                        exchange_account_elements_import.ExchangeAccountElements.from_dict(
                            exchange_account_snapshot_dict
                        )
                    )
                    last_open_order_count = len(
                        exchange_account_snapshot.orders.open_orders
                    )
                    if last_open_order_count >= 4:
                        break
                await asyncio.sleep(GRID_ORDERS_POLL_SEC)
            else:
                pytest.fail(
                    f"Timed out waiting for at least four open orders after merge in automation dump "
                    f"(last count={last_open_order_count}) within {GRID_ORDERS_TIMEOUT_SEC}s"
                )

            assert exchange_account_snapshot is not None

            # 2) One minimal read of process_bot_state.json for Metadata only (timestamps + dump interval).
            with open(state_path, encoding="utf-8") as process_state_file:
                file_metadata_payload = json.load(process_state_file)
            process_metadata = process_bot_state_import.Metadata.from_dict(
                file_metadata_payload["metadata"]
            )
            # Hybrid intent: business assertions use job.dump() EAE; file is not the source of truth for orders.
            assert "exchange_account_elements" in file_metadata_payload

            # --- Assertions: metadata liveness (file), exchange name, portfolio, grid ladder (dump EAE) ---
            assert isinstance(process_metadata, process_bot_state_import.Metadata)
            assert isinstance(process_metadata.updated_at, (int, float))
            assert isinstance(process_metadata.next_updated_at, (int, float))
            assert process_metadata.updated_at <= time.time()
            assert process_metadata.next_updated_at >= process_metadata.updated_at
            assert abs(
                (process_metadata.next_updated_at - process_metadata.updated_at)
                - EXPECTED_PROCESS_BOT_DUMP_INTERVAL_SEC
            ) < 1.0

            dumped_name = (exchange_account_snapshot.name or "").lower()
            assert dumped_name and "binance" in dumped_name

            portfolio_content = exchange_account_snapshot.portfolio.content
            assert "USDT" in portfolio_content and "BTC" in portfolio_content
            total_key = common_constants.PORTFOLIO_TOTAL
            avail_key = common_constants.PORTFOLIO_AVAILABLE
            usdt_c = portfolio_content["USDT"]
            btc_c = portfolio_content["BTC"]
            total_usdt = float(usdt_c[total_key])
            total_btc = float(btc_c[total_key])
            assert 800.0 <= total_usdt <= 1050.0
            assert 0.009 <= total_btc <= 0.011
            assert float(usdt_c[avail_key]) <= total_usdt
            assert float(btc_c[avail_key]) <= total_btc
            assert float(usdt_c[avail_key]) < total_usdt or float(btc_c[avail_key]) < total_btc

            _assert_two_by_two_grid_ladder_orders(
                exchange_account_snapshot.orders.open_orders,
            )

            child_pid = int(inner["pid"])
            assert process_util.pid_is_running(child_pid)

            # 3) Second automation run: re-call path only (no second Popen; same child pid).
            before = popen_calls["count"]
            async with octobot_flow.AutomationJob(state, [], [], {}) as idem_job:
                await idem_job.run()
            assert popen_calls["count"] == before
            idem_run = _get_action_by_id(idem_job, "action_run_octobot")
            assert idem_run is not None
            idem_inner = _recall_inner_from_dsl_action(idem_run)
            assert idem_inner is not None
            assert idem_inner.get("pid") == child_pid

            state = idem_job.dump()

            # 4) stop_automation + execution_stop on run_octobot (SIGTERM to child), then wait for exit.
            priority_actions = resolved_actions([stop_automation_action])
            async with octobot_flow.AutomationJob(state, priority_actions, [], {}) as stop_phase:
                await stop_phase.run()
            assert stop_phase.automation_state.automation.post_actions.stop_automation is True
            run_stopped = _get_action_by_id(stop_phase, "action_run_octobot")
            assert run_stopped is not None
            assert isinstance(run_stopped.result, dict)
            assert run_stopped.result.get("status") in ("stopped", "already_stopped")

            # SIGTERM triggers graceful stop; the HTTP server can keep returning 200
            # until late in shutdown, so wait for the child PID to be gone.
            process_deadline = time.monotonic() + CHILD_STOP_WAIT_SEC
            while time.monotonic() < process_deadline:
                if not process_util.pid_is_running(child_pid):
                    break
                await asyncio.sleep(0.5)
            else:
                pytest.fail(
                    f"expected child pid {child_pid} to be stopped after stop_automation/execution_stop "
                    f"within {CHILD_STOP_WAIT_SEC}s"
                )

    finally:
        # Remove user data and automation logs created under the project root for this run.
        if os.path.isdir(user_root_guess):
            shutil.rmtree(user_root_guess, ignore_errors=True)
        if os.path.isdir(log_folder_guess):
            shutil.rmtree(log_folder_guess, ignore_errors=True)
