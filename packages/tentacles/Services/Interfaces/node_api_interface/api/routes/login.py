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

from fastapi import APIRouter

try:
    from api.auth_errors import NodeAuthErrorDetail  # type: ignore[no-redef]
    from api.deps import LoginRateLimitedUser
    from api.rate_limits.rate_limit_response import RateLimitedDetail
except ImportError:
    from tentacles.Services.Interfaces.node_api_interface.api.auth_errors import NodeAuthErrorDetail
    from tentacles.Services.Interfaces.node_api_interface.api.deps import LoginRateLimitedUser  # type: ignore[no-redef]
    from tentacles.Services.Interfaces.node_api_interface.api.rate_limits.rate_limit_response import (  # type: ignore[no-redef]
        RateLimitedDetail,
    )
import octobot_node.models

router = APIRouter(tags=["login"])


@router.get(
    "/login/test",
    response_model=octobot_node.models.User,
    responses={
        401: {"model": NodeAuthErrorDetail, "description": "Authentication failed"},
        429: {"model": RateLimitedDetail, "description": "Too many login attempts"},
        503: {"model": NodeAuthErrorDetail, "description": "Node not configured"},
    },
)
def test_auth(current_user: LoginRateLimitedUser) -> typing.Any:
    return current_user
