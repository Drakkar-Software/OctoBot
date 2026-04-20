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

import typing

import fastapi
import fastapi.responses

import tentacles.Services.Interfaces.node_api_interface.api.route_provider as route_provider
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.api_handlers as market_making_handlers


class SimpleMarketMakingRouteProvider(route_provider.RouteProvider):
    ROUTE_TYPE: typing.ClassVar[route_provider.RouteType] = (
        route_provider.RouteType.TENTACLES
    )

    def get_router(self) -> fastapi.APIRouter:
        router = fastapi.APIRouter(
            prefix="/market-making", tags=["market-making"]
        )

        @router.get("/ping")
        def market_making_ping() -> fastapi.responses.Response:
            return fastapi.responses.Response(status_code=200, content=b"")

        @router.post("/")
        async def market_making_root(
            body: typing.Optional[dict] = fastapi.Body(default=None),
        ) -> fastapi.responses.JSONResponse:
            (
                payload,
                response_status_code,
            ) = await market_making_handlers.dispatch_market_making_request(body)
            return fastapi.responses.JSONResponse(
                content=payload, status_code=response_status_code
            )

        return router
