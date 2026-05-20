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


import typing

import cachetools

import octobot_sync.sync.collection_backend.abstract_local_collection_provider as abstract_provider
import octobot_sync.sync.collection_backend.base_local_collection_storage as base_storage
import octobot_sync.sync.collection_backend.single_item_local_collection_storage as single_item_storage
import octobot_sync.sync.collection_backend.state_model as state_model


S = typing.TypeVar("S", bound=state_model.StateModel)


class SingleItemLocalCollectionProvider(abstract_provider.AbstractLocalCollectionProvider[S]):
    """
    Provider for collections with one encrypted state file per identifier.

    Exposes whole-state load/save only (no list CRUD). Identifiers are typically
    ``<wallet_address>/<account_id>`` under the collection root.
    """

    @staticmethod
    def _create_storage(
        collection: str,
        base_folder: typing.Optional[str] = None,
    ) -> base_storage.BaseLocalCollectionStorage:
        return single_item_storage.SingleItemLocalCollectionStorage(
            collection=collection,
            base_folder=base_folder,
        )

    def _setup_caches(self) -> None:
        self._state_cache: cachetools.TTLCache[tuple[str, str], S] = cachetools.TTLCache(
            maxsize=self._CACHE_MAXSIZE,
            ttl=self._CACHE_TTL_SECONDS,
        )

    def _build_identifier(self, address: str, account_id: str) -> str:
        return (
            f"{self._storage._sanitize_address(address)}/{self._storage._sanitize_address(account_id)}"
        )

    def _get_cached_state(self, address: str, account_id: str) -> S | None:
        return self._state_cache.get((address, account_id))

    def _set_cached_state(self, address: str, account_id: str, state: S) -> None:
        self._state_cache[(address, account_id)] = state

    def load_state(self, address: str, account_id: str) -> S:
        cached_state = self._get_cached_state(address, account_id)
        if cached_state is not None:
            return cached_state
        identifier = self._build_identifier(address, account_id)
        wallet_private_key = self._get_wallet_private_key(address)
        persisted_state = self._storage.load_state(
            identifier,
            wallet_private_key,
            self.STATE_CLASS,
        )
        self._set_cached_state(address, account_id, persisted_state)
        return persisted_state

    def save_state(self, address: str, account_id: str, state: S) -> None:
        identifier = self._build_identifier(address, account_id)
        wallet_private_key = self._get_wallet_private_key(address)
        self._storage.save_state(identifier, wallet_private_key, state)
        self._set_cached_state(address, account_id, state)

    def load_state_encrypted(self, address: str, account_id: str) -> dict[str, str]:
        identifier = self._build_identifier(address, account_id)
        return self._storage.load_items_encrypted(identifier)
