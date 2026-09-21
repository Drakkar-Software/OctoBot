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

import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

_MAX_ATTEMPTS = 10
_WINDOW_SECONDS = 15 * 60

_lock = threading.Lock()
_attempts_by_client: dict[str, list[float]] = defaultdict(list)


def _client_key(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host


def enforce_recover_passphrase_rate_limit(request: Request) -> None:
    """Best-effort in-process rate limit for unauthenticated passphrase recovery."""
    client_key = _client_key(request)
    now = time.monotonic()
    with _lock:
        recent = [stamp for stamp in _attempts_by_client[client_key] if now - stamp < _WINDOW_SECONDS]
        if len(recent) >= _MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many recovery attempts. Try again later.",
            )
        recent.append(now)
        _attempts_by_client[client_key] = recent


def reset_recover_passphrase_rate_limits_for_tests() -> None:
    with _lock:
        _attempts_by_client.clear()
