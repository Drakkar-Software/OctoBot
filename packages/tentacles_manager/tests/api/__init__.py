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
import shutil
import aiohttp
import pytest
import pytest_asyncio

import octobot_tentacles_manager.api as api
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.managers as managers

TENTACLE_PACKAGE = "tentacle_package"
TEST_EXPORT_DIR = "test_export_dir"


@pytest_asyncio.fixture
async def install_tentacles():
    _cleanup()
    async with aiohttp.ClientSession() as session:
        assert await api.install_all_tentacles(os.path.join("tests", "static", "tentacles.zip"),
                                               aiohttp_session=session) == 0
        yield
    _cleanup()


def _cleanup():
    if os.path.exists(constants.TENTACLES_PATH):
        managers.TentaclesSetupManager.delete_tentacles_arch(force=True)
    if os.path.exists(constants.TENTACLES_PACKAGE_CREATOR_TEMP_FOLDER):
        shutil.rmtree(constants.TENTACLES_PACKAGE_CREATOR_TEMP_FOLDER)
    if os.path.exists(TENTACLE_PACKAGE):
        shutil.rmtree(TENTACLE_PACKAGE)
    if os.path.exists(TEST_EXPORT_DIR):
        shutil.rmtree(TEST_EXPORT_DIR)
    if os.path.exists(constants.DEFAULT_EXPORT_DIR):
        shutil.rmtree(constants.DEFAULT_EXPORT_DIR)
