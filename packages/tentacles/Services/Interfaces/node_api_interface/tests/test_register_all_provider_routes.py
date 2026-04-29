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

import fastapi
import fastapi.routing

import tentacles.Services.Interfaces.node_api_interface.api.route_provider as route_provider


def _api_route_paths(api_router: fastapi.APIRouter) -> set[str]:
    return {
        route.path
        for route in api_router.routes
        if isinstance(route, fastapi.routing.APIRoute)
    }


class RouteProviderTestAlpha(route_provider.RouteProvider):
    ROUTE_TYPE: typing.ClassVar[route_provider.RouteType] = (
        route_provider.RouteType.TENTACLES
    )

    def get_router(self) -> fastapi.APIRouter:
        router = fastapi.APIRouter()

        @router.get("/route-provider-test-alpha")
        def route_provider_test_alpha() -> dict[str, str]:
            return {"registered": "alpha"}

        return router


class RouteProviderTestAbstractInName(route_provider.RouteProvider):
    """
    ``class_inspector.is_abstract_using_inspection_and_class_naming`` treats any
    class name containing the substring "abstract" as not installable.
    """

    def get_router(self) -> fastapi.APIRouter:
        router = fastapi.APIRouter()

        @router.get("/route-provider-abstract-in-name-skip")
        def route_do_not_register() -> dict[str, str]:
            return {"should": "not appear"}

        return router


class UnimplementedRouteProvider(route_provider.RouteProvider):
    pass


class TestRegisterAllProviderRoutes:
    def test_includes_routers_from_concrete_subclasses(self) -> None:
        api_router = fastapi.APIRouter()
        route_provider.register_all_provider_routes(api_router)
        paths = _api_route_paths(api_router)
        assert "/tentacles/route-provider-test-alpha" in paths

    def test_skips_class_unimplemented_get_router(self) -> None:
        assert UnimplementedRouteProvider in route_provider.RouteProvider.__subclasses__()
        api_router = fastapi.APIRouter()
        route_provider.register_all_provider_routes(api_router)
        paths = _api_route_paths(api_router)
        assert not any("unimplemented" in path for path in paths)

    def test_skips_concrete_class_with_abstract_in_name(self) -> None:
        api_router = fastapi.APIRouter()
        route_provider.register_all_provider_routes(api_router)
        paths = _api_route_paths(api_router)
        assert "/route-provider-abstract-in-name-skip" not in paths
