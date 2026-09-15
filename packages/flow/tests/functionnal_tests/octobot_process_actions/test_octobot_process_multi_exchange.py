#  Drakkar-Software OctoBot
#  Functional test: run_octobot_process with two simulator exchanges (aggregated EAE dump).

import asyncio
import json
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
import pytest

import octobot_flow.jobs
import tests.functionnal_tests as functionnal_tests
import tests.functionnal_tests.octobot_process_actions.octobot_process_functional_shared as octobot_process_functional_shared

import octobot_flow.entities.accounts.exchange_account_elements as exchange_account_elements_import
import octobot_flow.entities.accounts.process_bot_state as process_bot_state_import

pytestmark = octobot_process_functional_shared.pytestmark
pytest_plugins = (octobot_process_functional_shared.__name__,)

EXPECTED_DUAL_EXCHANGE_SYMBOLS = {"BTC/USDT"}
MIN_AGGREGATED_OPEN_ORDERS = 4
DUAL_EXCHANGE_ORDERS_TIMEOUT_SEC = 45.0


@pytest.mark.xdist_group(name=octobot_process_functional_shared.OCTOBOT_PROCESS_TEST_GROUP)
async def test_run_octobot_process_aggregates_two_simulator_exchanges(
    init_action: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    if not os.path.isfile(os.path.join(os.getcwd(), "start.py")):
        pytest.skip("start.py missing: run pytest with cwd set to the OctoBot project root")

    monkeypatch.setenv(octobot_app_constants.ENV_PROCESS_BOT_STATE_DUMP_INTERVAL_SECONDS, "5")

    user_folder = f"functionnal_tests/octmulti_{uuid.uuid4().hex[:12]}"
    run_dsl = (
        "run_octobot_process("
        f"{user_folder!r}, profile_data={repr(octobot_process_functional_shared.DUAL_EXCHANGE_GRID_PROFILE_DATA)}, "
        f"user_id={octobot_process_functional_shared.FUNCTIONAL_TEST_USER_ID!r}, "
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
        with (
            functionnal_tests.mocked_community_authentication(),
            functionnal_tests.mocked_community_repository(),
            mock.patch.object(
                process_util,
                "spawn_managed_subprocess",
                side_effect=tracked_spawn_managed,
            ),
        ):
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

            state, inner, state_path = (
                await octobot_process_functional_shared.poll_automation_until_child_process_ready(
                    state
                )
            )

            assert popen_calls["count"] >= 1

            orders_deadline = time.monotonic() + DUAL_EXCHANGE_ORDERS_TIMEOUT_SEC
            exchange_account_snapshot: typing.Optional[
                exchange_account_elements_import.ExchangeAccountElements
            ] = None
            while time.monotonic() < orders_deadline:
                grid_poll_job = await octobot_process_functional_shared.run_automation_job_without_exchange_manager(
                    state, [], [], {}
                )
                octobot_process_functional_shared._assert_run_octobot_process_recall_scheduled_to_in_dump(
                    grid_poll_job.dump()
                )
                automation_dump = grid_poll_job.dump().get("automation")
                exchange_account_snapshot_dict = (
                    automation_dump.get("exchange_account_elements")
                    if isinstance(automation_dump, dict)
                    else None
                )
                state = grid_poll_job.dump()
                if exchange_account_snapshot_dict is not None:
                    exchange_account_snapshot = (
                        exchange_account_elements_import.ExchangeAccountElements.from_dict(
                            exchange_account_snapshot_dict
                        )
                    )
                    dumped_name = (exchange_account_snapshot.name or "").lower()
                    has_both_exchanges = (
                        octobot_process_functional_shared.EXCHANGE_BINANCEUS in dumped_name
                        and octobot_process_functional_shared.EXCHANGE_OKX in dumped_name
                    )
                    has_enough_orders = (
                        len(exchange_account_snapshot.orders.open_orders) >= MIN_AGGREGATED_OPEN_ORDERS
                    )
                    has_expected_symbols = (
                        octobot_process_functional_shared._open_order_symbols(
                            exchange_account_snapshot.orders.open_orders
                        )
                        >= EXPECTED_DUAL_EXCHANGE_SYMBOLS
                    )
                    if has_both_exchanges and has_enough_orders and has_expected_symbols:
                        break
                await asyncio.sleep(octobot_process_functional_shared.GRID_ORDERS_POLL_SEC)
            else:
                last_name = exchange_account_snapshot.name if exchange_account_snapshot else None
                last_order_count = (
                    len(exchange_account_snapshot.orders.open_orders)
                    if exchange_account_snapshot is not None
                    else 0
                )
                last_symbols = (
                    octobot_process_functional_shared._open_order_symbols(
                        exchange_account_snapshot.orders.open_orders
                    )
                    if exchange_account_snapshot is not None
                    else set()
                )
                pytest.fail(
                    f"Timed out waiting for aggregated dual-exchange snapshot "
                    f"(name={last_name!r}, orders={last_order_count}, symbols={last_symbols})"
                )

            assert exchange_account_snapshot is not None
            octobot_process_functional_shared._assert_orders_include_symbols(
                exchange_account_snapshot.orders.open_orders,
                EXPECTED_DUAL_EXCHANGE_SYMBOLS,
            )
            assert len(exchange_account_snapshot.orders.open_orders) >= MIN_AGGREGATED_OPEN_ORDERS

            dumped_name = (exchange_account_snapshot.name or "").lower()
            assert octobot_process_functional_shared.EXCHANGE_BINANCEUS in dumped_name
            assert octobot_process_functional_shared.EXCHANGE_OKX in dumped_name

            portfolio_content = exchange_account_snapshot.portfolio.content
            assert "USDT" in portfolio_content
            assert "BTC" in portfolio_content

            with open(state_path, encoding="utf-8") as process_state_file:
                file_payload = json.load(process_state_file)
            process_metadata = process_bot_state_import.Metadata.from_dict(file_payload["metadata"])
            file_exchange_account_elements = (
                exchange_account_elements_import.ExchangeAccountElements.from_dict(
                    file_payload["exchange_account_elements"]
                )
            )
            octobot_process_functional_shared._assert_orders_include_symbols(
                file_exchange_account_elements.orders.open_orders,
                EXPECTED_DUAL_EXCHANGE_SYMBOLS,
            )
            assert len(file_exchange_account_elements.orders.open_orders) >= MIN_AGGREGATED_OPEN_ORDERS
            assert isinstance(process_metadata, process_bot_state_import.Metadata)
            assert process_metadata.pid > 0

            priority_actions = functionnal_tests.resolved_actions([stop_automation_action])
            async with octobot_flow.jobs.AutomationJob(state, priority_actions, [], {}) as stop_phase:
                await stop_phase.run()
            stop_run = octobot_process_functional_shared._get_action_by_id(
                stop_phase, octobot_process_functional_shared.ACTION_ID_RUN_OCTOBOT
            )
            assert stop_run is not None
            stop_inner = octobot_process_functional_shared._recall_inner_from_dsl_action(stop_run)
            assert stop_inner is not None
            child_pid = int(stop_inner["pid"])
            process_deadline = time.monotonic() + octobot_process_functional_shared.CHILD_STOP_WAIT_SEC
            while time.monotonic() < process_deadline:
                if not process_util.pid_is_running(child_pid):
                    break
                await asyncio.sleep(0.5)
            else:
                pytest.fail(
                    f"expected child pid {child_pid} to stop within "
                    f"{octobot_process_functional_shared.CHILD_STOP_WAIT_SEC}s"
                )

    finally:
        if os.path.isdir(user_root_guess):
            shutil.rmtree(user_root_guess, ignore_errors=True)
        if os.path.isdir(log_folder_guess):
            shutil.rmtree(log_folder_guess, ignore_errors=True)
