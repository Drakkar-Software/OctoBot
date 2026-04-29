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
import pytest
from logging import INFO
import os

import octobot_commons.constants as commons_constants
from octobot_commons.logging.logging_util import set_logging_level
from octobot_tentacles_manager.constants import TENTACLES_PATH, \
    USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH, DEFAULT_BOT_PATH, TENTACLE_CONFIG, TENTACLES_EVALUATOR_PATH, \
    TENTACLES_EVALUATOR_REALTIME_PATH
from octobot_tentacles_manager.workers.install_worker import InstallWorker

from octobot_tentacles_manager.models.tentacle import Tentacle
from octobot_tentacles_manager.workers.uninstall_worker import UninstallWorker
from octobot_tentacles_manager.util.tentacle_fetching import fetch_and_extract_tentacles
from tests import event_loop, clean, fake_profiles, TEMP_DIR, OTHER_PROFILE, \
    CLEAN_TENTACLES_ARCHITECTURE_FILES_FOLDERS_COUNT

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_uninstall_two_tentacles(clean):
    _enable_loggers()
    tentacles_path = os.path.join("tests", "static", "tentacles.zip")
    await fetch_and_extract_tentacles(TEMP_DIR, tentacles_path, None)
    install_worker = InstallWorker(TEMP_DIR, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    install_worker.tentacles_path_or_url = tentacles_path
    install_worker.tentacles_setup_manager.default_tentacle_config \
        = os.path.join("tests", "static", "default_tentacle_config.json")
    assert await install_worker.process() == 0
    tentacles_files_count_after_install = sum(1 for _ in os.walk(TENTACLES_PATH))
    assert tentacles_files_count_after_install > 62

    uninstall_worker = UninstallWorker(None, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    uninstall_worker.tentacles_setup_manager.default_tentacle_config = \
        os.path.join("tests", "static", "default_tentacle_config.json")
    assert await uninstall_worker.process(["instant_fluctuations_evaluator", "generic_exchange_importer"]) == 0
    tentacles_files_count_after_uninstall = sum(1 for _ in os.walk(TENTACLES_PATH))
    # After uninstalling 2 tentacles, there should be fewer directories than after full install
    assert tentacles_files_count_after_uninstall < tentacles_files_count_after_install
    with open(USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH, "r") as config_f:
        assert json.load(config_f) == {
            'installation_context': {
                'octobot_version': 'unknown'
            },
            'registered_tentacles': {
                'OctoBot-Default-Tentacles': tentacles_path
            },
            'tentacle_activation': {
                'Backtesting': {},
                'Evaluator': {
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


async def test_profiles_update(clean, fake_profiles):
    _enable_loggers()
    tentacles_path = os.path.join("tests", "static", "tentacles.zip")
    await fetch_and_extract_tentacles(TEMP_DIR, tentacles_path, None)
    install_worker = InstallWorker(TEMP_DIR, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    install_worker.tentacles_path_or_url = tentacles_path
    install_worker.tentacles_setup_manager.default_tentacle_config \
        = os.path.join("tests", "static", "default_tentacle_config.json")
    assert await install_worker.process() == 0
    tentacles_files_count = sum(1 for _ in os.walk(TENTACLES_PATH))
    assert tentacles_files_count > 60

    ref_specific_tentacles_config = os.path.join(TENTACLES_PATH,
                                                 TENTACLES_EVALUATOR_PATH,
                                                 TENTACLES_EVALUATOR_REALTIME_PATH,
                                                 "instant_fluctuations_evaluator",
                                                 TENTACLE_CONFIG)
    with open(os.path.join(ref_specific_tentacles_config, "InstantFluctuationsEvaluator.json")) as ref_conf:
        instant_fluct_config = json.load(ref_conf)

    uninstall_worker = UninstallWorker(None, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    uninstall_worker.tentacles_setup_manager.default_tentacle_config = \
        os.path.join("tests", "static", "default_tentacle_config.json")
    # uninstall 2 tentacles
    assert await uninstall_worker.process(["instant_fluctuations_evaluator", "generic_exchange_importer"]) == 0

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


async def test_uninstall_all_tentacles(clean):
    _enable_loggers()
    tentacles_path = os.path.join("tests", "static", "tentacles.zip")
    await fetch_and_extract_tentacles(TEMP_DIR, tentacles_path, None)
    install_worker = InstallWorker(TEMP_DIR, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    install_worker.tentacles_path_or_url = tentacles_path
    install_worker.tentacles_setup_manager.default_tentacle_config = \
        os.path.join("tests", "static", "default_tentacle_config.json")
    assert await install_worker.process() == 0
    tentacles_files_count = sum(1 for _ in os.walk(TENTACLES_PATH))
    assert tentacles_files_count > 60

    uninstall_worker = UninstallWorker(None, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    uninstall_worker.tentacles_setup_manager.default_tentacle_config = \
        os.path.join("tests", "static", "default_tentacle_config.json")
    assert await uninstall_worker.process() == 0
    tentacles_files_count = sum(1 for _ in os.walk(TENTACLES_PATH))
    assert tentacles_files_count == CLEAN_TENTACLES_ARCHITECTURE_FILES_FOLDERS_COUNT
    with open(USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH, "r") as config_f:
        assert json.load(config_f) == {
            'installation_context': {
                'octobot_version': 'unknown'
            },
            'registered_tentacles': {},
            'tentacle_activation': {
                'Backtesting': {},
                'Evaluator': {},
                'Meta': {},
                'Services': {},
                'Trading': {}
            }
        }


def _enable_loggers():
    set_logging_level([clazz.__name__ for clazz in [InstallWorker, Tentacle]], INFO)
