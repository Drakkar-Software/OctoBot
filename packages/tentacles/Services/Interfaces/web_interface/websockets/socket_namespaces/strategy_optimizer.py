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


class StrategyOptimizerNamespace(abstract_websocket_namespace_notifier_module.AbstractWebSocketNamespaceNotifier):

    @staticmethod
    def _get_strategy_optimizer_status():
        status, progress, overall_progress, _remaining_time, errors = models.get_optimizer_status()
        return {
            "status": status,
            "progress": progress,
            "overall_progress": overall_progress,
            "errors": errors,
        }

    async def on_strategy_optimizer_status(
        self,
        connection: websocket_connection_module.WebSocketConnection,
    ) -> None:
        await self.registry.broadcast_async(
            "strategy_optimizer_status",
            self._get_strategy_optimizer_status(),
        )

    def all_clients_send_notifications(self, **kwargs) -> bool:
        if self._has_clients():
            try:
                return self.registry.schedule_broadcast(
                    "strategy_optimizer_status",
                    self._get_strategy_optimizer_status(),
                )
            except Exception as error:
                self.logger.exception(error, True, f"Error when sending strategy_optimizer_status: {error}")
        return False

    async def on_connect(self, connection: websocket_connection_module.WebSocketConnection) -> None:
        await self.on_strategy_optimizer_status(connection)


notifier = StrategyOptimizerNamespace('/strategy_optimizer')
web_interface.register_notifier(web_interface.STRATEGY_OPTIMIZER_NOTIFICATION_KEY, notifier)
