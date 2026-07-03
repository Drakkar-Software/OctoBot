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
import asyncio

import mock
import pytest

import octobot_services.constants as services_constants
import octobot_services.managers.service_manager as service_manager_module


pytestmark = pytest.mark.asyncio


class _SlowService:
    def get_name(self):
        return "SlowService"

    async def stop(self):
        await asyncio.sleep(60)


class _FastService:
    stopped = False

    def get_name(self):
        return "FastService"

    async def stop(self):
        _FastService.stopped = True


class TestStopServices:
    async def test_continues_after_slow_service_timeout(self):
        _FastService.stopped = False
        with mock.patch.object(
            service_manager_module,
            "_get_service_instances",
            return_value=[_SlowService(), _FastService()],
        ):
            with mock.patch.object(services_constants, "SERVICE_STOP_TIMEOUT_SECONDS", 0.01):
                await service_manager_module.stop_services()
        assert _FastService.stopped is True
