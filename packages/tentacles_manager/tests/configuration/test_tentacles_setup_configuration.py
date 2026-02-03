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
from shutil import rmtree

import aiohttp
import pytest
from os import path

import octobot_tentacles_manager.loaders as loaders
import octobot_tentacles_manager.models as models
import octobot_tentacles_manager.util as util
import octobot_tentacles_manager.api as api
from octobot_tentacles_manager.configuration import TentaclesSetupConfiguration
import octobot_tentacles_manager.constants as constants

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test__set_activation_using_default_config():
    _cleanup()
    async with aiohttp.ClientSession() as session:
        await api.install_all_tentacles(_tentacles_local_path(), aiohttp_session=session)
    tentacle_setup_config = TentaclesSetupConfiguration()
    tentacles = list(loaders.get_tentacle_classes().values())
    tentacle_setup_config._update_tentacles_setup_config(tentacles)

    tentacle_root_path = tentacles[0].tentacle_root_path
    tentacle_types = sorted(util.tentacle_explorer._get_tentacle_types(tentacle_root_path), key=lambda x: x.__str__())

    new_tentacles = []
    # Add Evaluators
    # TA one
    testTA = models.Tentacle(tentacles[0].tentacle_root_path, "testTA",
                             models.TentacleType(os.path.join(constants.TENTACLES_EVALUATOR_PATH,
                                                              constants.TENTACLES_EVALUATOR_TA_PATH)))
    testTA.tentacle_class_names = ["testTA"]
    new_tentacles.append(testTA)
    # Social one
    testSocial = models.Tentacle(tentacles[0].tentacle_root_path, "testSocial", tentacle_types[2])
    testSocial.tentacle_class_names = ["testSocial"]
    new_tentacles.append(testSocial)
    # RealTime one
    testRT = models.Tentacle(tentacles[0].tentacle_root_path, "testRT", tentacle_types[1])
    testRT.tentacle_class_names = ["testRT"]
    new_tentacles.append(testRT)
    # Strategy one
    testStrategy = models.Tentacle(tentacles[0].tentacle_root_path, "testStrategy", tentacle_types[3])
    testStrategy.tentacle_class_names = ["testStrategy"]
    new_tentacles.append(testStrategy)
    # Util one
    testUtil = models.Tentacle(tentacles[0].tentacle_root_path, "testUtil", tentacle_types[4])
    testUtil.tentacle_class_names = ["testUtil"]
    new_tentacles.append(testUtil)

    # Add Trading mode
    # Exchange
    testExchange = models.Tentacle(tentacles[0].tentacle_root_path, "testExchange",
                                   models.TentacleType(os.path.join(constants.TENTACLES_TRADING_PATH,
                                                                    constants.TENTACLES_TRADING_EXCHANGE_PATH)))
    testExchange.tentacle_class_names = ["testExchange"]
    new_tentacles.append(testExchange)
    # Mode
    testMode = models.Tentacle(tentacles[0].tentacle_root_path, "testMode", tentacle_types[8])
    testMode.tentacle_class_names = ["testMode"]
    new_tentacles.append(testMode)

    # Add backtesting
    testBacktesting = models.Tentacle(tentacles[0].tentacle_root_path, "testBacktesting", tentacle_types[0])
    testBacktesting.tentacle_class_names = ["testBacktesting"]
    new_tentacles.append(testBacktesting)

    # Add Meta
    testMetaKeyword = models.Tentacle(tentacles[0].tentacle_root_path, "testMetaKeyword", tentacle_types[5])
    testMetaKeyword.tentacle_class_names = ["testMetaKeyword"]
    new_tentacles.append(testMetaKeyword)

    # Add Service
    testServiceBase = models.Tentacle(tentacles[0].tentacle_root_path, "testServiceBase", tentacle_types[6])
    testServiceBase.tentacle_class_names = ["testServiceBase"]
    testServiceFeed = models.Tentacle(tentacles[0].tentacle_root_path, "testServiceFeed", tentacle_types[7])
    testServiceFeed.tentacle_class_names = ["testServiceFeed"]
    new_tentacles.append(testServiceFeed)
    new_tentacles.append(testServiceBase)

    tentacles += new_tentacles
    tentacle_setup_config._update_tentacles_setup_config(tentacles, newly_installed_tentacles=new_tentacles)

    # Evaluator are disabled by default except for Util
    assert not tentacle_setup_config.tentacles_activation[constants.TENTACLES_EVALUATOR_PATH]["testTA"]
    assert not tentacle_setup_config.tentacles_activation[constants.TENTACLES_EVALUATOR_PATH]["testSocial"]
    assert not tentacle_setup_config.tentacles_activation[constants.TENTACLES_EVALUATOR_PATH]["testStrategy"]
    assert tentacle_setup_config.tentacles_activation[constants.TENTACLES_EVALUATOR_PATH]["testUtil"]

    # Trading
    assert tentacle_setup_config.tentacles_activation[constants.TENTACLES_TRADING_PATH]["testExchange"]
    assert not tentacle_setup_config.tentacles_activation[constants.TENTACLES_TRADING_PATH]["testMode"]

    # Backtesting
    assert tentacle_setup_config.tentacles_activation[constants.TENTACLES_BACKTESTING_PATH]["testBacktesting"]

    # Meta
    assert tentacle_setup_config.tentacles_activation[constants.TENTACLES_META_PATH]["testMetaKeyword"]

    # Services
    assert tentacle_setup_config.tentacles_activation[constants.TENTACLES_SERVICES_PATH]["testServiceBase"]
    assert tentacle_setup_config.tentacles_activation[constants.TENTACLES_SERVICES_PATH]["testServiceFeed"]

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
