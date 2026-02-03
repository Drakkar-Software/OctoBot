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
from shutil import rmtree
import os
from os import walk, path

import octobot_commons.constants as commons_constants
from octobot_commons.logging.logging_util import set_logging_level
from octobot_tentacles_manager.constants import USER_REFERENCE_TENTACLE_SPECIFIC_CONFIG_PATH, \
    USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH, TENTACLES_PATH, DEFAULT_BOT_PATH, UNKNOWN_TENTACLES_PACKAGE_LOCATION, \
    TENTACLE_CONFIG, TENTACLES_SPECIFIC_CONFIG_FOLDER
from octobot_tentacles_manager.workers.install_worker import InstallWorker
from octobot_tentacles_manager.models.tentacle_factory import TentacleFactory
from octobot_tentacles_manager.workers.update_worker import UpdateWorker
from octobot_tentacles_manager.models.tentacle import Tentacle
from octobot_tentacles_manager.util.tentacle_fetching import fetch_and_extract_tentacles
from tests import event_loop, clean, TEMP_DIR, OTHER_PROFILE

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_update_two_tentacles(clean):
    _enable_loggers()
    await fetch_and_extract_tentacles(TEMP_DIR, path.join("tests", "static", "tentacles.zip"), None)
    install_worker = InstallWorker(TEMP_DIR, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    install_worker.tentacles_setup_manager.default_tentacle_config = \
        path.join("tests", "static", "default_tentacle_config.json")
    await install_worker.process(["instant_fluctuations_evaluator",
                                  "generic_exchange_importer",
                                  "text_analysis"])
    rmtree(TEMP_DIR)

    await fetch_and_extract_tentacles(TEMP_DIR, path.join("tests", "static", "update_tentacles.zip"), None)
    update_worker = UpdateWorker(TEMP_DIR, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    update_worker.tentacles_setup_manager.default_tentacle_config = \
        path.join("tests", "static", "default_tentacle_config.json")
    assert await update_worker.process(["instant_fluctuations_evaluator", "generic_exchange_importer"]) == 0

    # test installed files
    trading_mode_files_count = sum(1 for _ in walk(path.join(TENTACLES_PATH, "Trading", "Mode")))
    assert trading_mode_files_count == 1
    backtesting_mode_files_count = sum(1 for _ in walk(path.join(TENTACLES_PATH, "Backtesting", "importers")))
    assert backtesting_mode_files_count == 7
    config_files = [f for f in walk(USER_REFERENCE_TENTACLE_SPECIFIC_CONFIG_PATH)]
    config_files_count = len(config_files)
    assert config_files_count == 1

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
                'Backtesting': {
                    'GenericExchangeDataImporter': True
                },
                'Evaluator': {
                    'InstantFluctuationsEvaluator': True,
                    'TextAnalysis': True
                }
            }
        }

    # check updated versions
    # Use TENTACLES_PATH for file access - TentacleFactory auto-detects import root from basename
    factory = TentacleFactory(TENTACLES_PATH)
    from tentacles.Evaluator.RealTime import instant_fluctuations_evaluator
    ife_tentacle_data = await factory.create_and_load_tentacle_from_module(instant_fluctuations_evaluator)
    assert ife_tentacle_data.version == "1.3.0"
    # not updated because update version is "1.1.9"
    import tentacles.Backtesting.importers.exchanges.generic_exchange_importer as gei
    gei_tentacle_data = await factory.create_and_load_tentacle_from_module(gei)
    assert gei_tentacle_data.version == "1.2.0"
    import tentacles.Evaluator.Util.text_analysis
    ta_tentacle_data = await factory.create_and_load_tentacle_from_module(tentacles.Evaluator.Util.text_analysis)
    assert ta_tentacle_data.version == "1.2.0"


async def test_update_all_tentacles(clean):
    _enable_loggers()
    await fetch_and_extract_tentacles(TEMP_DIR, path.join("tests", "static", "tentacles.zip"), None)
    install_worker = InstallWorker(TEMP_DIR, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    install_worker.tentacles_setup_manager.default_tentacle_config = \
        path.join("tests", "static", "default_tentacle_config.json")
    await install_worker.process()
    rmtree(TEMP_DIR)
    await fetch_and_extract_tentacles(TEMP_DIR, path.join("tests", "static", "update_tentacles.zip"), None)
    update_worker = UpdateWorker(TEMP_DIR, TENTACLES_PATH, DEFAULT_BOT_PATH, False, None)
    update_worker.tentacles_setup_manager.default_tentacle_config = \
        path.join("tests", "static", "default_tentacle_config.json")
    assert await update_worker.process() == 0

    # check updated versions
    factory = TentacleFactory(TENTACLES_PATH)
    from tentacles.Evaluator.RealTime import instant_fluctuations_evaluator
    ife_tentacle_data = await factory.create_and_load_tentacle_from_module(instant_fluctuations_evaluator)
    assert ife_tentacle_data.version == "1.3.0"
    import tentacles.Backtesting.importers.exchanges.generic_exchange_importer as gei
    gei_tentacle_data = await factory.create_and_load_tentacle_from_module(gei)
    # not updated because update version is "1.1.9"
    assert gei_tentacle_data.version == "1.2.0"
    import tentacles.Evaluator.Util.text_analysis
    ta_tentacle_data = await factory.create_and_load_tentacle_from_module(tentacles.Evaluator.Util.text_analysis)
    assert ta_tentacle_data.version == "1.3.0"
    import tentacles.Trading.Mode.daily_trading_mode as dtm
    dtm_tentacle_data = await factory.create_and_load_tentacle_from_module(dtm)
    assert dtm_tentacle_data.version == "1.3.0"


def _enable_loggers():
    set_logging_level([clazz.__name__ for clazz in [InstallWorker, Tentacle]], INFO)
