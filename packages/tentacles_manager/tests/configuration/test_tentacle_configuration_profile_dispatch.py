#  Drakkar-Software OctoBot-Tentacles-Manager
#  Copyright (c) Drakkar-Software, All rights reserved.

import json
import os

import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_commons.errors as errors_module
import octobot_commons.json_util as json_util
import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.profile_storage as profile_storage_module
import octobot_commons.profiles.profile_types.ephemeral_profile as ephemeral_profile_module
import octobot_tentacles_manager.configuration.tentacle_configuration as tentacle_configuration
import octobot_tentacles_manager.configuration.tentacles_setup_configuration as tentacles_setup_configuration


class TestTentacleConfigurationProfileDispatch:
    def test_local_get_config_proxy_overrides_get_config(self):
        called = {}
        setup_config = tentacles_setup_configuration.TentaclesSetupConfiguration()

        def custom_get(tentacles_setup_config, klass):
            called["klass"] = klass
            return {"custom": True}

        with tentacle_configuration.local_get_config_proxy(custom_get):
            result = tentacle_configuration.get_config(setup_config, "TestKlass")
        assert result == {"custom": True}
        assert called["klass"] == "TestKlass"

    def test_sync_backed_profile_reads_config_from_profile_data(self):
        tentacle_klass = mock.Mock()
        tentacle_klass.get_name.return_value = "TestKlass"
        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(
                name="TestKlass", config={"from_profile_data": True}
            )
        ]
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = True
        profile.get_profile_data.return_value = profile_data
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        factory_config = {"required_strategies": []}
        with mock.patch.object(
            tentacle_configuration,
            "_get_config_from_file_system",
            mock.Mock(return_value=factory_config),
        ):
            result = tentacle_configuration.get_config(setup, tentacle_klass)
        assert result == {"required_strategies": [], "from_profile_data": True}

    def test_filesystem_profile_falls_back_to_file_system(self):
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = False
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        with mock.patch.object(
            tentacle_configuration,
            "_get_config_from_file_system",
            mock.Mock(return_value={"from_filesystem": True}),
        ) as get_from_filesystem_mock:
            result = tentacle_configuration.get_config(setup, "TestKlass")
        assert result == {"from_filesystem": True}
        get_from_filesystem_mock.assert_called_once_with(setup, "TestKlass")

    def test_sync_backed_update_config_does_not_write_to_filesystem(self):
        tentacle_klass = mock.Mock()
        tentacle_klass.get_name.return_value = "TestKlass"
        profile_data = profile_data_module.ProfileData()
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = True
        profile.get_profile_data.return_value = profile_data
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        with mock.patch.object(
            tentacle_configuration,
            "_update_config_from_file_system",
            mock.Mock(),
        ) as update_filesystem_mock:
            tentacle_configuration.update_config(
                setup, tentacle_klass, {"updated": True}
            )
        update_filesystem_mock.assert_not_called()
        assert profile_data.tentacles[0].name == "TestKlass"
        assert profile_data.tentacles[0].config == {"updated": True}

    def test_sync_backed_update_config_sets_activated_from_setup(self):
        tentacle_klass = mock.Mock()
        tentacle_klass.get_name.return_value = "GridTradingMode"
        profile_data = profile_data_module.ProfileData()
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = True
        profile.get_profile_data.return_value = profile_data
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        with mock.patch(
            "octobot_tentacles_manager.api.is_tentacle_activated_in_tentacles_setup_config",
            mock.Mock(return_value=False),
        ):
            tentacle_configuration.update_config(
                setup, tentacle_klass, {"flat_spread": 2}
            )
        assert profile_data.tentacles[0].name == "GridTradingMode"
        assert profile_data.tentacles[0].config == {"flat_spread": 2}
        assert profile_data.tentacles[0].activated is False

    def test_ephemeral_profile_reads_config_from_profile_data(self):
        tentacle_klass = type("TestKlass", (), {"get_name": staticmethod(lambda: "TestKlass")})()
        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(
                name="TestKlass", config={"from_ephemeral": True}
            )
        ]
        profile = ephemeral_profile_module.EphemeralProfile.from_profile_data(profile_data)
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        result = tentacle_configuration.get_config(setup, tentacle_klass)
        assert result == {"from_ephemeral": True}

    def test_ephemeral_profile_update_config_does_not_write_to_filesystem(self):
        tentacle_klass = mock.Mock()
        tentacle_klass.get_name.return_value = "TestKlass"
        profile_data = profile_data_module.ProfileData()
        profile = ephemeral_profile_module.EphemeralProfile.from_profile_data(profile_data)
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        with mock.patch.object(
            tentacle_configuration,
            "_update_config_from_file_system",
            mock.Mock(),
        ) as update_filesystem_mock:
            tentacle_configuration.update_config(
                setup, tentacle_klass, {"updated": True}
            )
        update_filesystem_mock.assert_not_called()
        assert profile_data.tentacles[0].name == "TestKlass"
        assert profile_data.tentacles[0].config == {"updated": True}

    def test_profile_not_persisted_in_setup_config_dict(self):
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = mock.Mock()
        setup.tentacles_activation = {"t": {"c": True}}
        persisted = setup._to_dict()
        assert "profile" not in persisted
        assert setup.profile is not None


class TestSyncBackedProfileConfigFilesystemFallback:
    def test_sync_backed_empty_config_falls_back_to_filesystem(self):
        tentacle_klass = mock.Mock()
        tentacle_klass.get_name.return_value = "TestKlass"
        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(name="TestKlass", config={}),
        ]
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = True
        profile.get_profile_data.return_value = profile_data
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        factory_config = {"required_evaluators": ["*"]}
        with mock.patch.object(
            tentacle_configuration,
            "_get_config_from_file_system",
            mock.Mock(return_value=factory_config),
        ) as get_from_filesystem_mock:
            result = tentacle_configuration.get_config(setup, tentacle_klass)
        assert result == factory_config
        get_from_filesystem_mock.assert_called_once_with(setup, tentacle_klass)

    def test_sync_backed_partial_inactive_config_merges_factory_defaults(self):
        tentacle_klass = mock.Mock()
        tentacle_klass.get_name.return_value = "GridTradingMode"
        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(
                name="GridTradingMode",
                config={"flat_spread": 2},
                activated=False,
            ),
        ]
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = True
        profile.get_profile_data.return_value = profile_data
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        factory_config = {"required_strategies": [], "flat_spread": 1}
        with mock.patch.object(
            tentacle_configuration,
            "_get_config_from_file_system",
            mock.Mock(return_value=factory_config),
        ):
            result = tentacle_configuration.get_config(setup, tentacle_klass)
        assert result["required_strategies"] == []
        assert result["flat_spread"] == 2

    def test_sync_backed_missing_tentacle_falls_back_to_filesystem(self):
        tentacle_klass = mock.Mock()
        tentacle_klass.get_name.return_value = "OtherKlass"
        profile_data = profile_data_module.ProfileData()
        profile_data.tentacles = [
            profile_data_module.TentaclesData(
                name="TestKlass", config={"from_profile_data": True}
            ),
        ]
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = True
        profile.get_profile_data.return_value = profile_data
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        factory_config = {"required_evaluators": ["TA"]}
        with mock.patch.object(
            tentacle_configuration,
            "_get_config_from_file_system",
            mock.Mock(return_value=factory_config),
        ) as get_from_filesystem_mock:
            result = tentacle_configuration.get_config(setup, tentacle_klass)
        assert result == factory_config
        get_from_filesystem_mock.assert_called_once_with(setup, tentacle_klass)


class TestUpdateConfigFromFileSystemReadOnlyOverlay:
    def test_writes_specific_config_to_child_overlay_path(self, tmp_path):
        child_profiles_path = tmp_path / "child" / commons_constants.PROFILES_FOLDER
        master_profiles_path = tmp_path / "master" / commons_constants.PROFILES_FOLDER
        profile_id = "readonly-strategy"
        master_profile_path = os.path.join(master_profiles_path, profile_id)
        os.makedirs(master_profile_path, exist_ok=True)
        profile_file = {
            commons_constants.CONFIG_PROFILE: {
                commons_constants.CONFIG_ID: profile_id,
                commons_constants.CONFIG_NAME: profile_id,
                commons_constants.CONFIG_READ_ONLY: True,
            },
            commons_constants.PROFILE_CONFIG: {
                commons_constants.CONFIG_CRYPTO_CURRENCIES: {},
                commons_constants.CONFIG_EXCHANGES: {},
                commons_constants.CONFIG_TRADER: {commons_constants.CONFIG_ENABLED_OPTION: False},
                commons_constants.CONFIG_SIMULATOR: {
                    commons_constants.CONFIG_ENABLED_OPTION: True,
                    commons_constants.CONFIG_STARTING_PORTFOLIO: {},
                    commons_constants.CONFIG_SIMULATOR_FEES: {},
                },
                commons_constants.CONFIG_TRADING: {
                    commons_constants.CONFIG_TRADER_REFERENCE_MARKET: commons_constants.DEFAULT_REFERENCE_MARKET,
                    commons_constants.CONFIG_TRADER_RISK: 1,
                },
                commons_constants.CONFIG_DISTRIBUTION: commons_constants.DEFAULT_DISTRIBUTION,
            },
        }
        json_util.safe_dump(
            profile_file,
            os.path.join(master_profile_path, commons_constants.PROFILE_CONFIG_FILE),
        )
        master_tentacles_config = {
            "tentacle_activation": {"Trading": {"DailyTradingMode": True}},
            "registered_tentacles": {},
            "installation_context": {},
        }
        json_util.safe_dump(
            master_tentacles_config,
            os.path.join(master_profile_path, commons_constants.CONFIG_TENTACLES_FILE),
        )
        child_profiles_path.mkdir(parents=True)
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
        profile = profile_storage.get_profile(profile_id)
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        setup.config_path = os.path.join(
            master_profile_path, commons_constants.CONFIG_TENTACLES_FILE
        )
        tentacle_klass = mock.Mock()
        tentacle_klass.get_name.return_value = "DailyTradingMode"
        child_specific_config_path = os.path.join(
            child_profiles_path, profile_id, "specific_config", "DailyTradingMode.json"
        )
        written_paths = []

        def write_config(config_path, config_data):
            written_paths.append(config_path)
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as config_file:
                json.dump(config_data, config_file)

        with mock.patch.object(
            tentacle_configuration,
            "_get_config_file_path",
            side_effect=lambda setup_config, klass, updated_config=False: (
                child_specific_config_path if updated_config else child_specific_config_path
            ),
        ), mock.patch.object(
            tentacle_configuration.configuration,
            "read_config",
            mock.Mock(return_value={}),
        ), mock.patch.object(
            tentacle_configuration.configuration,
            "write_config",
            write_config,
        ):
            tentacle_configuration.update_config(
                setup, tentacle_klass, {"amount": 1}, keep_existing=False
            )
        assert len(written_paths) == 1
        assert written_paths[0].startswith(
            os.path.join(child_profiles_path, profile_id, "specific_config")
        )


class TestTentaclesSetupConfigurationSaveConfigReadOnly:
    def test_blocks_activation_save_on_read_only_profile(self, tmp_path):
        child_profiles_path = tmp_path / "child" / commons_constants.PROFILES_FOLDER
        master_profiles_path = tmp_path / "master" / commons_constants.PROFILES_FOLDER
        profile_id = "readonly-strategy"
        master_profile_path = os.path.join(master_profiles_path, profile_id)
        os.makedirs(master_profile_path, exist_ok=True)
        profile_file = {
            commons_constants.CONFIG_PROFILE: {
                commons_constants.CONFIG_ID: profile_id,
                commons_constants.CONFIG_NAME: profile_id,
                commons_constants.CONFIG_READ_ONLY: True,
            },
            commons_constants.PROFILE_CONFIG: {
                commons_constants.CONFIG_CRYPTO_CURRENCIES: {},
                commons_constants.CONFIG_EXCHANGES: {},
                commons_constants.CONFIG_TRADER: {commons_constants.CONFIG_ENABLED_OPTION: False},
                commons_constants.CONFIG_SIMULATOR: {
                    commons_constants.CONFIG_ENABLED_OPTION: True,
                    commons_constants.CONFIG_STARTING_PORTFOLIO: {},
                    commons_constants.CONFIG_SIMULATOR_FEES: {},
                },
                commons_constants.CONFIG_TRADING: {
                    commons_constants.CONFIG_TRADER_REFERENCE_MARKET: commons_constants.DEFAULT_REFERENCE_MARKET,
                    commons_constants.CONFIG_TRADER_RISK: 1,
                },
                commons_constants.CONFIG_DISTRIBUTION: commons_constants.DEFAULT_DISTRIBUTION,
            },
        }
        json_util.safe_dump(
            profile_file,
            os.path.join(master_profile_path, commons_constants.PROFILE_CONFIG_FILE),
        )
        child_profiles_path.mkdir(parents=True)
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
        profile = profile_storage.get_profile(profile_id)
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        setup.config_path = os.path.join(
            master_profile_path, commons_constants.CONFIG_TENTACLES_FILE
        )
        with pytest.raises(errors_module.ProfileDataError, match="strategy is read-only"):
            setup.save_config(is_config_update=False)

    def test_skips_tentacles_setup_write_for_readonly_master_overlay(self, tmp_path):
        child_profiles_path = tmp_path / "child" / commons_constants.PROFILES_FOLDER
        master_profiles_path = tmp_path / "master" / commons_constants.PROFILES_FOLDER
        profile_id = "readonly-strategy"
        master_profile_path = os.path.join(master_profiles_path, profile_id)
        os.makedirs(master_profile_path, exist_ok=True)
        profile_file = {
            commons_constants.CONFIG_PROFILE: {
                commons_constants.CONFIG_ID: profile_id,
                commons_constants.CONFIG_NAME: profile_id,
                commons_constants.CONFIG_READ_ONLY: True,
            },
            commons_constants.PROFILE_CONFIG: {
                commons_constants.CONFIG_CRYPTO_CURRENCIES: {},
                commons_constants.CONFIG_EXCHANGES: {},
                commons_constants.CONFIG_TRADER: {commons_constants.CONFIG_ENABLED_OPTION: False},
                commons_constants.CONFIG_SIMULATOR: {
                    commons_constants.CONFIG_ENABLED_OPTION: True,
                    commons_constants.CONFIG_STARTING_PORTFOLIO: {},
                    commons_constants.CONFIG_SIMULATOR_FEES: {},
                },
                commons_constants.CONFIG_TRADING: {
                    commons_constants.CONFIG_TRADER_REFERENCE_MARKET: commons_constants.DEFAULT_REFERENCE_MARKET,
                    commons_constants.CONFIG_TRADER_RISK: 1,
                },
                commons_constants.CONFIG_DISTRIBUTION: commons_constants.DEFAULT_DISTRIBUTION,
            },
        }
        json_util.safe_dump(
            profile_file,
            os.path.join(master_profile_path, commons_constants.PROFILE_CONFIG_FILE),
        )
        child_profiles_path.mkdir(parents=True)
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
        profile = profile_storage.get_profile(profile_id)
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        setup.config_path = os.path.join(
            master_profile_path, commons_constants.CONFIG_TENTACLES_FILE
        )
        assert setup.save_config(is_config_update=True) is False


class TestUpdateActivationConfigurationReadOnly:
    def test_blocks_before_in_memory_mutation(self, tmp_path):
        child_profiles_path = tmp_path / "child" / commons_constants.PROFILES_FOLDER
        master_profiles_path = tmp_path / "master" / commons_constants.PROFILES_FOLDER
        profile_id = "readonly-strategy"
        master_profile_path = os.path.join(master_profiles_path, profile_id)
        os.makedirs(master_profile_path, exist_ok=True)
        profile_file = {
            commons_constants.CONFIG_PROFILE: {
                commons_constants.CONFIG_ID: profile_id,
                commons_constants.CONFIG_NAME: profile_id,
                commons_constants.CONFIG_READ_ONLY: True,
            },
            commons_constants.PROFILE_CONFIG: {
                commons_constants.CONFIG_CRYPTO_CURRENCIES: {},
                commons_constants.CONFIG_EXCHANGES: {},
                commons_constants.CONFIG_TRADER: {commons_constants.CONFIG_ENABLED_OPTION: False},
                commons_constants.CONFIG_SIMULATOR: {
                    commons_constants.CONFIG_ENABLED_OPTION: True,
                    commons_constants.CONFIG_STARTING_PORTFOLIO: {},
                    commons_constants.CONFIG_SIMULATOR_FEES: {},
                },
                commons_constants.CONFIG_TRADING: {
                    commons_constants.CONFIG_TRADER_REFERENCE_MARKET: commons_constants.DEFAULT_REFERENCE_MARKET,
                    commons_constants.CONFIG_TRADER_RISK: 1,
                },
                commons_constants.CONFIG_DISTRIBUTION: commons_constants.DEFAULT_DISTRIBUTION,
            },
        }
        json_util.safe_dump(
            profile_file,
            os.path.join(master_profile_path, commons_constants.PROFILE_CONFIG_FILE),
        )
        child_profiles_path.mkdir(parents=True)
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
        profile = profile_storage.get_profile(profile_id)
        setup = tentacles_setup_configuration.TentaclesSetupConfiguration()
        setup.profile = profile
        setup.tentacles_activation = {"Trading": {"DailyTradingMode": True}}
        original_activation = setup.tentacles_activation["Trading"]["DailyTradingMode"]
        with pytest.raises(errors_module.ProfileDataError, match="strategy is read-only"):
            setup.update_activation_configuration(
                {"DailyTradingMode": False}, False, False
            )
        assert setup.tentacles_activation["Trading"]["DailyTradingMode"] is original_activation
