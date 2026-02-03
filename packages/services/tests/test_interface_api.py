#  Drakkar-Software OctoBot-Interfaces
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

from octobot_services.api.interfaces import initialize_global_project_data, create_interface_factory, \
    start_interfaces, stop_interfaces
from octobot_services.interfaces.abstract_interface import AbstractInterface


def test_initialize_global_project_data():
    bot_api = "bot"
    initialize_global_project_data(bot_api, "1", "2")
    assert AbstractInterface.bot_api is bot_api
    assert AbstractInterface.project_name == "1"
    assert AbstractInterface.project_version == "2"


def test_create_interface_factory():
    create_interface_factory({})


@pytest.mark.asyncio
async def test_start_interfaces():
    await start_interfaces([])


@pytest.mark.asyncio
async def test_stop_interfaces():
    await stop_interfaces([])
