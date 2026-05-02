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
import collections
import time
import typing

import octobot_commons.constants as commons_constants
import octobot_commons.logging as commons_logging

_logger = commons_logging.get_logger("RPMLimiter")
_WINDOW_SECONDS = float(commons_constants.MINUTE_TO_SECONDS)


class RPMLimiter:
    """Sliding-window requests-per-minute limiter. Async-safe."""

    def __init__(self, rpm: int, name: str = ""):
        if rpm <= 0:
            raise ValueError(f"rpm must be > 0, got {rpm}")
        self._rpm = rpm
        self._name = name
        self._lock = asyncio.Lock()
        self._timestamps: typing.Deque[float] = collections.deque()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            self._evict(now)
            if len(self._timestamps) >= self._rpm:
                wait_for = self._timestamps[0] + _WINDOW_SECONDS - now
                if wait_for > 0:
                    _logger.debug(
                        f"{self._name} RPM cap hit ({self._rpm}/min); sleeping {wait_for:.2f}s"
                    )
                    await asyncio.sleep(wait_for)
                    self._evict(time.monotonic())
            self._timestamps.append(time.monotonic())

    def _evict(self, now: float) -> None:
        # Use <= so a timestamp exactly at the window boundary is considered expired.
        cutoff = now - _WINDOW_SECONDS
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()
