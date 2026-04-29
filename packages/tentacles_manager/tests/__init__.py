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
import pytest
import sys
import asyncio
import shutil
import os
import os.path as path

import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.constants as commons_constants
import octobot_tentacles_manager.constants as constants


TEMP_DIR = "temp_tests"
OTHER_PROFILE = "other_profile"


CLEAN_TENTACLES_ARCHITECTURE_FILES_FOLDERS_COUNT = 38


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


def _configure_async_test_loop():
    if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):
        # use WindowsSelectorEventLoopPolicy to avoid aiohttp connexion close warnings
        # https://github.com/encode/httpx/issues/914#issuecomment-622586610
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# set default values for async loop
_configure_async_test_loop()


@pytest.fixture
def clean():
    _cleanup()
    yield
    _cleanup()


@pytest.fixture
def fake_profiles():
    default_profile = path.join(commons_constants.USER_PROFILES_FOLDER, commons_constants.DEFAULT_PROFILE)
    other_profile = path.join(commons_constants.USER_PROFILES_FOLDER, OTHER_PROFILE)
    _reset_profile(default_profile)
    _reset_profile(other_profile)
    yield
    _reset_profile(default_profile, re_create=False)
    _reset_profile(other_profile, re_create=False)


def _cleanup():
    if path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    if path.exists(constants.TENTACLES_PATH):
        shutil.rmtree(constants.TENTACLES_PATH)
    if path.exists(constants.USER_REFERENCE_TENTACLE_CONFIG_PATH):
        shutil.rmtree(constants.USER_REFERENCE_TENTACLE_CONFIG_PATH)
    if os.path.isdir(commons_constants.USER_PROFILES_FOLDER):
        shutil.rmtree(commons_constants.USER_PROFILES_FOLDER)


def _reset_profile(profile_path, re_create=True):
    if path.exists(profile_path):
        shutil.rmtree(profile_path)
    if re_create:
        os.makedirs(profile_path)
