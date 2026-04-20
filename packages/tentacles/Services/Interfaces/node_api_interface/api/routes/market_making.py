#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import typing

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse, Response

try:
    import tentacles.Trading.Mode.simple_market_making_trading_mode.api.api_handlers as market_making_handlers
except ImportError:
    # market making tentacles are not available
    pass

router = APIRouter(prefix="/market-making", tags=["market-making"])


@router.get("/ping")
def market_making_ping() -> Response:
    return Response(status_code=200, content=b"")


@router.post("/")
async def market_making_root(
    body: typing.Optional[dict] = Body(default=None),
) -> JSONResponse:
    payload, status_code = await market_making_handlers.dispatch_market_making_request(body)
    return JSONResponse(content=payload, status_code=status_code)
