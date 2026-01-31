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
import copy
import json
import shutil
import pytest
import mock
import octobot_commons.json_util
import octobot_commons.profiles as profiles
import octobot_commons.constants as constants
import octobot_commons.enums as enums
import octobot_commons.tests.test_config as test_config

from tests.profiles import profile, get_profile_path, get_profiles_path


def test_read_config(profile):
    save_ref = profile
    assert profile.read_config() is save_ref
    assert profile.profile_id == "default"
    assert profile.name == "default"
    assert profile.description == "OctoBot default profile."
    assert profile.avatar == "default_profile.png"
    assert profile.avatar_path == os.path.join(test_config.TEST_CONFIG_FOLDER, "default_profile.png")
    assert profile.origin_url == "https://default.url"
    assert len(profile.config) == 5
    assert isinstance(profile.config, dict)

    profile.path = ""
    with pytest.raises(FileNotFoundError):
        profile.read_config()


def test_save_config(profile):
    with mock.patch.object(profile, "validate_and_save_config", mock.Mock()) as validate_and_save_config_mock, \
            mock.patch.object(profile, "_filter_fill_elements", mock.Mock()) as _filter_fill_elements_mock:
        profile.config = {}
        # nothing to operate on
        global_config = {}
        profile.save_config(global_config)
        assert profile.config == {}
        validate_and_save_config_mock.assert_called_once()
        _filter_fill_elements_mock.assert_not_called()

        validate_and_save_config_mock.reset_mock()
        _filter_fill_elements_mock.reset_mock()
        profile.config = {}
        # things in config
        global_config = {
            profile.FULLY_MANAGED_ELEMENTS[0]: "plop",
            profile.FULLY_MANAGED_ELEMENTS[1]: "plip",
            "stuff": "plip"
        }
        profile.save_config(global_config)
        assert profile.config == {
            profile.FULLY_MANAGED_ELEMENTS[0]: "plop",
            profile.FULLY_MANAGED_ELEMENTS[1]: "plip"
        }
        validate_and_save_config_mock.assert_called_once()
        _filter_fill_elements_mock.assert_not_called()

        validate_and_save_config_mock.reset_mock()
        _filter_fill_elements_mock.reset_mock()
        profile.config = {}
        # things in config
        global_config = {
            profile.FULLY_MANAGED_ELEMENTS[0]: "plop",
            profile.FULLY_MANAGED_ELEMENTS[1]: "plip",
            "stuff": "plip",
            next(iter(profile.PARTIALLY_MANAGED_ELEMENTS)): {"ploup": True},
        }
        profile.save_config(global_config)
        assert profile.config == {
            profile.FULLY_MANAGED_ELEMENTS[0]: "plop",
            profile.FULLY_MANAGED_ELEMENTS[1]: "plip",
        }
        validate_and_save_config_mock.assert_called_once()
        _filter_fill_elements_mock.assert_called_once_with(global_config,
                                                           profile.config,
                                                           next(iter(profile.PARTIALLY_MANAGED_ELEMENTS)),
                                                           profile.PARTIALLY_MANAGED_ELEMENTS_ALLOWED_KEYS[
                                                               next(iter(profile.PARTIALLY_MANAGED_ELEMENTS))
                                                           ])


def test_validate(profile):
    with mock.patch.object(octobot_commons.json_util, "validate", mock.Mock()) as validate_mock:
        profile.validate()
        validate_mock.assert_called_once_with(profile.as_dict(), profile.schema_path)


def test_validate_and_save_config(profile):
    save_file = "profile_config.json"
    with mock.patch.object(profile, "validate", mock.Mock()) as validate_mock, \
            mock.patch.object(profile, "config_file", mock.Mock(return_value=save_file)), \
            mock.patch.object(profile, "save", mock.Mock()) as save_mock:
        profile.validate_and_save_config()
        validate_mock.assert_called_once()
        save_mock.assert_called_once()


def test_save(profile):
    save_file = "profile_config.json"
    if os.path.isfile(save_file):
        os.remove(save_file)
    try:
        profile.read_config()
        with mock.patch.object(profile, "config_file", mock.Mock(return_value=save_file)):
            profile.save()
            with open(save_file) as config_file:
                saved_profile = json.load(config_file)
            assert saved_profile == profile.as_dict()
    finally:
        if os.path.isfile(save_file):
            os.remove(save_file)


def test_duplicate(profile):
    with mock.patch.object(shutil, "copytree", mock.Mock()) as copytree_mock, \
            mock.patch.object(profiles.Profile, "save", mock.Mock()) as save_mock:
        profile.read_only = True
        profile.imported = True
        profile.origin_url = "hello"
        clone = profile.duplicate()
        assert clone.name == profile.name
        assert clone.description == profile.description
        assert clone.profile_id != profile.description
        assert clone.path != profile.path
        assert clone.profile_id in clone.path
        assert clone.profile_id is not None
        # duplicates are not read_only
        assert clone.read_only is False
        # duplicates are never imported nor have an origin url
        assert clone.imported is False
        assert clone.origin_url is None
        copytree_mock.assert_called_with(profile.path, clone.path)
        save_mock.assert_called_once()

        clone = profile.duplicate(name="123", description="456")
        assert clone.name == "123"
        assert clone.name != profile.name
        assert clone.description == "456"
        assert clone.description != profile.description


def test_as_dict(profile):
    assert profile.as_dict() == {
        constants.CONFIG_PROFILE: {
            constants.CONFIG_ID: None,
            constants.CONFIG_NAME: None,
            constants.CONFIG_DESCRIPTION: None,
            constants.CONFIG_AVATAR: None,
            constants.CONFIG_ORIGIN_URL: None,
            constants.CONFIG_READ_ONLY: False,
            constants.CONFIG_IMPORTED: False,
            constants.CONFIG_AUTO_UPDATE: False,
            constants.CONFIG_SLUG: None,
            constants.CONFIG_COMPLEXITY: enums.ProfileComplexity.MEDIUM.value,
            constants.CONFIG_RISK: enums.ProfileRisk.MODERATE.value,
            constants.CONFIG_TYPE: enums.ProfileType.LIVE.value,
            constants.CONFIG_EXTRA_BACKTESTING_TIME_FRAMES: [],
        },
        constants.PROFILE_CONFIG: {},
    }
    profile.read_config()
    # do not test read config
    profile.config = {"a": 1}
    profile.imported = True
    profile.complexity = enums.ProfileComplexity.DIFFICULT
    profile.risk = enums.ProfileRisk.LOW
    profile.auto_update = True
    profile.slug = "slugg"
    profile.profile_type = enums.ProfileType.BACKTESTING
    profile.extra_backtesting_time_frames = [enums.TimeFrames.ONE_DAY.value]
    assert profile.as_dict() == {
        constants.CONFIG_PROFILE: {
            constants.CONFIG_ID: "default",
            constants.CONFIG_NAME: "default",
            constants.CONFIG_DESCRIPTION: "OctoBot default profile.",
            constants.CONFIG_AVATAR: "default_profile.png",
            constants.CONFIG_ORIGIN_URL: "https://default.url",
            constants.CONFIG_READ_ONLY: False,
            constants.CONFIG_IMPORTED: True,
            constants.CONFIG_AUTO_UPDATE: True,
            constants.CONFIG_SLUG: "slugg",
            constants.CONFIG_COMPLEXITY: enums.ProfileComplexity.DIFFICULT.value,
            constants.CONFIG_RISK: enums.ProfileRisk.LOW.value,
            constants.CONFIG_TYPE: enums.ProfileType.BACKTESTING.value,
            constants.CONFIG_EXTRA_BACKTESTING_TIME_FRAMES: [enums.TimeFrames.ONE_DAY.value],
        },
        constants.PROFILE_CONFIG: {
            "a": 1
        },
    }


def test_config_file(profile):
    assert profile.config_file() == os.path.join(get_profile_path(), constants.PROFILE_CONFIG_FILE)


def test_merge_partially_managed_element_into_config(profile):
    with mock.patch.object(profiles.Profile, "_merge_partially_managed_element", mock.Mock()) as _merge_mock:
        config = {}
        profile.merge_partially_managed_element_into_config(config, constants.CONFIG_EXCHANGES)
        _merge_mock.assert_called_once_with(config,
                                            profile.config,
                                            constants.CONFIG_EXCHANGES,
                                            profile.PARTIALLY_MANAGED_ELEMENTS[constants.CONFIG_EXCHANGES])


def test_merge_partially_managed_element(profile):
    profile.read_config()
    element = next(iter(profile.PARTIALLY_MANAGED_ELEMENTS))
    template = profile.PARTIALLY_MANAGED_ELEMENTS[element]
    config = {
        constants.CONFIG_EXCHANGES: {
            "binance": {
                constants.CONFIG_EXCHANGE_KEY: constants.DEFAULT_API_KEY,
                constants.CONFIG_EXCHANGE_SECRET: constants.DEFAULT_API_SECRET,
            }
        }
    }
    # add constants.CONFIG_ENABLED_OPTION
    profile._merge_partially_managed_element(config, profile.config, element, template)
    assert config == {
        constants.CONFIG_EXCHANGES: {
            "binance": {
                constants.CONFIG_EXCHANGE_KEY: constants.DEFAULT_API_KEY,
                constants.CONFIG_EXCHANGE_SECRET: constants.DEFAULT_API_SECRET,
                constants.CONFIG_ENABLED_OPTION: True
            }
        }
    }
    config = {
        constants.CONFIG_EXCHANGES: {}
    }
    profile.config[constants.CONFIG_EXCHANGES]["binance"][constants.CONFIG_ENABLED_OPTION] = False
    # add whole exchange
    profile._merge_partially_managed_element(config, profile.config, element, template)
    assert config == {
        constants.CONFIG_EXCHANGES: {
            "binance": {
                constants.CONFIG_EXCHANGE_KEY: constants.DEFAULT_API_KEY,
                constants.CONFIG_EXCHANGE_SECRET: constants.DEFAULT_API_SECRET,
                constants.CONFIG_EXCHANGE_PASSWORD: constants.DEFAULT_API_PASSWORD,
                constants.CONFIG_EXCHANGE_TYPE: constants.DEFAULT_EXCHANGE_TYPE,
                constants.CONFIG_ENABLED_OPTION: False
            }
        }
    }
    config = {}
    # add whole exchange and exchanges key with 2 exchanges in profile
    profile.config[constants.CONFIG_EXCHANGES]["kucoin"] = {
        constants.CONFIG_ENABLED_OPTION: True,
        constants.CONFIG_EXCHANGE_TYPE: constants.CONFIG_EXCHANGE_FUTURE
    }
    profile._merge_partially_managed_element(config, profile.config, element, template)
    assert config == {
        constants.CONFIG_EXCHANGES: {
            "binance": {
                constants.CONFIG_EXCHANGE_KEY: constants.DEFAULT_API_KEY,
                constants.CONFIG_EXCHANGE_SECRET: constants.DEFAULT_API_SECRET,
                constants.CONFIG_EXCHANGE_PASSWORD: constants.DEFAULT_API_PASSWORD,
                constants.CONFIG_EXCHANGE_TYPE: constants.DEFAULT_EXCHANGE_TYPE,
                constants.CONFIG_ENABLED_OPTION: False
            },
            "kucoin": {
                constants.CONFIG_EXCHANGE_KEY: constants.DEFAULT_API_KEY,
                constants.CONFIG_EXCHANGE_SECRET: constants.DEFAULT_API_SECRET,
                constants.CONFIG_EXCHANGE_PASSWORD: constants.DEFAULT_API_PASSWORD,
                constants.CONFIG_EXCHANGE_TYPE: constants.CONFIG_EXCHANGE_FUTURE,
                constants.CONFIG_ENABLED_OPTION: True
            }
        }
    }
    config = {
        constants.CONFIG_EXCHANGES: {
            "binance": {
                constants.CONFIG_EXCHANGE_KEY: constants.DEFAULT_API_KEY,
                constants.CONFIG_EXCHANGE_SECRET: constants.DEFAULT_API_SECRET,
                constants.CONFIG_ENABLED_OPTION: True
            }
        }
    }
    # add constants.CONFIG_ENABLED_OPTION with 2 exchanges in profile, update constants.CONFIG_ENABLED_OPTION
    profile._merge_partially_managed_element(config, profile.config, element, template)
    assert config == {
        constants.CONFIG_EXCHANGES: {
            "binance": {
                constants.CONFIG_EXCHANGE_KEY: constants.DEFAULT_API_KEY,
                constants.CONFIG_EXCHANGE_SECRET: constants.DEFAULT_API_SECRET,
                constants.CONFIG_ENABLED_OPTION: False
            },
            "kucoin": {
                constants.CONFIG_EXCHANGE_KEY: constants.DEFAULT_API_KEY,
                constants.CONFIG_EXCHANGE_SECRET: constants.DEFAULT_API_SECRET,
                constants.CONFIG_EXCHANGE_PASSWORD: constants.DEFAULT_API_PASSWORD,
                constants.CONFIG_EXCHANGE_TYPE: constants.CONFIG_EXCHANGE_FUTURE,
                constants.CONFIG_ENABLED_OPTION: True
            }
        }
    }


def test_remove_deleted_elements(profile):
    profile.read_config()
    element = next(iter(profile.PARTIALLY_MANAGED_ELEMENTS))
    config = {
        constants.CONFIG_EXCHANGES: {
            "binance": {
                constants.CONFIG_EXCHANGE_KEY: constants.DEFAULT_API_KEY,
                constants.CONFIG_EXCHANGE_SECRET: constants.DEFAULT_API_SECRET,
                constants.CONFIG_ENABLED_OPTION: True,
            }
        }
    }
    before_sync_elements_count = len(profile.config[element])
    profile.remove_deleted_elements(config)
    # did not remove any element
    assert before_sync_elements_count == len(profile.config[element])
    profile.config[element]["plop"] = config[constants.CONFIG_EXCHANGES]["binance"]
    assert len(profile.config[element]) == before_sync_elements_count + 1
    profile.remove_deleted_elements(config)
    assert before_sync_elements_count == len(profile.config[element])
    # removed "plop" element
    assert list(profile.config[element]) == ["binance"]


def test_get_element_from_template(profile):
    element = next(iter(profile.PARTIALLY_MANAGED_ELEMENTS))
    template = profile.PARTIALLY_MANAGED_ELEMENTS[element]
    template_copy = copy.deepcopy(template)

    template_copy["plop"] = 1
    assert profile._get_element_from_template(template, {"plop": 1}) == template_copy
    assert "plop" not in template


def test_filter_fill_elements(profile):
    profile.read_config()
    config = {
        constants.CONFIG_EXCHANGES: {
            "binance": {
                constants.CONFIG_EXCHANGE_KEY: constants.DEFAULT_API_KEY,
                constants.CONFIG_EXCHANGE_SECRET: constants.DEFAULT_API_SECRET,
                constants.CONFIG_EXCHANGE_PASSWORD: constants.DEFAULT_API_PASSWORD,
                constants.CONFIG_ENABLED_OPTION: True
            }
        }
    }
    allowed_keys = [constants.CONFIG_ENABLED_OPTION, constants.CONFIG_EXCHANGE_PASSWORD]
    profile._filter_fill_elements(config, profile.config, constants.CONFIG_EXCHANGES, allowed_keys)
    assert profile.config[constants.CONFIG_EXCHANGES] == {
        "binance": {
            constants.CONFIG_EXCHANGE_PASSWORD: constants.DEFAULT_API_PASSWORD,
            constants.CONFIG_ENABLED_OPTION: True
        }
    }


def test_get_all_profiles():
    with mock.patch.object(profiles.Profile, "_load_profile", mock.Mock()) as _load_profile_mock:
        nb_files = len(os.listdir(get_profiles_path()))
        assert nb_files > 1
        profiles.Profile.get_all_profiles(get_profiles_path())
        assert _load_profile_mock.call_count == nb_files


def test_load_profile():
    schema_path = "schema_path"
    with mock.patch.object(profiles.Profile, "read_config", mock.Mock()) as read_config_mock:
        profile = profiles.Profile._load_profile(test_config.TEST_CONFIG_FOLDER, schema_path)
        assert profile.path == test_config.TEST_CONFIG_FOLDER
        assert profile.schema_path == schema_path
        read_config_mock.assert_called_once()


def test_get_existing_profiles_ids(profile):
    assert profiles.Profile.get_all_profiles_ids(get_profiles_path()) == ["default"]
    assert profiles.Profile.get_all_profiles_ids(get_profiles_path(), ignore=profile.path) == []
