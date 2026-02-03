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
from os import path

from octobot_tentacles_manager.constants import TENTACLES_PATH
from octobot_tentacles_manager.api.installer import install_tentacles
from octobot_tentacles_manager.api.updater import update_all_tentacles, update_tentacles
from octobot_tentacles_manager.managers.tentacles_setup_manager import TentaclesSetupManager
from octobot_tentacles_manager.models.tentacle_factory import TentacleFactory

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_update_all_tentacles():
    async with aiohttp.ClientSession() as session:
        assert await update_all_tentacles(_tentacles_local_path(), aiohttp_session=session) == 0
    _cleanup()


async def test_update_one_tentacle_with_requirement():
    async with aiohttp.ClientSession() as session:
        assert await install_tentacles(["reddit_service_feed"], _tentacles_local_path(),
                                       aiohttp_session=session) == 0
        # Use TENTACLES_PATH for file access - TentacleFactory auto-detects import root from basename
        factory = TentacleFactory(TENTACLES_PATH)
        assert path.exists(path.join(TENTACLES_PATH, "Services", "Services_bases", "reddit_service", "reddit_service.py"))
        import tentacles.Services.Services_bases.reddit_service as red
        import tentacles.Services.Services_feeds.reddit_service_feed as feed
        dtm_tentacle_data = await factory.create_and_load_tentacle_from_module(feed)
        assert dtm_tentacle_data.version == "1.2.0"
        assert await update_tentacles(["reddit_service_feed"], _tentacles_update_local_path(),
                                      aiohttp_session=session) == 0
        dtm_tentacle_data = await factory.create_and_load_tentacle_from_module(feed)
        assert dtm_tentacle_data.version == "1.3.0"
    # _cleanup()


def _tentacles_local_path():
    return path.join("tests", "static", "tentacles.zip")


def _tentacles_update_local_path():
    return path.join("tests", "static", "update_tentacles.zip")


def _cleanup():
    TentaclesSetupManager.delete_tentacles_arch()
