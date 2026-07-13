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
import pathlib
import shutil
import sys
import threading
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
import octobot_commons.profiles.profile_types.profile as profiles_profile_module
import octobot_commons.profiles.tentacles_profile_data_translator as tentacles_profile_data_translator
import octobot_commons.enums as commons_enums
import octobot_commons.configuration

import octobot.constants as octobot_constants
import octobot.community.supabase_backend.enums as community_enums
import octobot_flow.entities as octobot_flow_entities
import octobot_flow.entities.accounts.process_bot_state as process_bot_state_import
import octobot_flow.entities.automations.octobot_process_state as octobot_process_state_import
import octobot_node.constants as octobot_node_constants
import octobot_services.constants as services_constants
import octobot_protocol.models.generic_process_configuration as generic_process_configuration
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers

DEFAULT_PING_WAITING_TIME = 2.0
DEFAULT_ENSURE_TIMEOUT = 120.0
DEFAULT_FORCE_KILL_EXIT_WAIT_SECONDS = 5.0
DEFAULT_DSL_PROFILE_ID = "non-trading"
RUN_OCTOBOT_PROCESS_OPERATOR_NAME = "run_octobot_process"


# run_octobot_process uses two state layers:
# - Recall state (`OctobotProcessState` in DSL `last_execution_result`): master-side
#   snapshot (ports, paths, stored pid, init_state_ok, executor_id). Persisted across
#   re-calls until STOP, UPDATE_CONFIG, or respawn.
# - Child dump (`process_bot_state.json` → `ProcessBotState`): written by the child; used for
#   timestamp-fresh checks and metadata.pid when the stored recall pid is stale.
# executor_id ties recall to the current DBOS scheduler worker. On mismatch
# with all child PIDs dead, respawn is forced immediately (grace is bypassed).


# Keys on `last_result` that `create_re_callable_result_dict` takes as top-level args (not state).
_RECALL_OVERRIDABLE_KEYS = frozenset(
    {
        dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value,
        dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value,
    }
)

_DEFAULT_ENCRYPTED_VALUE = octobot_commons.configuration.encrypt("").decode()


def _resolve_state_file_path(recall_state: octobot_process_state_import.OctobotProcessState) -> str:
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
    recall_state: octobot_process_state_import.OctobotProcessState,
    loaded_state: typing.Optional[process_bot_state_import.ProcessBotState],
) -> bool:
    """True when either recall pid or child dump metadata.pid is running."""
    if _stored_pid_is_running(recall_state):
        return True
    return _metadata_pid_is_running(loaded_state)


def _executor_restarted_requires_respawn(
    recall_state: octobot_process_state_import.OctobotProcessState,
    loaded_state: typing.Optional[process_bot_state_import.ProcessBotState],
    *,
    current_executor_id: str,
) -> bool:
    """Scheduler worker restarted: recall executor_id differs and no child PID is running."""
    if _any_child_pid_running(recall_state, loaded_state):
        return False
    return recall_state.executor_id != current_executor_id


def _stored_pid_is_running(recall_state: octobot_process_state_import.OctobotProcessState) -> bool:
    """Fast path: recall pid still running."""
    if recall_state.pid <= 0:
        return False
    return process_util.pid_is_running(recall_state.pid)


def _in_restart_grace_period(
    recall_state: octobot_process_state_import.OctobotProcessState,
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
    recall_state: octobot_process_state_import.OctobotProcessState,
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
    recall_state: octobot_process_state_import.OctobotProcessState,
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
    recall_state: octobot_process_state_import.OctobotProcessState,
    resolved_pid: typing.Optional[int],
) -> octobot_process_state_import.OctobotProcessState:
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


def _path_segments(relative_path: str) -> tuple[str, ...]:
    return tuple(
        segment
        for segment in str(relative_path).replace("\\", "/").split("/")
        if segment
    )


def _assert_automation_child_config_path(config_path: str) -> None:
    """
    Reject writes outside ``user/automations/<leaf>/config.json`` (master ``user/config.json`` is forbidden).
    """
    normalized_config_path = os.path.normpath(config_path)
    if os.path.basename(normalized_config_path) != commons_constants.CONFIG_FILE:
        raise commons_errors.DSLInterpreterError(
            f"Process child config must be named {commons_constants.CONFIG_FILE!r}, not {config_path!r}."
        )
    path_segments = pathlib.PurePath(normalized_config_path).parts
    automation_prefix = (
        commons_constants.USER_FOLDER,
        commons_constants.AUTOMATIONS_FOLDER,
    )
    prefix_length = len(automation_prefix)
    for segment_index in range(len(path_segments) - prefix_length):
        if path_segments[segment_index : segment_index + prefix_length] != automation_prefix:
            continue
        leaf_segments = path_segments[segment_index + prefix_length : -1]
        if not leaf_segments:
            raise commons_errors.DSLInterpreterError(
                f"Process child config must live under "
                f"{commons_constants.USER_AUTOMATIONS_FOLDER}/<automation_id>/{commons_constants.CONFIG_FILE}, "
                f"not {config_path!r}."
            )
        if ".." in leaf_segments:
            raise commons_errors.DSLInterpreterError(
                f"Process child config path must not contain parent segments: {config_path!r}."
            )
        return
    raise commons_errors.DSLInterpreterError(
        f"Process child config must be under {commons_constants.USER_AUTOMATIONS_FOLDER}/<automation_id>/, "
        f"not {config_path!r}."
    )


def _assert_automation_rel_folder(
    rel_folder: str,
    expected_prefix: tuple[str, ...],
    *,
    cli_flag_label: str,
    expected_folder_path: str,
) -> None:
    path_segments = _path_segments(rel_folder)
    if len(path_segments) < len(expected_prefix) + 1:
        raise commons_errors.DSLInterpreterError(
            f"Process child {cli_flag_label} must be under {expected_folder_path}/<automation_id>/, "
            f"got {rel_folder!r}."
        )
    if path_segments[: len(expected_prefix)] != expected_prefix:
        raise commons_errors.DSLInterpreterError(
            f"Process child {cli_flag_label} must start with {expected_folder_path}/, "
            f"got {rel_folder!r}."
        )
    if ".." in path_segments:
        raise commons_errors.DSLInterpreterError(
            f"Process child {cli_flag_label} must not contain parent segments: {rel_folder!r}."
        )


def _assert_automation_rel_user_folder(rel_user_folder: str) -> None:
    _assert_automation_rel_folder(
        rel_user_folder,
        (
            commons_constants.USER_FOLDER,
            commons_constants.AUTOMATIONS_FOLDER,
        ),
        cli_flag_label="--user-folder",
        expected_folder_path=commons_constants.USER_AUTOMATIONS_FOLDER,
    )


def _assert_automation_rel_log_folder(rel_log_folder: str) -> None:
    _assert_automation_rel_folder(
        rel_log_folder,
        tuple(octobot_node_constants.AUTOMATION_LOGS_FOLDER.split("/")),
        cli_flag_label="--log-folder",
        expected_folder_path=octobot_node_constants.AUTOMATION_LOGS_FOLDER,
    )


def _assert_spawn_cmd_isolation(cmd: list[str], rel_user: str, rel_log: str) -> None:
    if "--user-folder" not in cmd or "--log-folder" not in cmd:
        raise commons_errors.DSLInterpreterError(
            "Process child spawn command must include --user-folder and --log-folder."
        )
    _assert_automation_rel_user_folder(rel_user)
    _assert_automation_rel_log_folder(rel_log)


def _master_user_config_path(working_directory: str) -> str:
    return os.path.join(
        working_directory,
        commons_constants.USER_FOLDER,
        commons_constants.CONFIG_FILE,
    )


def _load_master_exchange_auth_data(
    working_directory: str,
) -> dict[str, exchange_auth_data_module.ExchangeAuthData]:
    master_config_path = _master_user_config_path(working_directory)
    if not os.path.isfile(master_config_path):
        return {}
    try:
        master_config = json_util.read_file(master_config_path)
    except Exception as error:
        raise commons_errors.DSLInterpreterError(
            f"Failed to read master user config at {master_config_path!r}: {error}"
        ) from error
    exchanges_config = master_config.get(commons_constants.CONFIG_EXCHANGES) or {}
    return {
        internal_name: exchange_auth_data_module.ExchangeAuthData(
            internal_name=internal_name,
            api_key=exchange_config.get(commons_constants.CONFIG_EXCHANGE_KEY, ""),
            api_secret=exchange_config.get(commons_constants.CONFIG_EXCHANGE_SECRET, ""),
            api_password=exchange_config.get(commons_constants.CONFIG_EXCHANGE_PASSWORD, ""),
            exchange_type=exchange_config.get(
                commons_constants.CONFIG_EXCHANGE_TYPE,
                commons_constants.DEFAULT_EXCHANGE_TYPE,
            ),
            sandboxed=exchange_config.get(commons_constants.CONFIG_EXCHANGE_SANDBOXED, False),
        )
        for internal_name, exchange_config in exchanges_config.items()
        if isinstance(exchange_config, dict)
    }


def _resolved_exchange_auth_data(
    working_directory: str,
    override_dicts: list[dict] | None,
) -> list[exchange_auth_data_module.ExchangeAuthData] | None:
    merged_auth = _load_master_exchange_auth_data(working_directory)
    if override_dicts:
        for override_dict in override_dicts:
            if not isinstance(override_dict, dict):
                continue
            internal_name = override_dict.get("internal_name")
            if not internal_name:
                continue
            merged_auth[internal_name] = exchange_auth_data_module.ExchangeAuthData.from_dict(
                override_dict
            )
    if not merged_auth:
        return None
    return list(merged_auth.values())


def _write_user_root_config_json(
    config_path: str,
    profile_id: str,
    profile_data: typing.Optional[profile_data_module.ProfileData] = None,
    exchange_auth_overrides: list[dict] | None = None,
    working_directory: str = "",
    readonly_profiles_path: str | None = None,
    readonly_reference_tentacles_path: str | None = None,
    octobot_name: str | None = None,
) -> None:
    """
    Writes user-root ``config.json``: selected profile, disabled web auto-open for DSL-spawned
    processes, optional exchange stubs from ``profile_data``, then credentials from the executor
    master ``user/config.json`` (forwarded for all exchanges), with optional
    ``exchange_auth_overrides`` fully replacing matching entries by ``internal_name``.
    """
    _assert_automation_child_config_path(config_path)
    # Load packaged defaults; pin profile and disable browser auto-open for headless DSL children.
    default_cfg = json_util.read_file(octobot_constants.DEFAULT_CONFIG_FILE)
    default_cfg[commons_constants.CONFIG_PROFILE] = profile_id
    default_cfg[commons_constants.CONFIG_ACCEPTED_TERMS] = True
    if octobot_name and str(octobot_name).strip():
        default_cfg[commons_constants.CONFIG_OCTOBOT_NAME] = str(octobot_name).strip()
    if readonly_profiles_path:
        default_cfg[commons_constants.CONFIG_READONLY_PROFILES_PATH] = readonly_profiles_path
    if readonly_reference_tentacles_path:
        default_cfg[commons_constants.CONFIG_READONLY_REFERENCE_TENTACLES_PATH] = (
            readonly_reference_tentacles_path
        )
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
    # Overlay master credentials and optional overrides onto matching exchange entries.
    resolved_auth = _resolved_exchange_auth_data(working_directory, exchange_auth_overrides)
    if resolved_auth:
        exchange_config_holder = types.SimpleNamespace(config=default_cfg)
        for auth_element in resolved_auth:
            auth_element.apply_to_exchange_config(exchange_config_holder)
    if profile_data is not None:
        profile_exchange_names = {
            exchange_details.internal_name
            for exchange_details in profile_data.exchanges
            if exchange_details.internal_name
        }
        exchanges_cfg = default_cfg.get(commons_constants.CONFIG_EXCHANGES) or {}
        for exchange_name, exchange_cfg in exchanges_cfg.items():
            if exchange_name not in profile_exchange_names and isinstance(exchange_cfg, dict):
                # don't inherit exchange activation from master config
                exchange_cfg[commons_constants.CONFIG_ENABLED_OPTION] = False
        # Re-enable profile exchanges after master auth overlay and non-profile disable guard.
        for profile_exchange_name in profile_exchange_names:
            profile_exchange_cfg = exchanges_cfg.get(profile_exchange_name)
            if isinstance(profile_exchange_cfg, dict):
                profile_exchange_cfg[commons_constants.CONFIG_ENABLED_OPTION] = True
    exchanges_cfg = default_cfg.get(commons_constants.CONFIG_EXCHANGES) or {}
    for exchange_cfg in exchanges_cfg.values():
        if isinstance(exchange_cfg, dict):
            exchange_cfg.setdefault(commons_constants.CONFIG_EXCHANGE_KEY, _DEFAULT_ENCRYPTED_VALUE)
            exchange_cfg.setdefault(commons_constants.CONFIG_EXCHANGE_SECRET, _DEFAULT_ENCRYPTED_VALUE)
    json_util.safe_dump(default_cfg, config_path)


def _executor_profiles_directory(working_directory: str) -> str:
    return os.path.normpath(
        os.path.join(
            working_directory,
            commons_constants.USER_FOLDER,
            commons_constants.PROFILES_FOLDER,
        )
    )


def _executor_reference_tentacles_directory(working_directory: str) -> str:
    return os.path.normpath(
        os.path.join(
            working_directory,
            commons_constants.USER_FOLDER,
            "reference_tentacles_config",
        )
    )


def _child_master_profile_config_kwargs(
    working_directory: str,
) -> dict[str, typing.Any]:
    return {
        "readonly_profiles_path": _executor_profiles_directory(working_directory),
        "readonly_reference_tentacles_path": _executor_reference_tentacles_directory(
            working_directory
        ),
    }


def _get_sync_strategy(sync_user_id: str, strategy_id: str) -> typing.Any:
    return collection_providers.StrategyProvider.instance().get_item(
        sync_user_id,
        strategy_id,
    )


def _sync_strategy_has_profile_data(strategy: typing.Any) -> bool:
    configuration = strategy.configuration
    if configuration is None or configuration.actual_instance is None:
        return False
    if not isinstance(
        configuration.actual_instance,
        generic_process_configuration.GenericProcessConfiguration,
    ):
        return False
    return configuration.actual_instance.profile_data is not None


def _assert_sync_strategy_exists(sync_user_id: str, sync_profile_id: str) -> typing.Any:
    try:
        return _get_sync_strategy(sync_user_id, sync_profile_id)
    except collection_errors.ItemNotFoundError as err:
        raise commons_errors.DSLInterpreterError(
            f"sync strategy {sync_profile_id!r} not found for sync user {sync_user_id!r}."
        ) from err


async def ensure_user_profile_and_layout(
    user_folder: str,
    working_directory: str,
    profile_data_dict: dict | None = None,
    exchange_auth_overrides: list[dict] | None = None,
    *,
    sync_profile_id: str | None = None,
    user_id: str | None = None,
    octobot_name: str | None = None,
) -> dict[str, typing.Any]:
    """
    One-time layout under user_root (<working_directory>/user/automations/<user_folder>/):
    profile tree and top-level config.json (with master readonly overlays).
    Idempotent when config.json already exists.
    """
    dsl_interpreter.ProcessBoundOperatorMixin.reject_user_path_segment(user_folder)
    user_folder_leaf_segments = _path_segments(user_folder)
    user_root = os.path.normpath(
        os.path.join(
            working_directory,
            *commons_constants.USER_AUTOMATIONS_FOLDER.split("/"),
            *user_folder_leaf_segments,
        )
    )
    config_path = os.path.join(user_root, commons_constants.CONFIG_FILE)
    # Already prepared: do not rewrite files (host may have re-used this folder).
    if os.path.isfile(config_path):
        profile_id = _read_top_level_profile_id(config_path)
        return {
            "user_root": user_root,
            "profile_id": profile_id,
            "already_prepared": True,
        }

    master_reference_tentacles_path = _executor_reference_tentacles_directory(working_directory)
    if not os.path.isdir(master_reference_tentacles_path):
        raise commons_errors.DSLInterpreterError(
            f"Master reference tentacles config not found at {master_reference_tentacles_path!r}. "
            "Install tentacles on the executor (master OctoBot) before spawning process children."
        )

    os.makedirs(user_root, exist_ok=True)

    if profile_data_dict is not None:
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

        _write_user_root_config_json(
            config_path,
            profile_id,
            profile_data,
            exchange_auth_overrides,
            working_directory,
            octobot_name=octobot_name,
            **_child_master_profile_config_kwargs(working_directory),
        )
    elif sync_profile_id is not None:
        if not user_id or not str(user_id).strip():
            raise commons_errors.DSLInterpreterError(
                f"sync_profile_id={sync_profile_id!r} requires user_id."
            )
        strategy = _assert_sync_strategy_exists(str(user_id), sync_profile_id)
        if _sync_strategy_has_profile_data(strategy):
            profile_id = sync_profile_id
        else:
            profile_id = DEFAULT_DSL_PROFILE_ID
        _write_user_root_config_json(
            config_path,
            profile_id,
            None,
            exchange_auth_overrides,
            working_directory,
            octobot_name=octobot_name,
            **_child_master_profile_config_kwargs(working_directory),
        )
    else:
        # Generic process: master profiles via overlay config.
        profile_id = DEFAULT_DSL_PROFILE_ID
        _write_user_root_config_json(
            config_path,
            profile_id,
            None,
            exchange_auth_overrides,
            working_directory,
            octobot_name=octobot_name,
            **_child_master_profile_config_kwargs(working_directory),
        )

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
    log_folder_param_segments = _path_segments(user_folder)
    return os.path.normpath(
        os.path.join(
            working_directory,
            *octobot_node_constants.AUTOMATION_LOGS_FOLDER.split("/"),
            *log_folder_param_segments,
        )
    )


def _ensure_child_environ(
    web_port: int,
    node_port: int,
    bind_host: str,
    sync_user_id: str,
    working_directory: str,
) -> dict:
    """Environment passed to the OctoBot child (ports, bind addresses, sync user id)."""
    child_env = os.environ.copy()
    child_env[services_constants.ENV_WEB_PORT] = str(web_port)
    child_env[services_constants.ENV_WEB_ADDRESS] = bind_host
    child_env[services_constants.ENV_NODE_API_PORT] = str(node_port)
    child_env[services_constants.ENV_NODE_API_ADDRESS] = bind_host
    child_env[commons_constants.ENV_USE_MINIMAL_LIBS] = "false"
    child_env["DISTRIBUTION"] = commons_constants.DEFAULT_DISTRIBUTION
    child_env[services_constants.ENV_ENABLE_NODE_API] = "false"
    child_env[octobot_constants.ENV_PROCESS_BOT_SYNC_USER_ID] = sync_user_id
    child_env[commons_constants.ENV_OCTOBOT_SYNC_DATA_ROOT] = os.path.normpath(
        os.path.join(working_directory, commons_constants.USER_FOLDER)
    )
    return child_env


def _ensure_start_cmd(
    start_script: str,
    rel_user: str,
    rel_log: str,
    no_telegram: bool,
    state_file_path: str,
) -> list[str]:
    """Argv for `python start.py --user-folder … --log-folder … --standalone` (+ optional -nt, --dump-state)."""
    cmd: list[str] = [
        sys.executable,
        start_script,
        "--user-folder",
        rel_user,
        "--log-folder",
        rel_log,
        "--standalone",
    ]
    if no_telegram:
        cmd.append("-nt")
    cmd.extend(["--dump-state", state_file_path])
    return cmd


_child_listen_ports_reserved: dict[int, str] = {}
_child_listen_ports_lock = threading.Lock()


def _reserve_child_listen_ports(web_port: int, node_port: int, user_folder: str) -> None:
    with _child_listen_ports_lock:
        _child_listen_ports_reserved[web_port] = user_folder
        _child_listen_ports_reserved[node_port] = user_folder


def _release_child_listen_ports(web_port: int, node_port: int, user_folder: str) -> None:
    with _child_listen_ports_lock:
        for listen_port in (web_port, node_port):
            if _child_listen_ports_reserved.get(listen_port) == user_folder:
                _child_listen_ports_reserved.pop(listen_port, None)


def _listen_port_pair_with_shared_scan_offset(
    probe_host: str,
    primary_listen_port_base: int,
    secondary_listen_port_base: int,
    *,
    max_offset: int = 256,
    extra_blocklist: set[int] | frozenset[int] | None = None,
) -> tuple[int, int]:
    """Delegates to ``find_first_free_listen_port_after_base`` paired scan (one loop)."""
    primary_blocklist = list(extra_blocklist) if extra_blocklist else None
    primary_listen_port = os_util.find_first_free_listen_port_after_base(
        probe_host,
        primary_listen_port_base,
        max_offset=max_offset,
        blocklist=primary_blocklist,
    )
    secondary_blocklist = set(extra_blocklist or ())
    secondary_blocklist.add(primary_listen_port)
    secondary_listen_port = os_util.find_first_free_listen_port_after_base(
        probe_host,
        secondary_listen_port_base,
        max_offset=max_offset,
        blocklist=list(secondary_blocklist),
    )
    return primary_listen_port, secondary_listen_port


def _allocate_child_listen_port_pair(
    probe_host: str,
    primary_listen_port_base: int,
    secondary_listen_port_base: int,
    user_folder: str,
    *,
    max_offset: int = 256,
) -> tuple[int, int]:
    with _child_listen_ports_lock:
        reserved_ports = frozenset(_child_listen_ports_reserved)
        web_port, node_port = _listen_port_pair_with_shared_scan_offset(
            probe_host,
            primary_listen_port_base,
            secondary_listen_port_base,
            max_offset=max_offset,
            extra_blocklist=reserved_ports,
        )
        _child_listen_ports_reserved[web_port] = user_folder
        _child_listen_ports_reserved[node_port] = user_folder
        return web_port, node_port


def _release_recall_state_listen_ports(
    recall_state: typing.Optional[octobot_process_state_import.OctobotProcessState],
) -> None:
    if recall_state is None:
        return
    _release_child_listen_ports(
        recall_state.web_port,
        recall_state.node_port,
        recall_state.user_folder,
    )


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
            "Prepares a per-bot user directory (profile + config with master readonly overlays), "
            "spawns an OctoBot child with unique WEB/NODE ports and --dump-state for process_bot_state.json. "
            "Always re-callable: each fresh state file (updated_at within twice the dump interval) schedules the next check (see waiting_time). "
            "If the state file never becomes live before ping_timeout from the first spawn, the keyword fails and the child is killed."
        )
        EXAMPLE = (
            f"{RUN_OCTOBOT_PROCESS_OPERATOR_NAME}(user_folder='bots/b1', "
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
                    f"executor_id is required for {RUN_OCTOBOT_PROCESS_OPERATOR_NAME}"
                )
            return executor_id

        @staticmethod
        def get_library() -> str:
            return commons_constants.CONTEXTUAL_OPERATORS_LIBRARY

        @staticmethod
        def get_name() -> str:
            return RUN_OCTOBOT_PROCESS_OPERATOR_NAME

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
                    name="octobot_name",
                    description=(
                        "Optional display name for this child OctoBot instance. "
                        "Written to config.json and shown in the web interface title and navbar."
                    ),
                    required=False,
                    type=str,
                    default=None,
                ),
                dsl_interpreter.OperatorParameter(
                    name="profile_data",
                    description=(
                        "Optional object compatible with octobot_commons.profiles.profile_data.ProfileData. "
                        "When omitted, the child uses the packaged default config and selects the "
                        f"{DEFAULT_DSL_PROFILE_ID!r} profile from the executor user profiles folder "
                        "via master profile overlay."
                    ),
                    required=False,
                    type=dict,
                    default=None,
                ),
                dsl_interpreter.OperatorParameter(
                    name="sync_profile_id",
                    description=(
                        "Optional sync profile id (strategy id). Used only when profile_data is omitted. "
                        "Validates the strategy exists in sync for user_id. When the strategy embeds "
                        "profile_data, selects it in child config.json without a local profiles/ tree; "
                        f"otherwise the child uses {DEFAULT_DSL_PROFILE_ID!r} from the executor profiles overlay."
                    ),
                    required=False,
                    type=str,
                    default=None,
                ),
                dsl_interpreter.OperatorParameter(
                    name="user_id",
                    description=(
                        "Sync wallet user id (same as node task user_id). Required to spawn the "
                        "process child (passed via environment, not config.json). Also required "
                        "when sync_profile_id is set for strategy validation."
                    ),
                    required=False,
                    type=str,
                    default=None,
                ),
                dsl_interpreter.OperatorParameter(
                    name="exchange_auth_data",
                    description=(
                        "Optional list of dicts compatible with "
                        "octobot_commons.profiles.exchange_auth_data.ExchangeAuthData "
                        "(e.g. internal_name, api_key, api_secret, api_password, exchange_type, sandboxed). "
                        "Exchanges not listed inherit credentials from the executor master user/config.json; "
                        "each listed entry fully replaces the master entry for that internal_name."
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
                return octobot_process_state_import.parse_octobot_process_state(inner) is not None
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
            state: octobot_process_state_import.OctobotProcessState,
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
            recall_state: octobot_process_state_import.OctobotProcessState,
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
                _release_recall_state_listen_ports(recall_state)
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
                if not recall_state.init_state_ok:
                    _release_recall_state_listen_ports(recall_state)
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
            exchange_auth_overrides = params.get("exchange_auth_data")
            init_info = await ensure_user_profile_and_layout(
                user_folder,
                working_directory,
                params.get("profile_data"),
                exchange_auth_overrides,
                sync_profile_id=params.get("sync_profile_id"),
                user_id=params.get("user_id"),
                octobot_name=params.get("octobot_name"),
            )
            user_root = init_info["user_root"]
            log_folder = _ensure_log_folder_path(working_directory, user_folder)
            bind_host, probe_host = (
                dsl_interpreter.ProcessBoundOperatorMixin.bind_address_for_env_and_probe_hosts(
                    params
                )
            )
            prior_recall_state = octobot_process_state_import.parse_octobot_process_state(last_result)
            _release_recall_state_listen_ports(prior_recall_state)
            web_b = int(params.get("web_port_base") or services_constants.DEFAULT_SERVER_PORT)
            node_b = int(params.get("node_port_base") or services_constants.DEFAULT_NODE_API_PORT)
            web_port, node_port = _allocate_child_listen_port_pair(
                probe_host, web_b, node_b, user_folder
            )
            start_script = os.path.join(working_directory, "start.py")
            if not os.path.isfile(start_script):
                raise commons_errors.DSLInterpreterError(
                    f"start.py not found at {start_script} (current working directory must be the OctoBot project root)."
                )
            process_sync_user_id = params.get("user_id")
            if not process_sync_user_id or not str(process_sync_user_id).strip():
                raise commons_errors.DSLInterpreterError(
                    f"{RUN_OCTOBOT_PROCESS_OPERATOR_NAME} requires user_id to spawn a process child."
                )
            child_env = _ensure_child_environ(
                web_port,
                node_port,
                bind_host,
                str(process_sync_user_id),
                working_directory,
            )
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
            _assert_spawn_cmd_isolation(cmd, rel_user, rel_log)
            _get_logger().info("Spawning OctoBot process child: cmd=%r", cmd)
            self.spawn_subprocess(
                cmd,
                working_directory=working_directory,
                environment=child_env,
                hide_console_window=True,
            )
            scheme = str(params.get("http_scheme") or "http").rstrip(":/")
            http_base_url = f"{scheme}://{bind_host}:{web_port}"
            state = octobot_process_state_import.OctobotProcessState(
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
                    _release_child_listen_ports(web_port, node_port, user_folder)
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

        async def _stop_bound_child_and_wait_for_exit(
            self,
            pid: int,
            *,
            ping_timeout: float,
            logger: typing.Any,
        ) -> dict[str, typing.Any]:
            # 1. Ask the child to shut down gracefully, then wait up to ping_timeout.
            stop_outcome = self.request_graceful_stop(logger=logger)
            try:
                await self.wait_until_pid_stopped(
                    pid,
                    logger=logger,
                    timeout_seconds=ping_timeout,
                )
                return stop_outcome
            except commons_errors.DSLInterpreterError as graceful_wait_error:
                logger.warning(
                    "Graceful stop timed out after %ss for pid=%s; attempting force kill: %s",
                    ping_timeout,
                    pid,
                    graceful_wait_error,
                )
            # 2. Escalate to force kill when graceful shutdown does not complete in time.
            process_util.request_force_kill(pid, logger=logger)
            try:
                await self.wait_until_pid_stopped(
                    pid,
                    logger=logger,
                    timeout_seconds=DEFAULT_FORCE_KILL_EXIT_WAIT_SECONDS,
                )
            except commons_errors.DSLInterpreterError as force_wait_error:
                raise commons_errors.DSLInterpreterError(
                    f"Child pid={pid} did not exit after graceful stop and force kill."
                ) from force_wait_error
            return {"status": "force_killed"}

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
            recall_state = self._try_parse_octobot_process_state(last_result)
            if recall_state is None:
                raise commons_errors.DSLInterpreterError(
                    f"{RUN_OCTOBOT_PROCESS_OPERATOR_NAME}(UPDATE_CONFIG) requires last_execution_result from a prior "
                    f"{RUN_OCTOBOT_PROCESS_OPERATOR_NAME} call.",
                )
            process_logger = _get_logger()
            state_path = _resolve_state_file_path(recall_state)
            loaded_state = await _load_process_bot_state(state_path)
            resolved_pid = _resolve_bound_pid(recall_state, loaded_state)
            if resolved_pid is None:
                raise commons_errors.DSLInterpreterError(
                    f"{RUN_OCTOBOT_PROCESS_OPERATOR_NAME}(UPDATE_CONFIG) cannot resolve a running child pid to stop."
                )
            self.pid = resolved_pid
            process_logger.info(
                "configuration update: begin refresh user_folder=%r user_root=%r log_folder=%r pid=%s",
                user_folder,
                recall_state.user_root,
                recall_state.log_folder,
                resolved_pid,
            )
            stop_outcome = await self._stop_bound_child_and_wait_for_exit(
                resolved_pid,
                ping_timeout=ping_timeout,
                logger=process_logger,
            )
            process_logger.info("configuration update: stop outcome: %s", stop_outcome)
            _release_recall_state_listen_ports(recall_state)
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
                recall_state = self._try_parse_octobot_process_state(last_result)
                if recall_state is None:
                    raise commons_errors.DSLInterpreterError(
                        f"{RUN_OCTOBOT_PROCESS_OPERATOR_NAME}(execution_stop) requires last_execution_result from a prior {RUN_OCTOBOT_PROCESS_OPERATOR_NAME} call.",
                    )
                state_path = _resolve_state_file_path(recall_state)
                loaded_state = await _load_process_bot_state(state_path)
                stored_pid_running = _stored_pid_is_running(recall_state)
                resolved_pid = _resolve_bound_pid(recall_state, loaded_state)
                if resolved_pid is not None:
                    self.pid = resolved_pid
                    process_logger = _get_logger()
                    ping_timeout = float(params.get("ping_timeout") or DEFAULT_ENSURE_TIMEOUT)
                    self.value = await self._stop_bound_child_and_wait_for_exit(
                        resolved_pid,
                        ping_timeout=ping_timeout,
                        logger=process_logger,
                    )
                    _release_recall_state_listen_ports(recall_state)
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
                        f"{RUN_OCTOBOT_PROCESS_OPERATOR_NAME}(STOP): child in restart grace; treating as already_stopped"
                    )
                self.value = {"status": "already_stopped", "reason": "not_running"}
                _release_recall_state_listen_ports(recall_state)
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
            recall_state = self._try_parse_octobot_process_state(last_result)
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
                    f"{RUN_OCTOBOT_PROCESS_OPERATOR_NAME}: respawning child (recall path declined): user_folder=%r "
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


        def _try_parse_octobot_process_state(self, raw: dict) -> typing.Optional[octobot_process_state_import.OctobotProcessState]:
            if state := octobot_process_state_import.parse_octobot_process_state(raw):
                if state.pid:
                    self.pid = state.pid
                return state
            return None
    
    return [EnsureOctobotProcessOperator]



def _get_logger():
    return commons_logging.get_logger("OctoBotProcessOperators")
