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
import contextlib

import flask
import starlette.applications
import starlette.routing
import starlette.websockets

import tentacles.Services.Interfaces.web_interface.asgi.wsgi_to_asgi as wsgi_to_asgi
import tentacles.Services.Interfaces.web_interface.util.uvicorn_log_util as uvicorn_log_util
import tentacles.Services.Interfaces.web_interface.websockets.core.runtime as ws_runtime
import tentacles.Services.Interfaces.web_interface.websockets.socket_namespaces as namespaces_package
import tentacles.Services.Interfaces.web_interface.websockets.server.websocket_endpoint as websocket_endpoint_module

_lifespan_web_loop: asyncio.AbstractEventLoop | None = None
_lifespan_previous_exception_handler = None


def teardown_web_interface_runtime() -> None:
    global _lifespan_web_loop, _lifespan_previous_exception_handler
    web_loop = _lifespan_web_loop
    previous_exception_handler = _lifespan_previous_exception_handler
    if web_loop is None:
        return
    _lifespan_web_loop = None
    _lifespan_previous_exception_handler = None
    ws_runtime.clear_web_loop()
    uvicorn_log_util.restore_exception_handler(web_loop, previous_exception_handler)


@contextlib.asynccontextmanager
async def _web_interface_lifespan(app: starlette.applications.Starlette):
    global _lifespan_web_loop, _lifespan_previous_exception_handler
    web_loop = asyncio.get_running_loop()
    previous_exception_handler = uvicorn_log_util.install_client_connection_reset_exception_handler(
        web_loop
    )
    ws_runtime.set_web_loop(web_loop)
    _lifespan_web_loop = web_loop
    _lifespan_previous_exception_handler = previous_exception_handler
    try:
        yield
    finally:
        teardown_web_interface_runtime()


def build_composite_asgi_app(flask_app: flask.Flask) -> starlette.applications.Starlette:
    flask_asgi = wsgi_to_asgi.WsgiToAsgi(flask_app)
    routes: list[starlette.routing.BaseRoute] = []
    for notifier in namespaces_package.namespaces:
        namespace_path = notifier.namespace

        async def endpoint(
            websocket: starlette.websockets.WebSocket,
            bound_notifier=notifier,
        ):
            await websocket_endpoint_module.websocket_endpoint(websocket, bound_notifier, flask_app)

        routes.append(starlette.routing.WebSocketRoute(namespace_path, endpoint))
    routes.append(starlette.routing.Mount("/", flask_asgi))
    return starlette.applications.Starlette(
        routes=routes,
        lifespan=_web_interface_lifespan,
    )
