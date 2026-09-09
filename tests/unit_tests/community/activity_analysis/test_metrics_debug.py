#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
import mock
import pytest

import octobot.community.activity_analysis.metrics_debug as metrics_debug_module
import octobot.constants as constants


class Test_log_activity:
    def test_no_op_when_debug_disabled(self):
        logger_mock = mock.Mock()
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", False), \
                mock.patch.object(metrics_debug_module, "_LOGGER", logger_mock):
            metrics_debug_module.log_activity("emit_count_skipped", event="node_process_start")
        logger_mock.info.assert_not_called()

    def test_logs_at_info_when_debug_enabled(self):
        logger_mock = mock.Mock()
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(metrics_debug_module, "_LOGGER", logger_mock):
            metrics_debug_module.log_activity(
                "emit_count_skipped",
                event="node_process_start",
                reason="metrics_disabled",
            )
        logger_mock.info.assert_called_once_with(
            "Activity metrics %s %s",
            "emit_count_skipped",
            "event=node_process_start reason=metrics_disabled",
        )


class Test_wrapped_exception:
    def test_does_not_propagate_and_logs_exception(self):
        logger_mock = mock.Mock()

        @metrics_debug_module.wrapped_exception
        def failing_hook() -> None:
            raise TypeError("cannot pickle '_asyncio.Task' object")

        with mock.patch.object(metrics_debug_module, "_LOGGER", logger_mock):
            failing_hook()
        logger_mock.exception.assert_called_once()
        exception_call = logger_mock.exception.call_args
        assert isinstance(exception_call.args[0], TypeError)
        assert exception_call.args[1] is True
        assert exception_call.args[2] == (
            "Activity metrics hook failed hook=failing_hook: cannot pickle '_asyncio.Task' object"
        )


class Test_wrapped_exception_async:
    @pytest.mark.asyncio
    async def test_does_not_propagate_and_logs_exception(self):
        logger_mock = mock.Mock()

        @metrics_debug_module.wrapped_exception_async
        async def failing_hook_async() -> None:
            raise TypeError("cannot pickle '_asyncio.Task' object")

        with mock.patch.object(metrics_debug_module, "_LOGGER", logger_mock):
            await failing_hook_async()
        logger_mock.exception.assert_called_once()
        exception_call = logger_mock.exception.call_args
        assert isinstance(exception_call.args[0], TypeError)
        assert exception_call.args[1] is True
        assert exception_call.args[2] == (
            "Activity metrics hook failed hook=failing_hook_async: cannot pickle '_asyncio.Task' object"
        )
