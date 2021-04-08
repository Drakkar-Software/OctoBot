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
import pytest

import octobot.api as octobot_api

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_create_updater_from_api():
    updater = octobot_api.get_updater()


async def test_should_update_on_updater_from_api():
    updater = octobot_api.get_updater()
    assert not (await updater.should_be_updated())
