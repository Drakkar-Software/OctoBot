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

import copy
import flask_socketio

import tentacles.Services.Interfaces.web_interface as web_interface
import tentacles.Services.Interfaces.web_interface.websockets as websockets


class NotificationsNamespace(websockets.AbstractWebSocketNamespaceNotifier):

    @staticmethod
    def _get_update_data():
        return {
            "notifications": web_interface.get_notifications(),
            "errors_count": web_interface.get_errors_count()
        }

    def _client_context_send_notifications(self):
        flask_socketio.emit("update", self._get_update_data())

    def all_clients_send_notifications(self, **kwargs) -> bool:
        if self._has_clients():
            try:
                self.socketio.emit("update", self._get_update_data(), namespace=self.namespace)
                return True
            except Exception as e:
                self.logger.exception(e, True, f"Error when sending web notification: {e}")
        return False

    @websockets.websocket_with_login_required_when_activated
    def on_connect(self):
        super().on_connect()
        self._client_context_send_notifications()
        web_interface.flush_notifications()


notifier = NotificationsNamespace('/notifications')
web_interface.register_notifier(web_interface.GENERAL_NOTIFICATION_KEY, notifier)
websockets.namespaces.append(notifier)
