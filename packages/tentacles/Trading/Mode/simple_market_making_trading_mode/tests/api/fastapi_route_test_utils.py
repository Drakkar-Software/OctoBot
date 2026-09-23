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

# Keep in sync with node_api_interface/tests/fastapi_route_test_utils.py

import typing

import fastapi.routing
import starlette.routing


def collect_effective_http_paths(
    routes: typing.Sequence[starlette.routing.BaseRoute],
) -> set[str]:
    paths: set[str] = set()
    for route_context in fastapi.routing.iter_route_contexts(routes):
        if isinstance(route_context.original_route, fastapi.routing.APIRoute):
            path = route_context.path
            if path is not None:
                paths.add(path)
    return paths
