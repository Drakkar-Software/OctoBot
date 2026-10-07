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


_web_loop: asyncio.AbstractEventLoop | None = None


def set_web_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _web_loop
    _web_loop = loop


def get_web_loop() -> asyncio.AbstractEventLoop:
    if _web_loop is None:
        raise RuntimeError("Web interface WebSocket loop is not initialized")
    return _web_loop


def clear_web_loop() -> None:
    global _web_loop
    _web_loop = None


def try_get_web_loop() -> asyncio.AbstractEventLoop | None:
    return _web_loop
