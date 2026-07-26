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
import packaging.version as packaging_version
import pytest

import octobot.api as octobot_api
import octobot.constants as constants
import octobot.updater.updater as updater_module

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class _TestUpdater(updater_module.Updater):
    def __init__(self, latest_version):
        super().__init__()
        self._latest_version = latest_version

    async def get_latest_version(self):
        return self._latest_version


class TestShouldBeUpdated:
    async def test_does_not_update_when_latest_equals_current_version(self):
        updater = _TestUpdater(constants.VERSION)
        assert not await updater.should_be_updated()

    async def test_updates_when_latest_is_newer_than_current_version(self):
        current_version = packaging_version.parse(constants.VERSION)
        newer_version = f"{current_version.major + 1}.0.0"
        updater = _TestUpdater(newer_version)
        assert await updater.should_be_updated()


async def test_create_updater_from_api():
    updater = octobot_api.get_updater()


async def test_should_update_on_updater_from_api():
    updater = octobot_api.get_updater()
    assert not (await updater.should_be_updated())
