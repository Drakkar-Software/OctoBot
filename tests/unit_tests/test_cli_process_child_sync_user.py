#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import mock
import pytest

import octobot.constants as octobot_constants
import octobot_commons.errors as commons_errors
import octobot.cli as octobot_cli


class TestConfigureProfileSyncUserProcessChild:
    def test_raises_when_process_child_env_missing(self, monkeypatch):
        monkeypatch.setattr(octobot_constants, "PROCESS_BOT_SYNC_USER_ID", "")
        config = mock.Mock()
        with pytest.raises(commons_errors.ConfigError, match=octobot_constants.ENV_PROCESS_BOT_SYNC_USER_ID):
            octobot_cli._configure_profile_sync_user(
                config,
                None,
                is_process_child=True,
            )
        config.profile_storage.configure_sync_user.assert_not_called()
        config.profile_storage.bind_process_child_sync_user_id.assert_not_called()

    def test_binds_sync_user_from_env_for_process_child(self, monkeypatch):
        monkeypatch.setattr(octobot_constants, "PROCESS_BOT_SYNC_USER_ID", "child-user")
        config = mock.Mock()
        octobot_cli._configure_profile_sync_user(
            config,
            None,
            is_process_child=True,
        )
        config.profile_storage.bind_process_child_sync_user_id.assert_called_once_with("child-user")
        config.profile_storage.configure_sync_user.assert_not_called()

    def test_raises_when_bind_process_child_sync_user_id_fails(self, monkeypatch):
        monkeypatch.setattr(octobot_constants, "PROCESS_BOT_SYNC_USER_ID", "child-user")
        config = mock.Mock()
        config.profile_storage.bind_process_child_sync_user_id.side_effect = commons_errors.ProfileDataError(
            "Process child sync user id must be non-empty"
        )
        with pytest.raises(commons_errors.ProfileDataError, match="Process child sync user id must be non-empty"):
            octobot_cli._configure_profile_sync_user(
                config,
                None,
                is_process_child=True,
            )
        config.profile_storage.configure_sync_user.assert_not_called()


class TestActivateSavedProfileAfterSync:
    def test_activate_saved_profile_after_sync(self):
        config = mock.Mock()
        logger = mock.Mock()
        with mock.patch.object(octobot_cli.commands, "ensure_profile", mock.Mock()) as ensure_profile_mock, \
                mock.patch.object(octobot_cli, "_validate_config", mock.Mock()) as validate_config_mock:
            octobot_cli._activate_saved_profile_after_sync(config, logger)
        config.activate_saved_profile.assert_called_once_with()
        ensure_profile_mock.assert_called_once_with(config)
        validate_config_mock.assert_called_once_with(config, logger)


class TestCreateStartupConfigDeferredProfileActivation:
    @pytest.mark.parametrize("is_process_child", [False, True])
    def test_defers_profile_activation_until_after_sync_configure(self, is_process_child):
        logger = mock.Mock()
        config = mock.Mock()
        config.is_config_file_empty_or_missing.return_value = False
        with mock.patch.object(octobot_cli, "_create_configuration", mock.Mock(return_value=config)), \
                mock.patch.object(octobot_cli, "_read_config", mock.Mock()) as read_config_mock, \
                mock.patch.object(octobot_cli.commands, "ensure_profile", mock.Mock()) as ensure_profile_mock, \
                mock.patch.object(octobot_cli, "_validate_config", mock.Mock()) as validate_config_mock, \
                mock.patch.object(
                    octobot_cli.configuration_manager,
                    "get_distribution",
                    mock.Mock(return_value=octobot_cli.enums.OctoBotDistribution.DEFAULT),
                ):
            octobot_cli._create_startup_config(
                logger,
                "default.json",
                is_process_child=is_process_child,
            )
        read_config_mock.assert_called_once_with(config, logger, activate_profile=False)
        ensure_profile_mock.assert_not_called()
        validate_config_mock.assert_not_called()


class TestLoadOrCreateTentaclesProfileDataBacked:
    def test_uses_active_tentacles_setup_config_for_profile_data_backed(self):
        config = mock.Mock()
        setup_config = mock.Mock()
        config.get_active_tentacles_setup_config.return_value = setup_config
        community_auth = mock.Mock()
        logger = mock.Mock()
        with mock.patch.object(
            octobot_cli.user_root_folder_provider,
            "get_user_reference_tentacle_config_file_path",
            mock.Mock(return_value="/tmp/tentacles.json"),
        ), mock.patch("octobot.cli.os.path.isfile", mock.Mock(return_value=True)), mock.patch.object(
            octobot_cli.commands,
            "run_update_or_repair_tentacles_if_necessary",
            mock.Mock(),
        ) as repair_mock:
            octobot_cli._load_or_create_tentacles(community_auth, config, logger)
        config.get_active_tentacles_setup_config.assert_called_once_with()
        config.get_tentacles_config_path.assert_not_called()
        repair_mock.assert_called_once_with(community_auth, config, setup_config)


class TestConfigureProfileSyncUserNormalBot:
    def test_uses_auto_init_sync_client(self):
        community_auth = mock.Mock()
        community_auth.auto_init_sync_client.return_value = True
        community_auth.sync_user_id = "normal-user"
        config = mock.Mock()
        octobot_cli._configure_profile_sync_user(
            config,
            community_auth,
            is_process_child=False,
        )
        community_auth.auto_init_sync_client.assert_called_once_with()
        config.profile_storage.configure_sync_user.assert_called_once_with("normal-user")
        config.profile_storage.bind_process_child_sync_user_id.assert_not_called()

    def test_skips_when_auto_init_sync_client_fails(self):
        community_auth = mock.Mock()
        community_auth.auto_init_sync_client.return_value = False
        config = mock.Mock()
        octobot_cli._configure_profile_sync_user(
            config,
            community_auth,
            is_process_child=False,
        )
        config.profile_storage.configure_sync_user.assert_not_called()
