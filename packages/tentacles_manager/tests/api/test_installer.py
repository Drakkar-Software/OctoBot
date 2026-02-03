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
from os.path import exists
from shutil import rmtree
from zipfile import ZipFile

import aiohttp
import pytest
from os import path, walk

import octobot_commons.constants as commons_constants
from octobot_tentacles_manager.api.installer import install_all_tentacles, install_tentacles, install_single_tentacle, \
    repair_installation
from octobot_tentacles_manager.configuration.tentacles_setup_configuration import TentaclesSetupConfiguration
from octobot_tentacles_manager.constants import TENTACLES_PATH, TENTACLES_REQUIREMENTS_INSTALL_TEMP_DIR, \
    PYTHON_INIT_FILE, TENTACLES_NOTIFIERS_PATH, USER_REFERENCE_TENTACLE_CONFIG_PATH, \
    USER_REFERENCE_TENTACLE_SPECIFIC_CONFIG_PATH, TENTACLES_SERVICES_PATH, TENTACLES_BACKTESTING_PATH, TENTACLES_EVALUATOR_PATH
from octobot_tentacles_manager.managers.tentacles_setup_manager import TentaclesSetupManager
from tests import event_loop, CLEAN_TENTACLES_ARCHITECTURE_FILES_FOLDERS_COUNT


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_install_all_tentacles():
    _cleanup(False)
    async with aiohttp.ClientSession() as session:
        assert await install_all_tentacles(_tentacles_local_path(), aiohttp_session=session) == 0
    _cleanup()


async def test_install_one_tentacle_with_requirement():
    async with aiohttp.ClientSession() as session:
        assert await install_tentacles(["reddit_service_feed"], _tentacles_local_path(), aiohttp_session=session) == 0
    assert path.exists(path.join(TENTACLES_PATH, "Services", "Services_bases", "reddit_service", "reddit_service.py"))
    _cleanup()


async def test_install_single_tentacle():
    tentacle_path = path.join("tests", "static", "momentum_evaluator")
    tentacle_type = "Evaluator/TA"
    async with aiohttp.ClientSession() as session:
        assert await install_single_tentacle(tentacle_path, tentacle_type, aiohttp_session=session) == 0
    assert path.exists(path.join(TENTACLES_PATH, "Evaluator", "TA", "momentum_evaluator", "momentum_evaluator.py"))
    assert not path.exists(TENTACLES_REQUIREMENTS_INSTALL_TEMP_DIR)
    # check availability of tentacle arch, installed momentum_evaluator and its reddit_service fake requirement
    assert len(list(walk(TENTACLES_PATH))) == CLEAN_TENTACLES_ARCHITECTURE_FILES_FOLDERS_COUNT + 5
    _cleanup()


async def test_repair_installation():
    # This test uses a pre-built broken_tentacles.zip which has "tentacles/" structure
    # We need to pass tentacle_path="tentacles" explicitly since the zip structure is fixed
    broken_install = "broken_installation"
    broken_tentacles = path.join("broken_installation", "tentacles")
    with ZipFile(path.join("tests", "static", "broken_tentacles.zip")) as zipped_broken_tentacles:
        zipped_broken_tentacles.extractall(broken_install)

    # Pass tentacle_path explicitly since the zip uses "tentacles/" structure
    assert await repair_installation(tentacle_path="tentacles", bot_path=broken_install) == 0

    # restore Notifiers directory
    assert path.isdir(path.join(broken_tentacles, TENTACLES_SERVICES_PATH, TENTACLES_NOTIFIERS_PATH))

    # restore backtesting init file
    assert path.isfile(path.join(broken_tentacles, TENTACLES_BACKTESTING_PATH, PYTHON_INIT_FILE))

    # restore main __init__ content
    with open(path.join(broken_tentacles, PYTHON_INIT_FILE)) as f:
        stripped_lines = [line.strip() for line in f.readlines()]
        assert "from .Trading import *" in stripped_lines
        assert "from .Backtesting import *" in stripped_lines
        assert "from .Interfaces import *" not in stripped_lines

    # restore Evaluator/Realtime  __init__ content
    rt_path = path.join(broken_tentacles, "Evaluator", "RealTime")
    with open(path.join(rt_path, PYTHON_INIT_FILE)) as f:
        stripped_lines = [line.strip() for line in f.readlines()]
        assert "from .other_instant_fluctuations_evaluator import *" in stripped_lines
        # did not add existing import twice
        assert sum([1
                    for line in stripped_lines
                    if "from .instant_fluctuations_evaluator" in line]) == 1

    # restore Evaluator/Realtime/other_instant_fluctuations_evaluator  __init__ file and content
    with open(path.join(rt_path, "other_instant_fluctuations_evaluator", PYTHON_INIT_FILE)) as f:
        assert "from .other_instant_fluctuations_evaluator import " \
               "OtherInstantFluctuationsEvaluator, SecondOtherInstantFluctuationsEvaluator" in f.readlines()

    # restore tentacles_config.json validity and content
    user_config_path = path.join(broken_install, USER_REFERENCE_TENTACLE_CONFIG_PATH)
    with open(path.join(user_config_path, commons_constants.CONFIG_TENTACLES_FILE)) as f:
        activations = json.load(f)[TentaclesSetupConfiguration.TENTACLE_ACTIVATION_KEY]
        # Evaluators are disabled by default by DEFAULT_DEACTIVATABLE_TENTACLE_SUB_TYPES
        assert activations[TENTACLES_EVALUATOR_PATH]["SecondOtherInstantFluctuationsEvaluator"] is False

    rmtree(broken_install)


def _tentacles_local_path():
    return path.join("tests", "static", "tentacles.zip")


def _cleanup(raises=True):
    if exists(TENTACLES_PATH):
        TentaclesSetupManager.delete_tentacles_arch(force=True, raises=raises)
