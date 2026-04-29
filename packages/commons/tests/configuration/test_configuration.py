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
import octobot_commons.constants as constants
import octobot_commons.tests.test_config as test_config
from ..profiles import get_profiles_path

DEFAULT_CONFIG = os.path.join(test_config.TEST_CONFIG_FOLDER, f"default_{constants.CONFIG_FILE}")


def get_fake_config_path():
    return os.path.join(test_config.TEST_CONFIG_FOLDER, f"test_{constants.CONFIG_FILE}")


def get_profile_path():
    return test_config.TEST_CONFIG_FOLDER


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
    with mock.patch.object(default_config, "load_profiles", mock.Mock()) as load_profiles_mock, \
            mock.patch.object(default_config, "_get_selected_profile", mock.Mock()) as _select_mock, \
            mock.patch.object(default_config, "select_profile",
                              mock.Mock()) as select_profile_mock:
        default_config.read()
        assert isinstance(default_config._read_config, dict)
        assert isinstance(default_config.config, dict)
        load_profiles_mock.assert_called_once()
        _select_mock.assert_called_once()
        select_profile_mock.assert_called_once()


def test_select_profile(config):
    with mock.patch.object(config, "_generate_config_from_user_config_and_profile",
                              mock.Mock()) as _generate_config_from_user_config_and_profile_mock:
        config.profile_by_id = {
            "1": profiles.Profile("plop"),
            "hoo": profiles.Profile("ah")
        }
        config.profile_by_id["1"].name = "ploup"
        config.config = {}
        config.select_profile("1")
        assert config.config[constants.CONFIG_PROFILE] == "1"
        assert config.profile is config.profile_by_id["1"]


def test_remove_profile(config):
    config.profile = profiles.Profile(get_profile_path(), config.profile_schema_path)
    config.profile.read_config()
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
    config.profile = profiles.Profile(get_profile_path(), config.profile_schema_path)
    config.profile.read_config()
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
        config.profile = profiles.Profile(get_profile_path(), config.profile_schema_path)
        config.profile.read_config()
        with mock.patch.object(config, "_get_config_without_profile_elements",
                               mock.Mock(return_value=config._read_config)) as _filter_mock, \
                mock.patch.object(config.profile, "save_config", mock.Mock()) as _save_profile_mock:
            config.save()
            assert os.path.isfile(save_file)
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
    assert config._get_selected_profile() == "default"
    # no default
    config.profile_by_id.pop("default")
    config._read_config[constants.CONFIG_PROFILE] = "66"
    with pytest.raises(errors.NoProfileError):
        assert config._get_selected_profile() == "default"
    config._read_config.pop(constants.CONFIG_PROFILE)
    with pytest.raises(errors.NoProfileError):
        assert config._get_selected_profile() == "default"


def test_load_profiles(config):
    config.profiles_path = get_profiles_path()
    nb_profiles = 1
    config.load_profiles()
    assert len(config.profile_by_id) == nb_profiles
    loaded_profile = config.profile_by_id["default"]
    # reload profile, keep loaded ones
    config.load_profiles()
    assert config.profile_by_id["default"] is loaded_profile


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
