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

import tentacles.Services.Interfaces.web_interface.websockets.protocol.wire_protocol as wire_protocol


def recv_ws_event(websocket) -> dict:
    frame = json.loads(websocket.receive_text())
    assert "event" in frame
    return frame


def send_ws_event(websocket, event: str, data=None) -> None:
    websocket.send_text(wire_protocol.encode_ws_event(event, data))
