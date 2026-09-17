#  Demo-only agent seed path helpers (stdlib only).

import os
import pathlib
import typing

AGENT_SEED_VERSION_MARKER_FILE = ".agent-seed-version"
OCTOBOT_AGENT_SEED_MASTER_USER_ROOT_ENV = "OCTOBOT_AGENT_SEED_MASTER_USER_ROOT"
MASTER_USER_FOLDER_NAME = "user"
REFERENCE_TENTACLES_CONFIG_DIR_NAME = "reference_tentacles_config"
TENTACLES_CONFIG_FILE_NAME = "tentacles_config.json"
PROFILES_DIR_NAME = "profiles"
USER_CONFIG_FILE_NAME = "config.json"


def default_octobot_repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def resolve_path_from_env(
    env_value: typing.Optional[str],
    repo_root: pathlib.Path,
) -> typing.Optional[pathlib.Path]:
    if not env_value:
        return None
    path = pathlib.Path(env_value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def marker_path(user_folder: pathlib.Path) -> pathlib.Path:
    return user_folder / AGENT_SEED_VERSION_MARKER_FILE


def default_master_user_root(repo_root: pathlib.Path) -> pathlib.Path:
    return (repo_root / MASTER_USER_FOLDER_NAME).resolve()


def resolve_master_user_root_from_env(repo_root: pathlib.Path) -> pathlib.Path:
    env_value = os.environ.get(OCTOBOT_AGENT_SEED_MASTER_USER_ROOT_ENV)
    if env_value:
        resolved = resolve_path_from_env(env_value, repo_root)
        if resolved is not None:
            return resolved
    return default_master_user_root(repo_root)


def master_reference_tentacles_config_dir(master_root: pathlib.Path) -> pathlib.Path:
    return master_root / REFERENCE_TENTACLES_CONFIG_DIR_NAME


def master_reference_tentacles_config_file(master_root: pathlib.Path) -> pathlib.Path:
    return master_reference_tentacles_config_dir(master_root) / TENTACLES_CONFIG_FILE_NAME


def master_profiles_dir(master_root: pathlib.Path) -> pathlib.Path:
    return master_root / PROFILES_DIR_NAME


def user_config_file(user_folder: pathlib.Path) -> pathlib.Path:
    return user_folder / USER_CONFIG_FILE_NAME
