#  Drakkar-Software OctoBot-Node
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
import mock

import octobot_node.scheduler as scheduler_module


pytestmark = pytest.mark.asyncio


class TestShutdownSchedulerAndTradingSignalChannel:
    async def test_second_call_is_no_op_after_shutdown(self):
        with mock.patch.object(scheduler_module.SCHEDULER, "is_initialized", return_value=True):
            with mock.patch.object(scheduler_module.SCHEDULER, "stop") as stop_mock:
                await scheduler_module.shutdown_scheduler_and_trading_signal_channel()
                await scheduler_module.shutdown_scheduler_and_trading_signal_channel()
        stop_mock.assert_called_once()

    async def test_skips_when_scheduler_not_initialized(self):
        with mock.patch.object(scheduler_module.SCHEDULER, "is_initialized", return_value=False):
            with mock.patch.object(scheduler_module.SCHEDULER, "stop") as stop_mock:
                await scheduler_module.shutdown_scheduler_and_trading_signal_channel()
        stop_mock.assert_not_called()

    async def test_initialize_scheduler_resets_shutdown_guard(self):
        with mock.patch.object(scheduler_module.SCHEDULER, "create"):
            with mock.patch.object(scheduler_module.SCHEDULER, "start"):
                with mock.patch("octobot_node.scheduler.workflows.register_workflows"):
                    scheduler_module._shutdown_done = True
                    scheduler_module.initialize_scheduler()
        assert scheduler_module._shutdown_done is False
