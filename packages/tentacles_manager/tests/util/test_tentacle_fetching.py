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
import copy
import aiohttp
import pytest
from os import path, walk

import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.util as tentacles_manager_util
from tests import event_loop

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

temp_dir = "tests_temp"


async def test_fetch_and_extract_tentacles_using_download():
    _cleanup()
    # ensure cleanup is working
    assert not path.isdir(temp_dir)
    async with aiohttp.ClientSession() as session:
        await tentacles_manager_util.fetch_and_extract_tentacles(temp_dir, constants.DEFAULT_TENTACLES_URL, session)
    _test_temp_tentacles([constants.TENTACLES_META_PATH])
    _cleanup()


async def test_fetch_and_extract_tentacles_using_download_with_wrong_url():
    _cleanup()
    # ensure cleanup is working
    assert not path.isdir(temp_dir)
    async with aiohttp.ClientSession() as session:
        with pytest.raises(RuntimeError):
            await tentacles_manager_util.fetch_and_extract_tentacles(temp_dir, constants.DEFAULT_TENTACLES_URL+"1213113a", session)
    _cleanup()


async def test_fetch_and_extract_tentacles_using_download_without_session():
    _cleanup()
    with pytest.raises(RuntimeError):
        await tentacles_manager_util.fetch_and_extract_tentacles(temp_dir, constants.DEFAULT_TENTACLES_URL, None)
    assert not path.isdir(temp_dir)


async def test_fetch_and_extract_tentacles_using_local_file():
    _cleanup()
    await tentacles_manager_util.fetch_and_extract_tentacles(temp_dir, path.join("tests", "static", "tentacles.zip"), None)
    _test_temp_tentacles()
    _cleanup()


def _test_temp_tentacles(missing_tentacles=None):
    missing_tentacles = missing_tentacles or []
    expected_tentacles_types = copy.copy(constants.TENTACLE_TYPES)
    expected_tentacles_types.remove(constants.TENTACLES_AUTOMATION_PATH)    # no automation tentacles in test file
    assert all(path.isdir(_tentacle_path(tentacle_type))
               for tentacle_type in expected_tentacles_types
               if tentacle_type not in missing_tentacles)
    # assert sub directories also got extracted
    total_files_count = sum(1 for _ in walk(temp_dir))
    assert total_files_count > len(expected_tentacles_types)


def _tentacle_path(tentacle_type):
    return path.join(temp_dir, constants.TENTACLES_ARCHIVE_ROOT, tentacle_type)


def _cleanup():
    tentacles_manager_util.cleanup_temp_dirs(temp_dir)
