#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import os

from octobot.configuration_manager import init_config
from octobot_commons.constants import CONFIG_FILE
from octobot_commons.tests.test_config import TEST_CONFIG_FOLDER


def get_fake_config_path():
    return os.path.join(TEST_CONFIG_FOLDER, f"test_{CONFIG_FILE}")


def test_init_config():
    config_path = get_fake_config_path()
    if os.path.isfile(config_path):
        os.remove(config_path)

    init_config(config_file=config_path, from_config_file=os.path.join(TEST_CONFIG_FOLDER, CONFIG_FILE))
    assert os.path.isfile(config_path)
    os.remove(config_path)
