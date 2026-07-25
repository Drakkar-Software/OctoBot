#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import argparse
import contextlib
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


def _start_octobot_cli_args(**overrides):
    cli_args = {
        "version": False,
        "encrypter": False,
        "backtesting": False,
        "standalone": False,
        "backtesting_files": None,
        "whole_data_range": True,
        "enable_backtesting_timeout": True,
        "risk": None,
        "user_folder": None,
        "log_folder": None,
        "no_web": False,
        "no_logs": False,
        "no_telegram": False,
        "dump_state": None,
        "identifier": None,
        "strategy_optimizer": False,
        "reset_trading_history": False,
        "update": False,
        "simulate": False,
        "master": False,
        "consumer_only": False,
        "host": None,
        "port": None,
    }
    cli_args.update(overrides)
    return argparse.Namespace(**cli_args)


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
        args = _start_octobot_cli_args(backtesting=True)
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


class TestApplyNodeStartupSettings:
    def test_apply_node_startup_settings_disables_web_and_sets_distribution(self, monkeypatch):
        args = argparse.Namespace(
            master=False,
            consumer_only=False,
            no_web=False,
        )
        monkeypatch.setattr(octobot_cli.constants, "FORCED_DISTRIBUTION", None)
        octobot_cli._apply_node_startup_settings(args)
        assert args.no_web is True
        assert octobot_cli.constants.FORCED_DISTRIBUTION == octobot_enums.OctoBotDistribution.NODE.value


class TestApplyNodeCliSettings:
    def test_apply_node_cli_settings_enables_master_mode(self, monkeypatch):
        import octobot_node.config

        monkeypatch.setattr(octobot_node.config.settings, "IS_MASTER_MODE", False)
        monkeypatch.setattr(octobot_node.config.settings, "CONSUMER_ONLY", False)
        args = argparse.Namespace(
            master=True,
            consumer_only=True,
        )
        octobot_cli._apply_node_cli_settings(args)
        assert octobot_node.config.settings.IS_MASTER_MODE is True
        assert octobot_node.config.settings.CONSUMER_ONLY is True


class TestApplyStandaloneStartupSettings:
    def test_applies_default_distribution_and_disables_node_stack(self, monkeypatch):
        import octobot_node.config

        args = argparse.Namespace(no_web=False)
        monkeypatch.setattr(octobot_cli.constants, "FORCED_DISTRIBUTION", None)
        monkeypatch.setattr(octobot_node.config.settings, "IS_MASTER_MODE", True)
        monkeypatch.setattr(octobot_node.config.settings, "CONSUMER_ONLY", True)
        octobot_cli._apply_standalone_startup_settings()
        assert octobot_cli.constants.FORCED_DISTRIBUTION == octobot_enums.OctoBotDistribution.DEFAULT.value
        assert octobot_node.config.settings.IS_MASTER_MODE is False
        assert octobot_node.config.settings.CONSUMER_ONLY is False
        assert args.no_web is False


class TestValidateStartupModeArgs:
    def test_standalone_rejects_master_flag(self):
        args = argparse.Namespace(standalone=True, master=True, consumer_only=False)
        with pytest.raises(commons_errors.ConfigError, match="--standalone cannot be used"):
            octobot_cli._validate_startup_mode_args(args)

    def test_standalone_rejects_consumer_only_flag(self):
        args = argparse.Namespace(standalone=True, master=False, consumer_only=True)
        with pytest.raises(commons_errors.ConfigError, match="--standalone cannot be used"):
            octobot_cli._validate_startup_mode_args(args)

    def test_standalone_allows_no_node_flags(self):
        args = argparse.Namespace(standalone=True, master=False, consumer_only=False)
        octobot_cli._validate_startup_mode_args(args)


class TestApplyStartupDistributionMode:
    def test_default_path_uses_node_mode(self, monkeypatch):
        args = argparse.Namespace(
            standalone=False,
            backtesting=False,
            master=False,
            consumer_only=False,
            no_web=False,
        )
        with mock.patch.object(octobot_cli, "_apply_node_cli_settings", mock.Mock()) as node_cli_mock, \
                mock.patch.object(octobot_cli, "_apply_node_startup_settings", mock.Mock()) as node_mock, \
                mock.patch.object(octobot_cli, "_apply_standalone_startup_settings", mock.Mock()) as standalone_mock:
            octobot_cli._apply_startup_distribution_mode(args)
        node_cli_mock.assert_called_once_with(args)
        node_mock.assert_called_once_with(args)
        standalone_mock.assert_not_called()

    def test_standalone_flag_uses_trading_mode(self, monkeypatch):
        args = argparse.Namespace(
            standalone=True,
            backtesting=False,
            master=False,
            consumer_only=False,
            no_web=False,
        )
        with mock.patch.object(octobot_cli, "_apply_node_cli_settings", mock.Mock()) as node_cli_mock, \
                mock.patch.object(octobot_cli, "_apply_node_startup_settings", mock.Mock()) as node_mock, \
                mock.patch.object(octobot_cli, "_apply_standalone_startup_settings", mock.Mock()) as standalone_mock:
            octobot_cli._apply_startup_distribution_mode(args)
        standalone_mock.assert_called_once_with()
        node_cli_mock.assert_not_called()
        node_mock.assert_not_called()

    def test_backtesting_uses_trading_mode(self, monkeypatch):
        args = argparse.Namespace(
            standalone=False,
            backtesting=True,
            master=False,
            consumer_only=False,
            no_web=False,
        )
        with mock.patch.object(octobot_cli, "_apply_node_cli_settings", mock.Mock()) as node_cli_mock, \
                mock.patch.object(octobot_cli, "_apply_node_startup_settings", mock.Mock()) as node_mock, \
                mock.patch.object(octobot_cli, "_apply_standalone_startup_settings", mock.Mock()) as standalone_mock:
            octobot_cli._apply_startup_distribution_mode(args)
        standalone_mock.assert_called_once_with()
        node_cli_mock.assert_not_called()
        node_mock.assert_not_called()


class TestLogStartupDistributionMode:
    def _log_message(self, **overrides):
        logger = mock.Mock()
        cli_args = {
            "standalone": False,
            "backtesting": False,
            "master": False,
            "consumer_only": False,
        }
        cli_args.update(overrides)
        args = argparse.Namespace(**cli_args)
        octobot_cli._log_startup_distribution_mode(logger, args)
        logger.info.assert_called_once()
        return logger.info.call_args.args[0]

    def test_default_node_mode_message(self):
        message = self._log_message()
        assert "node mode" in message
        assert "start OctoBots" in message
        assert "selected strategy" in message
        assert "exchanges of your choice" in message

    def test_trading_mode_message(self):
        message = self._log_message(standalone=True)
        assert "trading mode" in message
        assert "selected profile" in message

    def test_backtesting_mode_message(self):
        message = self._log_message(backtesting=True)
        assert message == "Starting OctoBot in backtesting mode."

    def test_master_qualifier_on_node_path(self):
        message = self._log_message(master=True)
        assert "Master scheduler enabled." in message

    def test_consumer_only_qualifier_on_node_path(self):
        message = self._log_message(consumer_only=True)
        assert "Consumer-only worker mode enabled." in message


class TestDefaultCliMode:
    def _run_start_octobot_with_distribution_mock(self, args, distribution):
        logger = mock.Mock()
        config = mock.Mock()
        config.is_loaded.return_value = True
        octobot_node_mock = mock.Mock()
        octobot_mock = mock.Mock()
        patch_targets = (
            (octobot_cli, "_init_cli_overriden_folders", mock.Mock(return_value=({}, None))),
            (octobot_cli, "_assert_process_child_folder_overrides", mock.Mock()),
            (octobot_cli.octobot_logger, "init_logger", mock.Mock(return_value=logger)),
            (octobot_cli, "_log_environment", mock.Mock()),
            (octobot_cli.octobot_community, "init_sentry_tracker", mock.Mock()),
            (octobot_cli, "_create_startup_config", mock.Mock(return_value=(config, False))),
            (octobot_cli, "_log_terms_if_unaccepted", mock.Mock()),
            (octobot_cli, "_get_authenticated_community_if_possible", mock.AsyncMock(return_value=None)),
            (
                octobot_cli.asyncio,
                "run",
                lambda coro: octobot_cli.asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro),
            ),
            (octobot_cli, "_configure_profile_sync_user", mock.Mock()),
            (octobot_cli, "_activate_saved_profile_after_sync", mock.Mock()),
            (octobot_cli, "_load_or_create_tentacles", mock.Mock()),
            (octobot_cli, "_apply_forced_configs", mock.Mock()),
            (octobot_cli, "update_config_with_args", mock.Mock()),
            (octobot_cli.configuration_manager, "config_health_check", mock.Mock()),
            (octobot_cli.limits, "apply_config_limits", mock.Mock(return_value=[])),
            (
                octobot_cli.configuration_manager,
                "get_distribution",
                mock.Mock(return_value=distribution),
            ),
            (octobot_cli.octobot_node_class, "OctoBotNode", octobot_node_mock),
            (octobot_cli.octobot_class, "OctoBot", octobot_mock),
            (octobot_cli.commands, "set_global_bot_instance", mock.Mock()),
            (octobot_cli, "_disable_interface_from_param", mock.Mock()),
            (octobot_cli.commands, "run_bot", mock.Mock()),
        )
        with contextlib.ExitStack() as exit_stack:
            for target_module, attribute_name, patch_value in patch_targets:
                exit_stack.enter_context(
                    mock.patch.object(target_module, attribute_name, patch_value)
                )
            octobot_cli.start_octobot(args, "default.json")
        return octobot_node_mock, octobot_mock

    def test_default_start_uses_node_distribution(self, monkeypatch):
        monkeypatch.setattr(octobot_cli.constants, "FORCED_DISTRIBUTION", None)
        args = _start_octobot_cli_args()
        octobot_node_mock, octobot_mock = self._run_start_octobot_with_distribution_mock(
            args,
            octobot_cli.enums.OctoBotDistribution.NODE,
        )
        assert args.no_web is True
        assert octobot_cli.constants.FORCED_DISTRIBUTION == octobot_enums.OctoBotDistribution.NODE.value
        octobot_node_mock.assert_called_once()
        octobot_mock.assert_not_called()

    @pytest.mark.parametrize(
        "standalone_source,standalone_arg,force_env_standalone",
        [
            ("cli_flag", True, False),
            ("env_var", False, True),
        ],
    )
    def test_standalone_uses_default_distribution(
        self, monkeypatch, standalone_source, standalone_arg, force_env_standalone
    ):
        monkeypatch.setattr(octobot_cli.constants, "FORCED_DISTRIBUTION", None)
        monkeypatch.setattr(
            octobot_cli.constants, "FORCE_OCTOBOT_STANDALONE", force_env_standalone
        )
        args = _start_octobot_cli_args(standalone=standalone_arg)
        octobot_node_mock, octobot_mock = self._run_start_octobot_with_distribution_mock(
            args,
            octobot_cli.enums.OctoBotDistribution.DEFAULT,
        )
        assert args.standalone is True
        assert args.no_web is False
        assert octobot_cli.constants.FORCED_DISTRIBUTION == octobot_enums.OctoBotDistribution.DEFAULT.value
        octobot_mock.assert_called_once()
        octobot_node_mock.assert_not_called()

    def test_dump_state_without_standalone_stays_node_mode(self, monkeypatch):
        monkeypatch.setattr(octobot_cli.constants, "FORCED_DISTRIBUTION", None)
        args = _start_octobot_cli_args(
            dump_state="/tmp/process_bot_state.json",
            user_folder="user/automations/bot-1",
        )
        octobot_node_mock, octobot_mock = self._run_start_octobot_with_distribution_mock(
            args,
            octobot_cli.enums.OctoBotDistribution.NODE,
        )
        assert octobot_cli.constants.FORCED_DISTRIBUTION == octobot_enums.OctoBotDistribution.NODE.value
        octobot_node_mock.assert_called_once()
        octobot_mock.assert_not_called()


class TestOctobotParser:
    def test_parse_args_empty_uses_main_entry_point(self):
        parser = argparse.ArgumentParser(description="OctoBot")
        octobot_cli.octobot_parser(parser)
        args = parser.parse_args([])
        assert args.func is not None
        assert args.standalone is False
        assert args.master is False

    def test_parse_args_master_exposed_on_main_parser(self):
        parser = argparse.ArgumentParser(description="OctoBot")
        octobot_cli.octobot_parser(parser)
        args = parser.parse_args(["--master"])
        assert args.master is True

    def test_parse_args_node_subcommand_removed(self):
        parser = argparse.ArgumentParser(description="OctoBot")
        octobot_cli.octobot_parser(parser)
        with pytest.raises(SystemExit):
            parser.parse_args(["node"])

    def test_standalone_with_master_raises_config_error(self):
        parser = argparse.ArgumentParser(description="OctoBot")
        octobot_cli.octobot_parser(parser)
        args = parser.parse_args(["--standalone", "--master"])
        with pytest.raises(commons_errors.ConfigError, match="--standalone cannot be used"):
            octobot_cli._validate_startup_mode_args(args)
