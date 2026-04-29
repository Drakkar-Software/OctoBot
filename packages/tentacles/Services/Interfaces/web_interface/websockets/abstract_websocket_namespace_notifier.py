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
import functools
import flask_login
import flask_socketio

import octobot_commons.logging as bot_logger
import tentacles.Services.Interfaces.web_interface as web_interface
import tentacles.Services.Interfaces.web_interface.login as login


class AbstractWebSocketNamespaceNotifier(flask_socketio.Namespace, web_interface.Notifier):

    def __init__(self, namespace=None):
        super(flask_socketio.Namespace, self).__init__(namespace)
        self.logger = bot_logger.get_logger(self.__class__.__name__)
        # constructor can be called in global project import, in this case manually enable logger
        self.logger.disable(False)
        self.clients_count = 0

    def all_clients_send_notifications(self, **kwargs) -> bool:
        raise NotImplementedError("all_clients_send_notifications is not implemented")

    def on_connect(self):
        self.clients_count += 1

    def on_disconnect(self, reason):
        # will be called after some time (requires timeout)
        self.clients_count -= 1

    def _has_clients(self):
        return self.clients_count > 0


def websocket_with_login_required_when_activated(func):
    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        # Use == because of the flask proxy (this is not a simple python None value)
        if login.is_login_required() and \
                (flask_login.current_user is None or not flask_login.current_user.is_authenticated):
            flask_socketio.disconnect(self)
        else:
            return func(self, *args, **kwargs)
    return wrapped
