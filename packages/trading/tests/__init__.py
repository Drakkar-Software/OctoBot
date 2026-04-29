#  Drakkar-Software OctoBot-Trading
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
import sys
import asyncio
import os

import aiohttp
import pytest
import pytest_asyncio
import requests

import octobot_commons.asyncio_tools as asyncio_tools
from octobot_commons.tests.test_config import load_test_config
from octobot_tentacles_manager.api.installer import install_all_tentacles
from octobot_tentacles_manager.constants import TENTACLES_PATH
from octobot_tentacles_manager.managers.tentacles_setup_manager import TentaclesSetupManager

OCTOBOT_ONLINE = os.getenv("TENTACLES_OCTOBOT_ONLINE_URL", "https://tentacles.octobot.online")
TENTACLES_LATEST_URL = f"{OCTOBOT_ONLINE}/repository/tentacles/officials/base/latest.zip"


@pytest.fixture
def event_loop():
    # re-configure async loop each time this fixture is called
    _configure_async_test_loop()
    loop = asyncio.new_event_loop()
    # use ErrorContainer to catch otherwise hidden exceptions occurring in async scheduled tasks
    error_container = asyncio_tools.ErrorContainer()
    loop.set_exception_handler(error_container.exception_handler)
    yield loop
    # will fail if exceptions have been silently raised
    loop.run_until_complete(error_container.check())
    loop.close()


@pytest_asyncio.fixture
async def config():
    return load_test_config()


@pytest_asyncio.fixture
async def install_tentacles():
    def _download_tentacles():
        r = requests.get(TENTACLES_LATEST_URL, stream=True)
        open(_tentacles_local_path(), 'wb').write(r.content)

    def _cleanup(raises=True):
        if os.path.exists(TENTACLES_PATH):
            TentaclesSetupManager.delete_tentacles_arch(force=True, raises=raises)

    def _tentacles_local_path():
        return os.path.join("tests", "static", "tentacles.zip")

    if not os.path.exists(_tentacles_local_path()):
        _download_tentacles()

    _cleanup(False)
    async with aiohttp.ClientSession() as session:
        yield await install_all_tentacles(_tentacles_local_path(), aiohttp_session=session)
    _cleanup()


@pytest_asyncio.fixture
async def skipped_on_github_CI():
    if is_on_github_ci():
        pytest.skip(reason="test skipped on github CI")


def is_on_github_ci():
    # Always set to true when GitHub Actions is running the workflow.
    # You can use this variable to differentiate when tests are being run locally or by GitHub Actions.
    # from https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/store-information-in-variables
    return bool(os.getenv("GITHUB_ACTIONS"))


def _configure_async_test_loop():
    if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):
        # use WindowsSelectorEventLoopPolicy to avoid aiohttp connexion close warnings
        # https://github.com/encode/httpx/issues/914#issuecomment-622586610
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# set default values for async loop
_configure_async_test_loop()
