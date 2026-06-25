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
import types
import typing
import uuid
import aiofiles
import pydantic

import octobot_commons.constants as commons_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.errors as commons_errors
import octobot_commons.json_util as json_util
import octobot_commons.logging as commons_logging
import octobot_commons.os_util as os_util
import octobot_commons.process_util as process_util
import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.profile_data_import as profile_data_import
import octobot_commons.profiles.exchange_auth_data as exchange_auth_data_module
import octobot_commons.profiles.profile as profiles_profile_module
import octobot_commons.profiles.tentacles_profile_data_translator as tentacles_profile_data_translator
import octobot_commons.enums as commons_enums
import octobot_commons.configuration

import octobot.constants as octobot_constants
import octobot.community.supabase_backend.enums as community_enums
import octobot_flow.entities as octobot_flow_entities
import octobot_flow.entities.accounts.process_bot_state as process_bot_state_import
import octobot_node.constants as octobot_node_constants
import octobot_services.constants as services_constants

# Written only after a successful full init so re-runs can detect an existing per-bot tree.
DSL_PREPARED_MARKER = ".octobot_dsl_prepared"
DEFAULT_PING_WAITING_TIME = 2.0
DEFAULT_ENSURE_TIMEOUT = 120.0
DEFAULT_DSL_PROFILE_ID = "non-trading"


# run_octobot_process uses two state layers:
# - Recall state (`EnsureOctobotProcessState` in DSL `last_execution_result`): master-side
#   snapshot (ports, paths, stored pid, init_state_ok, executor_id). Persisted across
#   re-calls until STOP, UPDATE_CONFIG, or respawn.
# - Child dump (`process_bot_state.json` → `ProcessBotState`): written by the child; used for
#   timestamp-fresh checks and metadata.pid when the stored recall pid is stale.
# executor_id ties recall to the current DBOS scheduler worker. On mismatch
# with all child PIDs dead, respawn is forced immediately (grace is bypassed).
class EnsureOctobotProcessState(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(validate_assignment=True, extra="ignore")
    http_base_url: str
    web_port: int
    node_port: int
    user_root: str
    user_folder: str
    log_folder: str
    profile_id: str | None
    # Last known child PID on the master; may lag after a child self-restart until adoption.
    pid: int
    state_file_path: str = ""
    # Wall-clock when the first spawn began; used only while init_state_ok is False (ping_timeout).
    started_waiting_at: float = 0.0
    # True once the child reached confirmed-alive; switches from init ping_timeout to recall/grace rules.
    init_state_ok: bool = False
    # Required scheduler executor id at emit time; compared on recall to detect worker restart.
    executor_id: str


# Keys on `last_result` that `create_re_callable_result_dict` takes as top-level args (not state).
_RECALL_OVERRIDABLE_KEYS = frozenset(
    {
        dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value,
        dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value,
    }
)

_DEFAULT_ENCRYPTED_VALUE = octobot_commons.configuration.encrypt("").decode()


def _resolve_state_file_path(recall_state: EnsureOctobotProcessState) -> str:
    if recall_state.state_file_path:
        return recall_state.state_file_path
    return os.path.normpath(
        os.path.join(
            recall_state.user_root,
            octobot_constants.PROCESS_BOT_STATE_FILE_NAME,
        )
    )


# --- Liveness and routing (recall state + child dump) ---


def _is_process_state_alive(state: process_bot_state_import.ProcessBotState) -> bool:
    """True when the child dump is timestamp-fresh (~2 × dump interval since metadata.updated_at)."""
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
    """Load child dump from disk; None if missing or unreadable."""
    try:
        async with aiofiles.open(state_file_path, mode="r", encoding="utf-8") as state_file:
            raw = await state_file.read()
        data = json.loads(raw)
        return process_bot_state_import.ProcessBotState.from_dict(data)
    except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError):
        return None


def _is_state_timestamp_fresh(
    loaded_state: typing.Optional[process_bot_state_import.ProcessBotState],
) -> bool:
    """Alias for timestamp-fresh child dump (see _is_process_state_alive)."""
    if loaded_state is None:
        return False
    return _is_process_state_alive(loaded_state)


def _parse_ensure_recall_state(raw: dict) -> typing.Optional[EnsureOctobotProcessState]:
    """Parse recall payload; empty or invalid dict → None."""
    if not raw:
        return None
    try:
        return EnsureOctobotProcessState.model_validate(raw)
    except pydantic.ValidationError:
        return None


def _metadata_pid_is_running(
    loaded_state: typing.Optional[process_bot_state_import.ProcessBotState],
) -> bool:
    """True when child dump metadata.pid is valid and still running in the OS."""
    if loaded_state is None:
        return False
    state_pid = loaded_state.metadata.pid
    if state_pid <= 0:
        return False
    return process_util.pid_is_running(state_pid)


def _is_child_confirmed_alive(
    loaded_state: typing.Optional[process_bot_state_import.ProcessBotState],
) -> bool:
    """Strongest child-alive signal: timestamp-fresh dump and metadata.pid running."""
    if loaded_state is None:
        return False
    if not _is_state_timestamp_fresh(loaded_state):
        return False
    return _metadata_pid_is_running(loaded_state)


def _any_child_pid_running(
    recall_state: EnsureOctobotProcessState,
    loaded_state: typing.Optional[process_bot_state_import.ProcessBotState],
) -> bool:
    """True when either recall pid or child dump metadata.pid is running."""
    if _stored_pid_is_running(recall_state):
        return True
    return _metadata_pid_is_running(loaded_state)


def _executor_restarted_requires_respawn(
    recall_state: EnsureOctobotProcessState,
    loaded_state: typing.Optional[process_bot_state_import.ProcessBotState],
    *,
    current_executor_id: str,
) -> bool:
    """Scheduler worker restarted: recall executor_id differs and no child PID is running."""
    if _any_child_pid_running(recall_state, loaded_state):
        return False
    return recall_state.executor_id != current_executor_id


def _stored_pid_is_running(recall_state: EnsureOctobotProcessState) -> bool:
    """Fast path: recall pid still running."""
    if recall_state.pid <= 0:
        return False
    return process_util.pid_is_running(recall_state.pid)


def _in_restart_grace_period(
    recall_state: EnsureOctobotProcessState,
    loaded_state: typing.Optional[process_bot_state_import.ProcessBotState],
    *,
    now: float,
    ping_timeout: float,
    stored_pid_running: bool,
) -> bool:
    """Child self-restart window: init done, all PIDs dead, recent dump within ping_timeout."""
    if not recall_state.init_state_ok or stored_pid_running:
        return False
    if loaded_state is None:
        return False
    last_updated_at = loaded_state.metadata.updated_at
    if last_updated_at <= 0:
        return False
    return (now - last_updated_at) < ping_timeout


def _should_use_recall_path(
    recall_state: EnsureOctobotProcessState,
    loaded_state: typing.Optional[process_bot_state_import.ProcessBotState],
    *,
    stored_pid_running: bool,
    now: float,
    ping_timeout: float,
) -> bool:
    """Recall vs respawn: stored PID → confirmed alive → init → grace → else first_spawn."""
    if stored_pid_running:
        return True
    if _is_child_confirmed_alive(loaded_state):
        return True
    if not recall_state.init_state_ok:
        return True
    return _in_restart_grace_period(
        recall_state,
        loaded_state,
        now=now,
        ping_timeout=ping_timeout,
        stored_pid_running=stored_pid_running,
    )


def _resolve_bound_pid(
    recall_state: EnsureOctobotProcessState,
    loaded_state: typing.Optional[process_bot_state_import.ProcessBotState],
) -> typing.Optional[int]:
    """Bind operating PID from recall or fresh dump; None if metadata.pid dead (no raise)."""
    if _stored_pid_is_running(recall_state):
        return recall_state.pid
    if loaded_state is None or not _is_state_timestamp_fresh(loaded_state):
        return None
    state_pid = loaded_state.metadata.pid
    if state_pid <= 0:
        raise commons_errors.DSLInterpreterError(
            "process_bot_state.json is live but metadata.pid is missing or invalid."
        )
    if process_util.pid_is_running(state_pid):
        return state_pid
    return None


def _apply_resolved_pid_to_state(
    recall_state: EnsureOctobotProcessState,
    resolved_pid: typing.Optional[int],
) -> EnsureOctobotProcessState:
    if resolved_pid is None or resolved_pid == recall_state.pid:
        return recall_state
    return recall_state.model_copy(update={"pid": resolved_pid})


def _remove_path_for_fresh_start(path: str, *, logger: typing.Any) -> None:
    if not path or not str(path).strip():
        logger.info("configuration update: skip remove (empty path)")
        return
    if not os.path.exists(path):
        logger.info("configuration update: skip remove (path missing): %s", path)
        return
    logger.info("configuration update: removing path for fresh start: %s", path)
    shutil.rmtree(path, ignore_errors=True)


def _profile_translator_additional_data(
    profile_data: profile_data_module.ProfileData,
) -> dict:
    return {
        community_enums.BotConfigKeys.IS_SIMULATED.value: bool(
            profile_data.trader_simulator.enabled
        ),
    }


async def _convert_profile_data_to_profile_directory(
    profile_data: profile_data_module.ProfileData,
    temp_profile_path: str,
) -> None:
    tentacles_snapshot = list(profile_data.tentacles)
    if tentacles_snapshot:
        profile_data.tentacles = []
        try:
            # in case a translator is enabled on the given tentacles,
            # apply it to the profile data
            await tentacles_profile_data_translator.TentaclesProfileDataTranslator(
                profile_data, []
            ).translate(
                tentacles_snapshot,
                _profile_translator_additional_data(profile_data),
                None,
                None,
            )
        except KeyError:
            # no translator found, restore tentacles
            profile_data.tentacles = tentacles_snapshot
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


def _write_user_root_config_json(
    config_path: str,
    profile_id: str,
    profile_data: typing.Optional[profile_data_module.ProfileData] = None,
    exchange_auth_data: typing.Optional[
        list[exchange_auth_data_module.ExchangeAuthData]
    ] = None,
) -> None:
    """
    Writes user-root ``config.json``: selected profile, disabled web auto-open for DSL-spawned
    processes, optional exchange stubs from ``profile_data``, then credentials from
    ``exchange_auth_data`` (merged into ``exchanges``).
    """
    # Load packaged defaults; pin profile and disable browser auto-open for headless DSL children.
    default_cfg = json_util.read_file(octobot_constants.DEFAULT_CONFIG_FILE)
    default_cfg[commons_constants.CONFIG_PROFILE] = profile_id
    default_cfg[commons_constants.CONFIG_ACCEPTED_TERMS] = True
    services_cfg = default_cfg.setdefault(services_constants.CONFIG_CATEGORY_SERVICES, {})
    web_cfg = services_cfg.setdefault(services_constants.CONFIG_WEB, {})
    web_cfg[services_constants.CONFIG_AUTO_OPEN_IN_WEB_BROWSER] = False
    # Seed top-level exchanges so partially-managed merge targets exist before applying secrets.
    if profile_data is not None:
        exchanges_cfg = default_cfg.setdefault(commons_constants.CONFIG_EXCHANGES, {})
        for exchange_details in profile_data.exchanges:
            internal_exchange_name = exchange_details.internal_name
            if not internal_exchange_name:
                continue
            exchange_entry = exchanges_cfg.setdefault(internal_exchange_name, {})
            exchange_entry.setdefault(commons_constants.CONFIG_ENABLED_OPTION, True)
            exchange_entry.setdefault(
                commons_constants.CONFIG_EXCHANGE_TYPE,
                exchange_details.exchange_type or commons_constants.DEFAULT_EXCHANGE_TYPE,
            )
    # Overlay credentials onto matching exchange entries (adds exchange if missing).
    if exchange_auth_data:
        exchange_config_holder = types.SimpleNamespace(config=default_cfg)
        for auth_element in exchange_auth_data:
            auth_element.apply_to_exchange_config(exchange_config_holder)
    exchanges_cfg = default_cfg.get(commons_constants.CONFIG_EXCHANGES) or {}
    for exchange_cfg in exchanges_cfg.values():
        if isinstance(exchange_cfg, dict):
            exchange_cfg.setdefault(commons_constants.CONFIG_EXCHANGE_KEY, _DEFAULT_ENCRYPTED_VALUE)
            exchange_cfg.setdefault(commons_constants.CONFIG_EXCHANGE_SECRET, _DEFAULT_ENCRYPTED_VALUE)
    json_util.safe_dump(default_cfg, config_path)


def _executor_non_trading_profile_source(working_directory: str) -> str:
    return os.path.normpath(
        os.path.join(
            working_directory,
            commons_constants.USER_FOLDER,
            commons_constants.PROFILES_FOLDER,
            DEFAULT_DSL_PROFILE_ID,
        )
    )


def _executor_profiles_directory(working_directory: str) -> str:
    return os.path.normpath(
        os.path.join(
            working_directory,
            commons_constants.USER_FOLDER,
            commons_constants.PROFILES_FOLDER,
        )
    )


async def _copy_read_only_profiles_to_user_root(
    working_directory: str,
    user_root: str,
    *,
    active_profile_id: str,
) -> None:
    """
    Copy read-only profiles from the master OctoBot into a generic process child layout.

    Generic process bots start on the default non-trading profile but should still see
    the same read-only strategy profiles as the master (community/imported templates).
    Editable profiles are intentionally omitted so each child keeps its own user edits.
    """
    profiles_src = _executor_profiles_directory(working_directory)
    if not os.path.isdir(profiles_src):
        return
    for profile in profiles_profile_module.Profile.get_all_profiles(profiles_src):
        if not profile.read_only:
            continue
        # Active profile was already copied by _copy_non_trading_profile_to_user_root.
        if profile.profile_id == active_profile_id:
            continue
        destination_profile_path = os.path.join(
            user_root,
            commons_constants.PROFILES_FOLDER,
            profile.profile_id,
        )
        if os.path.exists(destination_profile_path):
            shutil.rmtree(destination_profile_path)
        shutil.copytree(profile.path, destination_profile_path)


async def _copy_non_trading_profile_to_user_root(
    working_directory: str,
    user_root: str,
) -> str:
    source_profile_path = _executor_non_trading_profile_source(working_directory)
    if not os.path.isdir(source_profile_path):
        raise commons_errors.DSLInterpreterError(
            f"Default profile not found at {source_profile_path!r}; expected "
            f"{DEFAULT_DSL_PROFILE_ID!r} under the OctoBot user profiles folder."
        )
    destination_profile_path = os.path.join(
        user_root,
        commons_constants.PROFILES_FOLDER,
        DEFAULT_DSL_PROFILE_ID,
    )
    if os.path.exists(destination_profile_path):
        shutil.rmtree(destination_profile_path)
    shutil.copytree(source_profile_path, destination_profile_path)
    return DEFAULT_DSL_PROFILE_ID


async def ensure_user_profile_and_layout(
    user_folder: str,
    working_directory: str,
    profile_data_dict: dict | None,
    source_reference_tentacles_config: str | None,
    exchange_auth_data: typing.Optional[
        list[exchange_auth_data_module.ExchangeAuthData]
    ] = None,
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

    if profile_data_dict is None:
        # Generic process: default non-trading profile plus master's read-only profiles.
        profile_id = await _copy_non_trading_profile_to_user_root(
            working_directory,
            user_root,
        )
        await _copy_read_only_profiles_to_user_root(
            working_directory,
            user_root,
            active_profile_id=profile_id,
        )
        _write_user_root_config_json(
            config_path,
            profile_id,
            None,
            exchange_auth_data,
        )
    else:
        # Import writes to a throwaway folder first: the real profile id is assigned during import (see rename below).
        temp_profile_path = os.path.join(
            user_root,
            commons_constants.PROFILES_FOLDER,
            f"_dsl_tmp_{uuid.uuid4().hex}",
        )
        os.makedirs(os.path.dirname(temp_profile_path), exist_ok=True)

        profile_data = profile_data_module.ProfileData.from_dict(profile_data_dict)
        await _convert_profile_data_to_profile_directory(
            profile_data, temp_profile_path
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

        _write_user_root_config_json(config_path, profile_id, profile_data, exchange_auth_data)

    # Mirror default reference tentacles layout expected by the child.
    ref_src = source_reference_tentacles_config or os.path.join(
        working_directory, commons_constants.USER_FOLDER, "reference_tentacles_config"
    )
    ref_src = os.path.normpath(ref_src)
    ref_dst = os.path.join(user_root, "reference_tentacles_config")
    if os.path.isdir(ref_src):
        if os.path.exists(ref_dst):
            shutil.rmtree(ref_dst)
        shutil.copytree(ref_src, ref_dst)
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
    primary_listen_port = os_util.find_first_free_listen_port_after_base(
        probe_host,
        primary_listen_port_base,
        max_offset=max_offset,
    )
    secondary_listen_port = os_util.find_first_free_listen_port_after_base(
        probe_host,
        secondary_listen_port_base,
        max_offset=max_offset,
        blocklist=[primary_listen_port],
    )
    return primary_listen_port, secondary_listen_port


def create_octobot_process_operators(
    signals: typing.Optional[dsl_interpreter.OperatorSignals] = None,
    executor_id: str = "",
) -> list[type[dsl_interpreter.Operator]]:
    # Child process: user layout, ports, process_bot_state.json liveness (re-callable).
    class EnsureOctobotProcessOperator(
        dsl_interpreter.PreComputingCallOperator,
        dsl_interpreter.ReCallableOperatorMixin,
        dsl_interpreter.SignalableOperatorMixin,
        dsl_interpreter.ProcessBoundOperatorMixin,
    ):
        DESCRIPTION = (
            "Prepares a per-bot user directory (profile + config + reference_tentacles_config), "
            "spawns an OctoBot child with unique WEB/NODE ports and --dump-state for process_bot_state.json. "
            "Always re-callable: each fresh state file (updated_at within twice the dump interval) schedules the next check (see waiting_time). "
            "If the state file never becomes live before ping_timeout from the first spawn, the keyword fails and the child is killed."
        )
        EXAMPLE = (
            "run_octobot_process(user_folder='bots/b1', "
            "exchange_auth_data=[{'internal_name': 'binance', 'api_key': '...', 'api_secret': '...'}], "
            "last_execution_result=None)"
        )

        def __init__(self, *args, **kwargs):
            dsl_interpreter.PreComputingCallOperator.__init__(self, *args, **kwargs)
            dsl_interpreter.ProcessBoundOperatorMixin.__init__(self)
            dsl_interpreter.SignalableOperatorMixin.__init__(self, signals)

        def _read_executor_id(self) -> str:
            if not executor_id:
                raise commons_errors.DSLInterpreterError(
                    "executor_id is required for run_octobot_process"
                )
            return executor_id

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
                    description=(
                        "Optional object compatible with octobot_commons.profiles.profile_data.ProfileData. "
                        "When omitted, the child uses the packaged default config and copies the "
                        f"{DEFAULT_DSL_PROFILE_ID!r} profile from the executor user profiles folder."
                    ),
                    required=False,
                    type=dict,
                    default=None,
                ),
                dsl_interpreter.OperatorParameter(
                    name="exchange_auth_data",
                    description=(
                        "Optional list of dicts compatible with "
                        "octobot_commons.profiles.exchange_auth_data.ExchangeAuthData "
                        "(e.g. internal_name, api_key, api_secret, api_password, exchange_type, sandboxed)."
                    ),
                    required=False,
                    type=list[dict],
                    default=None,
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
        def _re_calling_result_dispatches_this_ensure(
            cls,
            re_calling_result: typing.Optional[dict],
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
            try:
                return _parse_ensure_recall_state(inner) is not None
            except commons_errors.DSLInterpreterError:
                return False

        @classmethod
        def should_dispatch_operator_signal_for_result(
            cls,
            signal: str,
            re_calling_result: typing.Optional[dict],
        ) -> bool:
            if signal not in (
                dsl_interpreter.OperatorSignal.STOP.value,
                dsl_interpreter.OperatorSignal.UPDATE_CONFIG.value,
            ):
                return False
            return cls._re_calling_result_dispatches_this_ensure(re_calling_result)

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
            loaded_state: typing.Optional[process_bot_state_import.ProcessBotState] = None,
        ) -> None:
            state_path = _resolve_state_file_path(recall_state)
            now = time.time()
            if loaded_state is None:
                loaded_state = await _load_process_bot_state(state_path)
            child_confirmed_alive = _is_child_confirmed_alive(loaded_state)
            stored_pid_running = _stored_pid_is_running(recall_state)
            # Init window: fail and kill the child if the state file never became live in time.
            if (
                not recall_state.init_state_ok
                and now - recall_state.started_waiting_at > ping_timeout
            ):
                resolved_pid = _resolve_bound_pid(recall_state, loaded_state)
                if resolved_pid is not None:
                    self.pid = resolved_pid
                self.value = self.request_graceful_stop(logger=_get_logger())
                raise commons_errors.DSLInterpreterError(
                    "Timed out waiting for OctoBot process_bot_state.json during init (see ping_timeout).",
                )
            if _in_restart_grace_period(
                recall_state,
                loaded_state,
                now=now,
                ping_timeout=ping_timeout,
                stored_pid_running=stored_pid_running,
            ):
                _get_logger().info(
                    "restart grace: waiting for child state dump (last_updated_at=%s, ping_timeout=%s)",
                    loaded_state.metadata.updated_at if loaded_state is not None else None,
                    ping_timeout,
                )
            resolved_pid = _resolve_bound_pid(recall_state, loaded_state)
            if resolved_pid is not None:
                if resolved_pid != recall_state.pid:
                    _get_logger().info(
                        "adopted pid=%s (was %s) from process_bot_state",
                        resolved_pid,
                        recall_state.pid,
                    )
                self.pid = resolved_pid
            recall_state = _apply_resolved_pid_to_state(recall_state, resolved_pid)
            _get_logger().info("process state path (re-call path): %s", state_path)
            # Running: stored recall pid or child-confirmed-alive → init_state_ok, optional EAE.
            is_running = stored_pid_running or child_confirmed_alive
            if is_running:
                logged_pid = resolved_pid if resolved_pid is not None else recall_state.pid
                _get_logger().info(
                    "OctoBot is running (re-call path): user_folder=%r base_url=%r pid=%s",
                    recall_state.user_folder,
                    recall_state.http_base_url,
                    logged_pid,
                )
                updated = recall_state.model_copy(
                    update={"init_state_ok": True, "state_file_path": state_path}
                )
                self._emit_ensure_recall(
                    state=updated,
                    last_result=last_result,
                    start_time=start_time,
                    recall_interval=recall_interval,
                    parsed_process_bot_state=loaded_state,
                )
                return
            # Still starting: not confirmed alive (grace or waiting for first dump); re-call only.
            logged_pid = resolved_pid if resolved_pid is not None else recall_state.pid
            _get_logger().info(
                "OctoBot is still starting (re-call path, child not confirmed alive): user_folder=%r "
                "base_url=%r pid=%s state_path=%s",
                recall_state.user_folder,
                recall_state.http_base_url,
                logged_pid,
                state_path,
            )
            self._emit_ensure_recall(
                state=recall_state.model_copy(update={"state_file_path": state_path}),
                last_result=last_result,
                start_time=start_time,
                recall_interval=recall_interval,
                parsed_process_bot_state=loaded_state,
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
            raw_exchange_auth = params.get("exchange_auth_data")
            exchange_auth: typing.Optional[
                list[exchange_auth_data_module.ExchangeAuthData]
            ] = None
            if raw_exchange_auth:
                exchange_auth = [
                    exchange_auth_data_module.ExchangeAuthData.from_dict(entry)
                    if isinstance(entry, dict)
                    else entry
                    for entry in raw_exchange_auth
                ]
            init_info = await ensure_user_profile_and_layout(
                user_folder,
                working_directory,
                params.get("profile_data"),
                None,
                exchange_auth,
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
                executor_id=self._read_executor_id(),
            )
            # First process state check after spawn (init cap still uses `state.started_waiting_at`).
            loaded = await _load_process_bot_state(state_file_path)
            is_live = loaded is not None and _is_process_state_alive(loaded)
            if is_live:
                state_pid = loaded.metadata.pid
                if state_pid <= 0:
                    raise commons_errors.DSLInterpreterError(
                        "process_bot_state.json is live but metadata.pid is missing or invalid."
                    )
                if process_util.pid_is_running(state_pid):
                    self.pid = state_pid
                    state = state.model_copy(update={"pid": state_pid})
                    _get_logger().info(
                        "OctoBot is running (first-spawn path): user_folder=%r base_url=%r pid=%s",
                        user_folder,
                        http_base_url,
                        state_pid,
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
                # Orphaned timestamp-fresh dump with dead metadata.pid (e.g. after master restart):
                # treat as still starting, not an error.
            _get_logger().info(
                "OctoBot is still starting (first-spawn path, child not confirmed alive): user_folder=%r base_url=%r "
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

        async def _pre_compute_update_config_refresh(
            self,
            last_result: dict,
            user_folder: str,
            working_directory: str,
            params: dict,
            *,
            start_time: float,
            recall_interval: float,
            ping_timeout: float,
        ) -> None:
            # Resolve prior child layout from re-call payload; required for stop, wait, and paths to remove.
            recall_state = self._try_parse_ensure_recall_state(last_result)
            if recall_state is None:
                raise commons_errors.DSLInterpreterError(
                    "run_octobot_process(UPDATE_CONFIG) requires last_execution_result from a prior "
                    "run_octobot_process call.",
                )
            process_logger = _get_logger()
            state_path = _resolve_state_file_path(recall_state)
            loaded_state = await _load_process_bot_state(state_path)
            resolved_pid = _resolve_bound_pid(recall_state, loaded_state)
            if resolved_pid is None:
                raise commons_errors.DSLInterpreterError(
                    "run_octobot_process(UPDATE_CONFIG) cannot resolve a running child pid to stop."
                )
            self.pid = resolved_pid
            process_logger.info(
                "configuration update: begin refresh user_folder=%r user_root=%r log_folder=%r pid=%s",
                user_folder,
                recall_state.user_root,
                recall_state.log_folder,
                resolved_pid,
            )
            stop_outcome = self.request_graceful_stop(logger=process_logger)
            process_logger.info("configuration update: graceful stop outcome: %s", stop_outcome)
            await self.wait_until_pid_stopped(
                resolved_pid,
                logger=process_logger,
                timeout_seconds=ping_timeout,
            )
            process_logger.info("configuration update: removing automation user and log directories")
            _remove_path_for_fresh_start(recall_state.user_root, logger=process_logger)
            _remove_path_for_fresh_start(recall_state.log_folder, logger=process_logger)
            process_logger.info("configuration update: spawning new OctoBot process from current parameters")
            await self._pre_compute_first_spawn(
                user_folder,
                working_directory,
                params,
                {},
                start_time=start_time,
                recall_interval=recall_interval,
            )

        async def pre_compute(self) -> None:
            await super().pre_compute()
            # Resolve params, project root, and a fixed re-call interval for this run.
            params = self.get_computed_value_by_parameter()
            if self.matches_operator_signal(dsl_interpreter.OperatorSignal.STOP.value):
                last_result = self.get_last_execution_result(params) or {}
                recall_state = self._try_parse_ensure_recall_state(last_result)
                if recall_state is None:
                    raise commons_errors.DSLInterpreterError(
                        "run_octobot_process(execution_stop) requires last_execution_result from a prior run_octobot_process call.",
                    )
                state_path = _resolve_state_file_path(recall_state)
                loaded_state = await _load_process_bot_state(state_path)
                stored_pid_running = _stored_pid_is_running(recall_state)
                resolved_pid = _resolve_bound_pid(recall_state, loaded_state)
                if resolved_pid is not None:
                    self.pid = resolved_pid
                    self.value = self.request_graceful_stop(logger=_get_logger())
                    return
                # Grace with dead metadata pid: child restarting; no SIGTERM, report already_stopped.
                if _in_restart_grace_period(
                    recall_state,
                    loaded_state,
                    now=time.time(),
                    ping_timeout=float(params.get("ping_timeout") or DEFAULT_ENSURE_TIMEOUT),
                    stored_pid_running=stored_pid_running,
                ):
                    _get_logger().info(
                        "run_octobot_process(STOP): child in restart grace; treating as already_stopped"
                    )
                self.value = {"status": "already_stopped", "reason": "not_running"}
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
            if self.matches_operator_signal(dsl_interpreter.OperatorSignal.UPDATE_CONFIG.value):
                await self._pre_compute_update_config_refresh(
                    last_result,
                    user_folder,
                    working_directory,
                    params,
                    start_time=start_time,
                    recall_interval=recall_interval,
                    ping_timeout=ping_timeout,
                )
                return
            recall_state = self._try_parse_ensure_recall_state(last_result)
            if recall_state is not None:
                # 1. Load child dump alongside strict recall state.
                state_path = _resolve_state_file_path(recall_state)
                loaded_state = await _load_process_bot_state(state_path)
                stored_pid_running = _stored_pid_is_running(recall_state)
                state_timestamp_fresh = _is_state_timestamp_fresh(loaded_state)
                # 2. Master restart → first_spawn immediately (grace bypassed).
                if _executor_restarted_requires_respawn(
                    recall_state,
                    loaded_state,
                    current_executor_id=self._read_executor_id(),
                ):
                    _get_logger().info(
                        "scheduler worker restarted; forcing child respawn for user_folder=%r "
                        "(recall executor_id=%r, current=%r)",
                        recall_state.user_folder,
                        recall_state.executor_id,
                        self._read_executor_id(),
                    )
                    await self._pre_compute_first_spawn(
                        user_folder,
                        working_directory,
                        params,
                        last_result,
                        start_time=start_time,
                        recall_interval=recall_interval,
                    )
                    return
                # 3. Recall vs respawn from liveness/grace rules.
                if _should_use_recall_path(
                    recall_state,
                    loaded_state,
                    stored_pid_running=stored_pid_running,
                    now=start_time,
                    ping_timeout=ping_timeout,
                ):
                    await self._pre_compute_recall_path(
                        recall_state,
                        last_result,
                        start_time=start_time,
                        recall_interval=recall_interval,
                        ping_timeout=ping_timeout,
                        loaded_state=loaded_state,
                    )
                    return
                # 4. Recall declined (e.g. grace expired) → log and first_spawn below.
                last_state_updated_at = (
                    loaded_state.metadata.updated_at if loaded_state is not None else None
                )
                _get_logger().info(
                    "run_octobot_process: respawning child (recall path declined): user_folder=%r "
                    "stored_pid=%s stored_pid_running=%s state_timestamp_fresh=%s init_state_ok=%s "
                    "last_state_updated_at=%s ping_timeout=%s",
                    recall_state.user_folder,
                    recall_state.pid,
                    stored_pid_running,
                    state_timestamp_fresh,
                    recall_state.init_state_ok,
                    last_state_updated_at,
                    ping_timeout,
                )
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
    
    return [EnsureOctobotProcessOperator]



def _get_logger():
    return commons_logging.get_logger("OctoBotProcessOperators")
