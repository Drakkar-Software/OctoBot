#  Drakkar-Software OctoBot
#  Functional test: run_octobot_process lifecycle + stop_automation (GridTradingMode, binanceus simulator)

import asyncio
import json
import os
import pathlib
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
import pytest

import octobot_flow.jobs
import tests.functionnal_tests as functionnal_tests
import tests.functionnal_tests.octobot_process_actions.octobot_process_functional_shared as octobot_process_functional_shared

import octobot_flow.entities.accounts.exchange_account_elements as exchange_account_elements_import
import octobot_flow.entities.accounts.process_bot_state as process_bot_state_import  # Metadata only (hybrid: EAE from job.dump)

pytestmark = octobot_process_functional_shared.pytestmark
pytest_plugins = (octobot_process_functional_shared.__name__,)


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
        f"{user_folder!r}, {repr(octobot_process_functional_shared.GRID_BINANCEUS_PROFILE_DATA)}, "
        f"waiting_time={octobot_process_functional_shared.WAITING_TIME_RUN_OCTOBOT_PROCESS_SEC}, ping_timeout=30.0)"
    )
    run_action = {
        "id": octobot_process_functional_shared.ACTION_ID_RUN_OCTOBOT,
        "dsl_script": run_dsl,
        "dependencies": [{"action_id": octobot_process_functional_shared.ACTION_ID_INIT}],
    }
    # Depends only on init so it can run in the same ActionsExecutor pass after run_octobot re-calls;
    # stop_automation() triggers _await_recallable_operator_signal(STOP) → run_octobot_process(execution_stop).
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
        # Mock community + wrap process_util.spawn_managed_subprocess: count spawns and force
        # forward_terminal_output so child stdout/stderr reach the pytest terminal.
        with (
            functionnal_tests.mocked_community_authentication(),
            functionnal_tests.mocked_community_repository(),
            mock.patch.object(
                process_util,
                "spawn_managed_subprocess",
                side_effect=tracked_spawn_managed,
            ),
        ):
            # 1) Apply init configuration (automation + exchange account seed).
            state = functionnal_tests.automation_state_dict(
                functionnal_tests.resolved_actions([init_action])
            )
            async with octobot_flow.jobs.AutomationJob(state, [], [], {}) as init_job:
                await init_job.run()
            state = init_job.dump()

            # 2) Register run_octobot_process; poll job until the child reports init_state_ok (live process_bot_state).
            async with octobot_flow.jobs.AutomationJob(state, [], [], {}) as job:
                job.automation_state.upsert_automation_actions(
                    functionnal_tests.resolved_actions([run_action])
                )
                state = job.dump()

            deadline = time.monotonic() + octobot_process_functional_shared.GLOBAL_START_TIMEOUT_SEC
            inner: typing.Optional[dict] = None
            # Run DSL job once, then optionally poll until recall payload shows init_state_ok.
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
            assert inner.get("pid"), "expected child pid in ensure state"
            assert popen_calls["count"] >= 1

            # --- process_bot_state path: must exist before poll (child wrote at least one dump) ---
            # First process_bot_state dump can lag init_state_ok (see shared wait helper).
            state_path = octobot_process_functional_shared._process_bot_state_path(inner)
            await octobot_process_functional_shared._wait_for_process_bot_state_file(state_path)

            # 1) Poll AutomationJob + dump() until merge yields ≥4 open orders (EAE from automation snapshot,
            #    not from parsing full process_bot_state on disk).
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
                    f"Timed out waiting for at least four open orders after merge in automation dump "
                    f"(last count={last_open_order_count}) within "
                    f"{octobot_process_functional_shared.GRID_ORDERS_TIMEOUT_SEC}s"
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
                - octobot_process_functional_shared.EXPECTED_PROCESS_BOT_DUMP_INTERVAL_SEC
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

            octobot_process_functional_shared._assert_two_by_two_grid_ladder_orders(
                exchange_account_snapshot.orders.open_orders,
            )

            child_pid = int(inner["pid"])
            assert process_util.pid_is_running(child_pid)

            # 3) Second automation run: re-call path only (no second Popen; same child pid).
            before = popen_calls["count"]
            async with octobot_flow.jobs.AutomationJob(state, [], [], {}) as idem_job:
                await idem_job.run()
            octobot_process_functional_shared._assert_run_octobot_process_recall_scheduled_to_in_dump(
                idem_job.dump()
            )
            assert popen_calls["count"] == before
            idem_run = octobot_process_functional_shared._get_action_by_id(
                idem_job, octobot_process_functional_shared.ACTION_ID_RUN_OCTOBOT
            )
            assert idem_run is not None
            idem_inner = octobot_process_functional_shared._recall_inner_from_dsl_action(idem_run)
            assert idem_inner is not None
            assert idem_inner.get("pid") == child_pid

            state = idem_job.dump()

            # 4) stop_automation + execution_stop on run_octobot (SIGTERM to child), then wait for exit.
            priority_actions = functionnal_tests.resolved_actions([stop_automation_action])
            async with octobot_flow.jobs.AutomationJob(state, priority_actions, [], {}) as stop_phase:
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

            # SIGTERM triggers graceful stop; the HTTP server can keep returning 200
            # until late in shutdown, so wait for the child PID to be gone.
            process_deadline = time.monotonic() + octobot_process_functional_shared.CHILD_STOP_WAIT_SEC
            while time.monotonic() < process_deadline:
                if not process_util.pid_is_running(child_pid):
                    break
                await asyncio.sleep(0.5)
            else:
                pytest.fail(
                    f"expected child pid {child_pid} to be stopped after stop_automation/execution_stop "
                    f"within {octobot_process_functional_shared.CHILD_STOP_WAIT_SEC}s"
                )

    finally:
        # Remove user data and automation logs created under the project root for this run.
        if os.path.isdir(user_root_guess):
            shutil.rmtree(user_root_guess, ignore_errors=True)
        if os.path.isdir(log_folder_guess):
            shutil.rmtree(log_folder_guess, ignore_errors=True)


async def test_run_octobot_process_lifecycle_default_config_no_profile_data(
    init_action: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    if not os.path.isfile(os.path.join(os.getcwd(), "start.py")):
        pytest.skip("start.py missing: run pytest with cwd set to the OctoBot project root")

    non_trading_profile_json = os.path.join(
        os.getcwd(),
        common_constants.USER_FOLDER,
        common_constants.PROFILES_FOLDER,
        "non-trading",
        common_constants.PROFILE_CONFIG_FILE,
    )
    if not os.path.isfile(non_trading_profile_json):
        pytest.skip("non-trading profile missing under OctoBot user/profiles")

    monkeypatch.setenv(octobot_app_constants.ENV_PROCESS_BOT_STATE_DUMP_INTERVAL_SECONDS, "5")

    user_folder = f"functionnal_tests/octlife_default_{uuid.uuid4().hex[:12]}"
    exchange_auth = [
        {
            "internal_name": octobot_process_functional_shared.EXCHANGE_BINANCEUS,
            "api_key": "functional-default-config-key",
            "api_secret": "functional-default-config-secret",
            "sandboxed": True,
            "exchange_type": common_constants.CONFIG_EXCHANGE_SPOT,
        }
    ]
    run_dsl = (
        f"run_octobot_process({user_folder!r}, "
        f"exchange_auth_data={dsl_interpreter.format_parameter_value(exchange_auth)}, "
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

            deadline = time.monotonic() + octobot_process_functional_shared.GLOBAL_START_TIMEOUT_SEC
            inner: typing.Optional[dict] = None
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
            assert inner.get("pid"), "expected child pid in ensure state"
            assert popen_calls["count"] >= 1
            child_pid = int(inner["pid"])
            assert process_util.pid_is_running(child_pid)

            user_root = pathlib.Path(inner["user_root"])
            assert inner.get("profile_id") == "non-trading"
            exchange_auth_entry = exchange_auth[0]
            # Child encrypts config.json after spawn; wait + assert in one helper (see shared module).
            await octobot_process_functional_shared._assert_encrypted_exchange_credentials_in_user_config(
                user_root,
                octobot_process_functional_shared.EXCHANGE_BINANCEUS,
                exchange_auth_entry["api_key"],
                exchange_auth_entry["api_secret"],
            )
            profile_json_path = (
                user_root
                / common_constants.PROFILES_FOLDER
                / "non-trading"
                / common_constants.PROFILE_CONFIG_FILE
            )
            assert profile_json_path.is_file()

            # First process_bot_state dump can lag init_state_ok (see shared wait helper).
            state_path = octobot_process_functional_shared._process_bot_state_path(inner)
            await octobot_process_functional_shared._wait_for_process_bot_state_file(state_path)
            with open(state_path, encoding="utf-8") as process_state_file:
                file_metadata_payload = json.load(process_state_file)
            process_metadata = process_bot_state_import.Metadata.from_dict(
                file_metadata_payload["metadata"]
            )
            assert isinstance(process_metadata, process_bot_state_import.Metadata)
            assert isinstance(process_metadata.updated_at, (int, float))
            assert isinstance(process_metadata.next_updated_at, (int, float))
            assert process_metadata.updated_at <= time.time()
            assert process_metadata.next_updated_at >= process_metadata.updated_at
            assert abs(
                (process_metadata.next_updated_at - process_metadata.updated_at)
                - octobot_process_functional_shared.EXPECTED_PROCESS_BOT_DUMP_INTERVAL_SEC
            ) < 1.0

            priority_actions = functionnal_tests.resolved_actions([stop_automation_action])
            async with octobot_flow.jobs.AutomationJob(state, priority_actions, [], {}) as stop_phase:
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
                if not process_util.pid_is_running(child_pid):
                    break
                await asyncio.sleep(0.5)
            else:
                pytest.fail(
                    f"expected child pid {child_pid} to be stopped after stop_automation/execution_stop "
                    f"within {octobot_process_functional_shared.CHILD_STOP_WAIT_SEC}s"
                )

    finally:
        if os.path.isdir(user_root_guess):
            shutil.rmtree(user_root_guess, ignore_errors=True)
        if os.path.isdir(log_folder_guess):
            shutil.rmtree(log_folder_guess, ignore_errors=True)
