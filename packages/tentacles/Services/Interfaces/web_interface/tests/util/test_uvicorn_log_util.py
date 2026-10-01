#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.

import asyncio
import logging

import mock

import tentacles.Services.Interfaces.web_interface.util.uvicorn_log_util as uvicorn_log_util


class TestUvicornHandshakeLogFilter:
    def test_allows_startup_message(self):
        handshake_filter = uvicorn_log_util.UvicornHandshakeLogFilter()
        record = logging.LogRecord(
            name="uvicorn.error",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Uvicorn running on http://127.0.0.1:5001 (Press CTRL+C to quit)",
            args=(),
            exc_info=None,
        )
        assert handshake_filter.filter(record) is True

    def test_rejects_websocket_accepted_message(self):
        handshake_filter = uvicorn_log_util.UvicornHandshakeLogFilter()
        record = logging.LogRecord(
            name="uvicorn.error",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='127.0.0.1:56993 - "WebSocket /notifications" [accepted]',
            args=(),
            exc_info=None,
        )
        assert handshake_filter.filter(record) is False


class TestShouldIgnoreClientConnectionResetContext:
    def test_ignores_connection_reset_in_connection_lost_callback(self):
        context = {
            "message": "Exception in callback _ProactorBasePipeTransport._call_connection_lost()",
            "exception": ConnectionResetError(10054, "connection reset"),
        }
        assert uvicorn_log_util._should_ignore_client_connection_reset_context(context) is True

    def test_does_not_ignore_unrelated_runtime_error(self):
        context = {
            "message": "Error in task",
            "exception": RuntimeError("something else"),
        }
        assert uvicorn_log_util._should_ignore_client_connection_reset_context(context) is False


class TestInstallClientConnectionResetExceptionHandler:
    def test_ignores_benign_reset_and_delegates_other_errors(self):
        web_loop = asyncio.new_event_loop()
        previous_handler = mock.Mock()
        web_loop.set_exception_handler(previous_handler)
        uvicorn_log_util.install_client_connection_reset_exception_handler(web_loop)

        web_loop.get_exception_handler()(
            web_loop,
            {
                "message": "Exception in callback _ProactorBasePipeTransport._call_connection_lost()",
                "exception": ConnectionResetError(10054, "reset"),
            },
        )
        previous_handler.assert_not_called()

        web_loop.get_exception_handler()(
            web_loop,
            {"message": "task failed", "exception": ValueError("bad")},
        )
        previous_handler.assert_called_once()
        web_loop.close()
