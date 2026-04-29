#  Drakkar-Software OctoBot-Services
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

from octobot_services.api.services import stop_services, get_available_services
from octobot_services.api.service_feeds import create_service_feed_factory


@pytest.mark.asyncio
async def test_init_services():
    get_available_services()
    await stop_services()


def test_init_service_feeds():
    factory = create_service_feed_factory({}, None, "")
    factory.get_available_service_feeds(True)
