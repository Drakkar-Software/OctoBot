#  Demo-only scheduler SQLite path resolution and wipe helpers.

import os
import pathlib
import shutil
import typing

import octobot_node.agent_seed.constants as demo_agent_seed_constants

import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.paths as agent_seed_paths

_SCHEDULER_SQLITE_FILE_ENV = "SCHEDULER_SQLITE_FILE"
_NODE_SQLITE_FILE_ENV = "NODE_SQLITE_FILE"
_DEFAULT_OCTOBOT_SCHEDULER_SQLITE_NAME = "tasks.db"
_SEED_AGENT_SHELL_HINT = (
    "bash .cursor/seed-agent.sh --restart (keep fixtures) or bash .cursor/seed-agent.sh --full"
)


class AgentSeedClearLockedSqliteError(RuntimeError):
    """Raised when scheduler sqlite files cannot be removed (node likely running)."""


def expected_agent_seed_tasks_db_path(user_folder: os.PathLike[str]) -> pathlib.Path:
    return pathlib.Path(user_folder).resolve() / _DEFAULT_OCTOBOT_SCHEDULER_SQLITE_NAME


def resolve_node_sqlite_path_from_env(
    repo_root: pathlib.Path,
) -> typing.Optional[pathlib.Path]:
    env_value = os.environ.get(_NODE_SQLITE_FILE_ENV)
    if not env_value:
        return None
    resolved = agent_seed_paths.resolve_path_from_env(env_value, repo_root)
    if resolved is None:
        return None
    return resolved.resolve()


def resolve_scheduler_sqlite_path_from_env(
    repo_root: pathlib.Path,
) -> typing.Optional[pathlib.Path]:
    env_value = os.environ.get(_SCHEDULER_SQLITE_FILE_ENV)
    if not env_value:
        return None
    resolved = agent_seed_paths.resolve_path_from_env(env_value, repo_root)
    if resolved is None:
        return None
    return resolved.resolve()


def octobot_scheduler_sqlite_path_without_scheduler_env(
    repo_root: pathlib.Path,
) -> pathlib.Path:
    return (repo_root / _DEFAULT_OCTOBOT_SCHEDULER_SQLITE_NAME).resolve()


def _scheduler_sqlite_config_error_message(
    *,
    scheduler_env_set: bool,
    node_env_set: bool,
    scheduler_resolved: typing.Optional[pathlib.Path],
    node_resolved: typing.Optional[pathlib.Path],
    expected_path: pathlib.Path,
    repo_root: pathlib.Path,
) -> str:
    if not scheduler_env_set:
        wrong_path = octobot_scheduler_sqlite_path_without_scheduler_env(repo_root)
        return (
            f"Cannot start agent-seed node: {_SCHEDULER_SQLITE_FILE_ENV} is not set. "
            f"OctoBot would open scheduler database {wrong_path!s} instead of the seeded "
            f"database {expected_path!s}, so automations from agent-seed would be missing "
            f"(debug may show automations: []). "
            f"Export {_SCHEDULER_SQLITE_FILE_ENV} to the same path as {_NODE_SQLITE_FILE_ENV} "
            f"({expected_path!s}). "
            f"Do not call `python -m tools.agent_seed start-background` after only "
            f"`source .cursor/agent-seed.env` — use {_SEED_AGENT_SHELL_HINT}."
        )
    scheduler_part = (
        f"{_SCHEDULER_SQLITE_FILE_ENV}={scheduler_resolved!s}"
        if scheduler_resolved is not None
        else f"{_SCHEDULER_SQLITE_FILE_ENV} is set but could not be resolved"
    )
    node_part = (
        f"{_NODE_SQLITE_FILE_ENV}={node_resolved!s}"
        if node_resolved is not None
        else f"{_NODE_SQLITE_FILE_ENV} is not set"
    )
    wrong_path = scheduler_resolved or octobot_scheduler_sqlite_path_without_scheduler_env(
        repo_root,
    )
    return (
        f"Cannot start agent-seed node: scheduler database paths must all match "
        f"{expected_path!s} ({scheduler_part}; {node_part}). "
        f"The node would use {wrong_path!s}, so seeded automations would be missing. "
        f"Use {_SEED_AGENT_SHELL_HINT} so env exports stay aligned."
    )


def ensure_scheduler_sqlite_for_agent_seed_start(
    user_folder: pathlib.Path,
    repo_root: pathlib.Path,
) -> None:
    expected_path = expected_agent_seed_tasks_db_path(user_folder)
    scheduler_env_set = bool(os.environ.get(_SCHEDULER_SQLITE_FILE_ENV))
    node_env_set = bool(os.environ.get(_NODE_SQLITE_FILE_ENV))
    scheduler_resolved = (
        resolve_scheduler_sqlite_path_from_env(repo_root) if scheduler_env_set else None
    )
    node_resolved = resolve_node_sqlite_path_from_env(repo_root) if node_env_set else None
    if not scheduler_env_set:
        raise agent_seed_errors.AgentSeedSchedulerSqliteConfigError(
            _scheduler_sqlite_config_error_message(
                scheduler_env_set=False,
                node_env_set=node_env_set,
                scheduler_resolved=scheduler_resolved,
                node_resolved=node_resolved,
                expected_path=expected_path,
                repo_root=repo_root,
            ),
        )
    paths_match = (
        scheduler_resolved == expected_path
        and node_resolved == expected_path
        and scheduler_resolved == node_resolved
    )
    if not paths_match:
        raise agent_seed_errors.AgentSeedSchedulerSqliteConfigError(
            _scheduler_sqlite_config_error_message(
                scheduler_env_set=True,
                node_env_set=node_env_set,
                scheduler_resolved=scheduler_resolved,
                node_resolved=node_resolved,
                expected_path=expected_path,
                repo_root=repo_root,
            ),
        )


def resolve_scheduler_sqlite_path(
    repo_root: typing.Optional[pathlib.Path] = None,
) -> typing.Optional[pathlib.Path]:
    resolved_repo_root = (
        repo_root if repo_root is not None else agent_seed_paths.default_octobot_repo_root()
    )
    for env_name in ("SCHEDULER_SQLITE_FILE", "NODE_SQLITE_FILE"):
        env_value = os.environ.get(env_name)
        if not env_value:
            continue
        resolved = agent_seed_paths.resolve_path_from_env(env_value, resolved_repo_root)
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
