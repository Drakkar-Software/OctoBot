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
from os.path import isdir, isfile

import aiohttp
import pytest
from importlib import reload
from os import path

from octobot_tentacles_manager.api.installer import install_all_tentacles
import octobot_tentacles_manager.loaders.tentacle_loading as tentacle_loading

# All test coroutines will be treated as marked.
from octobot_tentacles_manager.managers.tentacles_setup_manager import TentaclesSetupManager

pytestmark = pytest.mark.asyncio


async def test_get_tentacle_without_loading():
    # reload tentacle_loading module to force reset of cached tentacle data
    reload(tentacle_loading)
    async with aiohttp.ClientSession() as session:
        await install_all_tentacles(_tentacles_local_path(), aiohttp_session=session)
    # force tentacle data reset
    tentacle_loading._tentacle_by_tentacle_class = None
    with pytest.raises(RuntimeError):
        from tentacles.Services import RedditService
        tentacle_loading.get_tentacle(RedditService)
    _cleanup()


async def test_with_reload_tentacle_by_tentacle_class_installed_tentacles():
    async with aiohttp.ClientSession() as session:
        await install_all_tentacles(_tentacles_local_path(), aiohttp_session=session)
    tentacle_loading.reload_tentacle_by_tentacle_class()
    from tentacles.Services import RedditService
    from tentacles.Trading.Mode import DailyTradingMode
    assert tentacle_loading.get_tentacle(RedditService) is not None
    assert tentacle_loading.get_tentacle(DailyTradingMode) is not None
    assert isdir(tentacle_loading.get_resources_path(DailyTradingMode))
    assert isdir(tentacle_loading.get_resources_path(RedditService))
    assert isfile(tentacle_loading.get_documentation_file_path(DailyTradingMode))
    _cleanup()


def _tentacles_local_path():
    return path.join("tests", "static", "tentacles.zip")


def _cleanup():
    TentaclesSetupManager.delete_tentacles_arch()
