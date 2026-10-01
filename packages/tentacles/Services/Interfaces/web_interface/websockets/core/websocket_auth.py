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

import flask
import flask_login

import tentacles.Services.Interfaces.web_interface.login as login_module
import tentacles.Services.Interfaces.web_interface.websockets.core.websocket_connection as websocket_connection_module


def is_websocket_authenticated(
    flask_app: flask.Flask,
    connection: websocket_connection_module.WebSocketConnection,
) -> bool:
    if not login_module.is_login_required():
        return True
    cookie_header = connection.headers.get("cookie", "")
    with flask_app.test_request_context("/", headers={"Cookie": cookie_header}):
        user = flask_login.current_user
        return user is not None and getattr(user, "is_authenticated", False)
