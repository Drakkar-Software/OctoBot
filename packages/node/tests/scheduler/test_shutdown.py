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
            with mock.patch(
                "octobot_node.scheduler.workflows_retention.cancel_startup_cleanup_trigger",
            ):
                with mock.patch.object(scheduler_module.SCHEDULER, "stop") as stop_mock:
                    await scheduler_module.shutdown_scheduler_and_trading_signal_channel()
                    await scheduler_module.shutdown_scheduler_and_trading_signal_channel()
        stop_mock.assert_called_once()

    async def test_skips_when_scheduler_not_initialized(self):
        with mock.patch.object(scheduler_module.SCHEDULER, "is_initialized", return_value=False):
            with mock.patch(
                "octobot_node.scheduler.workflows_retention.cancel_startup_cleanup_trigger",
            ) as cancel_mock:
                with mock.patch.object(scheduler_module.SCHEDULER, "stop") as stop_mock:
                    await scheduler_module.shutdown_scheduler_and_trading_signal_channel()
        stop_mock.assert_not_called()
        cancel_mock.assert_not_called()

    async def test_cancels_startup_cleanup_before_stop(self):
        shutdown_call_order: list[str] = []

        def track_cancel(*args, **kwargs) -> None:
            shutdown_call_order.append("cancel_startup_cleanup_trigger")

        def track_stop() -> None:
            shutdown_call_order.append("stop")

        scheduler_module._shutdown_done = False
        with mock.patch.object(scheduler_module.SCHEDULER, "is_initialized", return_value=True):
            with mock.patch(
                "octobot_node.scheduler.workflows_retention.cancel_startup_cleanup_trigger",
                side_effect=track_cancel,
            ):
                with mock.patch.object(
                    scheduler_module.SCHEDULER,
                    "stop",
                    side_effect=track_stop,
                ):
                    await scheduler_module.shutdown_scheduler_and_trading_signal_channel()

        assert shutdown_call_order == ["cancel_startup_cleanup_trigger", "stop"]

    async def test_initialize_scheduler_resets_shutdown_guard(self):
        init_call_order: list[str] = []

        def track_start() -> None:
            init_call_order.append("start")

        def track_register_schedules(*args, **kwargs) -> None:
            init_call_order.append("register_schedules")

        def track_schedule_startup_cleanup_trigger(*args, **kwargs) -> None:
            init_call_order.append("schedule_startup_cleanup_trigger")

        with mock.patch.object(scheduler_module.SCHEDULER, "create"):
            with mock.patch.object(
                scheduler_module.SCHEDULER,
                "start",
                side_effect=track_start,
            ):
                with mock.patch("octobot_node.scheduler.workflows.register_workflows"):
                    with mock.patch(
                        "octobot_node.scheduler.schedules.register_schedules",
                        side_effect=track_register_schedules,
                    ):
                        with mock.patch(
                            "octobot_node.scheduler.workflows_retention.schedule_startup_cleanup_trigger",
                            side_effect=track_schedule_startup_cleanup_trigger,
                        ):
                            scheduler_module._shutdown_done = True
                            scheduler_module.initialize_scheduler()
        assert scheduler_module._shutdown_done is False
        assert init_call_order == [
            "start",
            "register_schedules",
            "schedule_startup_cleanup_trigger",
        ]
