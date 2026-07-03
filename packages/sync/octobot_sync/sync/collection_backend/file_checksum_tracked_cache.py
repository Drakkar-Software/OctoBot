#  Drakkar-Software OctoBot-Sync
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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


import dataclasses
import typing

import cachetools

import octobot_sync.sync.collection_backend.base_local_collection_storage as base_storage
import octobot_sync.sync.collection_backend.state_model as state_model


CacheKeyT = typing.TypeVar("CacheKeyT")
S = typing.TypeVar("S", bound=state_model.StateModel)


@dataclasses.dataclass(frozen=True, slots=True)
class CachedStateEnvelope(typing.Generic[S]):
    state: S
    file_checksum: str


class FileChecksumTrackedCache(typing.Generic[CacheKeyT, S]):
    """TTL cache that invalidates entries when the backing collection file changes."""

    def __init__(
        self,
        storage: base_storage.BaseLocalCollectionStorage,
        *,
        maxsize: int,
        ttl: float,
    ) -> None:
        self._storage = storage
        self._cache: cachetools.TTLCache[CacheKeyT, CachedStateEnvelope[S]] = cachetools.TTLCache(
            maxsize=maxsize,
            ttl=ttl,
        )

    def get_if_fresh(self, cache_key: CacheKeyT, storage_key: str) -> S | None:
        envelope = self._cache.get(cache_key)
        if envelope is None:
            return None
        current_checksum = self._storage.get_file_checksum(storage_key)
        if current_checksum != envelope.file_checksum:
            self._cache.pop(cache_key, None)
            return None
        return envelope.state

    def set(self, cache_key: CacheKeyT, storage_key: str, state: S) -> None:
        self._cache[cache_key] = CachedStateEnvelope(
            state=state,
            file_checksum=self._storage.get_file_checksum(storage_key),
        )
