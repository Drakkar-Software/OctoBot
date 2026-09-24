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

from fastapi import Request

import octobot.community.wallet_backend as wallet_backend
import octobot_commons.in_process_rate_limit as in_process_rate_limit

try:
    from core.http_rate_limit import HTTPRateLimiter  # type: ignore[no-redef]
except ImportError:
    from tentacles.Services.Interfaces.node_api_interface.core.http_rate_limit import (
        HTTPRateLimiter,
    )

_RECOVER_CLIENT_IP_POLICY = in_process_rate_limit.FailureWindowPolicy(
    name="client_ip",
    max_failures=5,
    window_seconds=15 * 60,
)
_RECOVER_ADDRESS_POLICY = in_process_rate_limit.FailureWindowPolicy(
    name="address",
    max_failures=10,
    window_seconds=60 * 60,
    normalize_key=str.lower,
)

RECOVER_PASSPHRASE_RATE_LIMITED_DETAIL = (
    "Too many recovery attempts. Try again later."
)

RECOVER_PASSPHRASE_FAILURE_EXCEPTIONS: tuple[type[Exception], ...] = (
    wallet_backend.WalletNotFoundError,
    wallet_backend.WalletProofMismatchError,
    wallet_backend.InvalidPrivateKeyError,
    wallet_backend.PassphraseTooShortError,
    wallet_backend.WalletError,
)

_recover_passphrase_rate_limiter = HTTPRateLimiter(
    (_RECOVER_CLIENT_IP_POLICY, _RECOVER_ADDRESS_POLICY),
    rate_limited_detail=RECOVER_PASSPHRASE_RATE_LIMITED_DETAIL,
)


def get_recover_passphrase_rate_limiter() -> HTTPRateLimiter:
    return _recover_passphrase_rate_limiter


def recover_passphrase_rate_dimensions(
    body: typing.Any,
    request: Request,
) -> dict[str, str]:
    if request.client is not None:
        client_ip = request.client.host
    else:
        client_ip = "unknown"
    return {"client_ip": client_ip, "address": body.address}
