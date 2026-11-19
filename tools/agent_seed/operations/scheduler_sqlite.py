#  Demo-only scheduler SQLite path resolution and wipe helpers.

import os
import pathlib
import shutil
import typing

import octobot_node.agent_seed.constants as demo_agent_seed_constants
import octobot_node.config as octobot_node_config
import octobot_services.constants as octobot_services_constants

import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.paths as agent_seed_paths


class AgentSeedClearLockedSqliteError(RuntimeError):
    """Raised when scheduler sqlite files cannot be removed (node likely running)."""


def _scheduler_sqlite_default_file_name() -> str:
    default = octobot_node_config.Settings.model_fields["SCHEDULER_SQLITE_FILE"].default
    return str(default)


def _resolve_env_path(
    env_name: str,
    repo_root: pathlib.Path,
) -> tuple[typing.Optional[str], typing.Optional[pathlib.Path]]:
    env_value = os.environ.get(env_name)
    if not env_value:
        return env_value, None
    resolved = agent_seed_paths.resolve_path_from_env(env_value, repo_root)
    if resolved is None:
        return env_value, None
    return env_value, resolved.resolve()


def ensure_scheduler_sqlite_for_agent_seed_start(
    user_folder: pathlib.Path,
    repo_root: pathlib.Path,
) -> None:
    scheduler_env_name = octobot_services_constants.ENV_NODE_SQLITE_FILE
    default_sqlite_name = _scheduler_sqlite_default_file_name()
    expected_path = (user_folder.resolve() / default_sqlite_name).resolve()
    default_node_path = (repo_root / default_sqlite_name).resolve()
    fix_hint = "bash .cursor/seed-agent.sh --restart or bash .cursor/seed-agent.sh --full"
    scheduler_raw, scheduler_path = _resolve_env_path(scheduler_env_name, repo_root)
    node_raw, node_path = _resolve_env_path("NODE_SQLITE_FILE", repo_root)
    if not scheduler_raw:
        raise agent_seed_errors.AgentSeedSchedulerSqliteConfigError(
            f"Cannot start agent-seed node: {scheduler_env_name} is not set. "
            f"OctoBot would open scheduler database {default_node_path!s} instead of the seeded "
            f"database {expected_path!s}, so automations from agent-seed would be missing "
            f"(debug may show automations: []). "
            f"Export {scheduler_env_name} to the same path as NODE_SQLITE_FILE "
            f"({expected_path!s}). "
            f"Do not call `python -m tools.agent_seed start-background` after only "
            f"`source .cursor/agent-seed.env` — use {fix_hint}."
        )
    if scheduler_path != expected_path or node_path != expected_path or scheduler_path != node_path:
        scheduler_part = (
            f"{scheduler_env_name}={scheduler_path!s}"
            if scheduler_path is not None
            else f"{scheduler_env_name} is set but could not be resolved"
        )
        node_part = (
            f"NODE_SQLITE_FILE={node_path!s}"
            if node_path is not None
            else "NODE_SQLITE_FILE is not set"
        )
        wrong_path = scheduler_path or default_node_path
        raise agent_seed_errors.AgentSeedSchedulerSqliteConfigError(
            f"Cannot start agent-seed node: scheduler database paths must all match "
            f"{expected_path!s} ({scheduler_part}; {node_part}). "
            f"The node would use {wrong_path!s}, so seeded automations would be missing. "
            f"Use {fix_hint} so env exports stay aligned."
        )


def resolve_scheduler_sqlite_path(
    repo_root: typing.Optional[pathlib.Path] = None,
) -> typing.Optional[pathlib.Path]:
    resolved_repo_root = (
        repo_root if repo_root is not None else agent_seed_paths.default_octobot_repo_root()
    )
    for env_name in (octobot_services_constants.ENV_NODE_SQLITE_FILE, "NODE_SQLITE_FILE"):
        _, resolved = _resolve_env_path(env_name, resolved_repo_root)
        if resolved is not None:
            return resolved
    return None


def scheduler_sqlite_path_for_errors(
    repo_root: typing.Optional[pathlib.Path] = None,
) -> str:
    resolved = resolve_scheduler_sqlite_path(repo_root)
    if resolved is not None:
        return str(resolved.resolve())
    return "<SCHEDULER_SQLITE_FILE not set>"


def scheduler_sqlite_companion_paths(node_sqlite_file: os.PathLike[str]) -> list[str]:
    sqlite_path = os.fspath(node_sqlite_file)
    return [
        sqlite_path,
        f"{sqlite_path}-wal",
        f"{sqlite_path}-shm",
    ]


def _locked_sqlite_message(node_sqlite_file: os.PathLike[str]) -> str:
    resolved = os.path.abspath(os.fspath(node_sqlite_file))
    return (
        f"{demo_agent_seed_constants.DEMO_AGENT_SEED_CLEAR_LOCKED_SQLITE_MESSAGE_PREFIX} "
        f"(NODE_SQLITE_FILE={resolved})."
    )


def scheduler_sqlite_targets_exist(
    user_folder: os.PathLike[str],
    node_sqlite_file: typing.Optional[os.PathLike[str]],
) -> bool:
    if node_sqlite_file is not None:
        for sqlite_path in scheduler_sqlite_companion_paths(node_sqlite_file):
            if os.path.exists(sqlite_path):
                return True
    folder_path = pathlib.Path(user_folder)
    if agent_seed_paths.marker_path(folder_path).is_file():
        return True
    if folder_path.is_dir():
        try:
            next(folder_path.iterdir())
            return True
        except StopIteration:
            return False
    return False


def _not_initialized_clear_message(
    user_folder: os.PathLike[str],
    node_sqlite_file: typing.Optional[os.PathLike[str]],
) -> str:
    user_resolved = os.path.abspath(os.fspath(user_folder))
    sqlite_resolved = (
        os.path.abspath(os.fspath(node_sqlite_file)) if node_sqlite_file is not None else None
    )
    sqlite_part = (
        f"NODE_SQLITE_FILE={sqlite_resolved!r}"
        if sqlite_resolved is not None
        else "NODE_SQLITE_FILE is not set"
    )
    return (
        "Agent seed --clear found nothing to wipe: the demo user folder and scheduler database "
        "were never initialized (or you are clearing the wrong paths). "
        f"Expected user folder {user_resolved!r} and scheduler sqlite at {sqlite_part}. "
        "Run `bash .cursor/seed-agent.sh seed` or `--full` first, or fix NODE_SQLITE_FILE / "
        "OCTOBOT_AGENT_SEED_USER_FOLDER to match the node (SCHEDULER_SQLITE_FILE must use the same "
        "tasks.db path when starting OctoBot)."
    )


def remove_scheduler_sqlite_files(node_sqlite_file: typing.Optional[os.PathLike[str]]) -> None:
    if node_sqlite_file is None:
        return
    for sqlite_path in scheduler_sqlite_companion_paths(node_sqlite_file):
        if not os.path.exists(sqlite_path):
            continue
        try:
            os.remove(sqlite_path)
        except (PermissionError, OSError) as error:
            raise AgentSeedClearLockedSqliteError(
                _locked_sqlite_message(node_sqlite_file),
            ) from error
        if os.path.exists(sqlite_path):
            raise AgentSeedClearLockedSqliteError(
                _locked_sqlite_message(node_sqlite_file),
            )


def clear_agent_seed_user_folder(
    user_folder: os.PathLike[str],
    node_sqlite_file: typing.Optional[os.PathLike[str]],
) -> None:
    if not scheduler_sqlite_targets_exist(user_folder, node_sqlite_file):
        raise agent_seed_errors.AgentSeedClearNotInitializedError(
            _not_initialized_clear_message(user_folder, node_sqlite_file),
        )
    remove_scheduler_sqlite_files(node_sqlite_file)
    folder_path = os.fspath(user_folder)
    if not os.path.isdir(folder_path):
        return
    try:
        shutil.rmtree(folder_path)
    except (PermissionError, OSError) as error:
        raise AgentSeedClearLockedSqliteError(
            _locked_sqlite_message(node_sqlite_file or folder_path),
        ) from error
