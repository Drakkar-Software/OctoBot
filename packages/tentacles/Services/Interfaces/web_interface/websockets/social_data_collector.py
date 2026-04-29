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

import flask_socketio

import tentacles.Services.Interfaces.web_interface as web_interface
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.websockets as websockets


class SocialDataCollectorNamespace(websockets.AbstractWebSocketNamespaceNotifier):

    @staticmethod
    def _get_social_data_collector_status():
        social_data_collector_status, progress = models.get_social_data_collector_status()
        return {"status": social_data_collector_status, "progress": progress}

    @websockets.websocket_with_login_required_when_activated
    def on_social_data_collector_status(self):
        flask_socketio.emit("social_data_collector_status", self._get_social_data_collector_status())

    def all_clients_send_notifications(self, **kwargs) -> bool:
        if self._has_clients():
            try:
                self.socketio.emit("social_data_collector_status", self._get_social_data_collector_status(), namespace=self.namespace)
                return True
            except Exception as e:
                self.logger.exception(e, True, f"Error when sending social_data_collector_status: {e}")
        return False

    @websockets.websocket_with_login_required_when_activated
    def on_connect(self):
        super().on_connect()
        self.on_social_data_collector_status()


notifier = SocialDataCollectorNamespace('/social_data_collector')
web_interface.register_notifier(web_interface.SOCIAL_DATA_COLLECTOR_NOTIFICATION_KEY, notifier)
websockets.namespaces.append(notifier)
