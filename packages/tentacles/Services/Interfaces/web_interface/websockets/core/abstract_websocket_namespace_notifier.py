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

import inspect

import octobot_commons.logging as bot_logger

import tentacles.Services.Interfaces.web_interface as web_interface
import tentacles.Services.Interfaces.web_interface.websockets.core.namespace_registry as namespace_registry_module
import tentacles.Services.Interfaces.web_interface.websockets.core.websocket_connection as websocket_connection_module


class AbstractWebSocketNamespaceNotifier(web_interface.Notifier):

    def __init__(self, namespace: str):
        self.namespace = namespace
        self.registry = namespace_registry_module.NamespaceRegistry(namespace)
        self.logger = bot_logger.get_logger(self.__class__.__name__)
        self.logger.disable(False)

    def all_clients_send_notifications(self, **kwargs) -> bool:
        raise NotImplementedError("all_clients_send_notifications is not implemented")

    def _has_clients(self) -> bool:
        return self.registry.has_clients()

    async def on_connect(self, connection: websocket_connection_module.WebSocketConnection) -> None:
        pass

    async def on_disconnect(
        self,
        connection: websocket_connection_module.WebSocketConnection,
        reason=None,
    ) -> None:
        pass

    async def handle_client_event(
        self,
        connection: websocket_connection_module.WebSocketConnection,
        event: str,
        data,
    ) -> None:
        handler = getattr(self, f"on_{event}", None)
        if handler is None:
            return
        parameters = [
            parameter_name
            for parameter_name, parameter in inspect.signature(handler).parameters.items()
            if parameter_name != "self"
        ]
        if len(parameters) >= 2:
            await handler(connection, data)
        elif len(parameters) == 1:
            await handler(connection)
