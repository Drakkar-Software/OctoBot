#  Demo-only scheduler SQLite path resolution and wipe helpers.

import os
import pathlib
import shutil
import typing

import octobot_node.agent_seed.constants as demo_agent_seed_constants

import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.paths as agent_seed_paths


class AgentSeedClearLockedSqliteError(RuntimeError):
    """Raised when scheduler sqlite files cannot be removed (node likely running)."""


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
