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

import tentacles.Services.Interfaces.web_interface as web_interface
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.websockets.core.abstract_websocket_namespace_notifier as abstract_websocket_namespace_notifier_module
import tentacles.Services.Interfaces.web_interface.websockets.core.websocket_connection as websocket_connection_module


class DataCollectorNamespace(abstract_websocket_namespace_notifier_module.AbstractWebSocketNamespaceNotifier):

    @staticmethod
    def _get_data_collector_status():
        data_collector_status, progress = models.get_data_collector_status()
        return {"status": data_collector_status, "progress": progress}

    async def on_data_collector_status(self, connection: websocket_connection_module.WebSocketConnection) -> None:
        await self.registry.broadcast_async("data_collector_status", self._get_data_collector_status())

    def all_clients_send_notifications(self, **kwargs) -> bool:
        if self._has_clients():
            try:
                return self.registry.schedule_broadcast(
                    "data_collector_status",
                    self._get_data_collector_status(),
                )
            except Exception as error:
                self.logger.exception(error, True, f"Error when sending data_collector_status: {error}")
        return False

    async def on_connect(self, connection: websocket_connection_module.WebSocketConnection) -> None:
        await self.on_data_collector_status(connection)


notifier = DataCollectorNamespace('/data_collector')
web_interface.register_notifier(web_interface.DATA_COLLECTOR_NOTIFICATION_KEY, notifier)
