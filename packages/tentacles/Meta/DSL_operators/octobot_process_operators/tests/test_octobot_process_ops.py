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
import pathlib
import shutil
import socket
import sys
import asyncio
import time
import uuid

import mock
import pytest

import octobot.constants as octobot_constants
import octobot_commons.constants as commons_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.errors as commons_errors
import octobot_commons.os_util as os_util
import octobot_commons.process_util as process_util
import octobot_node.constants as octobot_node_constants
import octobot_services.constants as services_constants

import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.exchange_auth_data as exchange_auth_data_module
import octobot_flow.entities as octobot_flow_entities
import octobot_flow.entities.accounts.process_bot_state as process_bot_state_import
import octobot_tentacles_manager.constants as tentacles_manager_constants

import tentacles.Meta.DSL_operators.octobot_process_operators.octobot_process_ops as octobot_process_ops
import tentacles.Trading.Mode.grid_trading_mode.grid_trading as grid_trading_module
import tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_trading as simple_market_making_trading

# Nested class from factory (not exposed on ``octobot_process_ops``).
TEST_EXECUTOR_ID = "test-executor"
EnsureOctobotProcessOperator = octobot_process_ops.create_octobot_process_operators(
    None, TEST_EXECUTOR_ID
)[0]

_TESTS_RUN_OCTOBOT_PROCESS_WAITING_TIME_SEC = 2
pytestmark = pytest.mark.asyncio


async def _async_return_none_mock(*_unused):
    return None


async def _async_live_process_bot_state_mock(*_unused, metadata_pid=20002):
    now = octobot_process_ops.time.time()
    interval = float(octobot_constants.PROCESS_BOT_STATE_DUMP_INTERVAL_SECONDS)
    return process_bot_state_import.ProcessBotState(
        metadata=process_bot_state_import.Metadata(
            updated_at=now - 0.1,
            next_updated_at=now + interval,
            pid=metadata_pid,
        ),
        exchange_account_elements=octobot_flow_entities.ExchangeAccountElements(),
    )


def _stale_process_bot_state_for_grace(*, age_seconds: float, metadata_pid: int = 10002):
    now = octobot_process_ops.time.time()
    interval = float(octobot_constants.PROCESS_BOT_STATE_DUMP_INTERVAL_SECONDS)
    return process_bot_state_import.ProcessBotState(
        metadata=process_bot_state_import.Metadata(
            updated_at=now - age_seconds,
            next_updated_at=now - age_seconds + interval,
            pid=metadata_pid,
        ),
        exchange_account_elements=octobot_flow_entities.ExchangeAccountElements(),
    )


async def _async_live_process_bot_state_with_pid_10001(*_unused):
    return await _async_live_process_bot_state_mock(metadata_pid=10001)


def _healthy_recall_inner(
    *,
    pid: int = 10002,
    init_state_ok: bool = True,
    user_root: str | None = None,
    tmp_path=None,
    executor_id: str = TEST_EXECUTOR_ID,
) -> dict:
    if user_root is None and tmp_path is not None:
        user_root = str(
            tmp_path / commons_constants.USER_FOLDER / commons_constants.AUTOMATIONS_FOLDER / "ub"
        )
    user_root = user_root or "/x/ub"
    state_fn = os.path.join(user_root, octobot_constants.PROCESS_BOT_STATE_FILE_NAME)
    return {
        "waiting_time": octobot_process_ops.DEFAULT_PING_WAITING_TIME,
        "last_execution_time": 0.0,
        "http_base_url": "http://127.0.0.1:20050",
        "web_port": 20050,
        "node_port": 30050,
        "user_root": user_root,
        "user_folder": "ub",
        "log_folder": "/x/logs/ub",
        "profile_id": "p",
        "pid": pid,
        "state_file_path": state_fn,
        "started_waiting_at": 0.0,
        "init_state_ok": init_state_ok,
        "executor_id": executor_id,
    }
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
        executor_id=TEST_EXECUTOR_ID,
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


def _octobot_project_root_from_test_file() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[6]


def _require_octobot_project_root_for_subprocess_tests() -> str:
    project_root = str(_octobot_project_root_from_test_file())
    start_script = os.path.join(project_root, "start.py")
    if not os.path.isfile(start_script):
        pytest.skip("start.py missing: run pytest with cwd set to the OctoBot project root")
    non_trading_profile_json = os.path.join(
        project_root,
        commons_constants.USER_FOLDER,
        commons_constants.PROFILES_FOLDER,
        octobot_process_ops.DEFAULT_DSL_PROFILE_ID,
        commons_constants.PROFILE_CONFIG_FILE,
    )
    if not os.path.isfile(non_trading_profile_json):
        pytest.skip(
            f"{octobot_process_ops.DEFAULT_DSL_PROFILE_ID!r} profile missing under OctoBot user/profiles"
        )
    return project_root


def _seed_executor_non_trading_profile(working_directory: pathlib.Path) -> None:
    source_profile_path = _octobot_project_root_from_test_file().joinpath(
        commons_constants.USER_FOLDER,
        commons_constants.PROFILES_FOLDER,
        octobot_process_ops.DEFAULT_DSL_PROFILE_ID,
    )
    if source_profile_path.is_dir():
        destination_profile_path = working_directory.joinpath(
            commons_constants.USER_FOLDER,
            commons_constants.PROFILES_FOLDER,
            octobot_process_ops.DEFAULT_DSL_PROFILE_ID,
        )
        destination_profile_path.parent.mkdir(parents=True, exist_ok=True)
        if destination_profile_path.exists():
            shutil.rmtree(destination_profile_path)
        shutil.copytree(source_profile_path, destination_profile_path)
        return
    minimal_profile_path = working_directory.joinpath(
        commons_constants.USER_FOLDER,
        commons_constants.PROFILES_FOLDER,
        octobot_process_ops.DEFAULT_DSL_PROFILE_ID,
    )
    minimal_profile_path.mkdir(parents=True, exist_ok=True)
    profile_payload = {
        commons_constants.CONFIG_PROFILE: {
            commons_constants.CONFIG_ID: octobot_process_ops.DEFAULT_DSL_PROFILE_ID,
            commons_constants.CONFIG_NAME: octobot_process_ops.DEFAULT_DSL_PROFILE_ID,
        }
    }
    (minimal_profile_path / commons_constants.PROFILE_CONFIG_FILE).write_text(
        json.dumps(profile_payload),
        encoding="utf-8",
    )


def _seed_executor_profile(
    working_directory: pathlib.Path,
    profile_id: str,
    *,
    read_only: bool,
) -> None:
    profile_path = working_directory.joinpath(
        commons_constants.USER_FOLDER,
        commons_constants.PROFILES_FOLDER,
        profile_id,
    )
    profile_path.mkdir(parents=True, exist_ok=True)
    profile_config = {
        commons_constants.CONFIG_ID: profile_id,
        commons_constants.CONFIG_NAME: profile_id,
    }
    if read_only:
        profile_config[commons_constants.CONFIG_READ_ONLY] = True
    profile_payload = {
        commons_constants.CONFIG_PROFILE: profile_config,
        commons_constants.PROFILE_CONFIG: {},
    }
    (profile_path / commons_constants.PROFILE_CONFIG_FILE).write_text(
        json.dumps(profile_payload),
        encoding="utf-8",
    )


def _recall_inner_from_interpreter_result(result: dict) -> dict | None:
    rec = result.get(dsl_interpreter.ReCallingOperatorResult.__name__)
    if not isinstance(rec, dict):
        return None
    inner = rec.get("last_execution_result")
    return inner if isinstance(inner, dict) else None


async def _poll_dsl_until_init_state_ok(
    interpreter: dsl_interpreter.Interpreter,
    user_folder: str,
    exchange_auth_list: list[dict],
    *,
    timeout_sec: float = 60.0,
) -> dict:
    base_arguments = (
        f"{user_folder!r}, exchange_auth_data={repr(exchange_auth_list)}, "
        f"waiting_time={_TESTS_RUN_OCTOBOT_PROCESS_WAITING_TIME_SEC}, ping_timeout=30.0"
    )
    deadline = time.monotonic() + timeout_sec
    last_full_result: dict | None = None
    while time.monotonic() < deadline:
        if last_full_result is None:
            expression = f"run_octobot_process({base_arguments})"
        else:
            expression = (
                f"run_octobot_process({base_arguments}, "
                f"last_execution_result={repr(last_full_result)})"
            )
        last_full_result = await interpreter.interprete(expression)
        assert isinstance(last_full_result, dict)
        inner = _recall_inner_from_interpreter_result(last_full_result)
        if inner and inner.get("init_state_ok") is True:
            return inner
        await asyncio.sleep(2.0)
    pytest.fail(f"OctoBot did not become ready (init_state_ok) within {timeout_sec}s")


def _fresh_default_like_cfg_template():
    """Minimal dict shaped like packaged ``default_config.json`` for isolated ``read_file`` mocks."""
    return {
        commons_constants.CONFIG_EXCHANGES: {},
        services_constants.CONFIG_CATEGORY_SERVICES: {
            services_constants.CONFIG_WEB: {
                services_constants.CONFIG_AUTO_OPEN_IN_WEB_BROWSER: True,
            },
        },
        commons_constants.CONFIG_PROFILE: "default",
    }


class TestWriteUserRootConfigJson:
    def test_sets_profile_and_disables_browser_auto_open(self, tmp_path):
        config_path = str(tmp_path / commons_constants.CONFIG_FILE)
        profile_id = "dsl_profile_abc"
        with mock.patch.object(
            octobot_process_ops.json_util,
            "read_file",
            side_effect=lambda *_unused: _fresh_default_like_cfg_template(),
        ):
            octobot_process_ops._write_user_root_config_json(
                config_path, profile_id, None, None
            )
        written = json.loads(pathlib.Path(config_path).read_text(encoding="utf-8"))
        assert written[commons_constants.CONFIG_PROFILE] == profile_id
        assert written[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_WEB][
            services_constants.CONFIG_AUTO_OPEN_IN_WEB_BROWSER
        ] is False
        assert written[commons_constants.CONFIG_EXCHANGES] == {}

    def test_seeds_exchanges_from_profile_data(self, tmp_path):
        config_path = str(tmp_path / commons_constants.CONFIG_FILE)
        profile_dict = {
            **_MINIMAL_PROFILE_DATA,
            "exchanges": [
                {"internal_name": "seed_exchange", "exchange_type": "future"},
                {"internal_name": "", "exchange_type": "spot"},
            ],
        }
        profile_data = profile_data_module.ProfileData.from_dict(profile_dict)
        with mock.patch.object(
            octobot_process_ops.json_util,
            "read_file",
            side_effect=lambda *_unused: _fresh_default_like_cfg_template(),
        ):
            octobot_process_ops._write_user_root_config_json(
                config_path, "p1", profile_data, None
            )
        written = json.loads(pathlib.Path(config_path).read_text(encoding="utf-8"))
        exchanges_cfg = written[commons_constants.CONFIG_EXCHANGES]
        assert set(exchanges_cfg) == {"seed_exchange"}
        seeded = exchanges_cfg["seed_exchange"]
        assert seeded[commons_constants.CONFIG_ENABLED_OPTION] is True
        assert seeded[commons_constants.CONFIG_EXCHANGE_TYPE] == "future"
        assert seeded[commons_constants.CONFIG_EXCHANGE_KEY] == octobot_process_ops._DEFAULT_ENCRYPTED_VALUE
        assert seeded[commons_constants.CONFIG_EXCHANGE_SECRET] == octobot_process_ops._DEFAULT_ENCRYPTED_VALUE

    def test_presets_encrypted_empty_credentials_when_default_config_exchange_has_no_api_fields(
        self, tmp_path
    ):
        """Mirrors packaged ``default_config.json`` rows that omit api-key/api-secret until setdefault."""
        config_path = str(tmp_path / commons_constants.CONFIG_FILE)
        template = _fresh_default_like_cfg_template()
        template[commons_constants.CONFIG_EXCHANGES] = {
            "prefilled_exchange": {
                commons_constants.CONFIG_ENABLED_OPTION: True,
                commons_constants.CONFIG_EXCHANGE_TYPE: commons_constants.CONFIG_EXCHANGE_SPOT,
            }
        }
        with mock.patch.object(
            octobot_process_ops.json_util,
            "read_file",
            side_effect=lambda *_unused: template,
        ):
            octobot_process_ops._write_user_root_config_json(config_path, "p0", None, None)
        written = json.loads(pathlib.Path(config_path).read_text(encoding="utf-8"))
        exch = written[commons_constants.CONFIG_EXCHANGES]["prefilled_exchange"]
        assert exch[commons_constants.CONFIG_EXCHANGE_KEY] == octobot_process_ops._DEFAULT_ENCRYPTED_VALUE
        assert exch[commons_constants.CONFIG_EXCHANGE_SECRET] == octobot_process_ops._DEFAULT_ENCRYPTED_VALUE

    def test_applies_exchange_auth_credentials(self, tmp_path):
        config_path = str(tmp_path / commons_constants.CONFIG_FILE)
        auth_list = [
            exchange_auth_data_module.ExchangeAuthData(
                internal_name="binance_test",
                api_key="key-a",
                api_secret="secret-b",
                api_password="pwd-c",
                exchange_type="spot",
                sandboxed=True,
            )
        ]
        with mock.patch.object(
            octobot_process_ops.json_util,
            "read_file",
            side_effect=lambda *_unused: _fresh_default_like_cfg_template(),
        ):
            octobot_process_ops._write_user_root_config_json(config_path, "p2", None, auth_list)
        written = json.loads(pathlib.Path(config_path).read_text(encoding="utf-8"))
        exch = written[commons_constants.CONFIG_EXCHANGES]["binance_test"]
        assert exch[commons_constants.CONFIG_EXCHANGE_KEY] == "key-a"
        assert exch[commons_constants.CONFIG_EXCHANGE_SECRET] == "secret-b"
        assert exch[commons_constants.CONFIG_EXCHANGE_PASSWORD] == "pwd-c"
        assert exch[commons_constants.CONFIG_EXCHANGE_TYPE] == "spot"
        assert exch[commons_constants.CONFIG_EXCHANGE_SANDBOXED] is True

    def test_profile_seed_then_auth_overlay(self, tmp_path):
        config_path = str(tmp_path / commons_constants.CONFIG_FILE)
        exchange_internal_name = "overlay_exchange"
        profile_dict = {
            **_MINIMAL_PROFILE_DATA,
            "exchanges": [{"internal_name": exchange_internal_name, "exchange_type": "spot"}],
        }
        profile_data = profile_data_module.ProfileData.from_dict(profile_dict)
        auth_list = [
            exchange_auth_data_module.ExchangeAuthData(
                internal_name=exchange_internal_name,
                api_key="overlay-key",
                api_secret="overlay-secret",
                exchange_type="spot",
            )
        ]
        with mock.patch.object(
            octobot_process_ops.json_util,
            "read_file",
            side_effect=lambda *_unused: _fresh_default_like_cfg_template(),
        ):
            octobot_process_ops._write_user_root_config_json(
                config_path, "p3", profile_data, auth_list
            )
        written = json.loads(pathlib.Path(config_path).read_text(encoding="utf-8"))
        exch = written[commons_constants.CONFIG_EXCHANGES][exchange_internal_name]
        assert exch[commons_constants.CONFIG_ENABLED_OPTION] is True
        assert exch[commons_constants.CONFIG_EXCHANGE_TYPE] == "spot"
        assert exch[commons_constants.CONFIG_EXCHANGE_KEY] == "overlay-key"
        assert exch[commons_constants.CONFIG_EXCHANGE_SECRET] == "overlay-secret"


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


class TestEnsureOctobotProcessOperatorProfileDataOptional:
    def test_declares_optional_profile_data_parameter(self):
        params = EnsureOctobotProcessOperator.get_parameters()
        profile_parameter = next(
            (parameter for parameter in params if parameter.name == "profile_data"),
            None,
        )
        assert profile_parameter is not None
        assert profile_parameter.required is False
        assert profile_parameter.default is None


class TestCopyReadOnlyProfilesToUserRoot:
    async def test_copies_read_only_profiles_and_skips_editable(self, tmp_path):
        _seed_executor_non_trading_profile(tmp_path)
        readonly_profile_id = "readonly_strategy"
        editable_profile_id = "editable_strategy"
        _seed_executor_profile(tmp_path, readonly_profile_id, read_only=True)
        _seed_executor_profile(tmp_path, editable_profile_id, read_only=False)
        user_root = tmp_path / "child_user_root"
        user_root.mkdir()
        await octobot_process_ops._copy_read_only_profiles_to_user_root(
            str(tmp_path),
            str(user_root),
            active_profile_id=octobot_process_ops.DEFAULT_DSL_PROFILE_ID,
        )
        profiles_root = user_root / commons_constants.PROFILES_FOLDER
        readonly_profile_json = (
            profiles_root / readonly_profile_id / commons_constants.PROFILE_CONFIG_FILE
        )
        editable_profile_json = (
            profiles_root / editable_profile_id / commons_constants.PROFILE_CONFIG_FILE
        )
        non_trading_profile_json = (
            profiles_root
            / octobot_process_ops.DEFAULT_DSL_PROFILE_ID
            / commons_constants.PROFILE_CONFIG_FILE
        )
        assert readonly_profile_json.is_file()
        assert not editable_profile_json.exists()
        assert not non_trading_profile_json.exists()

    async def test_skips_active_profile_id(self, tmp_path):
        _seed_executor_profile(
            tmp_path,
            octobot_process_ops.DEFAULT_DSL_PROFILE_ID,
            read_only=True,
        )
        user_root = tmp_path / "child_user_root"
        user_root.mkdir()
        destination_profile_path = (
            user_root
            / commons_constants.PROFILES_FOLDER
            / octobot_process_ops.DEFAULT_DSL_PROFILE_ID
        )
        destination_profile_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            tmp_path.joinpath(
                commons_constants.USER_FOLDER,
                commons_constants.PROFILES_FOLDER,
                octobot_process_ops.DEFAULT_DSL_PROFILE_ID,
            ),
            destination_profile_path,
        )
        profile_json_path = destination_profile_path / commons_constants.PROFILE_CONFIG_FILE
        original_mtime = profile_json_path.stat().st_mtime
        await octobot_process_ops._copy_read_only_profiles_to_user_root(
            str(tmp_path),
            str(user_root),
            active_profile_id=octobot_process_ops.DEFAULT_DSL_PROFILE_ID,
        )
        assert profile_json_path.stat().st_mtime == original_mtime


class TestEnsureUserProfileAndLayoutDefaultProfile:
    async def test_copies_non_trading_profile_and_writes_default_config(self, tmp_path):
        _seed_executor_non_trading_profile(tmp_path)
        user_leaf = "default_profile_layout_user"
        result = await octobot_process_ops.ensure_user_profile_and_layout(
            user_leaf,
            str(tmp_path),
            None,
            None,
            None,
        )
        assert result["already_prepared"] is False
        assert result["profile_id"] == octobot_process_ops.DEFAULT_DSL_PROFILE_ID
        user_root = pathlib.Path(result["user_root"])
        profile_json_path = (
            user_root
            / commons_constants.PROFILES_FOLDER
            / octobot_process_ops.DEFAULT_DSL_PROFILE_ID
            / commons_constants.PROFILE_CONFIG_FILE
        )
        assert profile_json_path.is_file()
        root_config_path = user_root / commons_constants.CONFIG_FILE
        root_cfg = json.loads(root_config_path.read_text(encoding="utf-8"))
        assert root_cfg[commons_constants.CONFIG_PROFILE] == octobot_process_ops.DEFAULT_DSL_PROFILE_ID
        assert (
            root_cfg[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_WEB][
                services_constants.CONFIG_AUTO_OPEN_IN_WEB_BROWSER
            ]
            is False
        )
        assert root_cfg[commons_constants.CONFIG_ACCEPTED_TERMS] is True

    async def test_copies_read_only_profiles_on_default_layout(self, tmp_path):
        _seed_executor_non_trading_profile(tmp_path)
        readonly_profile_id = "readonly_strategy"
        _seed_executor_profile(tmp_path, readonly_profile_id, read_only=True)
        user_leaf = "default_layout_with_readonly_profiles"
        result = await octobot_process_ops.ensure_user_profile_and_layout(
            user_leaf,
            str(tmp_path),
            None,
            None,
            None,
        )
        user_root = pathlib.Path(result["user_root"])
        profiles_root = user_root / commons_constants.PROFILES_FOLDER
        assert (
            profiles_root
            / octobot_process_ops.DEFAULT_DSL_PROFILE_ID
            / commons_constants.PROFILE_CONFIG_FILE
        ).is_file()
        assert (
            profiles_root / readonly_profile_id / commons_constants.PROFILE_CONFIG_FILE
        ).is_file()

    async def test_applies_exchange_auth_without_profile_data(self, tmp_path):
        _seed_executor_non_trading_profile(tmp_path)
        exchange_internal_name = "default_layout_exchange"
        exchange_auth_list = [
            exchange_auth_data_module.ExchangeAuthData(
                internal_name=exchange_internal_name,
                api_key="layout-key",
                api_secret="layout-secret",
                exchange_type=commons_constants.CONFIG_EXCHANGE_SPOT,
                sandboxed=True,
            )
        ]
        result = await octobot_process_ops.ensure_user_profile_and_layout(
            "default_exchange_user",
            str(tmp_path),
            None,
            None,
            exchange_auth_list,
        )
        user_root = pathlib.Path(result["user_root"])
        root_cfg = json.loads((user_root / commons_constants.CONFIG_FILE).read_text(encoding="utf-8"))
        exchange_cfg = root_cfg[commons_constants.CONFIG_EXCHANGES][exchange_internal_name]
        assert exchange_cfg[commons_constants.CONFIG_EXCHANGE_KEY] == "layout-key"
        assert exchange_cfg[commons_constants.CONFIG_EXCHANGE_SECRET] == "layout-secret"
        assert exchange_cfg[commons_constants.CONFIG_EXCHANGE_TYPE] == commons_constants.CONFIG_EXCHANGE_SPOT
        assert exchange_cfg[commons_constants.CONFIG_EXCHANGE_SANDBOXED] is True


class TestEnsureUserProfileAndLayoutFunctional:
    async def test_writes_profile_tree_top_level_config_and_exchange_credentials(self, tmp_path):
        exchange_internal_name = "functional_exchange_okx"
        fake_api_key = "functional-test-api-key"
        fake_api_secret = "functional-test-api-secret"
        fake_api_password = "functional-test-api-password"
        user_leaf = "functional_layout_user"
        profile_dict = {
            **_MINIMAL_PROFILE_DATA,
            "exchanges": [
                {
                    "internal_name": exchange_internal_name,
                    "exchange_type": commons_constants.CONFIG_EXCHANGE_SPOT,
                }
            ],
        }
        exchange_auth_list = [
            exchange_auth_data_module.ExchangeAuthData(
                internal_name=exchange_internal_name,
                api_key=fake_api_key,
                api_secret=fake_api_secret,
                api_password=fake_api_password,
                exchange_type=commons_constants.CONFIG_EXCHANGE_SPOT,
                sandboxed=True,
            )
        ]

        result = await octobot_process_ops.ensure_user_profile_and_layout(
            user_leaf,
            str(tmp_path),
            profile_dict,
            None,
            exchange_auth_list,
        )

        assert result["already_prepared"] is False
        profile_id = result["profile_id"]
        assert profile_id
        user_root = pathlib.Path(result["user_root"])
        assert user_root == (
            tmp_path / commons_constants.USER_FOLDER / commons_constants.AUTOMATIONS_FOLDER / user_leaf
        )

        marker_path = user_root / octobot_process_ops.DSL_PREPARED_MARKER
        root_config_path = user_root / commons_constants.CONFIG_FILE
        profile_dir = user_root / commons_constants.PROFILES_FOLDER / profile_id
        profile_json_path = profile_dir / commons_constants.PROFILE_CONFIG_FILE
        tentacles_setup_path = profile_dir / commons_constants.CONFIG_TENTACLES_FILE

        assert marker_path.is_file()
        assert root_config_path.is_file()
        assert profile_json_path.is_file()
        assert tentacles_setup_path.is_file()
        reference_layout = user_root / "reference_tentacles_config"
        assert reference_layout.is_dir()

        root_cfg = json.loads(root_config_path.read_text(encoding="utf-8"))
        assert root_cfg[commons_constants.CONFIG_PROFILE] == profile_id
        assert (
            root_cfg[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_WEB][
                services_constants.CONFIG_AUTO_OPEN_IN_WEB_BROWSER
            ]
            is False
        )
        exchange_root = root_cfg[commons_constants.CONFIG_EXCHANGES][exchange_internal_name]
        assert exchange_root[commons_constants.CONFIG_ENABLED_OPTION] is True
        assert exchange_root[commons_constants.CONFIG_EXCHANGE_TYPE] == commons_constants.CONFIG_EXCHANGE_SPOT
        assert exchange_root[commons_constants.CONFIG_EXCHANGE_KEY] == fake_api_key
        assert exchange_root[commons_constants.CONFIG_EXCHANGE_SECRET] == fake_api_secret
        assert exchange_root[commons_constants.CONFIG_EXCHANGE_PASSWORD] == fake_api_password
        assert exchange_root[commons_constants.CONFIG_EXCHANGE_SANDBOXED] is True

        profile_payload = json.loads(profile_json_path.read_text(encoding="utf-8"))
        profile_inner = profile_payload[commons_constants.PROFILE_CONFIG]
        profile_exchanges = profile_inner[commons_constants.CONFIG_EXCHANGES][exchange_internal_name]
        assert profile_exchanges[commons_constants.CONFIG_ENABLED_OPTION] is True
        assert profile_exchanges[commons_constants.CONFIG_EXCHANGE_TYPE] == commons_constants.CONFIG_EXCHANGE_SPOT


class TestConvertProfileDataToProfileDirectory:
    async def test_omits_translator_when_profile_has_no_tentacles(self, tmp_path):
        profile_data = profile_data_module.ProfileData.from_dict(_MINIMAL_PROFILE_DATA)
        output_dir = tmp_path / "profile_out"
        output_dir.mkdir()
        convert_mock = mock.AsyncMock()
        with mock.patch.object(
            octobot_process_ops.tentacles_profile_data_translator,
            "TentaclesProfileDataTranslator",
        ) as translator_class_mock, mock.patch.object(
            octobot_process_ops.profile_data_import,
            "convert_profile_data_to_profile_directory",
            new=convert_mock,
        ):
            await octobot_process_ops._convert_profile_data_to_profile_directory(
                profile_data, str(output_dir)
            )
        translator_class_mock.assert_not_called()
        convert_mock.assert_awaited_once()

    async def test_restores_tentacles_when_translator_raises_key_error(self, tmp_path):
        profile_with_grid = {
            **_MINIMAL_PROFILE_DATA,
            "tentacles": [
                {
                    "name": grid_trading_module.GridTradingMode.get_name(),
                    "config": {"pair_settings": []},
                }
            ],
        }
        profile_data = profile_data_module.ProfileData.from_dict(profile_with_grid)
        expected_tentacles_snapshot = list(profile_data.tentacles)
        output_dir = tmp_path / "profile_out"
        output_dir.mkdir()
        convert_mock = mock.AsyncMock()
        with mock.patch.object(
            octobot_process_ops.profile_data_import,
            "convert_profile_data_to_profile_directory",
            new=convert_mock,
        ):
            await octobot_process_ops._convert_profile_data_to_profile_directory(
                profile_data, str(output_dir)
            )
        assert len(profile_data.tentacles) == len(expected_tentacles_snapshot)
        assert [tentacle.name for tentacle in profile_data.tentacles] == [
            tentacle.name for tentacle in expected_tentacles_snapshot
        ]
        convert_mock.assert_awaited_once()

    async def test_calls_translator_then_convert_when_tentacles_present(self, tmp_path):
        profile_with_grid = {
            **_MINIMAL_PROFILE_DATA,
            "tentacles": [
                {
                    "name": grid_trading_module.GridTradingMode.get_name(),
                    "config": {"pair_settings": []},
                }
            ],
        }
        profile_data = profile_data_module.ProfileData.from_dict(profile_with_grid)
        expected_snapshot = list(profile_data.tentacles)
        output_dir = tmp_path / "profile_out"
        output_dir.mkdir()
        mock_translator = mock.Mock()
        mock_translator.translate = mock.AsyncMock()
        convert_mock = mock.AsyncMock()
        with mock.patch.object(
            octobot_process_ops.tentacles_profile_data_translator,
            "TentaclesProfileDataTranslator",
            return_value=mock_translator,
        ) as translator_class_mock, mock.patch.object(
            octobot_process_ops.profile_data_import,
            "convert_profile_data_to_profile_directory",
            new=convert_mock,
        ):
            await octobot_process_ops._convert_profile_data_to_profile_directory(
                profile_data, str(output_dir)
            )
        translator_class_mock.assert_called_once_with(profile_data, [])
        mock_translator.translate.assert_awaited_once_with(
            expected_snapshot, {"is_simulated": True}, None, None
        )
        convert_mock.assert_awaited_once()


class TestConvertProfileDataToProfileDirectorySimpleMarketMakingFunctional:
    async def test_writes_disk_profile_with_adapter_augmented_mm_config(self, tmp_path):
        exchange_internal_name = "binanceus"
        traded_pair = "BTC/USDT"
        _SMM = simple_market_making_trading.SimpleMarketMakingTradingMode
        profile_dict = {
            **_MINIMAL_PROFILE_DATA,
            "crypto_currencies": [],
            "exchanges": [
                {
                    "internal_name": exchange_internal_name,
                    "exchange_type": "spot",
                }
            ],
            "tentacles": [
                {
                    "name": _SMM.get_name(),
                    "config": {
                        _SMM.CONFIG_PAIR_SETTINGS: [
                            {
                                _SMM.CONFIG_PAIR: traded_pair,
                                _SMM.REFERENCE_PRICE: [
                                    {
                                        _SMM.EXCHANGE: exchange_internal_name,
                                        _SMM.PAIR: traded_pair,
                                        _SMM.WEIGHT: 1,
                                    }
                                ],
                                _SMM.MAX_BASE_BUDGET: 0.1,
                                _SMM.MAX_QUOTE_BUDGET: 3000,
                            }
                        ],
                    },
                }
            ],
        }
        profile_data = profile_data_module.ProfileData.from_dict(profile_dict)
        output_dir = tmp_path / "mm_profile"
        output_dir.mkdir()
        await octobot_process_ops._convert_profile_data_to_profile_directory(
            profile_data, str(output_dir)
        )

        profile_json_path = output_dir / commons_constants.PROFILE_CONFIG_FILE
        assert profile_json_path.is_file()
        profile_payload = json.loads(profile_json_path.read_text(encoding="utf-8"))
        profile_config = profile_payload[commons_constants.PROFILE_CONFIG]
        assert traded_pair in profile_config[commons_constants.CONFIG_CRYPTO_CURRENCIES]
        assert exchange_internal_name in profile_config[commons_constants.CONFIG_EXCHANGES]

        mm_specific = output_dir / tentacles_manager_constants.TENTACLES_SPECIFIC_CONFIG_FOLDER / (
            f"{_SMM.get_name()}{tentacles_manager_constants.CONFIG_EXT}"
        )
        assert mm_specific.is_file()
        mm_cfg = json.loads(mm_specific.read_text(encoding="utf-8"))
        pair_settings = mm_cfg[_SMM.CONFIG_PAIR_SETTINGS]
        assert len(pair_settings) >= 1
        ref_prices = pair_settings[0][_SMM.REFERENCE_PRICE]
        assert any(
            ref[_SMM.EXCHANGE] == exchange_internal_name for ref in ref_prices
        )

        tentacles_cfg_path = output_dir / commons_constants.CONFIG_TENTACLES_FILE
        assert tentacles_cfg_path.is_file()
        tentacles_raw = tentacles_cfg_path.read_text(encoding="utf-8")
        assert _SMM.get_name() in tentacles_raw


class TestListenPortPair:
    def test_finds_sequential_ports(self):
        web_port, node_port = octobot_process_ops._listen_port_pair_with_shared_scan_offset(
            "127.0.0.1", 20000, 30000, max_offset=100
        )
        assert os_util.tcp_port_is_free("127.0.0.1", web_port)
        assert os_util.tcp_port_is_free("127.0.0.1", node_port)

    def test_skips_port_occupied_on_host(self):
        node_port_base = 35000
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            occupied_port = listener.getsockname()[1]
            listener.listen(1)
            web_port, _node_port = octobot_process_ops._listen_port_pair_with_shared_scan_offset(
                "127.0.0.1", occupied_port, node_port_base, max_offset=10
            )
        assert web_port != occupied_port


class TestEnsureOctobotProcessOperatorExchangeAuthData:
    def test_declares_optional_exchange_auth_parameter(self):
        params = EnsureOctobotProcessOperator.get_parameters()
        auth_parameter = next(
            (parameter for parameter in params if parameter.name == "exchange_auth_data"),
            None,
        )
        assert auth_parameter is not None
        assert auth_parameter.required is False
        assert auth_parameter.default is None
        assert auth_parameter.type == list[dict]

    async def test_pre_compute_passes_dict_exchange_auth_into_ensure_layout(self, tmp_path):
        exchange_auth_dicts = [
            {
                "internal_name": "dsl_exchange_okx",
                "api_key": "dsl-precompute-key",
                "api_secret": "dsl-precompute-secret",
                "exchange_type": commons_constants.CONFIG_EXCHANGE_SPOT,
            }
        ]
        ensure_layout_mock = mock.AsyncMock(
            return_value={
                "user_root": str(
                    tmp_path / commons_constants.USER_FOLDER / commons_constants.AUTOMATIONS_FOLDER / "ub"
                ),
                "profile_id": "profile-from-mock",
                "already_prepared": True,
            }
        )
        start_script = tmp_path / "start.py"
        start_script.write_text("#", encoding="utf-8")
        operator_instance = EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            exchange_auth_data=exchange_auth_dicts,
            last_execution_result=None,
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            octobot_process_ops,
            "ensure_user_profile_and_layout",
            new=ensure_layout_mock,
        ), mock.patch.object(
            octobot_process_ops,
            "_listen_port_pair_with_shared_scan_offset",
            return_value=(20050, 30050),
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_managed_mock:
            spawn_managed_mock.return_value.pid = 424242
            await operator_instance.pre_compute()

        ensure_layout_mock.assert_awaited_once()
        await_arguments = ensure_layout_mock.await_args.args
        assert len(await_arguments) >= 5
        parsed_exchange_auth = await_arguments[4]
        assert parsed_exchange_auth is not None
        assert len(parsed_exchange_auth) == 1
        assert isinstance(parsed_exchange_auth[0], exchange_auth_data_module.ExchangeAuthData)
        assert parsed_exchange_auth[0].internal_name == "dsl_exchange_okx"
        assert parsed_exchange_auth[0].api_key == "dsl-precompute-key"
        assert parsed_exchange_auth[0].api_secret == "dsl-precompute-secret"
        assert parsed_exchange_auth[0].exchange_type == commons_constants.CONFIG_EXCHANGE_SPOT


class TestEnsureOctobotProcessOperatorPrecompute:
    async def test_returns_recallable_when_process_bot_state_not_live(self, tmp_path):
        start_script = tmp_path / "start.py"
        start_script.write_text("#", encoding="utf-8")
        op = EnsureOctobotProcessOperator(
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
        op = EnsureOctobotProcessOperator(
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
            process_util,
            "pid_is_running",
            side_effect=lambda process_id: process_id == 10001,
        ), mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(side_effect=_async_live_process_bot_state_with_pid_10001),
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
        op1 = EnsureOctobotProcessOperator(
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
        op2 = EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=first_value,
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            process_util,
            "pid_is_running",
            side_effect=lambda process_id: process_id == 10002,
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
            "executor_id": TEST_EXECUTOR_ID,
        }
        op = EnsureOctobotProcessOperator(
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
            new=mock.AsyncMock(return_value=None),
        ) as load_mock, mock.patch.object(
            octobot_process_ops,
            "_listen_port_pair_with_shared_scan_offset",
        ) as ffp:
            with pytest.raises(commons_errors.DSLInterpreterError, match="Timed out waiting"):
                await op.pre_compute()
        stop_mock.assert_called_once_with(logger=mock.ANY)
        load_mock.assert_called()
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
            "executor_id": TEST_EXECUTOR_ID,
        }
        op = EnsureOctobotProcessOperator(
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
            process_util,
            "pid_is_running",
            side_effect=lambda process_id: process_id in (88002, 20002),
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
        op = EnsureOctobotProcessOperator(
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
        # Contextual operator is excluded from get_all_operators(); append it explicitly.
        interpreter = dsl_interpreter.Interpreter(
            dsl_interpreter.get_all_operators()
            + [EnsureOctobotProcessOperator],
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
            assert spawn_kwargs.get("hide_console_window") is True
        finally:
            # Redundant with pytest’s tmp_path teardown; makes intent obvious if the test is copied elsewhere.
            shutil.rmtree(tmp_path / commons_constants.USER_FOLDER, ignore_errors=True)
            if (tmp_path / "logs").exists():
                shutil.rmtree(tmp_path / "logs", ignore_errors=True)

    async def test_run_octobot_process_via_dsl_writes_exchange_auth_into_user_config(
        self, tmp_path, monkeypatch
    ):
        """
        Same pipeline as ``test_run_octobot_process_via_dsl``, plus positional
        ``exchange_auth_data`` (list of dicts). Verifies API fields land under
        ``exchanges`` in the user-root ``config.json`` written during layout.
        """
        monkeypatch.chdir(tmp_path)
        (tmp_path / "start.py").write_text("#", encoding="utf-8")
        user_folder = "integration_dsl_exchange_auth_bot"
        exchange_internal_name = "dsl_integration_cred_exchange"
        fake_api_key = "dsl-integration-api-key"
        fake_api_secret = "dsl-integration-api-secret"
        fake_api_password = "dsl-integration-api-password"
        exchange_auth_list = [
            {
                "internal_name": exchange_internal_name,
                "api_key": fake_api_key,
                "api_secret": fake_api_secret,
                "api_password": fake_api_password,
                "exchange_type": commons_constants.CONFIG_EXCHANGE_SPOT,
                "sandboxed": True,
            }
        ]
        expression = (
            f"run_octobot_process({user_folder!r}, {repr(_MINIMAL_PROFILE_DATA_DSL_LITERAL)}, "
            f"{repr(exchange_auth_list)})"
        )
        interpreter = dsl_interpreter.Interpreter(
            dsl_interpreter.get_all_operators()
            + [EnsureOctobotProcessOperator],
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
                spawn_mock.return_value = mock.Mock(spec=["pid"], pid=12345)
                result = await interpreter.interprete(expression)
            assert isinstance(result, dict)
            assert dsl_interpreter.ReCallingOperatorResult.__name__ in result
            user_data_root = (
                tmp_path
                / commons_constants.USER_FOLDER
                / commons_constants.AUTOMATIONS_FOLDER
                / user_folder
            )
            root_config_path = user_data_root / commons_constants.CONFIG_FILE
            assert root_config_path.is_file()
            written_root_cfg = json.loads(root_config_path.read_text(encoding="utf-8"))
            exchange_cfg = written_root_cfg[commons_constants.CONFIG_EXCHANGES][exchange_internal_name]
            assert exchange_cfg[commons_constants.CONFIG_EXCHANGE_KEY] == fake_api_key
            assert exchange_cfg[commons_constants.CONFIG_EXCHANGE_SECRET] == fake_api_secret
            assert exchange_cfg[commons_constants.CONFIG_EXCHANGE_PASSWORD] == fake_api_password
            assert exchange_cfg[commons_constants.CONFIG_EXCHANGE_TYPE] == commons_constants.CONFIG_EXCHANGE_SPOT
            assert exchange_cfg[commons_constants.CONFIG_EXCHANGE_SANDBOXED] is True
            assert exchange_cfg[commons_constants.CONFIG_ENABLED_OPTION] is True
        finally:
            shutil.rmtree(tmp_path / commons_constants.USER_FOLDER, ignore_errors=True)
            if (tmp_path / "logs").exists():
                shutil.rmtree(tmp_path / "logs", ignore_errors=True)

    async def test_run_octobot_process_via_dsl_without_profile_data_accepts_exchange_auth(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "start.py").write_text("#", encoding="utf-8")
        _seed_executor_non_trading_profile(tmp_path)
        user_folder = "integration_dsl_no_profile_bot"
        exchange_internal_name = "dsl_no_profile_exchange"
        exchange_auth_list = [
            {
                "internal_name": exchange_internal_name,
                "api_key": "no-profile-key",
                "api_secret": "no-profile-secret",
                "exchange_type": commons_constants.CONFIG_EXCHANGE_SPOT,
                "sandboxed": True,
            }
        ]
        expression = (
            f"run_octobot_process({user_folder!r}, exchange_auth_data={repr(exchange_auth_list)}, "
            f"waiting_time={_TESTS_RUN_OCTOBOT_PROCESS_WAITING_TIME_SEC}, ping_timeout=30.0)"
        )
        interpreter = dsl_interpreter.Interpreter(
            dsl_interpreter.get_all_operators()
            + [EnsureOctobotProcessOperator],
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
                spawn_mock.return_value = mock.Mock(spec=["pid"], pid=54321)
                result = await interpreter.interprete(expression)
            assert isinstance(result, dict)
            assert dsl_interpreter.ReCallingOperatorResult.__name__ in result
            user_data_root = (
                tmp_path
                / commons_constants.USER_FOLDER
                / commons_constants.AUTOMATIONS_FOLDER
                / user_folder
            )
            root_config_path = user_data_root / commons_constants.CONFIG_FILE
            assert root_config_path.is_file()
            written_root_cfg = json.loads(root_config_path.read_text(encoding="utf-8"))
            assert written_root_cfg[commons_constants.CONFIG_PROFILE] == octobot_process_ops.DEFAULT_DSL_PROFILE_ID
            profile_json_path = (
                user_data_root
                / commons_constants.PROFILES_FOLDER
                / octobot_process_ops.DEFAULT_DSL_PROFILE_ID
                / commons_constants.PROFILE_CONFIG_FILE
            )
            assert profile_json_path.is_file()
            exchange_cfg = written_root_cfg[commons_constants.CONFIG_EXCHANGES][exchange_internal_name]
            assert exchange_cfg[commons_constants.CONFIG_EXCHANGE_KEY] == "no-profile-key"
            assert exchange_cfg[commons_constants.CONFIG_EXCHANGE_SECRET] == "no-profile-secret"
        finally:
            shutil.rmtree(tmp_path / commons_constants.USER_FOLDER, ignore_errors=True)
            if (tmp_path / "logs").exists():
                shutil.rmtree(tmp_path / "logs", ignore_errors=True)


class TestRunOctobotProcessDefaultConfigSubprocess:
    async def _run_default_config_lifecycle(
        self,
        *,
        project_root: str,
        exchange_auth_list: list[dict],
        user_folder_suffix: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(project_root)
        monkeypatch.setenv(octobot_constants.ENV_PROCESS_BOT_STATE_DUMP_INTERVAL_SECONDS, "5")
        user_folder = f"unit_tests/default_cfg_{user_folder_suffix}_{uuid.uuid4().hex[:10]}"
        interpreter = dsl_interpreter.Interpreter(
            dsl_interpreter.get_all_operators()
            + [EnsureOctobotProcessOperator],
        )
        user_root_guess = os.path.normpath(
            os.path.join(
                project_root,
                *commons_constants.USER_AUTOMATIONS_FOLDER.split("/"),
                *user_folder.replace("\\", "/").split("/"),
            )
        )
        log_folder_guess = os.path.normpath(
            os.path.join(
                project_root,
                *octobot_node_constants.AUTOMATION_LOGS_FOLDER.split("/"),
                *[segment for segment in user_folder.replace("\\", "/").split("/") if segment],
            )
        )
        child_pid: int | None = None
        try:
            inner = await _poll_dsl_until_init_state_ok(
                interpreter,
                user_folder,
                exchange_auth_list,
                timeout_sec=90.0,
            )
            assert inner.get("pid")
            child_pid = int(inner["pid"])
            assert process_util.pid_is_running(child_pid)
            user_root = pathlib.Path(inner["user_root"])
            assert inner.get("profile_id") == octobot_process_ops.DEFAULT_DSL_PROFILE_ID
            root_cfg = json.loads((user_root / commons_constants.CONFIG_FILE).read_text(encoding="utf-8"))
            exchange_internal_name = exchange_auth_list[0]["internal_name"]
            assert exchange_internal_name in root_cfg[commons_constants.CONFIG_EXCHANGES]
            exchange_cfg = root_cfg[commons_constants.CONFIG_EXCHANGES][exchange_internal_name]
            if exchange_auth_list[0].get("api_key"):
                stored_api_key = exchange_cfg[commons_constants.CONFIG_EXCHANGE_KEY]
                stored_api_secret = exchange_cfg[commons_constants.CONFIG_EXCHANGE_SECRET]
                assert stored_api_key != exchange_auth_list[0]["api_key"]
                assert stored_api_secret != exchange_auth_list[0]["api_secret"]
                assert isinstance(stored_api_key, str) and stored_api_key.startswith("gAAAAA")
                assert isinstance(stored_api_secret, str) and stored_api_secret.startswith("gAAAAA")
            else:
                assert exchange_cfg[commons_constants.CONFIG_EXCHANGE_SANDBOXED] is exchange_auth_list[0]["sandboxed"]
                assert exchange_cfg[commons_constants.CONFIG_EXCHANGE_TYPE] == exchange_auth_list[0]["exchange_type"]
            profile_json_path = (
                user_root
                / commons_constants.PROFILES_FOLDER
                / octobot_process_ops.DEFAULT_DSL_PROFILE_ID
                / commons_constants.PROFILE_CONFIG_FILE
            )
            assert profile_json_path.is_file()
            stop_expression = (
                f"run_octobot_process({user_folder!r}, exchange_auth_data={repr(exchange_auth_list)}, "
                f"waiting_time={_TESTS_RUN_OCTOBOT_PROCESS_WAITING_TIME_SEC}, ping_timeout=30.0, "
                f"last_execution_result={repr(_re_calling_ensure_value(inner))})"
            )
            operator_signals_holder = dsl_interpreter.OperatorSignals()
            stop_operator_cls = octobot_process_ops.create_octobot_process_operators(
                operator_signals_holder,
                TEST_EXECUTOR_ID,
            )[0]
            operator_signals_holder.sync({
                stop_operator_cls.get_name(): dsl_interpreter.OperatorSignal.STOP.value,
            })
            stop_interpreter = dsl_interpreter.Interpreter(
                dsl_interpreter.get_all_operators()
                + [stop_operator_cls],
            )
            stop_result = await stop_interpreter.interprete(stop_expression)
            assert isinstance(stop_result, dict)
            assert stop_result.get("status") in ("stopped", "already_stopped")
            process_deadline = time.monotonic() + 30.0
            while time.monotonic() < process_deadline:
                if not process_util.pid_is_running(child_pid):
                    break
                await asyncio.sleep(0.5)
            else:
                pytest.fail(f"expected child pid {child_pid} to exit after STOP within 30s")
        finally:
            if child_pid is not None and process_util.pid_is_running(child_pid):
                process_util.request_graceful_stop_via_sigterm(child_pid)
            if os.path.isdir(user_root_guess):
                shutil.rmtree(user_root_guess, ignore_errors=True)
            if os.path.isdir(log_folder_guess):
                shutil.rmtree(log_folder_guess, ignore_errors=True)

    async def test_simulated_bot_without_profile_data(self, monkeypatch):
        project_root = _require_octobot_project_root_for_subprocess_tests()
        exchange_auth_list = [
            {
                "internal_name": "binanceus",
                "sandboxed": True,
                "exchange_type": commons_constants.CONFIG_EXCHANGE_SPOT,
            }
        ]
        await self._run_default_config_lifecycle(
            project_root=project_root,
            exchange_auth_list=exchange_auth_list,
            user_folder_suffix="simulated",
            monkeypatch=monkeypatch,
        )

    async def test_real_bot_without_profile_data(self, monkeypatch):
        project_root = _require_octobot_project_root_for_subprocess_tests()
        exchange_auth_list = [
            {
                "internal_name": "binanceus",
                "api_key": "functional-test-api-key",
                "api_secret": "functional-test-api-secret",
                "sandboxed": True,
                "exchange_type": commons_constants.CONFIG_EXCHANGE_SPOT,
            }
        ]
        await self._run_default_config_lifecycle(
            project_root=project_root,
            exchange_auth_list=exchange_auth_list,
            user_folder_suffix="real_creds",
            monkeypatch=monkeypatch,
        )


class TestEnsureOctobotProcessOperatorExecutionStop:
    async def test_execution_stop_dead_child_is_already_stopped(self):
        inner = _stop_test_ensure_state_dict("http://127.0.0.1:7")
        operator_signals_holder = dsl_interpreter.OperatorSignals()
        operator_under_test = octobot_process_ops.create_octobot_process_operators(
            operator_signals_holder,
            TEST_EXECUTOR_ID,
        )[0]
        operator_signals_holder.sync({
            operator_under_test.get_name(): dsl_interpreter.OperatorSignal.STOP.value,
        })
        op = operator_under_test(
            user_folder="u1",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
        )
        with mock.patch.object(
            process_util,
            "pid_is_running",
            return_value=False,
        ):
            await op.pre_compute()
        assert isinstance(op.value, dict)
        assert op.value["status"] == "already_stopped"

    async def test_execution_stop_short_circuits_without_sigterm_when_not_running(self):
        """STOP branch returns already_stopped before ``request_graceful_stop`` when stored pid is not running."""
        inner = _stop_test_ensure_state_dict("http://127.0.0.1:7")
        operator_signals_holder = dsl_interpreter.OperatorSignals()
        operator_under_test = octobot_process_ops.create_octobot_process_operators(
            operator_signals_holder,
            TEST_EXECUTOR_ID,
        )[0]
        operator_signals_holder.sync({
            operator_under_test.get_name(): dsl_interpreter.OperatorSignal.STOP.value,
        })
        op = operator_under_test(
            user_folder="u1",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
        )
        graceful_stop_mock = mock.Mock()
        with (
            mock.patch.object(
                process_util,
                "pid_is_running",
                return_value=False,
            ),
            mock.patch.object(
                operator_under_test,
                "request_graceful_stop",
                new=graceful_stop_mock,
            ),
        ):
            await op.pre_compute()
        graceful_stop_mock.assert_not_called()
        assert op.value == {"status": "already_stopped", "reason": "not_running"}

    async def test_execution_stop_os_kill_failure_raises(self):
        inner = _stop_test_ensure_state_dict("http://127.0.0.1:7")
        operator_signals_holder = dsl_interpreter.OperatorSignals()
        operator_under_test = octobot_process_ops.create_octobot_process_operators(
            operator_signals_holder,
            TEST_EXECUTOR_ID,
        )[0]
        operator_signals_holder.sync({
            operator_under_test.get_name(): dsl_interpreter.OperatorSignal.STOP.value,
        })
        op = operator_under_test(
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
        ):
            with pytest.raises(commons_errors.DSLInterpreterError, match="simulated"):
                await op.pre_compute()


class TestEnsureOctobotProcessOperatorSignalDispatch:
    def test_should_dispatch_stop_and_update_config_for_valid_ensure_payload(self):
        inner = _stop_test_ensure_state_dict("http://127.0.0.1:7")
        payload = _re_calling_ensure_value(inner)
        op_cls = EnsureOctobotProcessOperator
        assert op_cls.should_dispatch_operator_signal_for_result(
            dsl_interpreter.OperatorSignal.STOP.value,
            payload,
        )
        assert op_cls.should_dispatch_operator_signal_for_result(
            dsl_interpreter.OperatorSignal.UPDATE_CONFIG.value,
            payload,
        )

    def test_should_dispatch_false_for_unsupported_signal(self):
        inner = _stop_test_ensure_state_dict("http://127.0.0.1:7")
        payload = _re_calling_ensure_value(inner)
        assert not EnsureOctobotProcessOperator.should_dispatch_operator_signal_for_result(
            "OTHER_SIGNAL",
            payload,
        )

    def test_should_dispatch_false_when_inner_not_ensure_state(self):
        payload = _re_calling_ensure_value({"invalid": "not_ensure"})
        assert not EnsureOctobotProcessOperator.should_dispatch_operator_signal_for_result(
            dsl_interpreter.OperatorSignal.UPDATE_CONFIG.value,
            payload,
        )


class TestEnsureOctobotProcessOperatorUpdateConfig:
    async def test_update_config_triggers_respawn_and_recallable_result(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "start.py").write_text("#", encoding="utf-8")
        user_automation = (
            tmp_path
            / commons_constants.USER_FOLDER
            / commons_constants.AUTOMATIONS_FOLDER
            / "nested"
            / "upd_bot"
        )
        user_automation.mkdir(parents=True)
        log_dir = (
            tmp_path.joinpath(*octobot_node_constants.AUTOMATION_LOGS_FOLDER.split("/")).joinpath(
                "nested", "upd_bot"
            )
        )
        log_dir.mkdir(parents=True)
        (user_automation / "stale_marker.txt").write_text("x", encoding="utf-8")
        inner = octobot_process_ops.EnsureOctobotProcessState(
            http_base_url="http://127.0.0.1:5001",
            web_port=5001,
            node_port=5002,
            user_root=str(user_automation),
            user_folder="nested/upd_bot",
            log_folder=str(log_dir),
            profile_id="p1",
            pid=4242,
            state_file_path=os.path.join(
                str(user_automation),
                octobot_constants.PROCESS_BOT_STATE_FILE_NAME,
            ),
            init_state_ok=True,
            executor_id=TEST_EXECUTOR_ID,
        ).model_dump()
        operator_signals_holder = dsl_interpreter.OperatorSignals()
        operator_under_test = octobot_process_ops.create_octobot_process_operators(
            operator_signals_holder,
            TEST_EXECUTOR_ID,
        )[0]
        operator_signals_holder.sync({
            operator_under_test.get_name(): dsl_interpreter.OperatorSignal.UPDATE_CONFIG.value,
        })
        op = operator_under_test(
            user_folder="nested/upd_bot",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
        )
        op.pid = 4242
        try:
            with (
                mock.patch.object(
                    operator_under_test,
                    "wait_until_pid_stopped",
                    new=mock.AsyncMock(),
                ) as wait_mock,
                mock.patch.object(
                    dsl_interpreter.ProcessBoundOperatorMixin,
                    "request_graceful_stop",
                    return_value={"status": "stopped", "signal": "sigterm"},
                ) as stop_mock,
                mock.patch.object(
                    process_util,
                    "pid_is_running",
                    side_effect=lambda process_id: process_id == 4242,
                ),
                mock.patch.object(
                    octobot_process_ops,
                    "_load_process_bot_state",
                    new=mock.AsyncMock(side_effect=_async_return_none_mock),
                ),
                mock.patch.object(
                    process_util,
                    "spawn_managed_subprocess",
                ) as spawn_mock,
            ):
                spawn_mock.return_value = mock.Mock(spec=["pid"], pid=5151)
                await op.pre_compute()
            stop_mock.assert_called_once()
            wait_mock.assert_awaited_once()
            spawn_mock.assert_called_once()
            assert dsl_interpreter.ReCallingOperatorResult.__name__ in op.value
        finally:
            shutil.rmtree(tmp_path / commons_constants.USER_FOLDER, ignore_errors=True)
            if (tmp_path / "logs").exists():
                shutil.rmtree(tmp_path / "logs", ignore_errors=True)


class TestMetadataPidRoundTrip:
    def test_metadata_pid_to_dict_from_dict(self):
        metadata = process_bot_state_import.Metadata(
            updated_at=1.0,
            next_updated_at=2.0,
            pid=424242,
        )
        restored = process_bot_state_import.Metadata.from_dict(
            metadata.to_dict(include_default_values=False)
        )
        assert restored.pid == 424242


class TestShouldUseRecallPathWhenStoredPidDeadButStateLive:
    async def test_adopts_pid_from_live_state_without_spawn(self, tmp_path):
        inner = _healthy_recall_inner(pid=10002, tmp_path=tmp_path)
        op = EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            process_util,
            "pid_is_running",
            side_effect=lambda process_id: process_id == 20002,
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock, mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(side_effect=_async_live_process_bot_state_mock),
        ):
            await op.pre_compute()
        spawn_mock.assert_not_called()
        le = op.value[dsl_interpreter.ReCallingOperatorResult.__name__]["last_execution_result"]
        assert le.get("init_state_ok") is True
        assert le.get("pid") == 20002


class TestShouldUseRecallPathDuringInitWhenStoredPidDead:
    async def test_recall_without_spawn_during_init(self, tmp_path):
        inner = _healthy_recall_inner(pid=10002, init_state_ok=False, tmp_path=tmp_path)
        inner["started_waiting_at"] = octobot_process_ops.time.time()
        op = EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            process_util,
            "pid_is_running",
            return_value=False,
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock, mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(side_effect=_async_return_none_mock),
        ):
            await op.pre_compute()
        spawn_mock.assert_not_called()
        assert dsl_interpreter.ReCallingOperatorResult.__name__ in op.value


class TestRecallPathWhenStateFileMissingButPidRunning:
    async def test_recall_when_pid_running_without_state_file(self, tmp_path):
        inner = _healthy_recall_inner(pid=10002, tmp_path=tmp_path)
        op = EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            process_util,
            "pid_is_running",
            side_effect=lambda process_id: process_id == 10002,
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock, mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(side_effect=_async_return_none_mock),
        ):
            await op.pre_compute()
        spawn_mock.assert_not_called()
        assert dsl_interpreter.ReCallingOperatorResult.__name__ in op.value


class TestRestartGracePeriodAvoidsRespawnWhileStateStale:
    async def test_recall_during_restart_grace(self, tmp_path):
        inner = _healthy_recall_inner(pid=10002, tmp_path=tmp_path)
        stale_state = _stale_process_bot_state_for_grace(
            age_seconds=float(octobot_constants.PROCESS_BOT_STATE_DUMP_INTERVAL_SECONDS) * 2.5,
            metadata_pid=10002,
        )
        op = EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
            ping_timeout=120.0,
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            process_util,
            "pid_is_running",
            return_value=False,
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock, mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(return_value=stale_state),
        ):
            await op.pre_compute()
        spawn_mock.assert_not_called()
        assert dsl_interpreter.ReCallingOperatorResult.__name__ in op.value


class TestFirstSpawnAfterRestartGraceExpires:
    async def test_respawns_when_grace_expired(self, tmp_path):
        (tmp_path / "start.py").write_text("#", encoding="utf-8")
        inner = _healthy_recall_inner(pid=10002, tmp_path=tmp_path)
        stale_state = _stale_process_bot_state_for_grace(age_seconds=200.0, metadata_pid=10002)
        op = EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
            ping_timeout=120.0,
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            process_util,
            "pid_is_running",
            return_value=False,
        ), mock.patch.object(
            octobot_process_ops,
            "ensure_user_profile_and_layout",
            new=mock.AsyncMock(
                return_value={
                    "user_root": inner["user_root"],
                    "profile_id": "x",
                    "already_prepared": True,
                }
            ),
        ), mock.patch.object(
            octobot_process_ops,
            "_listen_port_pair_with_shared_scan_offset",
            return_value=(20050, 30050),
        ), mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(return_value=stale_state),
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock:
            spawn_mock.return_value = mock.Mock(spec=["pid"], pid=30003)
            await op.pre_compute()
        spawn_mock.assert_called_once()


class TestFirstSpawnWhenStateFileMissingAndPidDeadAfterInit:
    async def test_respawns_when_no_state_file_and_pid_dead(self, tmp_path):
        (tmp_path / "start.py").write_text("#", encoding="utf-8")
        inner = _healthy_recall_inner(pid=10002, tmp_path=tmp_path)
        op = EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            process_util,
            "pid_is_running",
            return_value=False,
        ), mock.patch.object(
            octobot_process_ops,
            "ensure_user_profile_and_layout",
            new=mock.AsyncMock(
                return_value={
                    "user_root": inner["user_root"],
                    "profile_id": "x",
                    "already_prepared": True,
                }
            ),
        ), mock.patch.object(
            octobot_process_ops,
            "_listen_port_pair_with_shared_scan_offset",
            return_value=(20050, 30050),
        ), mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(side_effect=_async_return_none_mock),
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock:
            spawn_mock.return_value = mock.Mock(spec=["pid"], pid=30004)
            await op.pre_compute()
        spawn_mock.assert_called_once()


class TestStopAdoptsPidFromProcessBotState:
    async def test_stop_signals_adopted_pid(self):
        inner = _healthy_recall_inner(pid=10002)
        operator_signals_holder = dsl_interpreter.OperatorSignals()
        operator_under_test = octobot_process_ops.create_octobot_process_operators(
            operator_signals_holder,
            TEST_EXECUTOR_ID,
        )[0]
        operator_signals_holder.sync({
            operator_under_test.get_name(): dsl_interpreter.OperatorSignal.STOP.value,
        })
        op = operator_under_test(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
        )
        graceful_stop_mock = mock.Mock(return_value={"status": "stopped", "signal": "sigterm"})
        with (
            mock.patch.object(
                process_util,
                "pid_is_running",
                side_effect=lambda process_id: process_id == 20002,
            ),
            mock.patch.object(
                octobot_process_ops,
                "_load_process_bot_state",
                new=mock.AsyncMock(side_effect=_async_live_process_bot_state_mock),
            ),
            mock.patch.object(
                operator_under_test,
                "request_graceful_stop",
                new=graceful_stop_mock,
            ),
        ):
            await op.pre_compute()
        graceful_stop_mock.assert_called_once()
        assert op.pid == 20002
        assert op.value == {"status": "stopped", "signal": "sigterm"}


class TestExecutorRestartedRequiresRespawn:
    async def test_marker_mismatch_forces_first_spawn(self, tmp_path):
        (tmp_path / "start.py").write_text("#", encoding="utf-8")
        inner = _healthy_recall_inner(
            pid=10002,
            tmp_path=tmp_path,
            executor_id="old-executor-id",
        )
        live_state = await _async_live_process_bot_state_mock(metadata_pid=20002)
        op = octobot_process_ops.create_octobot_process_operators(
            None, TEST_EXECUTOR_ID
        )[0](
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            process_util,
            "pid_is_running",
            return_value=False,
        ), mock.patch.object(
            octobot_process_ops,
            "ensure_user_profile_and_layout",
            new=mock.AsyncMock(
                return_value={
                    "user_root": inner["user_root"],
                    "profile_id": "x",
                    "already_prepared": True,
                }
            ),
        ), mock.patch.object(
            octobot_process_ops,
            "_listen_port_pair_with_shared_scan_offset",
            return_value=(20050, 30050),
        ), mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(return_value=live_state),
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock:
            spawn_mock.return_value = mock.Mock(spec=["pid"], pid=30005)
            await op.pre_compute()
        spawn_mock.assert_called_once()


class TestExecutorRestartSkippedWhenChildPidRunning:
    async def test_marker_mismatch_but_metadata_pid_running_recalls(self, tmp_path):
        inner = _healthy_recall_inner(
            pid=10002,
            tmp_path=tmp_path,
            executor_id="old-executor-id",
        )
        op = octobot_process_ops.create_octobot_process_operators(
            None, TEST_EXECUTOR_ID
        )[0](
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            process_util,
            "pid_is_running",
            side_effect=lambda process_id: process_id == 20002,
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock, mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(side_effect=_async_live_process_bot_state_mock),
        ):
            await op.pre_compute()
        spawn_mock.assert_not_called()
        assert dsl_interpreter.ReCallingOperatorResult.__name__ in op.value


class TestGraceWhenTimestampFreshButMetadataPidDead:
    async def test_recall_during_grace_without_spawn(self, tmp_path):
        inner = _healthy_recall_inner(pid=10002, tmp_path=tmp_path)
        now = octobot_process_ops.time.time()
        interval = float(octobot_constants.PROCESS_BOT_STATE_DUMP_INTERVAL_SECONDS)
        fresh_dead_pid_state = process_bot_state_import.ProcessBotState(
            metadata=process_bot_state_import.Metadata(
                updated_at=now - 0.1,
                next_updated_at=now + interval,
                pid=20002,
            ),
            exchange_account_elements=octobot_flow_entities.ExchangeAccountElements(),
        )
        op = EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
            ping_timeout=120.0,
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            process_util,
            "pid_is_running",
            return_value=False,
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock, mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(return_value=fresh_dead_pid_state),
        ):
            await op.pre_compute()
        spawn_mock.assert_not_called()
        assert dsl_interpreter.ReCallingOperatorResult.__name__ in op.value


class TestExecutorRestartDoesNotBypassGraceWhenMarkerMatches:
    async def test_recall_during_grace_when_marker_matches(self, tmp_path):
        inner = _healthy_recall_inner(pid=10002, tmp_path=tmp_path)
        stale_state = _stale_process_bot_state_for_grace(
            age_seconds=float(octobot_constants.PROCESS_BOT_STATE_DUMP_INTERVAL_SECONDS) * 2.5,
            metadata_pid=10002,
        )
        op = EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
            ping_timeout=120.0,
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            process_util,
            "pid_is_running",
            return_value=False,
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock, mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(return_value=stale_state),
        ):
            await op.pre_compute()
        spawn_mock.assert_not_called()
        assert dsl_interpreter.ReCallingOperatorResult.__name__ in op.value


class TestRespawnsWhenGraceExpiredAndPidDead:
    async def test_first_spawn_when_grace_expired(self, tmp_path):
        (tmp_path / "start.py").write_text("#", encoding="utf-8")
        inner = _healthy_recall_inner(pid=10002, tmp_path=tmp_path)
        stale_state = _stale_process_bot_state_for_grace(age_seconds=200.0, metadata_pid=10002)
        op = EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
            ping_timeout=120.0,
        )
        with mock.patch.object(
            octobot_process_ops.os,
            "getcwd",
            return_value=str(tmp_path),
        ), mock.patch.object(
            process_util,
            "pid_is_running",
            return_value=False,
        ), mock.patch.object(
            octobot_process_ops,
            "ensure_user_profile_and_layout",
            new=mock.AsyncMock(
                return_value={
                    "user_root": inner["user_root"],
                    "profile_id": "x",
                    "already_prepared": True,
                }
            ),
        ), mock.patch.object(
            octobot_process_ops,
            "_listen_port_pair_with_shared_scan_offset",
            return_value=(20050, 30050),
        ), mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(return_value=stale_state),
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock:
            spawn_mock.return_value = mock.Mock(spec=["pid"], pid=30006)
            await op.pre_compute()
        spawn_mock.assert_called_once()


class TestEnsureOctobotProcessStateEmitsExecutorId:
    async def test_first_spawn_emits_executor_id(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "start.py").write_text("#", encoding="utf-8")
        op = EnsureOctobotProcessOperator(
            user_folder="emit_master_bot",
            profile_data=_MINIMAL_PROFILE_DATA,
        )
        with mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(side_effect=_async_return_none_mock),
        ), mock.patch.object(
            octobot_process_ops,
            "ensure_user_profile_and_layout",
            new=mock.AsyncMock(
                return_value={
                    "user_root": str(
                        tmp_path
                        / commons_constants.USER_FOLDER
                        / commons_constants.AUTOMATIONS_FOLDER
                        / "emit_master_bot"
                    ),
                    "profile_id": "x",
                    "already_prepared": False,
                }
            ),
        ), mock.patch.object(
            octobot_process_ops,
            "_listen_port_pair_with_shared_scan_offset",
            return_value=(20050, 30050),
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock:
            spawn_mock.return_value = mock.Mock(spec=["pid"], pid=40001)
            await op.pre_compute()
        le = op.value[dsl_interpreter.ReCallingOperatorResult.__name__]["last_execution_result"]
        assert le["executor_id"] == TEST_EXECUTOR_ID


class TestRecallStateRequiresExecutorId:
    async def test_missing_executor_id_falls_through_to_first_spawn(self, tmp_path):
        (tmp_path / "start.py").write_text("#", encoding="utf-8")
        inner = _healthy_recall_inner(pid=10002, tmp_path=tmp_path)
        del inner["executor_id"]
        op = EnsureOctobotProcessOperator(
            user_folder="ub",
            profile_data=_MINIMAL_PROFILE_DATA,
            last_execution_result=_re_calling_ensure_value(inner),
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
                    "user_root": inner["user_root"],
                    "profile_id": "x",
                    "already_prepared": True,
                }
            ),
        ), mock.patch.object(
            octobot_process_ops,
            "_listen_port_pair_with_shared_scan_offset",
            return_value=(20050, 30050),
        ), mock.patch.object(
            octobot_process_ops,
            "_load_process_bot_state",
            new=mock.AsyncMock(side_effect=_async_return_none_mock),
        ), mock.patch.object(
            process_util,
            "spawn_managed_subprocess",
        ) as spawn_mock:
            spawn_mock.return_value = mock.Mock(spec=["pid"], pid=30007)
            await op.pre_compute()
        spawn_mock.assert_called_once()
