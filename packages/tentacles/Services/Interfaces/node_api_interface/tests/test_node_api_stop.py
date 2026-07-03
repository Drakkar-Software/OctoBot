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
import asyncio
import threading

import mock
import pytest

import tentacles.Services.Interfaces.node_api_interface.node_api as node_api_module


pytestmark = pytest.mark.asyncio


class TestNodeApiInterfaceStop:
    async def test_stop_sets_should_exit_and_waits_for_serve_finished(self):
        interface = node_api_module.NodeApiInterface({})
        interface.logger = mock.Mock()
        interface.server = mock.Mock()
        interface.server.should_exit = False
        serve_finished = threading.Event()
        serve_finished.set()
        interface._serve_finished = serve_finished

        await interface.stop()

        assert interface.server.should_exit is True

    async def test_stop_logs_warning_when_serve_does_not_finish_in_time(self):
        interface = node_api_module.NodeApiInterface({})
        interface.logger = mock.Mock()
        interface.server = mock.Mock()
        interface._serve_finished = threading.Event()

        with mock.patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            await interface.stop()

        interface.logger.warning.assert_called_once()
