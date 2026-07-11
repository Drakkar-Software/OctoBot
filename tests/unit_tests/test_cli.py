#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import argparse
import os

import mock
import pytest

import octobot.constants as octobot_constants
import octobot.cli as octobot_cli
import octobot.enums as octobot_enums
import octobot_commons.configuration as configuration
import octobot_commons.constants as commons_constants
import octobot_commons.errors as commons_errors
import octobot_commons.json_util as json_util
import octobot_backtesting.constants as backtesting_constants
import octobot_services.constants as services_constants


def _write_minimal_profile(profile_folder):
    profile_file = {
        commons_constants.CONFIG_PROFILE: {
            commons_constants.CONFIG_ID: commons_constants.DEFAULT_PROFILE,
            commons_constants.CONFIG_NAME: commons_constants.DEFAULT_PROFILE,
        },
        commons_constants.PROFILE_CONFIG: {
            commons_constants.CONFIG_CRYPTO_CURRENCIES: {},
            commons_constants.CONFIG_EXCHANGES: {},
            commons_constants.CONFIG_TRADER: {commons_constants.CONFIG_ENABLED_OPTION: True},
            commons_constants.CONFIG_SIMULATOR: {
                commons_constants.CONFIG_ENABLED_OPTION: False,
                commons_constants.CONFIG_STARTING_PORTFOLIO: {},
                commons_constants.CONFIG_SIMULATOR_FEES: {},
            },
            commons_constants.CONFIG_TRADING: {
                commons_constants.CONFIG_TRADER_REFERENCE_MARKET: commons_constants.DEFAULT_REFERENCE_MARKET,
                commons_constants.CONFIG_TRADER_RISK: 0.5,
            },
            commons_constants.CONFIG_DISTRIBUTION: commons_constants.DEFAULT_DISTRIBUTION,
        },
    }
    json_util.safe_dump(
        profile_file,
        os.path.join(profile_folder, commons_constants.PROFILE_CONFIG_FILE),
    )


@pytest.fixture
def deferred_profile_config(tmp_path):
    profiles_path = tmp_path / commons_constants.PROFILES_FOLDER
    default_profile_path = profiles_path / commons_constants.DEFAULT_PROFILE
    default_profile_path.mkdir(parents=True)
    _write_minimal_profile(default_profile_path)

    config_file = tmp_path / commons_constants.CONFIG_FILE
    json_util.safe_dump(
        {
            backtesting_constants.CONFIG_BACKTESTING: {
                backtesting_constants.CONFIG_BACKTESTING_DATA_FILES: [],
            },
            commons_constants.CONFIG_EXCHANGES: {},
            commons_constants.CONFIG_PROFILE: commons_constants.DEFAULT_PROFILE,
            commons_constants.CONFIG_ACCEPTED_TERMS: True,
            commons_constants.CONFIG_DISTRIBUTION: commons_constants.DEFAULT_DISTRIBUTION,
        },
        str(config_file),
    )

    return configuration.Configuration(
        str(config_file),
        str(profiles_path),
        octobot_constants.CONFIG_FILE_SCHEMA,
        octobot_constants.PROFILE_FILE_SCHEMA,
    )


class TestUpdateConfigWithArgs:
    def test_requires_activated_profile_for_backtesting_flags(self, deferred_profile_config):
        config = deferred_profile_config
        config.read(activate_profile=False)
        assert commons_constants.CONFIG_TRADER not in config.config

        backtesting_args = argparse.Namespace(
            backtesting=True,
            backtesting_files=["test.data"],
            simulate=False,
            risk=None,
        )
        with pytest.raises(KeyError):
            octobot_cli.update_config_with_args(backtesting_args, config, mock.Mock())

        config.activate_saved_profile()
        octobot_cli.update_config_with_args(backtesting_args, config, mock.Mock())

        assert config.config[commons_constants.CONFIG_TRADER][commons_constants.CONFIG_ENABLED_OPTION] is False
        assert config.config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_ENABLED_OPTION] is True
        assert config.config[backtesting_constants.CONFIG_BACKTESTING][commons_constants.CONFIG_ENABLED_OPTION] is True
        assert config.config[backtesting_constants.CONFIG_BACKTESTING][
            backtesting_constants.CONFIG_BACKTESTING_DATA_FILES
        ] == ["test.data"]


class TestStartOctobot:
    def test_update_config_runs_after_profile_activation(self):
        logger = mock.Mock()
        config = mock.Mock()
        config.is_loaded.return_value = True
        args = argparse.Namespace(
            version=False,
            encrypter=False,
            backtesting=True,
            dump_state=None,
            user_folder=None,
            log_folder=None,
            whole_data_range=True,
            enable_backtesting_timeout=True,
            no_logs=False,
            identifier=None,
            update=False,
            strategy_optimizer=False,
            no_telegram=False,
            no_web=False,
            reset_trading_history=False,
        )
        call_order = []

        def track(name):
            def _tracked(*_args, **_kwargs):
                call_order.append(name)
            return _tracked

        with mock.patch.object(octobot_cli, "_init_cli_overriden_folders", mock.Mock(return_value=({}, None))), \
                mock.patch.object(octobot_cli, "_assert_process_child_folder_overrides", mock.Mock()), \
                mock.patch.object(octobot_cli.octobot_logger, "init_logger", mock.Mock(return_value=logger)), \
                mock.patch.object(octobot_cli, "_log_environment", mock.Mock()), \
                mock.patch.object(octobot_cli.octobot_community, "init_sentry_tracker", mock.Mock()), \
                mock.patch.object(
                    octobot_cli,
                    "_create_startup_config",
                    mock.Mock(return_value=(config, False)),
                ), \
                mock.patch.object(octobot_cli, "_log_terms_if_unaccepted", track("terms")), \
                mock.patch.object(octobot_cli, "_configure_profile_sync_user", track("sync_user")), \
                mock.patch.object(
                    octobot_cli,
                    "_activate_saved_profile_after_sync",
                    track("activate_profile"),
                ), \
                mock.patch.object(octobot_cli, "_load_or_create_tentacles", track("tentacles")), \
                mock.patch.object(octobot_cli, "_apply_forced_configs", track("forced_configs")), \
                mock.patch.object(octobot_cli, "update_config_with_args", track("update_config")), \
                mock.patch.object(
                    octobot_cli.configuration_manager,
                    "config_health_check",
                    track("health_check"),
                ), \
                mock.patch.object(octobot_cli.limits, "apply_config_limits", mock.Mock(return_value=[])), \
                mock.patch.object(
                    octobot_cli.configuration_manager,
                    "get_distribution",
                    mock.Mock(return_value=octobot_cli.enums.OctoBotDistribution.DEFAULT),
                ), \
                mock.patch.object(
                    octobot_cli.octobot_backtesting,
                    "OctoBotBacktestingFactory",
                    mock.Mock(),
                ), \
                mock.patch.object(octobot_cli.commands, "set_global_bot_instance", mock.Mock()), \
                mock.patch.object(octobot_cli.commands, "run_bot", mock.Mock()):
            octobot_cli.start_octobot(args, "default.json")

        activate_index = call_order.index("activate_profile")
        update_index = call_order.index("update_config")
        health_check_index = call_order.index("health_check")
        assert activate_index < update_index < health_check_index


class TestConfigureProfileSyncUser:
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


class TestCreateStartupConfig:
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


class TestLoadOrCreateTentacles:
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

    def test_process_child_with_readonly_reference_skips_repair(self):
        config = mock.Mock()
        setup_config = mock.Mock()
        config.config = {
            octobot_cli.common_constants.CONFIG_READONLY_REFERENCE_TENTACLES_PATH: "/master/reference",
        }
        config.get_active_tentacles_setup_config.return_value = setup_config
        community_auth = mock.Mock()
        logger = mock.Mock()
        with mock.patch.object(
            octobot_cli.user_root_folder_provider,
            "get_user_reference_tentacle_config_file_path",
            mock.Mock(return_value="/master/reference/tentacles_config.json"),
        ), mock.patch("octobot.cli.os.path.isfile", mock.Mock(return_value=True)), mock.patch.object(
            octobot_cli.tentacles_manager_api,
            "load_tentacles",
            mock.Mock(return_value=True),
        ) as load_tentacles_mock, mock.patch.object(
            config,
            "save",
            mock.Mock(),
        ) as save_mock, mock.patch.object(
            octobot_cli.commands,
            "run_update_or_repair_tentacles_if_necessary",
            mock.Mock(),
        ) as repair_mock:
            octobot_cli._load_or_create_tentacles(
                community_auth,
                config,
                logger,
                is_process_child=True,
            )
        load_tentacles_mock.assert_called_once_with(verbose=True)
        save_mock.assert_called_once()
        repair_mock.assert_not_called()


class TestStartNode:
    def test_start_node_disables_web_without_setting_node_api_env(self, monkeypatch):
        args = argparse.Namespace(
            master=False,
            consumer_only=False,
            host=None,
            port=None,
            no_web=False,
        )
        monkeypatch.delenv(services_constants.ENV_ENABLE_NODE_API, raising=False)
        monkeypatch.delenv(services_constants.ENV_NODE_API_ADDRESS, raising=False)
        monkeypatch.delenv(services_constants.ENV_NODE_API_PORT, raising=False)
        with mock.patch.object(octobot_cli, "start_octobot", mock.Mock()) as start_octobot_mock:
            octobot_cli.start_node(args, default_config_file="default.json")
        assert args.no_web is True
        assert services_constants.ENV_ENABLE_NODE_API not in os.environ
        assert services_constants.ENV_NODE_API_ADDRESS not in os.environ
        assert services_constants.ENV_NODE_API_PORT not in os.environ
        start_octobot_mock.assert_called_once_with(args, "default.json")
        assert octobot_cli.constants.FORCED_DISTRIBUTION == octobot_enums.OctoBotDistribution.NODE.value
