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

import fastapi.routing

import tentacles.Trading.Mode.simple_market_making_trading_mode.api.simple_market_making_trading_route_provider as simple_market_making_trading_route_provider


def _api_route_index(router) -> set[tuple[str, str]]:
    return {
        (http_method, route.path)
        for route in router.routes
        if isinstance(route, fastapi.routing.APIRoute)
        for http_method in route.methods
    }


class TestSimpleMarketMakingRouteProviderGetRouter:
    def test_prefix_tags_and_endpoints(self) -> None:
        provider = simple_market_making_trading_route_provider.SimpleMarketMakingRouteProvider()
        router = provider.get_router()
        assert router.prefix == "/market-making"
        assert router.tags == ["market-making"]
        path_methods = _api_route_index(router)
        assert ("GET", "/market-making/ping") in path_methods
        assert ("POST", "/market-making/") in path_methods
