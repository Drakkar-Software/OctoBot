#  Demo-only agent seed orchestration (run_seed + idempotency).

import os
import pathlib
import typing

import octobot_commons.user_root_folder_provider as user_root_folder_provider
import octobot_sync.sync.collection_providers as collection_providers

import octobot_node.agent_seed.constants as demo_agent_seed_constants

import tools.agent_seed.operations.clear as agent_seed_clear
import tools.agent_seed.operations.seed_octobot_config as agent_seed_seed_octobot_config
import tools.agent_seed.operations.seed_sync as agent_seed_seed_sync
import tools.agent_seed.paths as agent_seed_paths
import tools.agent_seed.secrets as agent_seed_secrets


def _is_demo_sync_complete(user_folder: pathlib.Path) -> bool:
    account_provider = collection_providers.AccountProvider(
        base_folder=str(user_folder),
    )
    strategy_provider = collection_providers.StrategyProvider(
        base_folder=str(user_folder),
    )
    user_id = demo_agent_seed_constants.DEMO_AGENT_SEED_USER_ID
    try:
        account_provider.get_exchange_config(
            user_id,
            demo_agent_seed_constants.DEMO_AGENT_SEED_EXCHANGE_CONFIG_ID,
        )
        account_provider.get_item(
            user_id,
            demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_GRID_ID,
        )
        account_provider.get_item(
            user_id,
            demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_INDEX_IDLE_ID,
        )
        strategy_provider.get_item(
            user_id,
            demo_agent_seed_constants.DEMO_AGENT_SEED_STRATEGY_GRID_ID,
        )
        strategy_provider.get_item(
            user_id,
            demo_agent_seed_constants.DEMO_AGENT_SEED_STRATEGY_INDEX_ID,
        )
    except Exception:
        return False
    return True


def _ensure_seed_marker(user_folder: pathlib.Path) -> None:
    marker_path = agent_seed_paths.marker_path(user_folder)
    expected_version = f"{demo_agent_seed_constants.DEMO_AGENT_SEED_MARKER_VERSION}\n"
    if marker_path.is_file() and marker_path.read_text(encoding="utf-8") == expected_version:
        return
    marker_path.write_text(expected_version, encoding="utf-8")


def is_already_seeded(user_folder: pathlib.Path) -> bool:
    return _is_demo_sync_complete(user_folder)


def run_seed(
    *,
    user_folder: pathlib.Path,
    clear: bool,
    node_sqlite_file: typing.Optional[pathlib.Path],
    repo_root: typing.Optional[pathlib.Path] = None,
) -> None:
    agent_seed_secrets.assert_demo_insecure_wallet_matches_node_constants()
    resolved_repo_root = (
        repo_root if repo_root is not None else agent_seed_paths.default_octobot_repo_root()
    )
    user_folder.mkdir(parents=True, exist_ok=True)
    if clear:
        agent_seed_clear.clear_agent_seed_user_folder(user_folder, node_sqlite_file)
        user_folder.mkdir(parents=True, exist_ok=True)
    agent_seed_seed_octobot_config.write_demo_user_config(user_folder, resolved_repo_root)
    user_root_folder_provider.instance().set_root(os.path.normpath(str(user_folder)))
    agent_seed_seed_sync.import_demo_wallet()
    if not clear and is_already_seeded(user_folder):
        _ensure_seed_marker(user_folder)
        return
    agent_seed_seed_sync.write_sync_collections(
        user_folder,
        demo_agent_seed_constants.DEMO_AGENT_SEED_USER_ID,
    )
    _ensure_seed_marker(user_folder)
