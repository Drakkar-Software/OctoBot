#  Demo user config.json writer unit tests.

import json

import pytest

import octobot_commons.constants as commons_constants

import tools.agent_seed.operations.seed_octobot_config as agent_seed_seed_octobot_config
import tools.agent_seed.paths as agent_seed_paths


class TestWriteDemoUserConfigRaisesWhenMasterReferenceMissing:
    def test_raises_when_tentacles_config_json_missing(self, tmp_path, monkeypatch):
        master_root = tmp_path / "master-user"
        master_root.mkdir()
        monkeypatch.setenv(
            agent_seed_paths.OCTOBOT_AGENT_SEED_MASTER_USER_ROOT_ENV,
            str(master_root),
        )
        user_folder = tmp_path / "agent-seed-child"
        with pytest.raises(
            agent_seed_seed_octobot_config.AgentSeedMasterReferenceTentaclesMissingError,
        ):
            agent_seed_seed_octobot_config.write_demo_user_config(
                user_folder,
                tmp_path,
            )


class TestWriteDemoUserConfigWritesConfigJson:
    def test_writes_accepted_terms_and_readonly_paths(self, tmp_path, monkeypatch):
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
        user_folder = tmp_path / "agent-seed-child"
        agent_seed_seed_octobot_config.write_demo_user_config(user_folder, tmp_path)

        config_path = agent_seed_paths.user_config_file(user_folder)
        assert config_path.is_file()
        config_data = json.loads(config_path.read_text(encoding="utf-8"))
        assert config_data[commons_constants.CONFIG_ACCEPTED_TERMS] is True
        assert config_data[commons_constants.CONFIG_PROFILE] == commons_constants.DEFAULT_PROFILE
        assert config_data[commons_constants.CONFIG_READONLY_REFERENCE_TENTACLES_PATH] == str(
            reference_dir.resolve(),
        )
        assert config_data[commons_constants.CONFIG_READONLY_PROFILES_PATH] == str(
            agent_seed_paths.master_profiles_dir(master_root).resolve(),
        )
