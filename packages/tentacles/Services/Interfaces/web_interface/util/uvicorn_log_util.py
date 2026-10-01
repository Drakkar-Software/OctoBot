#  Drakkar-Software OctoBot-Tentacles
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
import logging
import re

import tentacles.Services.Interfaces.web_interface.constants as constants

_WEBSOCKET_HANDSHAKE_STATUS_PATTERN = re.compile(r'"WebSocket [^"]+" \d+$')

_WEBSOCKETS_LOGGER_NAMES = (
    "websockets",
    "websockets.server",
)


class UvicornHandshakeLogFilter(logging.Filter):
    """
    Drop uvicorn.error INFO lines for WebSocket handshakes only.
    Startup/shutdown and real errors are kept.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if "WebSocket" not in message:
            return True
        if "[accepted]" in message:
            return False
        if _WEBSOCKET_HANDSHAKE_STATUS_PATTERN.search(message):
            return False
        return True


def minimal_uvicorn_config_kwargs() -> dict:
    return {
        "log_level": "info",
        "access_log": True,
        "timeout_graceful_shutdown": constants.UVICORN_GRACEFUL_SHUTDOWN_SECONDS,
        "timeout_keep_alive": constants.UVICORN_TIMEOUT_KEEP_ALIVE_SECONDS,
    }


_CONNECTION_LOST_CALLBACK_MARKER = "_call_connection_lost"


def _is_benign_client_connection_reset(context: dict) -> bool:
    exception = context.get("exception")
    if isinstance(exception, ConnectionResetError):
        return True
    if isinstance(exception, OSError) and getattr(exception, "winerror", None) == 10054:
        return True
    return False


def _should_ignore_client_connection_reset_context(context: dict) -> bool:
    if not _is_benign_client_connection_reset(context):
        return False
    message = context.get("message", "")
    if _CONNECTION_LOST_CALLBACK_MARKER in message:
        return True
    return isinstance(context.get("exception"), ConnectionResetError)


def install_client_connection_reset_exception_handler(loop: asyncio.AbstractEventLoop):
    previous_handler = loop.get_exception_handler()

    def exception_handler(inner_loop: asyncio.AbstractEventLoop, context: dict) -> None:
        if _should_ignore_client_connection_reset_context(context):
            return
        if previous_handler is not None:
            previous_handler(inner_loop, context)
        else:
            inner_loop.default_exception_handler(context)

    loop.set_exception_handler(exception_handler)
    return previous_handler


def restore_exception_handler(loop: asyncio.AbstractEventLoop, previous_handler) -> None:
    loop.set_exception_handler(previous_handler)


def apply_minimal_uvicorn_logging() -> None:
    for logger_name in _WEBSOCKETS_LOGGER_NAMES:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    if not any(
        isinstance(existing_filter, UvicornHandshakeLogFilter)
        for existing_filter in uvicorn_error_logger.filters
    ):
        uvicorn_error_logger.addFilter(UvicornHandshakeLogFilter())
