#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import os
import shutil
import json
import copy
import pytest
import mock
import octobot_commons.errors as errors
import octobot_commons.json_util
import octobot_commons.configuration as configuration
import octobot_commons.profiles as profiles
import octobot_commons.profiles.backends as profile_backends_module
import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.profile_types.ephemeral_profile as ephemeral_profile_module
import octobot_commons.user_root_folder_provider as user_root_folder_provider
import octobot_commons.constants as constants
import octobot_commons.tests.test_config as test_config
from ..profiles import get_profiles_path

DEFAULT_CONFIG = os.path.join(test_config.TEST_CONFIG_FOLDER, f"default_{constants.CONFIG_FILE}")


def get_fake_config_path():
    return os.path.join(test_config.TEST_CONFIG_FOLDER, f"test_{constants.CONFIG_FILE}")


def get_profile_path():
    return test_config.TEST_CONFIG_FOLDER


def _load_test_profile(config, profile_path=None):
    resolved_profile_path = profile_path or get_profile_path()
    loaded_profile = profile_backends_module.FilesystemProfileBackend().read_profile_from_path(
        resolved_profile_path
    )
    loaded_profile.bind_profile_storage(config.profile_storage)
    return loaded_profile


@pytest.fixture
def config():
    return configuration.Configuration(get_fake_config_path(), get_profile_path())


@pytest.fixture
def default_config():
    return configuration.Configuration(DEFAULT_CONFIG, get_profile_path())


def test_load_config():
    assert test_config.load_test_config()


def test_validate(config):
    config.profile = profiles.Profile(config.profiles_path)
    config._read_config = {}
    with mock.patch.object(octobot_commons.json_util, "validate", mock.Mock()) as validate_mock:
        config.validate()
        assert validate_mock.mock_calls[0].args == (config._read_config, config.config_schema_path)
        assert validate_mock.mock_calls[1].args == (config.profile.as_dict(), config.profile.schema_path)


def test_read(default_config):
    with mock.patch.object(
        default_config,
        "load_profiles_if_possible_and_necessary",
        mock.Mock(),
    ) as load_profiles_mock:
        default_config.read()
        assert isinstance(default_config._read_config, dict)
        assert isinstance(default_config.config, dict)
        load_profiles_mock.assert_called_once()
    with mock.patch.object(
        default_config,
        "load_profiles_if_possible_and_necessary",
        mock.Mock(),
    ) as load_profiles_mock:
        default_config.read(activate_profile=False)
        load_profiles_mock.assert_not_called()
        assert default_config.profile is None


def test_select_profile(config, tmp_path):
    with mock.patch.object(config, "_generate_config_from_user_config_and_profile",
                              mock.Mock()) as _generate_config_from_user_config_and_profile_mock:
        config.profile_by_id = {
            "1": profiles.Profile(str(tmp_path / "plop")),
            "hoo": profiles.Profile(str(tmp_path / "ah")),
        }
        config.profile_by_id["1"].name = "ploup"
        config.config = {}
        config.select_profile("1")
        assert config.config[constants.CONFIG_PROFILE] == "1"
        assert config.profile is config.profile_by_id["1"]


def test_remove_profile(config):
    config.profile = _load_test_profile(config)
    config.profile.read_only = True
    config.profile_by_id[config.profile.profile_id] = config.profile
    # id not in loaded profiles
    with pytest.raises(KeyError):
        config.remove_profile("random_id")
    # read only profile
    with pytest.raises(errors.ProfileRemovalError):
        config.remove_profile("default")
        assert os.path.isdir(config.profile.path)
    # valid profile removal
    other_profile = profiles.Profile("path", config.profile_schema_path)
    other_profile.profile_id = "profile_id"
    config.profile_by_id[other_profile.profile_id] = other_profile
    with mock.patch.object(shutil, "rmtree", mock.Mock()) as rmtree_mock:
        config.remove_profile("profile_id")
        rmtree_mock.assert_called_once_with("path")
        assert "profile_id" not in config.profile_by_id


def test_generate_config_from_user_config_and_profile(config):
    with open(DEFAULT_CONFIG) as config_file:
        config._read_config = json.load(config_file)
    config.profile = _load_test_profile(config)
    for key in config.profile.FULLY_MANAGED_ELEMENTS:
        assert key not in config._read_config
    for key in config.profile.PARTIALLY_MANAGED_ELEMENTS:
        assert key in config._read_config
    config.config = copy.deepcopy(config._read_config)
    config._generate_config_from_user_config_and_profile()
    for key in config.profile.FULLY_MANAGED_ELEMENTS:
        assert key in config.config
    for key in config.profile.PARTIALLY_MANAGED_ELEMENTS:
        assert key in config.config
    assert config.config is not config._read_config


def _align_config_with_profile(config):
    config.config = copy.deepcopy(config._read_config) if config._read_config else {}
    config._generate_config_from_user_config_and_profile()


class TestConfigurationProfileManagedElementsChanged:
    def test_returns_false_when_profile_unset(self, config):
        config.profile = None
        config.config = {"community": {"token": "value"}}
        assert config._profile_managed_elements_changed() is False

    def test_returns_false_when_only_community_changed(self, config):
        config.profile = _load_test_profile(config)
        with open(DEFAULT_CONFIG) as config_file:
            config._read_config = json.load(config_file)
        _align_config_with_profile(config)
        config.config["community"] = {"token": "updated"}
        assert config._profile_managed_elements_changed() is False

    def test_returns_true_when_fully_managed_element_changed(self, config):
        config.profile = _load_test_profile(config)
        with open(DEFAULT_CONFIG) as config_file:
            config._read_config = json.load(config_file)
        _align_config_with_profile(config)
        config.config[constants.CONFIG_CRYPTO_CURRENCIES] = {"Updated": {"pairs": ["ETH/USDT"]}}
        assert config._profile_managed_elements_changed() is True

    def test_returns_true_when_partial_exchange_allowed_key_changed(self, config):
        config.profile = _load_test_profile(config)
        with open(DEFAULT_CONFIG) as config_file:
            config._read_config = json.load(config_file)
        _align_config_with_profile(config)
        exchange_name = next(iter(config.config[constants.CONFIG_EXCHANGES]))
        config.config[constants.CONFIG_EXCHANGES][exchange_name][
            constants.CONFIG_ENABLED_OPTION
        ] = not config.profile.config[constants.CONFIG_EXCHANGES][exchange_name][
            constants.CONFIG_ENABLED_OPTION
        ]
        assert config._profile_managed_elements_changed() is True

    def test_returns_false_when_partial_exchange_non_allowed_key_differs(self, config):
        config.profile = _load_test_profile(config)
        with open(DEFAULT_CONFIG) as config_file:
            config._read_config = json.load(config_file)
        _align_config_with_profile(config)
        exchange_name = next(iter(config.config[constants.CONFIG_EXCHANGES]))
        config.config[constants.CONFIG_EXCHANGES][exchange_name][
            constants.CONFIG_EXCHANGE_KEY
        ] = "updated-api-key"
        assert config._profile_managed_elements_changed() is False


class TestConfigurationSaveSkipUnchangedProfile:
    def test_skips_profile_save_when_only_non_profile_config_changed(self, config):
        config.profile = _load_test_profile(config)
        with open(DEFAULT_CONFIG) as config_file:
            config._read_config = json.load(config_file)
        _align_config_with_profile(config)
        config.config["community"] = {"token": "updated"}
        with mock.patch(
            "octobot_commons.configuration.configuration.config_file_manager.dump",
            mock.Mock(),
        ), mock.patch.object(
            config,
            "_get_config_without_profile_elements",
            mock.Mock(return_value={}),
        ), mock.patch.object(
            config.profile,
            "save_config",
            mock.Mock(),
        ) as save_profile_config_mock:
            config.save()
        save_profile_config_mock.assert_not_called()

    def test_saves_profile_when_managed_elements_changed(self, config):
        config.profile = _load_test_profile(config)
        with open(DEFAULT_CONFIG) as config_file:
            config._read_config = json.load(config_file)
        _align_config_with_profile(config)
        config.config[constants.CONFIG_CRYPTO_CURRENCIES] = {"Updated": {"pairs": ["ETH/USDT"]}}
        with mock.patch(
            "octobot_commons.configuration.configuration.config_file_manager.dump",
            mock.Mock(),
        ), mock.patch.object(
            config,
            "_get_config_without_profile_elements",
            mock.Mock(return_value={}),
        ), mock.patch.object(
            config.profile,
            "save_config",
            mock.Mock(),
        ) as save_profile_config_mock:
            config.save()
        save_profile_config_mock.assert_called_once_with(config.config)

    def test_save_profile_true_forces_persist(self, config):
        config.profile = _load_test_profile(config)
        config.config = {"community": {"token": "updated"}}
        with mock.patch(
            "octobot_commons.configuration.configuration.config_file_manager.dump",
            mock.Mock(),
        ), mock.patch.object(
            config,
            "_get_config_without_profile_elements",
            mock.Mock(return_value={}),
        ), mock.patch.object(
            config.profile,
            "save_config",
            mock.Mock(),
        ) as save_profile_config_mock:
            config.save(save_profile=True)
        save_profile_config_mock.assert_called_once_with(config.config)

    def test_saves_profile_after_prior_save_when_crypto_mutated(self, config):
        config.profile = _load_test_profile(config)
        with open(DEFAULT_CONFIG) as config_file:
            config._read_config = json.load(config_file)
        _align_config_with_profile(config)
        config.profile.save_config(config.config)
        config.config[constants.CONFIG_CRYPTO_CURRENCIES]["Ethereum"] = {
            constants.CONFIG_CRYPTO_PAIRS: ["ETH/USDT"],
            constants.CONFIG_ENABLED_OPTION: True,
        }
        assert config._profile_managed_elements_changed() is True
        with mock.patch(
            "octobot_commons.configuration.configuration.config_file_manager.dump",
            mock.Mock(),
        ), mock.patch.object(
            config,
            "_get_config_without_profile_elements",
            mock.Mock(return_value={}),
        ), mock.patch.object(
            config.profile,
            "save_config",
            mock.Mock(),
        ) as save_profile_config_mock:
            config.save()
        save_profile_config_mock.assert_called_once_with(config.config)

    def test_sync_all_profiles_still_runs_when_active_profile_unchanged(self, config):
        config.profile = _load_test_profile(config)
        with open(DEFAULT_CONFIG) as config_file:
            config._read_config = json.load(config_file)
        _align_config_with_profile(config)
        config.config["community"] = {"token": "updated"}
        with mock.patch(
            "octobot_commons.configuration.configuration.config_file_manager.dump",
            mock.Mock(),
        ), mock.patch.object(
            config,
            "_get_config_without_profile_elements",
            mock.Mock(return_value={}),
        ), mock.patch.object(
            config.profile,
            "save_config",
            mock.Mock(),
        ), mock.patch.object(
            config,
            "_sync_other_profiles",
            mock.Mock(),
        ) as sync_other_profiles_mock:
            config.save(sync_all_profiles=True)
        sync_other_profiles_mock.assert_called_once_with()


def test_save(config):
    save_file = "saved_config.json"
    config.config_path = save_file
    if os.path.isfile(save_file):
        os.remove(save_file)
    # used as a restore file
    shutil.copy(DEFAULT_CONFIG, save_file)
    try:
        with open(DEFAULT_CONFIG) as config_file:
            config._read_config = json.load(config_file)
        # add profile data
        config.profile = _load_test_profile(config)
        with mock.patch.object(config, "_get_config_without_profile_elements",
                               mock.Mock(return_value=config._read_config)) as _filter_mock, \
                mock.patch.object(config.profile, "save_config", mock.Mock()) as save_profile_config_mock:
            config.save(save_profile=True)
            assert os.path.isfile(save_file)
            save_profile_config_mock.assert_called_once_with(config.config)
        with open(save_file) as config_file:
            saved_config = json.load(config_file)
        assert saved_config == config._read_config
    finally:
        if os.path.isfile(save_file):
            os.remove(save_file)


def test_is_loaded(config):
    assert not config.is_loaded()
    config.config = ""
    assert config.is_loaded()


def test_is_config_empty_or_missing(config):
    if os.path.isfile(get_fake_config_path()):
        os.remove(get_fake_config_path())

    assert config.is_config_file_empty_or_missing()
    shutil.copy(os.path.join(test_config.TEST_CONFIG_FOLDER, constants.DEFAULT_CONFIG_FILE), get_fake_config_path())
    assert not config.is_config_file_empty_or_missing()

    if os.path.isfile(get_fake_config_path()):
        os.remove(get_fake_config_path())


def test_get_tentacles_config_path(config):
    config.profile = profiles.Profile(get_profile_path(), config.profile_schema_path)
    assert config.get_tentacles_config_path() == os.path.join(test_config.TEST_CONFIG_FOLDER,
                                                              constants.CONFIG_TENTACLES_FILE)


class TestGetActiveTentaclesSetupConfigProfileDataBacked:
    def test_returns_in_memory_setup_without_filesystem_path(self, config):
        profile_data = profile_data_module.ProfileData()
        profile = ephemeral_profile_module.EphemeralProfile.from_profile_data(profile_data)
        profile.init_tentacles_setup_config()
        config.profile = profile
        setup_config = config.get_active_tentacles_setup_config()
        assert setup_config is profile.tentacles_setup_config
        assert setup_config.profile is profile

    def test_init_setup_when_missing(self, config):
        profile_data = profile_data_module.ProfileData()
        profile = ephemeral_profile_module.EphemeralProfile.from_profile_data(profile_data)
        config.profile = profile
        assert profile.tentacles_setup_config is None
        setup_config = config.get_active_tentacles_setup_config()
        assert setup_config is not None
        assert setup_config.profile is profile


class TestGetActiveTentaclesSetupConfigFilesystemBacked:
    def test_delegates_to_tentacles_manager_api(self, config):
        config.profile = profiles.Profile(get_profile_path(), config.profile_schema_path)
        expected_setup = mock.Mock()
        with mock.patch(
            "octobot_tentacles_manager.api.get_tentacles_setup_config",
            mock.Mock(return_value=expected_setup),
        ) as get_setup_mock:
            setup_config = config.get_active_tentacles_setup_config()
        get_setup_mock.assert_called_once_with(
            config.get_tentacles_config_path(),
            profile=config.profile,
        )
        assert setup_config is expected_setup


class TestGetTentaclesSetupConfigForPackageOperations:
    def test_profile_data_backed_uses_reference_config_file(self, config, tmp_path):
        profile_data = profile_data_module.ProfileData()
        profile = ephemeral_profile_module.EphemeralProfile.from_profile_data(profile_data)
        config.profile = profile
        reference_config_file = str(
            tmp_path / constants.REFERENCE_TENTACLES_CONFIG_DIR / constants.CONFIG_TENTACLES_FILE
        )
        expected_setup = mock.Mock()
        with mock.patch.object(
            config,
            "_get_master_reference_tentacles_config_file_path",
            mock.Mock(return_value=reference_config_file),
        ), mock.patch(
            "octobot_tentacles_manager.api.get_tentacles_setup_config",
            mock.Mock(return_value=expected_setup),
        ) as get_setup_mock:
            setup_config = config.get_tentacles_setup_config_for_package_operations()
        get_setup_mock.assert_called_once_with(reference_config_file)
        assert setup_config is expected_setup

    def test_filesystem_profile_uses_active_setup_config(self, config):
        config.profile = profiles.Profile(get_profile_path(), config.profile_schema_path)
        expected_setup = mock.Mock()
        with mock.patch.object(
            config,
            "get_active_tentacles_setup_config",
            mock.Mock(return_value=expected_setup),
        ) as active_setup_mock:
            setup_config = config.get_tentacles_setup_config_for_package_operations()
        active_setup_mock.assert_called_once_with()
        assert setup_config is expected_setup

    def test_master_reference_path_uses_sync_data_root_for_child_process(self, config, tmp_path, monkeypatch):
        master_user_root = tmp_path / "master" / "user"
        child_user_root = tmp_path / "child" / "user"
        master_user_root.mkdir(parents=True)
        child_user_root.mkdir(parents=True)
        monkeypatch.setenv(constants.ENV_OCTOBOT_SYNC_DATA_ROOT, str(master_user_root))
        provider = user_root_folder_provider.UserRootFolderProvider.instance()
        provider.set_root(str(child_user_root))
        config.config = {}
        expected_path = os.path.join(
            str(master_user_root),
            constants.REFERENCE_TENTACLES_CONFIG_DIR,
            constants.CONFIG_TENTACLES_FILE,
        )
        assert config._get_master_reference_tentacles_config_file_path() == expected_path


def test_get_metrics_enabled(config):
    config.config = {}
    assert config.get_metrics_enabled() is True
    config.config = {
        constants.CONFIG_METRICS: {}
    }
    assert config.get_metrics_enabled() is True
    config.config = {
        constants.CONFIG_METRICS: {
            constants.CONFIG_ENABLED_OPTION: True
        }
    }
    assert config.get_metrics_enabled() is True
    config.config = {
        constants.CONFIG_METRICS: {
            constants.CONFIG_ENABLED_OPTION: False
        }
    }
    assert config.get_metrics_enabled() is False


def test_accepted_terms(config):
    config.config = {}
    assert config.accepted_terms() is False
    config.config = {
        constants.CONFIG_ACCEPTED_TERMS: False
    }
    assert config.accepted_terms() is False
    config.config = {
        constants.CONFIG_ACCEPTED_TERMS: True
    }
    assert config.accepted_terms() is True


def test_update_config_fields(config):
    config.config = {}
    separator = "_"
    with mock.patch.object(config, "save", mock.Mock()) as save_mock:
        to_update_fields = {'crypto-currencies_01coin_pairs': ['dqd/dd']}
        config.update_config_fields(to_update_fields, False, separator)
        assert config.config == {
            "crypto-currencies": {
                "01coin": {
                    "pairs": ["dqd/dd"]
                }
            }
        }
        save_mock.assert_called_once()
        save_mock.reset_mock()
        to_update_fields = {
            'crypto-currencies_plop_p': ['dqd/dd', '111'],
            'rfzr_r_r': True
        }
        # no crypto-currencies update since in_backtesting = True
        config.update_config_fields(to_update_fields, True, separator)
        assert config.config == {
            "crypto-currencies": {
                "01coin": {
                    "pairs": ["dqd/dd"]
                }
            },
            "rfzr": {
                "r": {
                    "r": True
                }
            }
        }
        save_mock.assert_called_once()
        save_mock.reset_mock()
        to_update_fields = {
            'crypto-currencies_plop_p': ['dqd/dd', '111']
        }
        # change separator
        config.update_config_fields(to_update_fields, False, "-")
        assert config.config == {
            "crypto-currencies": {
                "01coin": {
                    "pairs": ["dqd/dd"]
                }
            },
            "crypto": {
                "currencies_plop_p": ['dqd/dd', '111']
            },
            "rfzr": {
                "r": {
                    "r": True
                }
            }
        }
        save_mock.assert_called_once()
        save_mock.reset_mock()
        # delete
        config.update_config_fields(to_update_fields, False, "-", delete=True)
        assert config.config == {
            "crypto-currencies": {
                "01coin": {
                    "pairs": ["dqd/dd"]
                }
            },
            "crypto": {},
            "rfzr": {
                "r": {
                    "r": True
                }
            }
        }
        save_mock.assert_called_once()


def test_get_selected_profile(config):
    config.profile_by_id = {
        "55": "123",
        "default": "456",
    }
    config._read_config = {}
    # missing profile key
    assert config._get_selected_profile() == "default"
    # normal case
    config._read_config[constants.CONFIG_PROFILE] = "55"
    assert config._get_selected_profile() == "55"
    # missing profile
    config._read_config[constants.CONFIG_PROFILE] = "66"
    with mock.patch.object(config.logger, "warning", mock.Mock()) as warning_mock:
        assert config._get_selected_profile() == "default"
        warning_mock.assert_called_once()
    # no default
    config.profile_by_id.pop("default")
    config._read_config[constants.CONFIG_PROFILE] = "66"
    with pytest.raises(errors.NoProfileError):
        assert config._get_selected_profile() == "default"
    config._read_config.pop(constants.CONFIG_PROFILE)
    with pytest.raises(errors.NoProfileError):
        assert config._get_selected_profile() == "default"


class TestConfigurationSave:
    def test_calls_profile_save_config_with_live_config(self, config):
        config.profile = _load_test_profile(config)
        with open(DEFAULT_CONFIG) as config_file:
            config._read_config = json.load(config_file)
        _align_config_with_profile(config)
        config.config[constants.CONFIG_CRYPTO_CURRENCIES] = {"Updated": {"pairs": ["ETH/USDT"]}}
        with mock.patch(
            "octobot_commons.configuration.configuration.config_file_manager.dump",
            mock.Mock(),
        ), mock.patch.object(
            config,
            "_get_config_without_profile_elements",
            mock.Mock(return_value={}),
        ), mock.patch.object(
            config.profile,
            "save_config",
            mock.Mock(),
        ) as save_profile_config_mock:
            config.save()
        save_profile_config_mock.assert_called_once_with(config.config)


class TestConfigurationDeferredProfileActivation:
    def test_activate_saved_profile_loads_and_selects(self, config):
        sync_profile_id = "sync-only-profile-id"
        config._read_config = {constants.CONFIG_PROFILE: sync_profile_id}
        config.config = copy.deepcopy(config._read_config)
        sync_profile = profiles.Profile("sync-path")
        sync_profile.profile_id = sync_profile_id
        sync_profile.name = "AAAA"
        with mock.patch.object(config, "load_profiles", mock.Mock()) as load_profiles_mock, \
                mock.patch.object(config, "_get_selected_profile", mock.Mock(return_value=sync_profile_id)) as get_selected_mock, \
                mock.patch.object(config, "select_profile", mock.Mock()) as select_profile_mock:
            config.activate_saved_profile()
            load_profiles_mock.assert_called_once()
            get_selected_mock.assert_called_once()
            select_profile_mock.assert_called_once_with(sync_profile_id)

    def test_read_without_activate_profile_leaves_profile_unset(self, default_config):
        with mock.patch.object(
            default_config,
            "load_profiles_if_possible_and_necessary",
            mock.Mock(),
        ) as load_mock:
            default_config.read(activate_profile=False)
            load_mock.assert_not_called()
            assert default_config.profile is None
            assert default_config.config is not None


def test_load_profiles(config):
    config.profiles_path = get_profiles_path()
    nb_profiles = 1
    config.load_profiles()
    assert len(config.profile_by_id) == nb_profiles
    loaded_profile = config.profile_by_id["default"]
    # reload profile, keep loaded ones
    config.load_profiles()
    assert config.profile_by_id["default"] is loaded_profile


class TestConfigurationRefreshSyncProfiles:
    def test_no_op_when_sync_unavailable(self, config):
        config.profile_by_id = {"sync-profile-id": mock.Mock()}
        with mock.patch.object(
            config.profile_storage,
            "is_sync_available",
            mock.Mock(return_value=False),
        ), mock.patch.object(
            config.profile_storage,
            "list_sync_profiles",
            mock.Mock(),
        ) as list_sync_profiles_mock:
            config.refresh_sync_profiles()
        list_sync_profiles_mock.assert_not_called()
        assert "sync-profile-id" in config.profile_by_id

    def test_adds_new_sync_profile(self, config):
        new_sync_profile = mock.Mock()
        new_sync_profile.is_sync_backed.return_value = True
        config.profile_by_id = {}
        config.profile = None
        with mock.patch.object(
            config.profile_storage,
            "is_sync_available",
            mock.Mock(return_value=True),
        ), mock.patch.object(
            config.profile_storage,
            "list_sync_profiles",
            mock.Mock(return_value={"new-sync-profile-id": new_sync_profile}),
        ):
            config.refresh_sync_profiles()
        assert config.profile_by_id["new-sync-profile-id"] is new_sync_profile

    def test_replaces_updated_sync_profile(self, config):
        stale_sync_profile = mock.Mock()
        stale_sync_profile.is_sync_backed.return_value = True
        refreshed_sync_profile = mock.Mock()
        refreshed_sync_profile.is_sync_backed.return_value = True
        config.profile_by_id = {"sync-profile-id": stale_sync_profile}
        config.profile = None
        with mock.patch.object(
            config.profile_storage,
            "is_sync_available",
            mock.Mock(return_value=True),
        ), mock.patch.object(
            config.profile_storage,
            "list_sync_profiles",
            mock.Mock(return_value={"sync-profile-id": refreshed_sync_profile}),
        ):
            config.refresh_sync_profiles()
        assert config.profile_by_id["sync-profile-id"] is refreshed_sync_profile

    def test_removes_deleted_sync_profile(self, config):
        removed_sync_profile = mock.Mock()
        removed_sync_profile.is_sync_backed.return_value = True
        config.profile_by_id = {"removed-sync-profile-id": removed_sync_profile}
        config.profile = None
        with mock.patch.object(
            config.profile_storage,
            "is_sync_available",
            mock.Mock(return_value=True),
        ), mock.patch.object(
            config.profile_storage,
            "list_sync_profiles",
            mock.Mock(return_value={}),
        ):
            config.refresh_sync_profiles()
        assert "removed-sync-profile-id" not in config.profile_by_id

    def test_leaves_filesystem_profiles_untouched(self, config):
        filesystem_profile = mock.Mock()
        filesystem_profile.is_sync_backed.return_value = False
        config.profile_by_id = {"filesystem-profile-id": filesystem_profile}
        config.profile = None
        with mock.patch.object(
            config.profile_storage,
            "is_sync_available",
            mock.Mock(return_value=True),
        ), mock.patch.object(
            config.profile_storage,
            "list_sync_profiles",
            mock.Mock(return_value={}),
        ):
            config.refresh_sync_profiles()
        assert config.profile_by_id["filesystem-profile-id"] is filesystem_profile

    def test_updates_active_profile_when_sync_backed(self, config):
        stale_active_profile = mock.Mock()
        stale_active_profile.is_sync_backed.return_value = True
        stale_active_profile.profile_id = "active-sync-profile-id"
        refreshed_active_profile = mock.Mock()
        refreshed_active_profile.is_sync_backed.return_value = True
        config.profile_by_id = {"active-sync-profile-id": stale_active_profile}
        config.profile = stale_active_profile
        with mock.patch.object(
            config.profile_storage,
            "is_sync_available",
            mock.Mock(return_value=True),
        ), mock.patch.object(
            config.profile_storage,
            "list_sync_profiles",
            mock.Mock(
                return_value={"active-sync-profile-id": refreshed_active_profile}
            ),
        ):
            config.refresh_sync_profiles()
        assert config.profile is refreshed_active_profile


def test_get_config_without_profile_elements(config):
    config.profile = profiles.Profile(config.profiles_path)
    config.config = {
        "plop": 1,
        "plip": True,
        profiles.Profile.FULLY_MANAGED_ELEMENTS[0]: "dd",
        next(iter(profiles.Profile.PARTIALLY_MANAGED_ELEMENTS)): "tt"
    }
    assert config._get_config_without_profile_elements() == {
        "plop": 1,
        "plip": True,
        next(iter(profiles.Profile.PARTIALLY_MANAGED_ELEMENTS)): "tt"
    }


class TestConfigurationReadonlyProfileOverlay:
    def _write_readonly_master_profile(
        self,
        profile_folder_path: str,
        profile_id: str,
    ) -> None:
        self._write_master_profile(profile_folder_path, profile_id, read_only=True)

    def _write_master_profile(
        self,
        profile_folder_path: str,
        profile_id: str,
        *,
        read_only: bool,
    ) -> None:
        os.makedirs(profile_folder_path, exist_ok=True)
        profile_file = {
            constants.CONFIG_PROFILE: {
                constants.CONFIG_ID: profile_id,
                constants.CONFIG_NAME: "Non-Trading",
                constants.CONFIG_READ_ONLY: read_only,
            },
            constants.PROFILE_CONFIG: {
                constants.CONFIG_CRYPTO_CURRENCIES: {},
                constants.CONFIG_EXCHANGES: {},
                constants.CONFIG_TRADER: {constants.CONFIG_ENABLED_OPTION: False},
                constants.CONFIG_SIMULATOR: {
                    constants.CONFIG_ENABLED_OPTION: True,
                    constants.CONFIG_STARTING_PORTFOLIO: {},
                    constants.CONFIG_SIMULATOR_FEES: {},
                },
                constants.CONFIG_TRADING: {
                    constants.CONFIG_TRADER_REFERENCE_MARKET: constants.DEFAULT_REFERENCE_MARKET,
                    constants.CONFIG_TRADER_RISK: 1,
                },
                constants.CONFIG_DISTRIBUTION: constants.DEFAULT_DISTRIBUTION,
            },
        }
        octobot_commons.json_util.safe_dump(
            profile_file,
            os.path.join(profile_folder_path, constants.PROFILE_CONFIG_FILE),
        )

    def _child_config_with_readonly_overlay(
        self,
        tmp_path,
    ) -> tuple[configuration.Configuration, str]:
        child_user_root = tmp_path / "child" / "user"
        child_profiles_path = child_user_root / constants.PROFILES_FOLDER
        master_profiles_path = tmp_path / "master" / constants.PROFILES_FOLDER
        self._write_readonly_master_profile(
            str(master_profiles_path / "non-trading"),
            constants.DEFAULT_PROFILE,
        )
        child_user_root.mkdir(parents=True)
        config_path = child_user_root / constants.CONFIG_FILE
        config_data = {
            constants.CONFIG_PROFILE: "non-trading",
            constants.CONFIG_READONLY_PROFILES_PATH: str(master_profiles_path),
            constants.CONFIG_ACCEPTED_TERMS: True,
        }
        with open(config_path, "w", encoding="utf-8") as config_file:
            json.dump(config_data, config_file)
        bot_config = configuration.Configuration(
            str(config_path),
            str(child_profiles_path),
        )
        return bot_config, str(master_profiles_path)

    def _child_config_with_editable_overlay(
        self,
        tmp_path,
    ) -> tuple[configuration.Configuration, str]:
        child_user_root = tmp_path / "child" / "user"
        child_profiles_path = child_user_root / constants.PROFILES_FOLDER
        master_profiles_path = tmp_path / "master" / constants.PROFILES_FOLDER
        self._write_master_profile(
            str(master_profiles_path / "editable-strategy"),
            "editable-strategy",
            read_only=False,
        )
        child_user_root.mkdir(parents=True)
        config_path = child_user_root / constants.CONFIG_FILE
        config_data = {
            constants.CONFIG_PROFILE: "editable-strategy",
            constants.CONFIG_READONLY_PROFILES_PATH: str(master_profiles_path),
            constants.CONFIG_ACCEPTED_TERMS: True,
        }
        with open(config_path, "w", encoding="utf-8") as config_file:
            json.dump(config_data, config_file)
        bot_config = configuration.Configuration(
            str(config_path),
            str(child_profiles_path),
        )
        return bot_config, str(master_profiles_path)

    def test_are_profiles_empty_or_missing_false_with_readonly_overlay(self, tmp_path):
        bot_config, _master_profiles_path = self._child_config_with_readonly_overlay(tmp_path)
        bot_config.read(should_raise=False, fill_missing_fields=True)
        assert bot_config.are_profiles_empty_or_missing() is False

    def test_read_loads_profile_from_readonly_overlay(self, tmp_path):
        bot_config, _master_profiles_path = self._child_config_with_readonly_overlay(tmp_path)
        bot_config.read(should_raise=False, fill_missing_fields=True)
        assert bot_config.profile is not None
        assert bot_config.profile.profile_id == constants.DEFAULT_PROFILE
        assert bot_config.config[constants.CONFIG_PROFILE] == constants.DEFAULT_PROFILE

    def test_save_persists_readonly_master_overlay_profile_to_child_path(self, tmp_path):
        bot_config, master_profiles_path = self._child_config_with_readonly_overlay(tmp_path)
        bot_config.read(should_raise=False, fill_missing_fields=True)
        bot_config.config[constants.CONFIG_TRADER] = {
            constants.CONFIG_ENABLED_OPTION: True,
        }
        bot_config.save(save_profile=True)
        child_overlay_file = octobot_commons.json_util.read_file(
            os.path.join(
                bot_config.profiles_path,
                constants.DEFAULT_PROFILE,
                constants.PROFILE_CONFIG_FILE,
            )
        )
        master_profile_file = octobot_commons.json_util.read_file(
            os.path.join(
                master_profiles_path,
                "non-trading",
                constants.PROFILE_CONFIG_FILE,
            )
        )
        assert (
            child_overlay_file[constants.PROFILE_CONFIG][constants.CONFIG_TRADER][
                constants.CONFIG_ENABLED_OPTION
            ]
            is True
        )
        assert (
            master_profile_file[constants.PROFILE_CONFIG][constants.CONFIG_TRADER][
                constants.CONFIG_ENABLED_OPTION
            ]
            is False
        )

    def test_save_persists_crypto_after_prior_profile_save(self, tmp_path):
        bot_config, _master_profiles_path = self._child_config_with_readonly_overlay(tmp_path)
        bot_config.read(should_raise=False, fill_missing_fields=True)
        bot_config.save()
        bot_config.config[constants.CONFIG_CRYPTO_CURRENCIES]["Ethereum"] = {
            constants.CONFIG_CRYPTO_PAIRS: ["ETH/USDT"],
            constants.CONFIG_ENABLED_OPTION: True,
        }
        bot_config.save()
        child_overlay_file = octobot_commons.json_util.read_file(
            os.path.join(
                bot_config.profiles_path,
                constants.DEFAULT_PROFILE,
                constants.PROFILE_CONFIG_FILE,
            )
        )
        assert (
            child_overlay_file[constants.PROFILE_CONFIG][constants.CONFIG_CRYPTO_CURRENCIES][
                "Ethereum"
            ][constants.CONFIG_CRYPTO_PAIRS]
            == ["ETH/USDT"]
        )

    def test_save_persists_editable_master_overlay_profile(self, tmp_path):
        bot_config, _master_profiles_path = self._child_config_with_editable_overlay(tmp_path)
        bot_config.read(should_raise=False, fill_missing_fields=True)
        with mock.patch.object(
            bot_config.profile_storage,
            "save_active_profile",
            mock.Mock(),
        ) as save_active_profile_mock:
            bot_config.save(save_profile=True)
        save_active_profile_mock.assert_called_once()

    def test_read_configures_readonly_reference_tentacles_path(self, tmp_path):
        child_user_root = tmp_path / "child" / "user"
        child_profiles_path = child_user_root / constants.PROFILES_FOLDER
        master_reference_path = tmp_path / "master" / constants.REFERENCE_TENTACLES_CONFIG_DIR
        master_reference_path.mkdir(parents=True)
        (master_reference_path / constants.CONFIG_TENTACLES_FILE).write_text("{}", encoding="utf-8")
        child_user_root.mkdir(parents=True)
        config_path = child_user_root / constants.CONFIG_FILE
        config_data = {
            constants.CONFIG_PROFILE: constants.DEFAULT_PROFILE,
            constants.CONFIG_READONLY_REFERENCE_TENTACLES_PATH: str(master_reference_path),
            constants.CONFIG_ACCEPTED_TERMS: True,
        }
        with open(config_path, "w", encoding="utf-8") as config_file:
            json.dump(config_data, config_file)
        provider = user_root_folder_provider.UserRootFolderProvider.instance()
        provider.configure_readonly_reference_tentacles_path("")
        bot_config = configuration.Configuration(
            str(config_path),
            str(child_profiles_path),
        )
        bot_config.read(should_raise=False, fill_missing_fields=True)
        assert provider.get_user_reference_tentacle_config_path() == str(master_reference_path)


class TestSyncOtherProfiles:
    def _profile_map(self, config, active_profile, *other_profiles):
        profile_by_id = {active_profile.profile_id: active_profile}
        for other_profile in other_profiles:
            profile_by_id[other_profile.profile_id] = other_profile
        config.profile = active_profile
        config.profile_by_id = profile_by_id
        return profile_by_id

    def test_skips_active_profile(self, config):
        active_profile = _load_test_profile(config)
        other_profile = _load_test_profile(config)
        self._profile_map(config, active_profile, other_profile)
        with mock.patch.object(
            active_profile,
            "remove_deleted_elements",
            mock.Mock(return_value=False),
        ) as active_remove_deleted_elements_mock, mock.patch.object(
            active_profile,
            "validate_and_save_config",
            mock.Mock(),
        ) as active_validate_and_save_config_mock, mock.patch.object(
            other_profile,
            "remove_deleted_elements",
            mock.Mock(return_value=False),
        ), mock.patch.object(
            config.profile_storage,
            "is_readonly_master_overlay_profile",
            mock.Mock(return_value=False),
        ):
            config._sync_other_profiles()
        active_remove_deleted_elements_mock.assert_not_called()
        active_validate_and_save_config_mock.assert_not_called()

    def test_skips_readonly_master_overlay_profile(self, config):
        active_profile = _load_test_profile(config)
        readonly_overlay_profile = _load_test_profile(config)
        writable_other_profile = _load_test_profile(config)
        self._profile_map(
            config,
            active_profile,
            readonly_overlay_profile,
            writable_other_profile,
        )
        with mock.patch.object(
            config.profile_storage,
            "is_readonly_master_overlay_profile",
            side_effect=lambda profile: profile is readonly_overlay_profile,
        ), mock.patch.object(
            readonly_overlay_profile,
            "remove_deleted_elements",
            mock.Mock(return_value=True),
        ) as readonly_remove_deleted_elements_mock, mock.patch.object(
            readonly_overlay_profile,
            "validate_and_save_config",
            mock.Mock(),
        ) as readonly_validate_and_save_config_mock, mock.patch.object(
            writable_other_profile,
            "remove_deleted_elements",
            mock.Mock(return_value=False),
        ) as writable_remove_deleted_elements_mock, mock.patch.object(
            writable_other_profile,
            "validate_and_save_config",
            mock.Mock(),
        ) as writable_validate_and_save_config_mock:
            config._sync_other_profiles()
        readonly_remove_deleted_elements_mock.assert_not_called()
        readonly_validate_and_save_config_mock.assert_not_called()
        writable_remove_deleted_elements_mock.assert_called_once_with(config.config)
        writable_validate_and_save_config_mock.assert_not_called()

    def test_skips_other_profile_when_exchanges_unchanged(self, config):
        active_profile = _load_test_profile(config)
        other_profile = _load_test_profile(config)
        self._profile_map(config, active_profile, other_profile)
        with mock.patch.object(
            config.profile_storage,
            "is_readonly_master_overlay_profile",
            mock.Mock(return_value=False),
        ), mock.patch.object(
            other_profile,
            "remove_deleted_elements",
            mock.Mock(return_value=False),
        ) as remove_deleted_elements_mock, mock.patch.object(
            other_profile,
            "validate_and_save_config",
            mock.Mock(),
        ) as validate_and_save_config_mock:
            config._sync_other_profiles()
        remove_deleted_elements_mock.assert_called_once_with(config.config)
        validate_and_save_config_mock.assert_not_called()

    def test_saves_other_profile_when_exchange_removed(self, config):
        active_profile = _load_test_profile(config)
        other_profile = _load_test_profile(config)
        self._profile_map(config, active_profile, other_profile)
        with mock.patch.object(
            config.profile_storage,
            "is_readonly_master_overlay_profile",
            mock.Mock(return_value=False),
        ), mock.patch.object(
            other_profile,
            "remove_deleted_elements",
            mock.Mock(return_value=True),
        ), mock.patch.object(
            other_profile,
            "validate_and_save_config",
            mock.Mock(),
        ) as validate_and_save_config_mock:
            config._sync_other_profiles()
        validate_and_save_config_mock.assert_called_once()

    def test_does_not_save_on_second_sync_when_exchanges_still_unchanged(self, config):
        active_profile = _load_test_profile(config)
        other_profile = _load_test_profile(config)
        self._profile_map(config, active_profile, other_profile)
        with mock.patch.object(
            config.profile_storage,
            "is_readonly_master_overlay_profile",
            mock.Mock(return_value=False),
        ), mock.patch.object(
            other_profile,
            "remove_deleted_elements",
            mock.Mock(side_effect=[False, False]),
        ), mock.patch.object(
            other_profile,
            "validate_and_save_config",
            mock.Mock(),
        ) as validate_and_save_config_mock:
            config._sync_other_profiles()
            config._sync_other_profiles()
        validate_and_save_config_mock.assert_not_called()

    def test_saves_only_on_second_sync_when_exchange_removed_on_second_call(self, config):
        active_profile = _load_test_profile(config)
        other_profile = _load_test_profile(config)
        self._profile_map(config, active_profile, other_profile)
        with mock.patch.object(
            config.profile_storage,
            "is_readonly_master_overlay_profile",
            mock.Mock(return_value=False),
        ), mock.patch.object(
            other_profile,
            "remove_deleted_elements",
            mock.Mock(side_effect=[False, True]),
        ), mock.patch.object(
            other_profile,
            "validate_and_save_config",
            mock.Mock(),
        ) as validate_and_save_config_mock:
            config._sync_other_profiles()
            config._sync_other_profiles()
        validate_and_save_config_mock.assert_called_once()

    def test_logs_exception_when_validate_and_save_raises(self, config):
        active_profile = _load_test_profile(config)
        other_profile = _load_test_profile(config)
        self._profile_map(config, active_profile, other_profile)
        with mock.patch.object(
            config.profile_storage,
            "is_readonly_master_overlay_profile",
            mock.Mock(return_value=False),
        ), mock.patch.object(
            other_profile,
            "remove_deleted_elements",
            mock.Mock(return_value=True),
        ), mock.patch.object(
            other_profile,
            "validate_and_save_config",
            mock.Mock(side_effect=errors.ProfileDataError("sync failed")),
        ), mock.patch.object(
            config.logger,
            "exception",
            mock.Mock(),
        ) as logger_exception_mock:
            config._sync_other_profiles()
        logger_exception_mock.assert_called_once()

