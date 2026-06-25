#  Drakkar-Software OctoBot
#  Functional test: update_automation_configuration / grid refresh (GridTradingMode, binanceus simulator)

import asyncio
import os
import shutil
import time
import typing
import uuid

import mock
import octobot.constants as octobot_app_constants
import octobot_commons.constants as common_constants
import octobot_commons.process_util as process_util
import octobot_node.constants as octobot_node_constants
import octobot_trading.enums as trading_enums
import pytest

import octobot_flow.jobs
import tests.functionnal_tests as functionnal_tests
import tests.functionnal_tests.octobot_process_actions.octobot_process_functional_shared as octobot_process_functional_shared

import octobot_flow.entities.accounts.exchange_account_elements as exchange_account_elements_import

pytestmark = octobot_process_functional_shared.pytestmark
pytest_plugins = (octobot_process_functional_shared.__name__,)

ACTION_ID_UPDATE_AUTOMATION_CONFIGURATION = "action_update_automation_configuration"


def _assert_three_by_three_grid_ladder_orders(orders_wrapped: list[dict]) -> None:
    open_orders_origin_values = octobot_process_functional_shared._open_orders_origins(orders_wrapped)
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
    assert len(buy_orders) == len(sell_orders) == 3
    sym = trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value
    for ord_dict in buy_orders + sell_orders:
        assert ord_dict.get(sym) == "BTC/USDT"
    price_col = trading_enums.ExchangeConstantsOrderColumns.PRICE.value
    # After UPDATE_CONFIG the grid may re-anchor to a new reference price; require ladder steps and buy/sell gap.
    for step_index in range(1, 3):
        assert functionnal_tests.d_order_price(buy_orders[step_index][price_col]) == functionnal_tests.d_order_price(
            buy_orders[step_index - 1][price_col]
        ) + octobot_process_functional_shared.D_INCREMENT
        assert functionnal_tests.d_order_price(sell_orders[step_index][price_col]) == functionnal_tests.d_order_price(
            sell_orders[step_index - 1][price_col]
        ) + octobot_process_functional_shared.D_INCREMENT
    assert functionnal_tests.d_order_price(buy_orders[-1][price_col]) < functionnal_tests.d_order_price(
        sell_orders[0][price_col]
    )


async def test_run_octobot_process_grid_refresh_four_to_six_orders(
    init_action: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    """2×2 grid (4 orders) → priority `update_automation_configuration(new_run_dsl)` → 3×3 grid (6 orders) + stop."""
    # Preamble: unique user folder, DSL actions, spawn counter, predicted cleanup paths.
    if not os.path.isfile(os.path.join(os.getcwd(), "start.py")):
        pytest.skip("start.py missing: run pytest with cwd set to the OctoBot project root")

    monkeypatch.setenv(octobot_app_constants.ENV_PROCESS_BOT_STATE_DUMP_INTERVAL_SECONDS, "5")

    user_folder = f"functionnal_tests/octocfg_{uuid.uuid4().hex[:12]}"
    profile_2x2 = octobot_process_functional_shared._grid_binanceus_profile_data(2, 2)
    run_dsl = (
        "run_octobot_process("
        f"{user_folder!r}, {repr(profile_2x2)}, "
        f"waiting_time={octobot_process_functional_shared.WAITING_TIME_RUN_OCTOBOT_PROCESS_SEC}, ping_timeout=30.0)"
    )
    run_action = {
        "id": octobot_process_functional_shared.ACTION_ID_RUN_OCTOBOT,
        "dsl_script": run_dsl,
        "dependencies": [{"action_id": octobot_process_functional_shared.ACTION_ID_INIT}],
    }
    stop_automation_action = {
        "id": octobot_process_functional_shared.ACTION_ID_STOP_AUTOMATION,
        "dsl_script": "stop_automation()",
        "dependencies": [{"action_id": octobot_process_functional_shared.ACTION_ID_INIT}],
    }

    popen_calls = {"count": 0}
    tracked_spawn_managed = (
        octobot_process_functional_shared._make_tracked_spawn_managed_with_forward_terminal_output(
            process_util.spawn_managed_subprocess,
            popen_calls,
        )
    )

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
        # Real child via patched spawn_managed_subprocess (spawn count + forward_terminal_output).
        with (
            functionnal_tests.mocked_community_authentication(),
            functionnal_tests.mocked_community_repository(),
            mock.patch.object(
                process_util,
                "spawn_managed_subprocess",
                side_effect=tracked_spawn_managed,
            ),
        ):
            # 1) Bootstrap automation state and register run_octobot_process with a 2×2 grid profile.
            state = functionnal_tests.automation_state_dict(
                functionnal_tests.resolved_actions([init_action])
            )
            async with octobot_flow.jobs.AutomationJob(state, [], [], {}) as init_job:
                await init_job.run()
            state = init_job.dump()

            async with octobot_flow.jobs.AutomationJob(state, [], [], {}) as job:
                job.automation_state.upsert_automation_actions(
                    functionnal_tests.resolved_actions([run_action])
                )
                state = job.dump()

            deadline = time.monotonic() + octobot_process_functional_shared.GLOBAL_START_TIMEOUT_SEC
            inner: typing.Optional[dict] = None
            # 2) First automation pass, then poll until the child reports init_state_ok (ready to query).
            async with octobot_flow.jobs.AutomationJob(state, [], [], {}) as first_poll:
                await first_poll.run()
            octobot_process_functional_shared._assert_run_octobot_process_recall_scheduled_to_in_dump(
                first_poll.dump()
            )
            first_run = octobot_process_functional_shared._get_action_by_id(
                first_poll, octobot_process_functional_shared.ACTION_ID_RUN_OCTOBOT
            )
            assert first_run is not None
            inner = octobot_process_functional_shared._recall_inner_from_dsl_action(first_run)
            state = first_poll.dump()
            if not (inner and inner.get("init_state_ok") is True):
                while time.monotonic() < deadline:
                    await asyncio.sleep(octobot_process_functional_shared.SLEEP_BETWEEN_JOB_POLLS_SEC)
                    async with octobot_flow.jobs.AutomationJob(state, [], [], {}) as poll_job:
                        await poll_job.run()
                    octobot_process_functional_shared._assert_run_octobot_process_recall_scheduled_to_in_dump(
                        poll_job.dump()
                    )
                    run_details = octobot_process_functional_shared._get_action_by_id(
                        poll_job, octobot_process_functional_shared.ACTION_ID_RUN_OCTOBOT
                    )
                    assert run_details is not None
                    inner = octobot_process_functional_shared._recall_inner_from_dsl_action(run_details)
                    if inner and inner.get("init_state_ok") is True:
                        state = poll_job.dump()
                        break
                    state = poll_job.dump()
                else:
                    pytest.fail(
                        f"OctoBot did not become ready (init_state_ok) within "
                        f"{octobot_process_functional_shared.GLOBAL_START_TIMEOUT_SEC}s"
                    )

            assert inner is not None
            assert inner.get("pid")
            initial_spawn_count = popen_calls["count"]
            assert initial_spawn_count >= 1

            # First process_bot_state dump can lag init_state_ok (see shared wait helper).
            state_path = octobot_process_functional_shared._process_bot_state_path(inner)
            await octobot_process_functional_shared._wait_for_process_bot_state_file(state_path)

            # 3) Wait until at least four open ladder orders exist, then assert a 2×2 grid pattern.
            orders_deadline = time.monotonic() + octobot_process_functional_shared.GRID_ORDERS_TIMEOUT_SEC
            exchange_account_snapshot: typing.Optional[
                exchange_account_elements_import.ExchangeAccountElements
            ] = None
            last_open_order_count = 0
            while time.monotonic() < orders_deadline:
                async with octobot_flow.jobs.AutomationJob(state, [], [], {}) as grid_poll_job:
                    await grid_poll_job.run()
                    job_dump_payload = grid_poll_job.dump()
                octobot_process_functional_shared._assert_run_octobot_process_recall_scheduled_to_in_dump(
                    job_dump_payload
                )
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
                await asyncio.sleep(octobot_process_functional_shared.GRID_ORDERS_POLL_SEC)
            else:
                pytest.fail(
                    f"Timed out waiting for at least four open orders (last count={last_open_order_count}) "
                    f"within {octobot_process_functional_shared.GRID_ORDERS_TIMEOUT_SEC}s"
                )
            assert exchange_account_snapshot is not None
            octobot_process_functional_shared._assert_two_by_two_grid_ladder_orders(
                exchange_account_snapshot.orders.open_orders,
            )

            profile_3x3 = octobot_process_functional_shared._grid_binanceus_profile_data(3, 3)
            new_run_dsl = (
                "run_octobot_process("
                f"{user_folder!r}, {repr(profile_3x3)}, "
                f"waiting_time={octobot_process_functional_shared.WAITING_TIME_RUN_OCTOBOT_PROCESS_SEC}, ping_timeout=30.0)"
            )
            update_config_priority_action = {
                "id": ACTION_ID_UPDATE_AUTOMATION_CONFIGURATION,
                "dsl_script": f"update_automation_configuration({new_run_dsl!r})",
                "dependencies": [{"action_id": octobot_process_functional_shared.ACTION_ID_INIT}],
            }

            spawn_before_refresh = popen_calls["count"]
            priority_actions = functionnal_tests.resolved_actions([update_config_priority_action])
            async with octobot_flow.jobs.AutomationJob(state, priority_actions, [], {}) as refresh_phase:
                await refresh_phase.run()
            octobot_process_functional_shared._assert_run_octobot_process_recall_scheduled_to_in_dump(
                refresh_phase.dump()
            )
            assert popen_calls["count"] == spawn_before_refresh + 1
            state = refresh_phase.dump()

            # 6) Poll until six open ladder orders exist, then assert a 3×3 grid pattern.
            six_orders_deadline = (
                time.monotonic() + octobot_process_functional_shared.GRID_ORDERS_TIMEOUT_SEC * 3
            )
            exchange_account_after: typing.Optional[
                exchange_account_elements_import.ExchangeAccountElements
            ] = None
            last_six_count = 0
            inner_after: typing.Optional[dict] = None
            while time.monotonic() < six_orders_deadline:
                async with octobot_flow.jobs.AutomationJob(state, [], [], {}) as six_poll:
                    await six_poll.run()
                    dump_payload = six_poll.dump()
                octobot_process_functional_shared._assert_run_octobot_process_recall_scheduled_to_in_dump(
                    dump_payload
                )
                automation_dump = dump_payload.get("automation")
                eae_dict = (
                    automation_dump.get("exchange_account_elements")
                    if isinstance(automation_dump, dict)
                    else None
                )
                state = dump_payload
                run_action_details = octobot_process_functional_shared._get_action_by_id(
                    six_poll, octobot_process_functional_shared.ACTION_ID_RUN_OCTOBOT
                )
                if run_action_details is not None:
                    inner_after = octobot_process_functional_shared._recall_inner_from_dsl_action(
                        run_action_details
                    )
                if eae_dict is not None:
                    exchange_account_after = (
                        exchange_account_elements_import.ExchangeAccountElements.from_dict(eae_dict)
                    )
                    last_six_count = len(exchange_account_after.orders.open_orders)
                    if last_six_count >= 6:
                        break
                await asyncio.sleep(octobot_process_functional_shared.GRID_ORDERS_POLL_SEC)
            else:
                pytest.fail(
                    f"Timed out waiting for six open orders after config refresh "
                    f"(last count={last_six_count})"
                )
            assert exchange_account_after is not None
            assert inner_after is not None
            _assert_three_by_three_grid_ladder_orders(
                exchange_account_after.orders.open_orders,
            )

            # After refresh, expect a new managed child PID (extra spawn in step 5).
            refreshed_pid = int(inner_after["pid"])
            assert process_util.pid_is_running(refreshed_pid)

            # 7) stop_automation (execution stop on run_octobot), then wait until the child PID is gone.
            priority_stop = functionnal_tests.resolved_actions([stop_automation_action])
            async with octobot_flow.jobs.AutomationJob(state, priority_stop, [], {}) as stop_phase:
                await stop_phase.run()
            octobot_process_functional_shared._assert_run_octobot_process_recall_scheduled_to_in_dump(
                stop_phase.dump(),
                assert_delay_matches_waiting_time=False,
            )
            assert stop_phase.automation_state.automation.post_actions.stop_automation is True
            run_stopped = octobot_process_functional_shared._get_action_by_id(
                stop_phase, octobot_process_functional_shared.ACTION_ID_RUN_OCTOBOT
            )
            assert run_stopped is not None
            assert isinstance(run_stopped.result, dict)
            assert run_stopped.result.get("status") in ("stopped", "already_stopped")

            process_deadline = time.monotonic() + octobot_process_functional_shared.CHILD_STOP_WAIT_SEC
            while time.monotonic() < process_deadline:
                if not process_util.pid_is_running(refreshed_pid):
                    break
                await asyncio.sleep(0.5)
            else:
                pytest.fail(
                    f"expected child pid {refreshed_pid} to be stopped after stop_automation "
                    f"within {octobot_process_functional_shared.CHILD_STOP_WAIT_SEC}s"
                )

    finally:
        # Tear down dirs created under the project root for this test run.
        if os.path.isdir(user_root_guess):
            shutil.rmtree(user_root_guess, ignore_errors=True)
        if os.path.isdir(log_folder_guess):
            shutil.rmtree(log_folder_guess, ignore_errors=True)
