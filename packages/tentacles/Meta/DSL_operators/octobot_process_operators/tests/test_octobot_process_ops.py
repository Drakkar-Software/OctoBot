#  Drakkar-Software OctoBot-Commons
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
import json
import os
import shutil
import sys

import mock
import pytest

import octobot.constants as octobot_constants
import octobot_commons.constants as commons_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.errors as commons_errors
import octobot_commons.process_util as process_util
import octobot_node.constants as octobot_node_constants
import octobot_services.constants as services_constants

import octobot_flow.entities as octobot_flow_entities
import octobot_flow.entities.accounts.process_bot_state as process_bot_state_import

import tentacles.Meta.DSL_operators.octobot_process_operators.octobot_process_ops as octobot_process_ops

pytestmark = pytest.mark.asyncio


async def _async_return_none_mock(*_unused):
    return None


async def _async_live_process_bot_state_mock(*_unused):
    now = octobot_process_ops.time.time()
    interval = float(octobot_constants.PROCESS_BOT_STATE_DUMP_INTERVAL_SECONDS)
    return process_bot_state_import.ProcessBotState(
        metadata=process_bot_state_import.Metadata(
            updated_at=now - 0.1,
            next_updated_at=now + interval,
        ),
        exchange_account_elements=octobot_flow_entities.ExchangeAccountElements(),
    )
def _stop_test_ensure_state_dict(http_base_url: str) -> dict:
    return octobot_process_ops.EnsureOctobotProcessState(
        http_base_url=http_base_url,
        web_port=1,
        node_port=1,
        user_root="/x",
        user_folder="u",
        log_folder="/x/l",
        profile_id=None,
        pid=1,
        state_file_path=os.path.normpath(
            os.path.join("/x", octobot_constants.PROCESS_BOT_STATE_FILE_NAME)
        ),
    ).model_dump()


def _re_calling_ensure_value(last_execution_result: dict) -> dict:
    return {
        dsl_interpreter.ReCallingOperatorResult.__name__: {
            "keyword": "run_octobot_process",
            "last_execution_result": last_execution_result,
        }
    }


_MINIMAL_PROFILE_DATA = {
    "profile_details": {"name": "dsl_test", "id": "fixed_profile_id"},
    "crypto_currencies": [],
    "exchanges": [],
    "tentacles": [],
    "trader": {
        "enabled": True,
        "load_trade_history": True,
    },
    "trader_simulator": {
        "enabled": True,
        "starting_portfolio": {"USDT": 1000},
        "maker_fees": 0.0,
        "taker_fees": 0.0,
    },
    "trading": {
        "reference_market": "USDT",
        "risk": 1.0,
        "paused": False,
    },
    "options": {},
    "distribution": "default",
}

# No list literals: the DSL interpreter cannot parse ast.List inside dicts without a List operator.
_MINIMAL_PROFILE_DATA_DSL_LITERAL = {
    "profile_details": {"name": "dsl_test", "id": "fixed_profile_id"},
    "trader": {
        "enabled": True,
        "load_trade_history": True,
    },
    "trader_simulator": {
        "enabled": True,
        "starting_portfolio": {"USDT": 1000},
        "maker_fees": 0.0,
        "taker_fees": 0.0,
    },
    "trading": {
        "reference_market": "USDT",
        "risk": 1.0,
        "paused": False,
    },
    "options": {},
    "distribution": "default",
}


class TestEnsureUserProfileAndLayout:
    async def test_marked_prepared_is_skipped(self, tmp_path):
        user = tmp_path / commons_constants.USER_FOLDER / commons_constants.AUTOMATIONS_FOLDER / "u1"
        user.mkdir(parents=True)
        config_path = user / commons_constants.CONFIG_FILE
        config_path.write_text(
            json.dumps({commons_constants.CONFIG_PROFILE: "p1"}),
            encoding="utf-8",
        )
        (user / octobot_process_ops.DSL_PREPARED_MARKER).write_text("1", encoding="utf-8")
        res = await octobot_process_ops.ensure_user_profile_and_layout(
            "u1",
            str(tmp_path),
            _MINIMAL_PROFILE_DATA,
            None,
        )
        assert res["already_prepared"] is True
        assert res["profile_id"] == "p1"


class TestListenPortPair:
    def test_finds_sequential_ports(self):
        web_port, node_port = octobot_process_ops._listen_port_pair_with_shared_scan_offset(
            "127.0.0.1", 20000, 30000, max_offset=100
        )
        mixin = dsl_interpreter.ProcessBoundOperatorMixin
        assert mixin._tcp_port_is_free("127.0.0.1", web_port)
        assert mixin._tcp_port_is_free("127.0.0.1", node_port)


class TestEnsureOctobotProcessOperatorPrecompute:
    async def test_returns_recallable_when_process_bot_state_not_live(self, tmp_path):
        start_script = tmp_path / "start.py"
        start_script.write_text("#", encoding="utf-8")
        op = octobot_process_ops.EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=None,
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            octobot_process_ops,
            "ensure_user_profile_and_layout",
            new=mock.AsyncMock(
                return_value={
                    "user_root": str(
                        tmp_path / commons_constants.USER_FOLDER / commons_constants.AUTOMATIONS_FOLDER / "ub"
                    ),
                    "profile_id": "x",
                    "already_prepared": True,
                }
            ),
        ), mock.patch.object(
            octobot_process_ops,
            "_listen_port_pair_with_shared_scan_offset",
            return_value=(20050, 30050),
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock, mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(side_effect=_async_return_none_mock),
        ):
            spawn_mock.return_value.pid = 99999
            await op.pre_compute()
        assert isinstance(op.value, dict)
        assert dsl_interpreter.ReCallingOperatorResult.__name__ in op.value
        rec = op.value[dsl_interpreter.ReCallingOperatorResult.__name__]
        le = rec["last_execution_result"]
        assert le.get("init_state_ok") is False


class TestEnsureOctobotProcessPrecomputeWhenProcessStateLiveAfterFirstSpawn:
    async def test_returns_recallable_with_init_state_ok_after_first_spawn(self, tmp_path):
        start_script = tmp_path / "start.py"
        start_script.write_text("#", encoding="utf-8")
        op = octobot_process_ops.EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=None,
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            octobot_process_ops,
            "ensure_user_profile_and_layout",
            new=mock.AsyncMock(
                return_value={
                    "user_root": str(
                        tmp_path / commons_constants.USER_FOLDER / commons_constants.AUTOMATIONS_FOLDER / "ub"
                    ),
                    "profile_id": "x",
                    "already_prepared": True,
                }
            ),
        ), mock.patch.object(
            octobot_process_ops,
            "_listen_port_pair_with_shared_scan_offset",
            return_value=(20050, 30050),
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock, mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(side_effect=_async_live_process_bot_state_mock),
        ):
            spawn_mock.return_value.pid = 10001
            await op.pre_compute()
        assert isinstance(op.value, dict)
        assert dsl_interpreter.ReCallingOperatorResult.__name__ in op.value
        le = op.value[dsl_interpreter.ReCallingOperatorResult.__name__]["last_execution_result"]
        assert isinstance(le, dict)
        assert le.get("init_state_ok") is True
        assert le.get("http_base_url", "").startswith("http://")
        assert le.get("pid") == 10001
        assert le.get("waiting_time") == octobot_process_ops.DEFAULT_PING_WAITING_TIME
        assert octobot_flow_entities.PostIterationActionsDetails.__name__ in le
        post = octobot_flow_entities.PostIterationActionsDetails.from_dict(
            le[octobot_flow_entities.PostIterationActionsDetails.__name__]
        )
        assert post.updated_exchange_account_elements is not None


class TestEnsureOctobotProcessPrecomputeRecallPathWhenProcessStateLive:
    async def test_returns_recallable_with_init_state_ok_on_recall_path(self, tmp_path):
        start_script = tmp_path / "start.py"
        start_script.write_text("#", encoding="utf-8")
        op1 = octobot_process_ops.EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=None,
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            octobot_process_ops,
            "ensure_user_profile_and_layout",
            new=mock.AsyncMock(
                return_value={
                    "user_root": str(
                        tmp_path / commons_constants.USER_FOLDER / commons_constants.AUTOMATIONS_FOLDER / "ub"
                    ),
                    "profile_id": "x",
                    "already_prepared": True,
                }
            ),
        ), mock.patch.object(
            octobot_process_ops,
            "_listen_port_pair_with_shared_scan_offset",
            return_value=(20050, 30050),
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock, mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(side_effect=_async_return_none_mock),
        ):
            spawn_mock.return_value.pid = 10002
            await op1.pre_compute()
        first_value = op1.value
        assert isinstance(first_value, dict)
        first_le = first_value[dsl_interpreter.ReCallingOperatorResult.__name__]["last_execution_result"]
        assert isinstance(first_le, dict)
        anchor = first_le["started_waiting_at"]
        op2 = octobot_process_ops.EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=first_value,
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            dsl_interpreter.ProcessBoundOperatorMixin,
            "is_process_running",
            return_value=True,
        ), mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(side_effect=_async_live_process_bot_state_mock),
        ):
            await op2.pre_compute()
        assert isinstance(op2.value, dict)
        assert dsl_interpreter.ReCallingOperatorResult.__name__ in op2.value
        le2 = op2.value[dsl_interpreter.ReCallingOperatorResult.__name__]["last_execution_result"]
        assert isinstance(le2, dict)
        assert le2.get("init_state_ok") is True
        assert le2["started_waiting_at"] == anchor
        assert octobot_flow_entities.PostIterationActionsDetails.__name__ in le2
        post_after_recall = octobot_flow_entities.PostIterationActionsDetails.from_dict(
            le2[octobot_flow_entities.PostIterationActionsDetails.__name__]
        )
        assert post_after_recall.updated_exchange_account_elements is not None


class TestEnsureOctobotProcessInitTimeoutRaisesAndKills:
    async def test_init_timeout_kills_and_raises_dsl_error(self, tmp_path):
        user_root = str(
            tmp_path / commons_constants.USER_FOLDER / commons_constants.AUTOMATIONS_FOLDER / "ub"
        )
        state_fn = os.path.join(user_root, octobot_constants.PROCESS_BOT_STATE_FILE_NAME)
        inner = {
            "waiting_time": octobot_process_ops.DEFAULT_PING_WAITING_TIME,
            "last_execution_time": 0.0,
            "http_base_url": "http://127.0.0.1:20050",
            "web_port": 20050,
            "node_port": 30050,
            "user_root": user_root,
            "user_folder": "ub",
            "log_folder": str(tmp_path / "logs" / "a" / "ub"),
            "profile_id": "p",
            "pid": 88001,
            "port_offset": 0,
            "state_file_path": state_fn,
            "started_waiting_at": 0.0,
            "init_state_ok": False,
        }
        op = octobot_process_ops.EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
        )
        stop_mock = mock.Mock()
        st_time = mock.MagicMock()
        st_time.time = mock.Mock(return_value=500.0)
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            dsl_interpreter.ProcessBoundOperatorMixin,
            "is_process_running",
            return_value=True,
        ), mock.patch.object(octobot_process_ops, "time", st_time), mock.patch.object(
            dsl_interpreter.ProcessBoundOperatorMixin,
            "request_graceful_stop",
            new=stop_mock,
        ), mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
        ) as load_mock, mock.patch.object(
            octobot_process_ops,
            "_listen_port_pair_with_shared_scan_offset",
        ) as ffp:
            with pytest.raises(commons_errors.DSLInterpreterError, match="Timed out waiting"):
                await op.pre_compute()
        stop_mock.assert_called_once_with(logger=mock.ANY)
        load_mock.assert_not_called()
        ffp.assert_not_called()


class TestEnsureOctobotProcessLivenessNotBlockedByInitTimeout:
    async def test_does_not_apply_init_timeout_after_init_state_ok(self, tmp_path):
        user_root = str(
            tmp_path / commons_constants.USER_FOLDER / commons_constants.AUTOMATIONS_FOLDER / "ub"
        )
        state_fn2 = os.path.join(user_root, octobot_constants.PROCESS_BOT_STATE_FILE_NAME)
        inner = {
            "waiting_time": octobot_process_ops.DEFAULT_PING_WAITING_TIME,
            "last_execution_time": 0.0,
            "http_base_url": "http://127.0.0.1:20050",
            "web_port": 20050,
            "node_port": 30050,
            "user_root": user_root,
            "user_folder": "ub",
            "log_folder": str(tmp_path / "logs" / "a" / "ub"),
            "profile_id": "p",
            "pid": 88002,
            "port_offset": 0,
            "state_file_path": state_fn2,
            "started_waiting_at": 0.0,
            "init_state_ok": True,
        }
        op = octobot_process_ops.EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
        )
        st_time = mock.MagicMock()
        st_time.time = mock.Mock(return_value=1_000_000.0)
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            dsl_interpreter.ProcessBoundOperatorMixin,
            "is_process_running",
            return_value=True,
        ), mock.patch.object(octobot_process_ops, "time", st_time), mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(side_effect=_async_live_process_bot_state_mock),
        ):
            await op.pre_compute()
        assert isinstance(op.value, dict)
        rec = op.value[dsl_interpreter.ReCallingOperatorResult.__name__]
        assert isinstance(rec, dict)
        le = rec["last_execution_result"]
        assert isinstance(le, dict)
        assert le.get("init_state_ok") is True
        assert le["started_waiting_at"] == 0.0


class TestEnsureOctobotProcessWaitingTimeConstantInPayload:
    async def test_waiting_time_uses_parameter_for_recall_emissions(self, tmp_path):
        start_script = tmp_path / "start.py"
        start_script.write_text("#", encoding="utf-8")
        op = octobot_process_ops.EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=None,
            waiting_time=7.0,
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            octobot_process_ops,
            "ensure_user_profile_and_layout",
            new=mock.AsyncMock(
                return_value={
                    "user_root": str(
                        tmp_path / commons_constants.USER_FOLDER / commons_constants.AUTOMATIONS_FOLDER / "ub"
                    ),
                    "profile_id": "x",
                    "already_prepared": True,
                }
            ),
        ), mock.patch.object(
            octobot_process_ops,
            "_listen_port_pair_with_shared_scan_offset",
            return_value=(20050, 30050),
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock, mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(side_effect=_async_return_none_mock),
        ):
            spawn_mock.return_value.pid = 99999
            await op.pre_compute()
        assert isinstance(op.value, dict)
        le = op.value[dsl_interpreter.ReCallingOperatorResult.__name__]["last_execution_result"]
        assert isinstance(le, dict)
        assert le.get("waiting_time") == 7.0


class TestEnsureOctobotProcessDslIntegration:
    async def test_run_octobot_process_via_dsl(self, tmp_path, monkeypatch):
        """
        End-to-end: `run_octobot_process` is registered only on this interpreter; cwd is a fake
        project root. `spawn_managed_subprocess` is mocked so profile import, free ports, and
        process state liveness still run. With no state file, the operator returns a re-call;
        we then assert on-disk layout, re-call `log_folder`, and the single spawn invocation
        (argv, working_directory, env, hide_console_window).
        """
        # Minimal OctoBot project: `getcwd` must resolve `start.py` where `pre_compute` expects it.
        monkeypatch.chdir(tmp_path)
        (tmp_path / "start.py").write_text("#", encoding="utf-8")
        user_folder = "integration_dsl_bot"
        expression = f"run_octobot_process({user_folder!r}, {repr(_MINIMAL_PROFILE_DATA_DSL_LITERAL)})"
        # Contextual operator: excluded from get_all_operators(), so pass the class explicitly.
        interpreter = dsl_interpreter.Interpreter(
            [octobot_process_ops.EnsureOctobotProcessOperator],
        )
        try:
            with mock.patch.object(
                octobot_process_ops,
                "_load_process_bot_state",
                new=mock.AsyncMock(side_effect=_async_return_none_mock),
            ), mock.patch.object(
                process_util,
                "spawn_managed_subprocess",
            ) as spawn_mock:
                # Fake child pid; real spawn would run `start.py` with the env below.
                spawn_mock.return_value = mock.Mock(spec=["pid"], pid=12345)
                result = await interpreter.interprete(expression)
            assert isinstance(result, dict)
            # Re-call path: process state not live yet, interpreter should schedule another step.
            assert dsl_interpreter.ReCallingOperatorResult.__name__ in result
            user_data_root = (
                tmp_path
                / commons_constants.USER_FOLDER
                / commons_constants.AUTOMATIONS_FOLDER
                / user_folder
            )
            assert (user_data_root / commons_constants.CONFIG_FILE).is_file()
            assert (user_data_root / octobot_process_ops.DSL_PREPARED_MARKER).is_file()
            # Same normpath as ensure uses for the computed absolute log path (dir may not exist until the child runs).
            expected_log_folder = os.path.normpath(
                os.path.join(
                    str(tmp_path),
                    *octobot_node_constants.AUTOMATION_LOGS_FOLDER.split("/"),
                    user_folder,
                )
            )
            recalling = result[dsl_interpreter.ReCallingOperatorResult.__name__]
            assert isinstance(recalling, dict)
            last_execution = recalling["last_execution_result"]
            assert isinstance(last_execution, dict)
            assert last_execution.get("init_state_ok") is False
            assert last_execution["log_folder"] == expected_log_folder

            # spawn_managed_subprocess: project-root cwd, argv to `start.py` with relative --user-folder / --log-folder, and env
            # carrying chosen ports and bind address (see `EnsureOctobotProcessOperator.pre_compute`).
            spawn_mock.assert_called_once()
            spawn_argv = spawn_mock.call_args.args[0]
            spawn_kwargs = spawn_mock.call_args.kwargs
            assert spawn_kwargs["working_directory"] == str(tmp_path)
            expected_start_script = os.path.join(str(tmp_path), "start.py")
            rel_user = os.path.relpath(last_execution["user_root"], str(tmp_path))
            rel_log = os.path.relpath(last_execution["log_folder"], str(tmp_path))
            expected_state_path = os.path.normpath(
                os.path.join(
                    last_execution["user_root"],
                    octobot_constants.PROCESS_BOT_STATE_FILE_NAME,
                )
            )
            assert spawn_argv == [
                octobot_process_ops.sys.executable,
                expected_start_script,
                "--user-folder",
                rel_user,
                "--log-folder",
                rel_log,
                "-nt",
                "--dump-state",
                expected_state_path,
            ]
            child_env = spawn_kwargs["environment"]
            assert child_env[services_constants.ENV_WEB_PORT] == str(last_execution["web_port"])
            assert child_env[services_constants.ENV_WEB_ADDRESS] == "127.0.0.1"
            assert child_env[services_constants.ENV_NODE_API_PORT] == str(last_execution["node_port"])
            assert child_env[services_constants.ENV_NODE_API_ADDRESS] == "127.0.0.1"
            if sys.platform == "win32":
                assert spawn_kwargs.get("hide_console_window") is True
            else:
                assert spawn_kwargs.get("hide_console_window") is False
        finally:
            # Redundant with pytest’s tmp_path teardown; makes intent obvious if the test is copied elsewhere.
            shutil.rmtree(tmp_path / commons_constants.USER_FOLDER, ignore_errors=True)
            if (tmp_path / "logs").exists():
                shutil.rmtree(tmp_path / "logs", ignore_errors=True)


class TestEnsureOctobotProcessOperatorExecutionStop:
    async def test_execution_stop_dead_child_is_already_stopped(self):
        inner = _stop_test_ensure_state_dict("http://127.0.0.1:7")
        op = octobot_process_ops.EnsureOctobotProcessOperator(
            user_folder="u1",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
        )
        with (
            mock.patch.object(
                dsl_interpreter.ProcessBoundOperatorMixin,
                "is_process_running",
                return_value=False,
            ),
            octobot_process_ops.EnsureOctobotProcessOperator.set_execution_stop(),
        ):
            await op.pre_compute()
        assert isinstance(op.value, dict)
        assert op.value["status"] == "already_stopped"

    async def test_execution_stop_os_kill_failure_raises(self):
        inner = _stop_test_ensure_state_dict("http://127.0.0.1:7")
        op = octobot_process_ops.EnsureOctobotProcessOperator(
            user_folder="u1",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
        )

        def _kill_failed(_pid, _sig):
            raise OSError("simulated os.kill failure")

        with (
            mock.patch.object(
                process_util,
                "pid_is_running",
                return_value=True,
            ),
            mock.patch(
                "octobot_commons.process_util.os.kill",
                side_effect=_kill_failed,
            ),
            octobot_process_ops.EnsureOctobotProcessOperator.set_execution_stop(),
        ):
            with pytest.raises(commons_errors.DSLInterpreterError, match="simulated"):
                await op.pre_compute()
