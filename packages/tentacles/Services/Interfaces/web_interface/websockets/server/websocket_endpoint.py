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
import starlette.websockets
import octobot_commons.logging as bot_logger

import tentacles.Services.Interfaces.web_interface.websockets.core.websocket_auth as websocket_auth
import tentacles.Services.Interfaces.web_interface.websockets.core.websocket_connection as websocket_connection_module
import tentacles.Services.Interfaces.web_interface.websockets.protocol.wire_protocol as wire_protocol


async def websocket_endpoint(
    websocket: starlette.websockets.WebSocket,
    notifier,
    flask_app: flask.Flask,
):
    logger = bot_logger.get_logger("WebSocketEndpoint")
    connection = websocket_connection_module.WebSocketConnection(websocket)
    if not websocket_auth.is_websocket_authenticated(flask_app, connection):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    notifier.registry.add(connection)
    try:
        await notifier.on_connect(connection)
        while True:
            message = await websocket.receive_text()
            try:
                event, data = wire_protocol.decode_ws_event(message)
            except (ValueError, TypeError) as error:
                logger.debug("Ignored invalid WebSocket frame on %s: %s", notifier.namespace, error)
                continue
            if not websocket_auth.is_websocket_authenticated(flask_app, connection):
                await websocket.close(code=4401)
                return
            await notifier.handle_client_event(connection, event, data)
    except starlette.websockets.WebSocketDisconnect:
        pass
    except Exception as error:
        logger.exception(error, True, f"WebSocket error on {notifier.namespace}: {error}")
    finally:
        notifier.registry.remove(connection)
        await notifier.on_disconnect(connection)
