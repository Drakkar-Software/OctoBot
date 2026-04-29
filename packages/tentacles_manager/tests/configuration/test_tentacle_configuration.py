#  Drakkar-Software OctoBot-Tentacles-Manager
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
from os.path import isfile
from shutil import rmtree
from unittest import mock

import aiohttp
import pytest
from os import path

import octobot_tentacles_manager.configuration as configuration
import octobot_tentacles_manager.api as api
from octobot_tentacles_manager.configuration.tentacle_configuration import get_config, update_config, \
    factory_reset_config, get_config_schema_path
import octobot_tentacles_manager.util as util
import octobot_tentacles_manager.constants as constants
from octobot_tentacles_manager.loaders.tentacle_loading import reload_tentacle_by_tentacle_class

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_get_config():
    _cleanup()
    async with aiohttp.ClientSession() as session:
        await api.install_all_tentacles(_tentacles_local_path(), aiohttp_session=session)
    from tentacles.Evaluator.RealTime import InstantFluctuationsEvaluator
    setup_config = configuration.TentaclesSetupConfiguration()
    assert get_config(setup_config, InstantFluctuationsEvaluator) == {
        "price_difference_threshold_percent": 1,
        "volume_difference_threshold_percent": 400
    }
    from tentacles.Services import RedditService
    assert get_config(setup_config, RedditService) == {}
    _cleanup()


async def test_update_config():
    async with aiohttp.ClientSession() as session:
        await api.install_all_tentacles(_tentacles_local_path(), aiohttp_session=session)
    from tentacles.Evaluator.RealTime import InstantFluctuationsEvaluator
    setup_config = configuration.TentaclesSetupConfiguration()
    config_update = {
        "price_difference_threshold_percent": 2,
        "plop": 42
    }
    update_config(setup_config, InstantFluctuationsEvaluator, config_update)
    assert get_config(setup_config, InstantFluctuationsEvaluator) == {
        "price_difference_threshold_percent": 2,
        "volume_difference_threshold_percent": 400,
        "plop": 42
    }
    _cleanup()


async def test_keep_existing_update_config():
    async with aiohttp.ClientSession() as session:
        await api.install_all_tentacles(_tentacles_local_path(), aiohttp_session=session)
    from tentacles.Evaluator.RealTime import InstantFluctuationsEvaluator
    setup_config = configuration.TentaclesSetupConfiguration()
    # init nested config
    config_update = {
        "price_difference_threshold_percent": 2,
        "plop": 42,
        "nested_thing": {
            "price_difference_threshold_percent": 2,
            "plop": 42,
            "another_nested_thing": {
                "price_difference_threshold_percent": 2,
                "plop": 42
            }
        }
    }
    update_config(setup_config, InstantFluctuationsEvaluator, config_update)
    assert get_config(setup_config, InstantFluctuationsEvaluator) == {
        "price_difference_threshold_percent": 2,
        "volume_difference_threshold_percent": 400,
        "plop": 42,
        "nested_thing": {
            "price_difference_threshold_percent": 2,
            "plop": 42,
            "another_nested_thing": {
                "price_difference_threshold_percent": 2,
                "plop": 42
            }
        }
    }
    
    # test keep existing option
    config_update = {
        "nested_thing": {
            "new_other_nested_thing": {
                "price_difference_threshold_percent": 2,
                "plop": 42
            }
        }
    }
    update_config(setup_config, InstantFluctuationsEvaluator, config_update, keep_existing=True)
    assert get_config(setup_config, InstantFluctuationsEvaluator) == {
        "price_difference_threshold_percent": 2,
        "volume_difference_threshold_percent": 400,
        "plop": 42,
        "nested_thing": {
            "price_difference_threshold_percent": 2,
            "plop": 42,
            "another_nested_thing": {
                "price_difference_threshold_percent": 2,
                "plop": 42
            },
            "new_other_nested_thing": {
                "price_difference_threshold_percent": 2,
                "plop": 42
            }
        }
    }
    # test deep nested with keep existing option
    config_update = {
        "nested_thing": {
            "new_other_nested_thing": {
                "i am very deep": {
                    "price_difference_threshold_percent": 2,
                    "plop": 42
                }
            }
        }
    }
    update_config(setup_config, InstantFluctuationsEvaluator, config_update, keep_existing=True)
    assert get_config(setup_config, InstantFluctuationsEvaluator) == {
        "price_difference_threshold_percent": 2,
        "volume_difference_threshold_percent": 400,
        "plop": 42,
        "nested_thing": {
            "price_difference_threshold_percent": 2,
            "plop": 42,
            "another_nested_thing": {
                "price_difference_threshold_percent": 2,
                "plop": 42
            },
            "new_other_nested_thing": {
                "price_difference_threshold_percent": 2,
                "plop": 42,
                "i am very deep": {
                    "price_difference_threshold_percent": 2,
                    "plop": 42
                }
            }
        }
    }
    # try adding to deep config
    config_update = {
        "nested_thing": {
            "new_other_nested_thing": {
                "i am also deep": {
                    "price_difference_threshold_percent": 2,
                    "plop": 42
                }
            }
        }
    }
    update_config(setup_config, InstantFluctuationsEvaluator, config_update, keep_existing=True)
    assert get_config(setup_config, InstantFluctuationsEvaluator) == {
        "price_difference_threshold_percent": 2,
        "volume_difference_threshold_percent": 400,
        "plop": 42,
        "nested_thing": {
            "price_difference_threshold_percent": 2,
            "plop": 42,
            "another_nested_thing": {
                "price_difference_threshold_percent": 2,
                "plop": 42
            },
            "new_other_nested_thing": {
                "price_difference_threshold_percent": 2,
                "plop": 42,
                "i am very deep": {
                    "price_difference_threshold_percent": 2,
                    "plop": 42
                },
                "i am also deep": {
                    "price_difference_threshold_percent": 2,
                    "plop": 42
                }
            }
        }
    }
    
    # test keep existing false
    config_update = {
        "nested_thing": {
            "i am alone here": {
                "price_difference_threshold_percent": 42,
            }
        }
    }
    update_config(setup_config, InstantFluctuationsEvaluator, config_update, keep_existing=False)
    assert get_config(setup_config, InstantFluctuationsEvaluator) == {
        "price_difference_threshold_percent": 2,
        "volume_difference_threshold_percent": 400,
        "plop": 42,
        "nested_thing": {
            "i am alone here": {
                "price_difference_threshold_percent": 42,
            }
        }
    }
    _cleanup()


async def test_factory_reset_config():
    async with aiohttp.ClientSession() as session:
        await api.install_all_tentacles(_tentacles_local_path(), aiohttp_session=session)
    from tentacles.Evaluator.RealTime import InstantFluctuationsEvaluator
    setup_config = configuration.TentaclesSetupConfiguration()
    config_update = {
        "price_difference_threshold_percent": 2,
        "plop": 42
    }
    update_config(setup_config, InstantFluctuationsEvaluator, config_update)
    reload_tentacle_by_tentacle_class()
    factory_reset_config(setup_config, InstantFluctuationsEvaluator)
    assert get_config(setup_config, InstantFluctuationsEvaluator) == {
        "price_difference_threshold_percent": 1,
        "volume_difference_threshold_percent": 400
    }
    _cleanup()


async def test_fill_tentacle_config():
    async with aiohttp.ClientSession() as session:
        await api.install_all_tentacles(_tentacles_local_path(), aiohttp_session=session)

    setup_config = configuration.TentaclesSetupConfiguration()
    available_tentacle = util.load_tentacle_with_metadata(constants.TENTACLES_PATH)
    with mock.patch.object(setup_config, "_get_installation_context_bot_version", mock.Mock()) as bot_version_mock:
        bot_version_mock.return_value = "1.0.5"
        setup_config.fill_tentacle_config(available_tentacle, constants.TENTACLE_CONFIG_FILE_NAME)
        assert setup_config.installation_context == {
            constants.TENTACLE_INSTALLATION_CONTEXT_OCTOBOT_VERSION: "1.0.5"
        }

    setup_config = configuration.TentaclesSetupConfiguration()
    setup_config.fill_tentacle_config(available_tentacle, constants.TENTACLE_CONFIG_FILE_NAME)
    assert setup_config.installation_context == {
        constants.TENTACLE_INSTALLATION_CONTEXT_OCTOBOT_VERSION:
            constants.TENTACLE_INSTALLATION_CONTEXT_OCTOBOT_VERSION_UNKNOWN
    }

    assert not api.are_tentacles_up_to_date(setup_config,
                                            constants.TENTACLE_INSTALLATION_CONTEXT_OCTOBOT_VERSION_UNKNOWN)
    assert not api.are_tentacles_up_to_date(setup_config, '1.0.0')
    setup_config.installation_context[constants.TENTACLE_INSTALLATION_CONTEXT_OCTOBOT_VERSION] = '2.0.0'
    assert not api.are_tentacles_up_to_date(setup_config, '2.1.0')
    assert api.are_tentacles_up_to_date(setup_config, '2.0.0')
    assert api.are_tentacles_up_to_date(setup_config, '2.0.0b1')
    _cleanup()


async def test_get_config_schema_path():
    async with aiohttp.ClientSession() as session:
        await api.install_all_tentacles(_tentacles_local_path(), aiohttp_session=session)
    from tentacles.Evaluator.RealTime import InstantFluctuationsEvaluator
    assert isfile(get_config_schema_path(InstantFluctuationsEvaluator))
    _cleanup()


def _tentacles_local_path():
    return path.join("tests", "static", "tentacles.zip")


def _cleanup():
    if path.exists(constants.TENTACLES_PATH):
        rmtree(constants.TENTACLES_PATH)
    if path.exists(constants.TENTACLE_CONFIG_FILE_NAME):
        os.remove(constants.TENTACLE_CONFIG_FILE_NAME)
    if path.exists(constants.USER_REFERENCE_TENTACLE_CONFIG_PATH):
        rmtree(constants.USER_REFERENCE_TENTACLE_CONFIG_PATH)
