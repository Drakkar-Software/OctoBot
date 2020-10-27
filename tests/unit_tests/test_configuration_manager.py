#  Drakkar-Software OctoBot
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
import pytest

from octobot.configuration_manager import init_config
from octobot_commons.constants import CONFIG_FILE
from octobot_commons.tests.test_config import TEST_CONFIG_FOLDER


def get_fake_config_path():
    return os.path.join(TEST_CONFIG_FOLDER, f"test_{CONFIG_FILE}")


@pytest.mark.timeout(2)
def test_init_config():
    fake_config_path = get_fake_config_path()
    if os.path.isfile(fake_config_path):
        os.remove(fake_config_path)

    init_config(config_file=fake_config_path, from_config_file=os.path.join(TEST_CONFIG_FOLDER, CONFIG_FILE))
    assert os.path.isfile(fake_config_path)
    os.remove(fake_config_path)
