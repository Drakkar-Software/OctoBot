#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.

import os

import octobot_commons.constants as constants
import octobot_commons.user_root_folder_provider as user_root_folder_provider


class TestUserRootFolderProviderReadonlyReferenceTentaclesPath:
    def setup_method(self):
        provider = user_root_folder_provider.UserRootFolderProvider.instance()
        provider.set_root("user/automations/test-bot")
        provider.configure_readonly_reference_tentacles_path("")

    def teardown_method(self):
        provider = user_root_folder_provider.UserRootFolderProvider.instance()
        provider.set_root(None)  # type: ignore[arg-type]
        provider.configure_readonly_reference_tentacles_path("")

    def test_uses_override_for_reference_directory(self, tmp_path):
        master_reference_path = tmp_path / "master" / constants.REFERENCE_TENTACLES_CONFIG_DIR
        master_reference_path.mkdir(parents=True)
        provider = user_root_folder_provider.UserRootFolderProvider.instance()
        provider.configure_readonly_reference_tentacles_path(str(master_reference_path))
        assert provider.get_user_reference_tentacle_config_path() == str(master_reference_path)

    def test_derives_reference_file_and_specific_paths_from_override(self, tmp_path):
        master_reference_path = tmp_path / "master" / constants.REFERENCE_TENTACLES_CONFIG_DIR
        master_reference_path.mkdir(parents=True)
        provider = user_root_folder_provider.UserRootFolderProvider.instance()
        provider.configure_readonly_reference_tentacles_path(str(master_reference_path))
        assert provider.get_user_reference_tentacle_config_file_path() == str(
            master_reference_path / constants.CONFIG_TENTACLES_FILE
        )
        assert provider.get_user_reference_tentacle_specific_config_path() == str(
            master_reference_path / constants.TENTACLES_SPECIFIC_CONFIG_FOLDER
        )

    def test_falls_back_to_user_root_when_override_unset(self):
        provider = user_root_folder_provider.UserRootFolderProvider.instance()
        provider.set_root("user/automations/child-bot")
        provider.configure_readonly_reference_tentacles_path("")
        assert provider.get_user_reference_tentacle_config_path() == os.path.join(
            "user/automations/child-bot",
            constants.REFERENCE_TENTACLES_CONFIG_DIR,
        )
