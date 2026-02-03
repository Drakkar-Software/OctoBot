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
import aiohttp
import pytest
from os import path, walk

from octobot_tentacles_manager.constants import TENTACLES_PATH
from octobot_tentacles_manager.api.installer import install_all_tentacles, install_tentacles
from octobot_tentacles_manager.api.uninstaller import uninstall_all_tentacles, uninstall_tentacles
from octobot_tentacles_manager.loaders.tentacle_loading import get_tentacle_classes
from octobot_tentacles_manager.managers.tentacles_setup_manager import TentaclesSetupManager
import tests

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_uninstall_all_tentacles():
    async with aiohttp.ClientSession() as session:
        assert await install_all_tentacles(_tentacles_local_path(), aiohttp_session=session) == 0
        trading_mode_files_count = sum(1 for _ in walk(TENTACLES_PATH))
        assert trading_mode_files_count > 50
    assert await uninstall_all_tentacles() == 0
    trading_mode_files_count = sum(1 for _ in walk(TENTACLES_PATH))
    assert trading_mode_files_count == tests.CLEAN_TENTACLES_ARCHITECTURE_FILES_FOLDERS_COUNT
    _cleanup()


async def test_uninstall_one_tentacle():
    async with aiohttp.ClientSession() as session:
        assert await install_tentacles(["reddit_service"], _tentacles_local_path(), aiohttp_session=session) == 0
        trading_mode_files_count = sum(1 for _ in walk(TENTACLES_PATH))
        assert trading_mode_files_count > 25
    assert "RedditService" in get_tentacle_classes()
    assert await uninstall_tentacles(["reddit_service"]) == 0
    trading_mode_files_count = sum(1 for _ in walk(TENTACLES_PATH))
    assert trading_mode_files_count == tests.CLEAN_TENTACLES_ARCHITECTURE_FILES_FOLDERS_COUNT
    assert "RedditService" not in get_tentacle_classes()
    _cleanup()


def _tentacles_local_path():
    return path.join("tests", "static", "tentacles.zip")


def _cleanup():
    TentaclesSetupManager.delete_tentacles_arch()
