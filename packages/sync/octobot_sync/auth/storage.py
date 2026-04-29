#  This file is part of OctoBot Sync (https://github.com/Drakkar-Software/OctoBot)
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

"""Storage adapter protocol and in-memory implementation for nonce dedup."""

import time
from typing import Protocol


class AbstractStorageAdapter(Protocol):
    """Atomic key-value store with TTL."""

    async def set_if_absent(self, key: str, value: str, ttl_ms: int) -> bool: ...
    async def set(self, key: str, value: str, ttl_ms: int | None = None) -> None: ...
    async def get(self, key: str) -> str | None: ...
    async def delete(self, key: str) -> None: ...


class MemoryStorageAdapter:
    """In-memory AbstractStorageAdapter for testing."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float]] = {}

    def _cleanup(self) -> None:
        now = time.time() * 1000
        expired = [k for k, (_, exp) in self._store.items() if exp < now]
        for k in expired:
            del self._store[k]

    async def set_if_absent(self, key: str, value: str, ttl_ms: int) -> bool:
        self._cleanup()
        if key in self._store:
            return False
        self._store[key] = (value, time.time() * 1000 + ttl_ms)
        return True

    async def set(self, key: str, value: str, ttl_ms: int | None = None) -> None:
        exp = time.time() * 1000 + (ttl_ms if ttl_ms is not None else 999_999_999_999)
        self._store[key] = (value, exp)

    async def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None or entry[1] < time.time() * 1000:
            self._store.pop(key, None)
            return None
        return entry[0]

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)
