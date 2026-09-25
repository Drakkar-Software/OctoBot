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

from fastapi import Request

import octobot_commons.in_process_rate_limit as in_process_rate_limit

try:
    from tentacles.Services.Interfaces.node_api_interface.core.http_rate_limit import (
        HTTPRateLimiter,
    )
except ImportError:
    from core.http_rate_limit import HTTPRateLimiter  # type: ignore[no-redef]


_LOGIN_CLIENT_IP_POLICY = in_process_rate_limit.FailureWindowPolicy(
    name="client_ip",
    max_failures=10,
    window_seconds=15 * 60,
)

LOGIN_RATE_LIMITED_DETAIL = "Too many login attempts. Try again later."

_login_rate_limiter = HTTPRateLimiter(
    (_LOGIN_CLIENT_IP_POLICY,),
    rate_limited_detail=LOGIN_RATE_LIMITED_DETAIL,
)


def get_login_rate_limiter() -> HTTPRateLimiter:
    return _login_rate_limiter


def login_client_ip(request: Request) -> str:
    if request.client is not None:
        return request.client.host
    return "unknown"
