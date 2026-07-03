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
import copy
import pytest
import mock
import octobot_commons.json_util
import octobot_commons.profiles as profiles
import octobot_commons.constants as constants
import octobot_commons.enums as enums
import octobot_commons.errors as errors
import octobot_commons.tests.test_config as test_config

from tests.profiles import get_profile_path


def test_save_config(profile):
    with mock.patch.object(profile, "_save_through_profile_storage", mock.Mock()) as save_mock, \
            mock.patch.object(profile, "_filter_fill_elements", mock.Mock()) as _filter_fill_elements_mock:
        profile.config = {}
        global_config = {}
        profile.save_config(global_config)
        assert profile.config == {}
        save_mock.assert_called_once_with(global_config)
        _filter_fill_elements_mock.assert_not_called()

        save_mock.reset_mock()
        _filter_fill_elements_mock.reset_mock()
        profile.config = {}
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
        save_mock.assert_called_once_with(global_config)
        _filter_fill_elements_mock.assert_not_called()

        save_mock.reset_mock()
        _filter_fill_elements_mock.reset_mock()
        profile.config = {}
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
        save_mock.assert_called_once_with(global_config)
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
    with mock.patch.object(profile, "validate", mock.Mock()) as validate_mock, \
            mock.patch.object(profile, "_save_through_profile_storage", mock.Mock()) as save_mock:
        profile.validate_and_save_config()
        validate_mock.assert_called_once()
        save_mock.assert_called_once()


def test_save(profile):
    with mock.patch.object(profile, "validate_and_save_config", mock.Mock()) as validate_and_save_mock:
        profile.save()
        validate_and_save_mock.assert_called_once()


def test_save_requires_profile_storage():
    unbound_profile = profiles.Profile(get_profile_path())
    with pytest.raises(errors.ProfileDataError):
        unbound_profile.save()


def test_duplicate(profile):
    clone = mock.Mock()
    with mock.patch.object(
        profile.get_profile_storage(),
        "duplicate_profile",
        mock.Mock(return_value=clone),
    ) as duplicate_mock:
        profile.read_only = True
        profile.imported = True
        profile.origin_url = "hello"
        assert profile.duplicate() is clone
        duplicate_mock.assert_called_once_with(profile, name=None, description=None)

        profile.duplicate(name="123", description="456")
        duplicate_mock.assert_called_with(profile, name="123", description="456")


def test_as_dict(profile):
    empty_profile = profiles.Profile(get_profile_path())
    assert empty_profile.as_dict() == {
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
            constants.CONFIG_HIDDEN: False,
        },
        constants.PROFILE_CONFIG: {},
    }
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
            constants.CONFIG_HIDDEN: False,
        },
        constants.PROFILE_CONFIG: {
            "a": 1
        },
    }


def test_merge_partially_managed_element_into_config(profile):
    with mock.patch.object(profiles.Profile, "_merge_partially_managed_element", mock.Mock()) as _merge_mock:
        config = {}
        profile.merge_partially_managed_element_into_config(config, constants.CONFIG_EXCHANGES)
        _merge_mock.assert_called_once_with(config,
                                            profile.config,
                                            constants.CONFIG_EXCHANGES,
                                            profile.PARTIALLY_MANAGED_ELEMENTS[constants.CONFIG_EXCHANGES])


def test_merge_partially_managed_element(profile):
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
    assert before_sync_elements_count == len(profile.config[element])
    profile.config[element]["plop"] = config[constants.CONFIG_EXCHANGES]["binance"]
    assert len(profile.config[element]) == before_sync_elements_count + 1
    profile.remove_deleted_elements(config)
    assert before_sync_elements_count == len(profile.config[element])
    assert list(profile.config[element]) == ["binance"]


def test_get_element_from_template(profile):
    element = next(iter(profile.PARTIALLY_MANAGED_ELEMENTS))
    template = profile.PARTIALLY_MANAGED_ELEMENTS[element]
    template_copy = copy.deepcopy(template)

    template_copy["plop"] = 1
    assert profile._get_element_from_template(template, {"plop": 1}) == template_copy
    assert "plop" not in template


def test_filter_fill_elements(profile):
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
