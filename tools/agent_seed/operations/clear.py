#  Demo-only agent seed data wipe. Stop the OctoBot node before clearing tasks.db.

import os
import shutil
import typing

import octobot_node.agent_seed.constants as demo_agent_seed_constants


class AgentSeedClearLockedSqliteError(RuntimeError):
    """Raised when scheduler sqlite files cannot be removed (node likely running)."""


def _sqlite_companion_paths(node_sqlite_file: os.PathLike[str]) -> list[str]:
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


def remove_scheduler_sqlite_files(node_sqlite_file: typing.Optional[os.PathLike[str]]) -> None:
    if node_sqlite_file is None:
        return
    for sqlite_path in _sqlite_companion_paths(node_sqlite_file):
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
