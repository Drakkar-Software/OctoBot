#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT THE IMPLIED WARRANTY OF MERCHANTABILITY or FITNESS
#  FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <https://www.gnu.org/licenses/>.
# pylint: disable=missing-class-docstring,missing-function-docstring
import asyncio
import json
import os
import shutil
import sys
import time
import typing
import uuid
import aiofiles
import pydantic

import octobot_commons.constants as commons_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.errors as commons_errors
import octobot_commons.json_util as json_util
import octobot_commons.logging as commons_logging
import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.profile_data_import as profile_data_import
import octobot_commons.enums as commons_enums

import octobot.constants as octobot_constants
import octobot_flow.entities as octobot_flow_entities
import octobot_flow.entities.accounts.process_bot_state as process_bot_state_import
import octobot_node.constants as octobot_node_constants
import octobot_services.constants as services_constants

# Written only after a successful full init so re-runs can detect an existing per-bot tree.
DSL_PREPARED_MARKER = ".octobot_dsl_prepared"
DEFAULT_PING_WAITING_TIME = 2.0
DEFAULT_ENSURE_TIMEOUT = 120.0


class EnsureOctobotProcessState(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(validate_assignment=True, extra="ignore")
    http_base_url: str
    web_port: int
    node_port: int
    user_root: str
    user_folder: str
    log_folder: str
    profile_id: str | None
    pid: int
    state_file_path: str = ""
    # Omitted in ensure success `self.value` (stop command); 0.0 is unused there.
    started_waiting_at: float = 0.0
    # Set after process_bot_state.json liveness passes; disables the init `ping_timeout` cap (re-calls only use `waiting_time`).
    init_state_ok: bool = False


# Keys on `last_result` that `create_re_callable_result_dict` takes as top-level args (not state).
_RECALL_OVERRIDABLE_KEYS = frozenset(
    {
        dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value,
        dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value,
    }
)


def _resolve_state_file_path(recall_state: EnsureOctobotProcessState) -> str:
    if recall_state.state_file_path:
        return recall_state.state_file_path
    return os.path.normpath(
        os.path.join(
            recall_state.user_root,
            octobot_constants.PROCESS_BOT_STATE_FILE_NAME,
        )
    )


def _is_process_state_alive(state: process_bot_state_import.ProcessBotState) -> bool:
    interval = octobot_constants.PROCESS_BOT_STATE_DUMP_INTERVAL_SECONDS
    epsilon = max(0.1 * interval, 1e-6)
    now = time.time()
    meta = state.metadata
    if meta.updated_at > now:
        return False
    period = max(meta.next_updated_at - meta.updated_at, epsilon)
    return (now - meta.updated_at) < 2 * period


async def _load_process_bot_state(
    state_file_path: str,
) -> typing.Optional[process_bot_state_import.ProcessBotState]:
    try:
        async with aiofiles.open(state_file_path, mode="r", encoding="utf-8") as state_file:
            raw = await state_file.read()
        data = json.loads(raw)
        return process_bot_state_import.ProcessBotState.from_dict(data)
    except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError):
        return None


def _parse_ensure_recall_state(raw: dict) -> typing.Optional[EnsureOctobotProcessState]:
    if not raw:
        return None
    try:
        return EnsureOctobotProcessState.model_validate(raw)
    except pydantic.ValidationError:
        return None


async def ensure_user_profile_and_layout(
    user_folder: str,
    working_directory: str,
    profile_data_dict: dict,
    source_reference_tentacles_config: str | None,
) -> dict[str, typing.Any]:
    """
    One-time layout under user_root (<working_directory>/user/automations/<user_folder>/):
    profile tree, top-level config.json, reference_tentacles_config copy.
    Idempotent when config.json + marker both exist.
    """
    dsl_interpreter.ProcessBoundOperatorMixin.reject_user_path_segment(user_folder)
    user_folder_leaf_segments = [
        segment for segment in str(user_folder).replace("\\", "/").split("/") if segment
    ]
    user_root = os.path.normpath(
        os.path.join(
            working_directory,
            *commons_constants.USER_AUTOMATIONS_FOLDER.split("/"),
            *user_folder_leaf_segments,
        )
    )
    config_path = os.path.join(user_root, commons_constants.CONFIG_FILE)
    marker_path = os.path.join(user_root, DSL_PREPARED_MARKER)
    # Already prepared: do not rewrite files (host may have re-used this folder).
    if os.path.isfile(config_path) and os.path.isfile(marker_path):
        profile_id = _read_top_level_profile_id(config_path)
        return {
            "user_root": user_root,
            "profile_id": profile_id,
            "already_prepared": True,
        }

    os.makedirs(user_root, exist_ok=True)
    # Import writes to a throwaway folder first: the real profile id is assigned during import (see rename below).
    temp_profile_path = os.path.join(
        user_root,
        commons_constants.PROFILES_FOLDER,
        f"_dsl_tmp_{uuid.uuid4().hex}",
    )
    os.makedirs(os.path.dirname(temp_profile_path), exist_ok=True)

    profile_data = profile_data_module.ProfileData.from_dict(profile_data_dict)
    await profile_data_import.convert_profile_data_to_profile_directory(
        profile_data,
        temp_profile_path,
        description=profile_data.profile_details.name or "",
        risk=commons_enums.ProfileRisk.MODERATE,
        auto_update=False,
        slug=None,
        avatar_url=None,
        force_simulator=False,
    )

    profile_file = os.path.join(temp_profile_path, commons_constants.PROFILE_CONFIG_FILE)
    profile_on_disk = json_util.read_file(profile_file)
    profile_id = profile_on_disk[commons_constants.CONFIG_PROFILE][commons_constants.CONFIG_ID]
    # OctoBot expects each profile under profiles/<profile_id>/; move the temp tree to that name.
    final_profile_path = os.path.join(
        user_root, commons_constants.PROFILES_FOLDER, profile_id
    )
    if os.path.normpath(temp_profile_path) != os.path.normpath(final_profile_path):
        if os.path.exists(final_profile_path):
            shutil.rmtree(final_profile_path)
        os.replace(temp_profile_path, final_profile_path)

    # Top-level user config.json: selected profile; disable auto-open (DSL-spawned child, no local browser).
    default_cfg = json_util.read_file(octobot_constants.DEFAULT_CONFIG_FILE)
    default_cfg[commons_constants.CONFIG_PROFILE] = profile_id
    services_cfg = default_cfg.setdefault(services_constants.CONFIG_CATEGORY_SERVICES, {})
    web_cfg = services_cfg.setdefault(services_constants.CONFIG_WEB, {})
    web_cfg[services_constants.CONFIG_AUTO_OPEN_IN_WEB_BROWSER] = False
    json_util.safe_dump(default_cfg, config_path)

    # Mirror default reference tentacles layout expected by the child.
    ref_src = source_reference_tentacles_config or os.path.join(
        working_directory, commons_constants.USER_FOLDER, "reference_tentacles_config"
    )
    ref_src = os.path.normpath(ref_src)
    ref_dst = os.path.join(user_root, "reference_tentacles_config")
    if os.path.isdir(ref_src):
        if os.path.exists(ref_dst):
            shutil.rmtree(ref_dst)
        await asyncio.to_thread(shutil.copytree, ref_src, ref_dst)
    else:
        os.makedirs(ref_dst, exist_ok=True)

    # Marker last: if anything above failed, a partial tree will not look "prepared".
    with open(marker_path, "w", encoding="utf-8") as marker_file:
        marker_file.write("1")

    return {
        "user_root": user_root,
        "profile_id": profile_id,
        "already_prepared": False,
    }


def _read_top_level_profile_id(config_path: str) -> str | None:
    """Selected profile id from user root config.json (``"profile"`` key). None if unreadable."""
    if not os.path.isfile(config_path):
        return None
    try:
        cfg = json_util.read_file(config_path)
        return cfg.get(commons_constants.CONFIG_PROFILE)
    except Exception:
        return None


def _ensure_log_folder_path(working_directory: str, user_folder: str) -> str:
    """Absolute log directory for this `user_folder` (matches ensure_state.log_folder)."""
    log_folder_param_segments = [segment for segment in str(user_folder).replace("\\", "/").split("/") if segment]
    return os.path.normpath(
        os.path.join(
            working_directory,
            *octobot_node_constants.AUTOMATION_LOGS_FOLDER.split("/"),
            *log_folder_param_segments,
        )
    )


def _ensure_child_environ(web_port: int, node_port: int, bind_host: str) -> dict:
    """Environment passed to the OctoBot child (ports and bind addresses)."""
    child_env = os.environ.copy()
    child_env[services_constants.ENV_WEB_PORT] = str(web_port)
    child_env[services_constants.ENV_WEB_ADDRESS] = bind_host
    child_env[services_constants.ENV_NODE_API_PORT] = str(node_port)
    child_env[services_constants.ENV_NODE_API_ADDRESS] = bind_host
    child_env[commons_constants.ENV_USE_MINIMAL_LIBS] = "false"
    return child_env


def _ensure_start_cmd(
    start_script: str,
    rel_user: str,
    rel_log: str,
    no_telegram: bool,
    state_file_path: str,
) -> list[str]:
    """Argv for `python start.py --user-folder … --log-folder …` (+ optional -nt, --dump-state)."""
    cmd: list[str] = [
        sys.executable,
        start_script,
        "--user-folder",
        rel_user,
        "--log-folder",
        rel_log,
    ]
    if no_telegram:
        cmd.append("-nt")
    cmd.extend(["--dump-state", state_file_path])
    return cmd


def _listen_port_pair_with_shared_scan_offset(
    probe_host: str,
    primary_listen_port_base: int,
    secondary_listen_port_base: int,
    *,
    max_offset: int = 256,
) -> tuple[int, int]:
    """Delegates to ``find_first_free_listen_port_after_base`` paired scan (one loop)."""
    mixin = dsl_interpreter.ProcessBoundOperatorMixin
    primary_listen_port = mixin.find_first_free_listen_port_after_base(
        probe_host,
        primary_listen_port_base,
        max_offset=max_offset,
    )
    secondary_listen_port = mixin.find_first_free_listen_port_after_base(
        probe_host,
        secondary_listen_port_base,
        max_offset=max_offset,
        blocklist=[primary_listen_port],
    )
    return primary_listen_port, secondary_listen_port


# Child process: user layout, ports, process_bot_state.json liveness (re-callable).
class EnsureOctobotProcessOperator(
    dsl_interpreter.PreComputingCallOperator,
    dsl_interpreter.ReCallableOperatorMixin,
    dsl_interpreter.ProcessBoundOperatorMixin,
):
    DESCRIPTION = (
        "Prepares a per-bot user directory (profile + config + reference_tentacles_config), "
        "spawns an OctoBot child with unique WEB/NODE ports and --dump-state for process_bot_state.json. "
        "Always re-callable: each fresh state file (updated_at within twice the dump interval) schedules the next check (see waiting_time). "
        "If the state file never becomes live before ping_timeout from the first spawn, the keyword fails and the child is killed."
    )
    EXAMPLE = (
        "run_octobot_process(user_folder='bots/b1', profile_data={...}, "
        "last_execution_result=None)"
    )

    @staticmethod
    def get_library() -> str:
        return commons_constants.CONTEXTUAL_OPERATORS_LIBRARY

    @staticmethod
    def get_name() -> str:
        return "run_octobot_process"

    @classmethod
    def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(
                name="user_folder",
                description=(
                    "Path segment(s) under <cwd>/user/automations/ for this bot."
                ),
                required=True,
                type=str,
            ),
            dsl_interpreter.OperatorParameter(
                name="profile_data",
                description="Object compatible with octobot_commons.profiles.profile_data.ProfileData.",
                required=True,
                type=dict,
            ),
            dsl_interpreter.OperatorParameter(
                name="web_port_base",
                description="Base port for the web interface (uses base+offset; default from services constants).",
                required=False,
                type=int,
                default=services_constants.DEFAULT_SERVER_PORT,
            ),
            dsl_interpreter.OperatorParameter(
                name="node_port_base",
                description="Base port for the node API (uses base+offset).",
                required=False,
                type=int,
                default=services_constants.DEFAULT_NODE_API_PORT,
            ),
            dsl_interpreter.OperatorParameter(
                name="bind_host",
                description="Host used for free-port checks and WEB_ADDRESS / NODE_API_ADDRESS for the child.",
                required=False,
                type=str,
                default="127.0.0.1",
            ),
            dsl_interpreter.OperatorParameter(
                name="http_scheme",
                description="Scheme for http_base_url (default http).",
                required=False,
                type=str,
                default="http",
            ),
            dsl_interpreter.OperatorParameter(
                name="no_telegram",
                description="If true, spawns with -nt (default true).",
                required=False,
                type=bool,
                default=True,
            ),
            dsl_interpreter.OperatorParameter(
                name="ping_timeout",
                description=(
                    "Init-only: max seconds from the first spawn until process_bot_state.json is first considered live "
                    "(fresh updated_at / next_updated_at). After that, the child is killed and the keyword fails. "
                    "Does not cap liveness re-calls once up."
                ),
                required=False,
                type=float,
                default=DEFAULT_ENSURE_TIMEOUT,
            ),
            dsl_interpreter.OperatorParameter(
                name="waiting_time",
                description=(
                    "Fixed interval in seconds before each re-call (init polling and ongoing liveness while the state file is live)."
                ),
                required=False,
                type=float,
                default=DEFAULT_PING_WAITING_TIME,
            ),
        ] + super().get_re_callable_parameters()

    @classmethod
    def should_run_execution_stop_for_result(
        cls, re_calling_result: typing.Optional[dict]
    ) -> bool:
        if not re_calling_result or not dsl_interpreter.ReCallingOperatorResult.is_re_calling_operator_result(
            re_calling_result
        ):
            return False
        try:
            keyword = dsl_interpreter.ReCallingOperatorResult.get_keyword(re_calling_result)
        except (KeyError, TypeError, AttributeError):
            return False
        if keyword != cls.get_name():
            return False
        rec = re_calling_result.get(dsl_interpreter.ReCallingOperatorResult.__name__)
        if not isinstance(rec, dict):
            return False
        inner = rec.get("last_execution_result")
        if not isinstance(inner, dict):
            return False
        return _parse_ensure_recall_state(inner) is not None

    def _emit_ensure_recall(
        self,
        *,
        state: EnsureOctobotProcessState,
        last_result: dict,
        start_time: float,
        recall_interval: float,
        parsed_process_bot_state: typing.Optional[process_bot_state_import.ProcessBotState] = None,
    ) -> None:
        re_call_payload = {**state.model_dump()}
        for payload_key, payload_value in last_result.items():
            if payload_key in re_call_payload or payload_key in _RECALL_OVERRIDABLE_KEYS:
                continue
            re_call_payload[payload_key] = payload_value
        if parsed_process_bot_state is not None:
            re_call_payload[octobot_flow_entities.PostIterationActionsDetails.__name__] = (
                octobot_flow_entities.PostIterationActionsDetails(
                    updated_exchange_account_elements=(
                        parsed_process_bot_state.exchange_account_elements.to_dict(
                            include_default_values=True
                        )
                    ),
                ).to_dict(include_default_values=False)
            )
        self.value = self.create_re_callable_result_dict(
            keyword=self.get_name(),
            waiting_time=recall_interval,
            last_execution_time=start_time,
            **re_call_payload,
        )

    async def _pre_compute_recall_path(
        self,
        recall_state: EnsureOctobotProcessState,
        last_result: dict,
        *,
        start_time: float,
        recall_interval: float,
        ping_timeout: float,
    ) -> None:
        state_path = _resolve_state_file_path(recall_state)
        # Init window: fail and kill the child if the state file never became live in time.
        if (
            not recall_state.init_state_ok
            and time.time() - recall_state.started_waiting_at > ping_timeout
        ):
            self.value = self.request_graceful_stop(logger=_get_logger())
            raise commons_errors.DSLInterpreterError(
                "Timed out waiting for OctoBot process_bot_state.json during init (see ping_timeout).",
            )
        _get_logger().info("process state path (re-call path): %s", state_path)
        loaded = await _load_process_bot_state(state_path)
        is_live = loaded is not None and _is_process_state_alive(loaded)
        if is_live:
            _get_logger().info(
                "OctoBot is running (re-call path): user_folder=%r base_url=%r pid=%s",
                recall_state.user_folder,
                recall_state.http_base_url,
                recall_state.pid,
            )
            updated = recall_state.model_copy(
                update={"init_state_ok": True, "state_file_path": state_path}
            )
            self._emit_ensure_recall(
                state=updated,
                last_result=last_result,
                start_time=start_time,
                recall_interval=recall_interval,
                parsed_process_bot_state=loaded,
            )
            return
        _get_logger().info(
            "OctoBot is still starting (re-call path, process state not live): user_folder=%r "
            "base_url=%r pid=%s state_path=%s",
            recall_state.user_folder,
            recall_state.http_base_url,
            recall_state.pid,
            state_path,
        )
        self._emit_ensure_recall(
            state=recall_state.model_copy(update={"state_file_path": state_path}),
            last_result=last_result,
            start_time=start_time,
            recall_interval=recall_interval,
            parsed_process_bot_state=loaded,
        )

    async def _pre_compute_first_spawn(
        self,
        user_folder: str,
        working_directory: str,
        params: dict,
        last_result: dict,
        *,
        start_time: float,
        recall_interval: float,
    ) -> None:
        # One-time (or re-) materialization, free ports, env, and `Popen` at project root.
        init_info = await ensure_user_profile_and_layout(
            user_folder,
            working_directory,
            params["profile_data"],
            None,
        )
        user_root = init_info["user_root"]
        log_folder = _ensure_log_folder_path(working_directory, user_folder)
        bind_host, probe_host = (
            dsl_interpreter.ProcessBoundOperatorMixin.bind_address_for_env_and_probe_hosts(
                params
            )
        )
        web_b = int(params.get("web_port_base") or services_constants.DEFAULT_SERVER_PORT)
        node_b = int(params.get("node_port_base") or services_constants.DEFAULT_NODE_API_PORT)
        web_port, node_port = _listen_port_pair_with_shared_scan_offset(
            probe_host, web_b, node_b
        )
        start_script = os.path.join(working_directory, "start.py")
        if not os.path.isfile(start_script):
            raise commons_errors.DSLInterpreterError(
                f"start.py not found at {start_script} (current working directory must be the OctoBot project root)."
            )
        child_env = _ensure_child_environ(web_port, node_port, bind_host)
        rel_user = os.path.relpath(user_root, working_directory)
        rel_log = os.path.relpath(log_folder, working_directory)
        state_file_path = os.path.normpath(
            os.path.join(user_root, octobot_constants.PROCESS_BOT_STATE_FILE_NAME)
        )
        cmd = _ensure_start_cmd(
            start_script,
            rel_user,
            rel_log,
            bool(params.get("no_telegram", True)),
            state_file_path,
        )
        self.spawn_subprocess(
            cmd,
            working_directory=working_directory,
            environment=child_env,
            hide_console_window=True,
        )
        scheme = str(params.get("http_scheme") or "http").rstrip(":/")
        http_base_url = f"{scheme}://{bind_host}:{web_port}"
        state = EnsureOctobotProcessState(
            http_base_url=http_base_url,
            web_port=web_port,
            node_port=node_port,
            user_root=user_root,
            user_folder=str(user_folder),
            log_folder=log_folder,
            profile_id=init_info.get("profile_id"),
            pid=self.pid or 0,
            state_file_path=state_file_path,
            started_waiting_at=start_time,
        )
        # First process state check after spawn (init cap still uses `state.started_waiting_at`).
        loaded = await _load_process_bot_state(state_file_path)
        is_live = loaded is not None and _is_process_state_alive(loaded)
        if is_live:
            _get_logger().info(
                "OctoBot is running (first-spawn path): user_folder=%r base_url=%r pid=%s",
                user_folder,
                http_base_url,
                self.pid,
            )
            ready = state.model_copy(update={"init_state_ok": True})
            self._emit_ensure_recall(
                state=ready,
                last_result=last_result,
                start_time=start_time,
                recall_interval=recall_interval,
                parsed_process_bot_state=loaded,
            )
            return
        _get_logger().info(
            "OctoBot is still starting (first-spawn path, process state not live): user_folder=%r base_url=%r "
            "pid=%s state_path=%s",
            user_folder,
            http_base_url,
            self.pid,
            state_file_path,
        )
        self._emit_ensure_recall(
            state=state,
            last_result=last_result,
            start_time=start_time,
            recall_interval=recall_interval,
            parsed_process_bot_state=loaded,
        )

    async def pre_compute(self) -> None:
        await super().pre_compute()
        # Resolve params, project root, and a fixed re-call interval for this run.
        params = self.get_computed_value_by_parameter()
        if type(self).get_execution_stop():
            last_result = self.get_last_execution_result(params) or {}
            recall_state = self._try_parse_ensure_recall_state(last_result)
            if recall_state is None:
                raise commons_errors.DSLInterpreterError(
                    "run_octobot_process(execution_stop) requires last_execution_result from a prior run_octobot_process call.",
                )
            self.value = self.request_graceful_stop(logger=_get_logger())
            return
        working_directory = os.path.normpath(os.getcwd())
        user_folder = params["user_folder"]
        if not user_folder or not str(user_folder).strip():
            raise commons_errors.DSLInterpreterError("user_folder is required")
        dsl_interpreter.ProcessBoundOperatorMixin.reject_user_path_segment(user_folder)
        last_result = self.get_last_execution_result(params) or {}
        start_time = time.time()
        ping_timeout = float(params.get("ping_timeout") or DEFAULT_ENSURE_TIMEOUT)
        recall_interval = float(params.get("waiting_time") or DEFAULT_PING_WAITING_TIME)
        recall_state = self._try_parse_ensure_recall_state(last_result)
        if recall_state is not None and self.is_process_running():
            await self._pre_compute_recall_path(
                recall_state,
                last_result,
                start_time=start_time,
                recall_interval=recall_interval,
                ping_timeout=ping_timeout,
            )
            return
        await self._pre_compute_first_spawn(
            user_folder,
            working_directory,
            params,
            last_result,
            start_time=start_time,
            recall_interval=recall_interval,
        )


    def _try_parse_ensure_recall_state(self, raw: dict) -> typing.Optional[EnsureOctobotProcessState]:
        if state := _parse_ensure_recall_state(raw):
            if state.pid:
                self.pid = state.pid
            return state
        return None


def _get_logger():
    return commons_logging.get_logger("octobot_process_ops")
