#  Drakkar-Software OctoBot-Notifications
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

from octobot_services.api.notification import create_notifier_factory, send_notification, create_notification


def test_create_notifier_factory():
    factory = create_notifier_factory({})
    factory.get_available_notifiers()


def test_create_notification():
    create_notification("plop")


@pytest.mark.asyncio
async def test_send_notification():
    await send_notification(create_notification(""))
