#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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
from unittest import mock

import octobot.configuration_manager as configuration_manager
import octobot.constants as constants
import octobot_commons.constants as commons_constants
import octobot_commons.tests.test_config as test_config
import octobot_commons.user_root_folder_provider as user_root_folder_provider


def get_fake_config_path():
    return os.path.join(test_config.TEST_CONFIG_FOLDER, f"test_{commons_constants.CONFIG_FILE}")


def test_init_config():
    config_path = get_fake_config_path()
    if os.path.isfile(config_path):
        os.remove(config_path)

    configuration_manager.init_config(
        config_file=config_path,
        from_config_file=os.path.join(test_config.TEST_CONFIG_FOLDER, "bot_config.json"),
    )
    assert os.path.isfile(config_path)
    os.remove(config_path)


def test_init_config_uses_runtime_user_root_not_import_time_default(tmp_path):
    automation_user_root = tmp_path / "user" / "automations" / "child_a"
    automation_config_path = automation_user_root / commons_constants.CONFIG_FILE
    provider = user_root_folder_provider.instance()
    previous_root = provider.get_root()
    provider.set_root(str(automation_user_root))
    try:
        configuration_manager.init_config(
            from_config_file=os.path.join(
                test_config.TEST_CONFIG_FOLDER,
                "bot_config.json",
            ),
        )
        assert automation_config_path.is_file()
        master_config_path = tmp_path / commons_constants.USER_FOLDER / commons_constants.CONFIG_FILE
        assert not master_config_path.is_file()
    finally:
        if previous_root == commons_constants.USER_FOLDER:
            provider.set_root(previous_root)
        else:
            provider._root = None
        if automation_config_path.is_file():
            os.remove(automation_config_path)


class TestGetDefaultTentaclesUrl:
    def test_explicit_version_is_embedded_in_url(self):
        tentacles_url = configuration_manager.get_default_tentacles_url(version=constants.LONG_VERSION)
        assert constants.LONG_VERSION in tentacles_url

    def test_default_url_uses_long_version(self):
        with mock.patch("octobot.configuration_manager.os.getenv", side_effect=lambda key, default=None: default):
            tentacles_url = configuration_manager.get_default_tentacles_url()
        assert constants.LONG_VERSION in tentacles_url
