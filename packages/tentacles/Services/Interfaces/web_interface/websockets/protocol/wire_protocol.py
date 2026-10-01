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

import json
import typing


def encode_ws_event(event: str, data: typing.Any = None) -> str:
    return json.dumps({"event": event, "data": data})


def decode_ws_event(text: str) -> tuple[str, typing.Any]:
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("WebSocket frame must be a JSON object")
    event = payload.get("event")
    if not isinstance(event, str):
        raise ValueError("WebSocket frame must include string 'event'")
    return event, payload.get("data")


def build_ws_client_url(
    host: str,
    namespace: str,
    *,
    secure: bool = False,
    base_path: str = "",
) -> str:
    scheme = "wss" if secure else "ws"
    path_prefix = base_path.rstrip("/")
    namespace_path = namespace if namespace.startswith("/") else f"/{namespace}"
    return f"{scheme}://{host}{path_prefix}{namespace_path}"
