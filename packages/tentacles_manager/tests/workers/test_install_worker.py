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
import json
import aiohttp
import pytest
import os
from logging import INFO

import octobot_commons.constants as commons_constants
from octobot_commons.logging.logging_util import set_logging_level
from octobot_tentacles_manager.constants import USER_REFERENCE_TENTACLE_SPECIFIC_CONFIG_PATH, \
    TENTACLES_REQUIREMENTS_INSTALL_TEMP_DIR, USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH, TENTACLES_PATH, DEFAULT_BOT_PATH, \
    UNKNOWN_TENTACLES_PACKAGE_LOCATION, TENTACLES_SPECIFIC_CONFIG_FOLDER
from octobot_tentacles_manager.workers.install_worker import InstallWorker
from octobot_tentacles_manager.models.tentacle import Tentacle
from octobot_tentacles_manager.util.tentacle_fetching import fetch_and_extract_tentacles
from tests import event_loop, clean, fake_profiles, TEMP_DIR, OTHER_PROFILE

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_install_two_tentacles(clean):
    _enable_loggers()
    tentacles_path = os.path.join("tests", "static", "tentacles.zip")
    await fetch_and_extract_tentacles(TEMP_DIR, tentacles_path, None)
    worker = InstallWorker(TEMP_DIR, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    worker.tentacles_path_or_url = tentacles_path
    worker.tentacles_setup_manager.default_tentacle_config = \
        os.path.join("tests", "static", "default_tentacle_config.json")
    assert await worker.process(["instant_fluctuations_evaluator", "generic_exchange_importer"]) == 0

    # test installed files
    trading_mode_files_count = sum(1 for _ in os.walk(os.path.join(TENTACLES_PATH, "Trading", "Mode")))
    assert trading_mode_files_count == 1
    backtesting_mode_files_count = sum(1 for _ in os.walk(os.path.join(TENTACLES_PATH, "Backtesting", "importers")))
    assert backtesting_mode_files_count == 7
    config_files = [f for f in os.walk(USER_REFERENCE_TENTACLE_SPECIFIC_CONFIG_PATH)]
    config_files_count = len(config_files)
    assert config_files_count == 1

    # test tentacles config
    with open(USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH, "r") as config_f:
        ref_profile_config = json.load(config_f)
        assert ref_profile_config == {
            'installation_context': {
                'octobot_version': 'unknown'
            },
            'registered_tentacles': {
                'OctoBot-Default-Tentacles': tentacles_path
            },
            'tentacle_activation': {
                'Backtesting': {
                    'GenericExchangeDataImporter': True
                },
                'Evaluator': {
                    'InstantFluctuationsEvaluator': True
                }
            }
        }


async def test_install_one_tentacle_with_requirement(clean):
    async with aiohttp.ClientSession() as session:
        _enable_loggers()
        await fetch_and_extract_tentacles(TEMP_DIR, os.path.join("tests", "static", "tentacles.zip"), None)
        worker = InstallWorker(TEMP_DIR, TENTACLES_PATH, DEFAULT_BOT_PATH, False, session)
        worker.tentacles_setup_manager.default_tentacle_config = \
            os.path.join("tests", "static", "default_tentacle_config.json")
        assert await worker.process(["reddit_service_feed"]) == 0

    # test removed temporary requirements files
    assert not os.path.exists(TENTACLES_REQUIREMENTS_INSTALL_TEMP_DIR)

    # test installed files
    trading_mode_files_count = sum(1 for _ in os.walk(os.path.join(TENTACLES_PATH, "Trading", "Mode")))
    assert trading_mode_files_count == 1
    config_files = [f for f in os.walk(USER_REFERENCE_TENTACLE_SPECIFIC_CONFIG_PATH)]
    assert len(config_files) == 1
    assert len(config_files[0][2]) == 0

    # test tentacles config
    with open(USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH, "r") as config_f:
        assert json.load(config_f) == {
            'installation_context': {
                'octobot_version': 'unknown'
            },
            'registered_tentacles': {
                'OctoBot-Default-Tentacles': UNKNOWN_TENTACLES_PACKAGE_LOCATION
            },
            'tentacle_activation': {
                'Services': {
                    'RedditService': True,
                    'RedditServiceFeed': True
                }
            }
        }
    assert os.path.exists(
        os.path.join(TENTACLES_PATH, "Services", "Services_bases", "reddit_service", "reddit.py"))


async def test_install_all_tentacles(clean):
    _enable_loggers()
    tentacles_path = os.path.join("tests", "static", "tentacles.zip")
    await fetch_and_extract_tentacles(TEMP_DIR, tentacles_path, None)
    worker = InstallWorker(TEMP_DIR, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    worker.tentacles_path_or_url = tentacles_path
    worker.tentacles_setup_manager.default_tentacle_config = \
        os.path.join("tests", "static", "default_tentacle_config.json")
    assert await worker.process() == 0

    # test installed files
    trading_mode_files_count = sum(1 for _ in os.walk(os.path.join(TENTACLES_PATH, "Trading", "Mode")))
    assert trading_mode_files_count == 5
    config_files = [f for f in os.walk(USER_REFERENCE_TENTACLE_SPECIFIC_CONFIG_PATH)]
    config_files_count = len(config_files)
    assert config_files_count == 1

    # test tentacles config
    with open(USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH, "r") as config_f:
        assert json.load(config_f) == {
            'installation_context': {
                'octobot_version': 'unknown'
            },
            'registered_tentacles': {
                'OctoBot-Default-Tentacles': tentacles_path
            },
            'tentacle_activation': {
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
        }


async def test_install_all_tentacles_with_profile(clean):
    _enable_loggers()
    profile_path = os.path.join(commons_constants.USER_PROFILES_FOLDER, "many_traded_elements")
    assert not os.path.isfile(os.path.join(profile_path, commons_constants.PROFILE_CONFIG_FILE))
    tentacles_path = os.path.join("tests", "static", "tentacles_with_profile.zip")
    await fetch_and_extract_tentacles(TEMP_DIR, tentacles_path, None)
    worker = InstallWorker(TEMP_DIR, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    worker.tentacles_path_or_url = tentacles_path
    worker.tentacles_setup_manager.default_tentacle_config = \
        os.path.join("tests", "static", "default_tentacle_config.json")
    assert await worker.process() == 0

    # test installed files to ensure tentacles installation got well
    trading_mode_files_count = sum(1 for _ in os.walk(os.path.join(TENTACLES_PATH, "Trading", "Mode")))
    assert trading_mode_files_count == 5
    config_files = [f for f in os.walk(os.path.join(profile_path, TENTACLES_SPECIFIC_CONFIG_FOLDER))]
    config_files_count = len(config_files)
    assert config_files_count == 1
    assert "DailyTradingMode.json" in config_files[0][2]
    assert len(config_files[0][2]) == 18

    # test installed profile
    assert os.path.isfile(os.path.join(profile_path, commons_constants.PROFILE_CONFIG_FILE))
    assert os.path.isfile(os.path.join(profile_path, "default_profile.png"))
    assert os.path.isfile(os.path.join(profile_path, commons_constants.CONFIG_TENTACLES_FILE))
    assert os.path.isfile(os.path.join(profile_path, TENTACLES_SPECIFIC_CONFIG_FOLDER, "DailyTradingMode.json"))
    assert os.path.isfile(os.path.join(profile_path, TENTACLES_SPECIFIC_CONFIG_FOLDER, "TwitterNewsEvaluator.json"))


async def test_profiles_update(clean, fake_profiles):
    _enable_loggers()
    tentacles_path = os.path.join("tests", "static", "tentacles.zip")
    await fetch_and_extract_tentacles(TEMP_DIR, tentacles_path, None)
    worker = InstallWorker(TEMP_DIR, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    worker.tentacles_path_or_url = tentacles_path
    worker.tentacles_setup_manager.default_tentacle_config = \
        os.path.join("tests", "static", "default_tentacle_config.json")
    # install all tentacles
    assert await worker.process() == 0

    # test tentacles setup config
    with open(USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH) as config_f:
        ref_profile_config = json.load(config_f)

        # test profiles tentacles config
        with open(os.path.join(commons_constants.USER_PROFILES_FOLDER,
                               commons_constants.DEFAULT_PROFILE,
                               commons_constants.CONFIG_TENTACLES_FILE)) as default_c:
            assert ref_profile_config == json.load(default_c)
        with open(os.path.join(commons_constants.USER_PROFILES_FOLDER,
                               OTHER_PROFILE,
                               commons_constants.CONFIG_TENTACLES_FILE)) as other_c:
            assert ref_profile_config == json.load(other_c)

    # test specific tentacles config
    default_profile_tentacles_config = os.path.join(commons_constants.USER_PROFILES_FOLDER,
                                                    commons_constants.DEFAULT_PROFILE,
                                                    TENTACLES_SPECIFIC_CONFIG_FOLDER)
    other_profile_tentacles_config = os.path.join(commons_constants.USER_PROFILES_FOLDER,
                                                  OTHER_PROFILE,
                                                  TENTACLES_SPECIFIC_CONFIG_FOLDER)
    for tentacle_config in os.scandir(os.path.join(os.path.split(USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH)[0],
                                                   TENTACLES_SPECIFIC_CONFIG_FOLDER)):
        with open(tentacle_config) as ref_config_file:
            ref_config = json.load(ref_config_file)
        with open(os.path.join(default_profile_tentacles_config, tentacle_config.name)) as default_profile_config_file:
            assert ref_config == json.load(default_profile_config_file)
        with open(os.path.join(other_profile_tentacles_config, tentacle_config.name)) as other_profile_config_file:
            assert ref_config == json.load(other_profile_config_file)


async def test_install_all_tentacles_twice(clean):
    await fetch_and_extract_tentacles(TEMP_DIR, os.path.join("tests", "static", "tentacles.zip"), None)
    worker = InstallWorker(TEMP_DIR, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    worker.tentacles_setup_manager.default_tentacle_config = \
        os.path.join("tests", "static", "default_tentacle_config.json")
    assert await worker.process() == 0
    assert await worker.process() == 0
    trading_mode_files_count = sum(1 for _ in os.walk(os.path.join(TENTACLES_PATH, "Trading", "Mode")))
    assert trading_mode_files_count == 5


async def test_install_all_tentacles_fetching_requirements(clean):
    async with aiohttp.ClientSession() as session:
        _enable_loggers()
        await fetch_and_extract_tentacles(TEMP_DIR, os.path.join("tests", "static", "requirements_tentacles.zip"), None)
        worker = InstallWorker(TEMP_DIR, TENTACLES_PATH, DEFAULT_BOT_PATH, False, session)
        worker.tentacles_setup_manager.default_tentacle_config = \
            os.path.join("tests", "static", "default_tentacle_config.json")
        assert await worker.process() == 0

    trading_mode_files_count = sum(1 for _ in os.walk(os.path.join(TENTACLES_PATH, "Trading", "Mode")))
    assert trading_mode_files_count == 5
    config_files = [f for f in os.walk(USER_REFERENCE_TENTACLE_SPECIFIC_CONFIG_PATH)]
    config_files_count = len(config_files)
    assert config_files_count == 1
    # ensure fetched InstantFluctuationsEvaluator requirement
    assert os.path.exists(os.path.join(TENTACLES_PATH, "Evaluator", "RealTime",
                                       "instant_fluctuations_evaluator", "instant_fluctuations.py"))


def _enable_loggers():
    set_logging_level([clazz.__name__ for clazz in [InstallWorker, Tentacle]], INFO)
