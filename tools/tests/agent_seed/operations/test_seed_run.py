#  Functional agent seed run tests (isolated tmp_path).

import json

import octobot.constants as octobot_constants
import octobot.community.authentication as community_authentication
import octobot_sync.sync.collection_providers as collection_providers

import octobot_commons.constants as commons_constants

import octobot_node.agent_seed.constants as demo_agent_seed_constants

import tools.agent_seed.operations.seed_run as agent_seed_seed_run
import tools.agent_seed.paths as agent_seed_paths
import tools.agent_seed.secrets as agent_seed_secrets


def _install_master_reference_tentacles(monkeypatch, tmp_path):
    master_root = tmp_path / "master-user"
    reference_dir = agent_seed_paths.master_reference_tentacles_config_dir(master_root)
    reference_dir.mkdir(parents=True)
    (reference_dir / agent_seed_paths.TENTACLES_CONFIG_FILE_NAME).write_text(
        "{}",
        encoding="utf-8",
    )
    monkeypatch.setenv(
        agent_seed_paths.OCTOBOT_AGENT_SEED_MASTER_USER_ROOT_ENV,
        str(master_root),
    )
    return master_root


def _persisted_wallet_addresses(config_data: dict) -> list[str]:
    wallets_root = config_data.get(octobot_constants.CONFIG_COMMUNITY, {}).get(
        octobot_constants.CONFIG_COMMUNITY_WALLETS,
        {},
    )
    if not isinstance(wallets_root, dict):
        return []
    chain_wallets = wallets_root.get(octobot_constants.CHAIN_TYPE, {})
    if not isinstance(chain_wallets, dict):
        return []
    entries = chain_wallets.get(octobot_constants.CHAIN_NETWORK, [])
    if not isinstance(entries, list):
        return []
    return [
        entry.get("address", "").lower()
        for entry in entries
        if isinstance(entry, dict) and entry.get("address")
    ]


def _assert_demo_wallet_in_config(user_folder):
    config_data = json.loads(
        agent_seed_paths.user_config_file(user_folder).read_text(encoding="utf-8"),
    )
    demo_address = demo_agent_seed_constants.DEMO_AGENT_SEED_WALLET_EVM_ADDRESS.lower()
    assert demo_address in _persisted_wallet_addresses(config_data)


class TestRunSeed:
    def test_seed_writes_wallet_sync_and_marker(self, tmp_path, monkeypatch):
        _install_master_reference_tentacles(monkeypatch, tmp_path)
        user_folder = tmp_path / "agent-seed-user"
        sqlite_path = user_folder / "tasks.db"
        monkeypatch.setenv("OCTOBOT_AGENT_SEED_USER_FOLDER", str(user_folder))
        monkeypatch.setenv("NODE_SQLITE_FILE", str(sqlite_path))
        agent_seed_seed_run.run_seed(
            user_folder=user_folder,
            clear=False,
            node_sqlite_file=sqlite_path,
            repo_root=tmp_path,
        )

        community_auth = community_authentication.CommunityAuthentication.instance()
        community_auth.authenticate_wallet(
            demo_agent_seed_constants.DEMO_AGENT_SEED_WALLET_EVM_ADDRESS,
            agent_seed_secrets.DEMO_INSECURE_WALLET_PASSPHRASE,
        )
        wallet = community_auth.get_wallet(
            demo_agent_seed_constants.DEMO_AGENT_SEED_WALLET_EVM_ADDRESS,
        )
        assert wallet.address.lower() == (
            demo_agent_seed_constants.DEMO_AGENT_SEED_WALLET_EVM_ADDRESS.lower()
        )
        assert community_auth.get_wallet_name(wallet.address) == (
            demo_agent_seed_constants.DEMO_AGENT_SEED_WALLET_DISPLAY_NAME
        )
        _assert_demo_wallet_in_config(user_folder)

        account_provider = collection_providers.AccountProvider(base_folder=str(user_folder))
        grid_account = account_provider.get_item(
            demo_agent_seed_constants.DEMO_AGENT_SEED_USER_ID,
            demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_GRID_ID,
        )
        assert grid_account.is_simulated is True
        assert grid_account.name == demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_GRID_DISPLAY_NAME
        index_account = account_provider.get_item(
            demo_agent_seed_constants.DEMO_AGENT_SEED_USER_ID,
            demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_INDEX_IDLE_ID,
        )
        assert index_account.name == demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_INDEX_IDLE_DISPLAY_NAME
        assert agent_seed_paths.marker_path(user_folder).is_file()

        agent_seed_seed_run.run_seed(
            user_folder=user_folder,
            clear=False,
            node_sqlite_file=sqlite_path,
            repo_root=tmp_path,
        )
        assert account_provider.get_item(
            demo_agent_seed_constants.DEMO_AGENT_SEED_USER_ID,
            demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_GRID_ID,
        ).id == demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_GRID_ID


class TestRunSeedWritesOctobotConfig:
    def test_run_seed_writes_config_json_pointing_at_master(self, tmp_path, monkeypatch):
        master_root = _install_master_reference_tentacles(monkeypatch, tmp_path)
        user_folder = tmp_path / "agent-seed-user"
        sqlite_path = user_folder / "tasks.db"
        agent_seed_seed_run.run_seed(
            user_folder=user_folder,
            clear=False,
            node_sqlite_file=sqlite_path,
            repo_root=tmp_path,
        )
        config_data = json.loads(
            agent_seed_paths.user_config_file(user_folder).read_text(encoding="utf-8"),
        )
        assert config_data[commons_constants.CONFIG_ACCEPTED_TERMS] is True
        assert config_data[commons_constants.CONFIG_READONLY_REFERENCE_TENTACLES_PATH] == str(
            agent_seed_paths.master_reference_tentacles_config_dir(master_root).resolve(),
        )

    def test_run_seed_skips_sync_when_demo_sync_complete(self, tmp_path, monkeypatch):
        _install_master_reference_tentacles(monkeypatch, tmp_path)
        user_folder = tmp_path / "agent-seed-user"
        sqlite_path = user_folder / "tasks.db"
        agent_seed_seed_run.run_seed(
            user_folder=user_folder,
            clear=False,
            node_sqlite_file=sqlite_path,
            repo_root=tmp_path,
        )
        agent_seed_paths.marker_path(user_folder).unlink()
        agent_seed_seed_run.run_seed(
            user_folder=user_folder,
            clear=False,
            node_sqlite_file=sqlite_path,
            repo_root=tmp_path,
        )
        assert agent_seed_paths.marker_path(user_folder).is_file()
        config_data = json.loads(
            agent_seed_paths.user_config_file(user_folder).read_text(encoding="utf-8"),
        )
        assert config_data[commons_constants.CONFIG_ACCEPTED_TERMS] is True

    def test_run_seed_rewrites_config_on_idempotent_second_run(self, tmp_path, monkeypatch):
        master_root = _install_master_reference_tentacles(monkeypatch, tmp_path)
        user_folder = tmp_path / "agent-seed-user"
        sqlite_path = user_folder / "tasks.db"
        agent_seed_seed_run.run_seed(
            user_folder=user_folder,
            clear=False,
            node_sqlite_file=sqlite_path,
            repo_root=tmp_path,
        )
        config_path = agent_seed_paths.user_config_file(user_folder)
        config_path.write_text('{"stale": true}\n', encoding="utf-8")
        agent_seed_seed_run.run_seed(
            user_folder=user_folder,
            clear=False,
            node_sqlite_file=sqlite_path,
            repo_root=tmp_path,
        )
        config_data = json.loads(config_path.read_text(encoding="utf-8"))
        assert "stale" not in config_data
        assert config_data[commons_constants.CONFIG_ACCEPTED_TERMS] is True
        assert config_data[commons_constants.CONFIG_READONLY_REFERENCE_TENTACLES_PATH] == str(
            agent_seed_paths.master_reference_tentacles_config_dir(master_root).resolve(),
        )


class TestRunSeedPartialSyncRecovery:
    def test_run_seed_recreates_missing_grid_account_after_partial_state(
        self,
        tmp_path,
        monkeypatch,
    ):
        _install_master_reference_tentacles(monkeypatch, tmp_path)
        user_folder = tmp_path / "agent-seed-user"
        sqlite_path = user_folder / "tasks.db"
        agent_seed_seed_run.run_seed(
            user_folder=user_folder,
            clear=False,
            node_sqlite_file=sqlite_path,
            repo_root=tmp_path,
        )
        account_provider = collection_providers.AccountProvider(base_folder=str(user_folder))
        account_provider.delete_account(
            demo_agent_seed_constants.DEMO_AGENT_SEED_USER_ID,
            demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_GRID_ID,
        )
        agent_seed_seed_run.run_seed(
            user_folder=user_folder,
            clear=False,
            node_sqlite_file=sqlite_path,
            repo_root=tmp_path,
        )
        grid_account = account_provider.get_item(
            demo_agent_seed_constants.DEMO_AGENT_SEED_USER_ID,
            demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_GRID_ID,
        )
        assert grid_account.id == demo_agent_seed_constants.DEMO_AGENT_SEED_ACCOUNT_GRID_ID


class TestRunSeedWalletPersistence:
    def test_run_seed_restores_wallet_when_sync_complete_but_wallets_missing(
        self,
        tmp_path,
        monkeypatch,
    ):
        _install_master_reference_tentacles(monkeypatch, tmp_path)
        user_folder = tmp_path / "agent-seed-user"
        sqlite_path = user_folder / "tasks.db"
        agent_seed_seed_run.run_seed(
            user_folder=user_folder,
            clear=False,
            node_sqlite_file=sqlite_path,
            repo_root=tmp_path,
        )
        config_path = agent_seed_paths.user_config_file(user_folder)
        config_data = json.loads(config_path.read_text(encoding="utf-8"))
        community_block = config_data.setdefault(octobot_constants.CONFIG_COMMUNITY, {})
        community_block.pop(octobot_constants.CONFIG_COMMUNITY_WALLETS, None)
        config_path.write_text(json.dumps(config_data, indent=2) + "\n", encoding="utf-8")
        agent_seed_seed_run.run_seed(
            user_folder=user_folder,
            clear=False,
            node_sqlite_file=sqlite_path,
            repo_root=tmp_path,
        )
        _assert_demo_wallet_in_config(user_folder)

    def test_run_seed_second_run_keeps_persisted_wallet(self, tmp_path, monkeypatch):
        _install_master_reference_tentacles(monkeypatch, tmp_path)
        user_folder = tmp_path / "agent-seed-user"
        sqlite_path = user_folder / "tasks.db"
        agent_seed_seed_run.run_seed(
            user_folder=user_folder,
            clear=False,
            node_sqlite_file=sqlite_path,
            repo_root=tmp_path,
        )
        agent_seed_seed_run.run_seed(
            user_folder=user_folder,
            clear=False,
            node_sqlite_file=sqlite_path,
            repo_root=tmp_path,
        )
        _assert_demo_wallet_in_config(user_folder)
