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
import typing

import octobot_commons.logging as bot_logger

import tentacles.Services.Interfaces.web_interface.websockets.core.runtime as ws_runtime
import tentacles.Services.Interfaces.web_interface.websockets.core.websocket_connection as websocket_connection_module


class NamespaceRegistry:
    def __init__(self, namespace_path: str):
        self.namespace_path = namespace_path
        self._connections: set[websocket_connection_module.WebSocketConnection] = set()
        self._logger = bot_logger.get_logger(self.__class__.__name__)

    def add(self, connection: websocket_connection_module.WebSocketConnection) -> None:
        self._connections.add(connection)

    def remove(self, connection: websocket_connection_module.WebSocketConnection) -> None:
        self._connections.discard(connection)

    def has_clients(self) -> bool:
        return bool(self._connections)

    async def broadcast_async(self, event: str, data: typing.Any = None) -> None:
        if not self._connections:
            return
        stale_connections: list[websocket_connection_module.WebSocketConnection] = []
        for connection in list(self._connections):
            try:
                await connection.send_event(event, data)
            except Exception as error:
                self._logger.debug(
                    "Dropping WebSocket client on %s after send failure: %s",
                    self.namespace_path,
                    error,
                )
                stale_connections.append(connection)
        for connection in stale_connections:
            self.remove(connection)

    def schedule_broadcast(self, event: str, data: typing.Any = None) -> bool:
        if not self.has_clients():
            return False
        web_loop = ws_runtime.try_get_web_loop()
        if web_loop is None:
            self._logger.debug(
                "Skipped WebSocket broadcast on %s: web loop not running",
                self.namespace_path,
            )
            return False
        asyncio.run_coroutine_threadsafe(self.broadcast_async(event, data), web_loop)
        return True
