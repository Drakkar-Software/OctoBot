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
from shutil import rmtree
from os import walk, path

import octobot_commons.user_root_folder_provider as user_root_folder_provider
import octobot_tentacles_manager.constants as tm_constants
from octobot_tentacles_manager.constants import TENTACLES_REQUIREMENTS_INSTALL_TEMP_DIR, TENTACLES_PATH
from octobot_tentacles_manager.managers.tentacles_setup_manager import TentaclesSetupManager
import tests

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

temp_dir = "temp_tests"


async def test_create_missing_tentacles_arch():
    _cleanup()
    tentacles_setup_manager = TentaclesSetupManager(TENTACLES_PATH)
    await tentacles_setup_manager.create_missing_tentacles_arch()
    trading_mode_files_count = sum(1 for _ in walk(TENTACLES_PATH))
    assert trading_mode_files_count == tests.CLEAN_TENTACLES_ARCHITECTURE_FILES_FOLDERS_COUNT
    assert path.exists(user_root_folder_provider.get_user_reference_tentacle_config_path())
    _cleanup()


def _cleanup():
    if path.exists(temp_dir):
        rmtree(temp_dir)
    if path.exists(TENTACLES_REQUIREMENTS_INSTALL_TEMP_DIR):
        rmtree(TENTACLES_REQUIREMENTS_INSTALL_TEMP_DIR)
    if path.exists(TENTACLES_PATH):
        rmtree(TENTACLES_PATH)
    ref = user_root_folder_provider.get_user_reference_tentacle_config_path()
    if path.exists(ref):
        rmtree(ref)
