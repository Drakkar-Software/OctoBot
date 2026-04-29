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
from shutil import rmtree
import pytest
from copy import copy
from os.path import exists, join
from os import path

from octobot_commons.constants import USER_FOLDER
from octobot_tentacles_manager.api.configurator import get_tentacles_setup_config, update_activation_configuration, \
    get_tentacles_activation
from octobot_tentacles_manager.constants import TENTACLES_PATH, DEFAULT_BOT_PATH, TENTACLES_INSTALL_TEMP_DIR
from octobot_tentacles_manager.managers.tentacles_setup_manager import TentaclesSetupManager
from octobot_tentacles_manager.util.tentacle_fetching import fetch_and_extract_tentacles
from octobot_tentacles_manager.workers.install_worker import InstallWorker

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

temp_dir = "temp_tests"


async def test_update_activation_configuration():
    _cleanup(False)
    await fetch_and_extract_tentacles(temp_dir, join("tests", "static", "tentacles.zip"), None)
    worker = InstallWorker(temp_dir, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    worker.tentacles_setup_manager.default_tentacle_config = join("tests", "static", "default_tentacle_config.json")
    assert await worker.process() == 0
    setup_config = get_tentacles_setup_config()
    default_activation = copy(get_tentacles_activation(setup_config))
    assert default_activation == {
        'Backtesting': {
            'GenericExchangeDataImporter': True
        },
        'Evaluator': {
            'InstantFluctuationsEvaluator': True,
            'OtherInstantFluctuationsEvaluator': False,
            'OverallStateAnalyser': True,
            'RedditForumEvaluator': False,
            'SecondOtherInstantFluctuationsEvaluator': False,
            'SimpleMixedStrategyEvaluator': True,
            'TextAnalysis': True
        },
        'Meta': {},
        'Services': {
            'RedditService': True,
            'RedditServiceFeed': True
        },
        'Trading': {
            'DailyTradingMode': True
        }
    }
    # Did not add OtherTentacle since it is not in original activation
    assert update_activation_configuration(setup_config, {"OtherTentacle": True}, False) is False
    assert default_activation == get_tentacles_activation(setup_config)

    # No change
    assert update_activation_configuration(setup_config, {"InstantFluctuationsEvaluator": True}, False) is False
    assert default_activation == get_tentacles_activation(setup_config)

    # One change
    assert update_activation_configuration(setup_config, {"InstantFluctuationsEvaluator": False}, False) is True
    assert get_tentacles_activation(setup_config) == {
        'Backtesting': {
            'GenericExchangeDataImporter': True
        },
        'Evaluator': {
            'InstantFluctuationsEvaluator': False,
            'OtherInstantFluctuationsEvaluator': False,
            'OverallStateAnalyser': True,
            'RedditForumEvaluator': False,
            'SecondOtherInstantFluctuationsEvaluator': False,
            'SimpleMixedStrategyEvaluator': True,
            'TextAnalysis': True
        },
        'Meta': {},
        'Services': {
            'RedditService': True,
            'RedditServiceFeed': True
        },
        'Trading': {
            'DailyTradingMode': True
        }
    }

    # Two changes
    assert update_activation_configuration(setup_config,
                                           {
                                              "InstantFluctuationsEvaluator": True,
                                              'RedditForumEvaluator': True
                                           },
                                           False) is True
    assert get_tentacles_activation(setup_config) == {
        'Backtesting': {
            'GenericExchangeDataImporter': True
        },
        'Evaluator': {
            'InstantFluctuationsEvaluator': True,
            'OtherInstantFluctuationsEvaluator': False,
            'OverallStateAnalyser': True,
            'RedditForumEvaluator': True,
            'SecondOtherInstantFluctuationsEvaluator': False,
            'SimpleMixedStrategyEvaluator': True,
            'TextAnalysis': True
        },
        'Meta': {},
        'Services': {
            'RedditService': True,
            'RedditServiceFeed': True
        },
        'Trading': {
            'DailyTradingMode': True
        }
    }

    # Two changes with deactivate others evaluators
    assert update_activation_configuration(setup_config,
                                           {
                                              "InstantFluctuationsEvaluator": True,
                                              'RedditForumEvaluator': True
                                           },
                                           True) is False
    assert get_tentacles_activation(setup_config) == {
        'Backtesting': {
            'GenericExchangeDataImporter': True
        },
        'Evaluator': {
            'InstantFluctuationsEvaluator': True,
            'OtherInstantFluctuationsEvaluator': False,
            'OverallStateAnalyser': True,
            'RedditForumEvaluator': True,
            'SecondOtherInstantFluctuationsEvaluator': False,
            'SimpleMixedStrategyEvaluator': True,
            'TextAnalysis': True
        },
        'Meta': {},
        'Services': {
            'RedditService': True,
            'RedditServiceFeed': True
        },
        'Trading': {
            'DailyTradingMode': True
        }
    }
    _cleanup()


def _tentacles_local_path():
    return path.join("tests", "static", "tentacles.zip")


def _cleanup(raises=True):
    if exists(TENTACLES_PATH):
        TentaclesSetupManager.delete_tentacles_arch(force=True, raises=raises, with_user_config=True)
    if exists(USER_FOLDER):
        rmtree(USER_FOLDER)
    if exists(TENTACLES_INSTALL_TEMP_DIR):
        rmtree(TENTACLES_INSTALL_TEMP_DIR)
