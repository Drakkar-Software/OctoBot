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


import abc
import typing

import cachetools

import octobot.community.authentication as community_authentication
import octobot_sync.sync.collection_backend.base_local_collection_storage as base_storage
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_backend.state_model as state_model


T = typing.TypeVar("T")
S = typing.TypeVar("S", bound=state_model.StateModel)


class BaseLocalCollectionProvider(typing.Generic[T, S], abc.ABC):
    """
    Generic provider exposing CRUD operations on typed pydantic model items ``T``.

    Items are grouped per wallet address and persisted via a BaseLocalCollectionStorage
    inside a typed pydantic state model ``S`` (with version + items list keyed by
    ``ITEMS_KEY``).  Subclasses must set the class variables and implement
    ``_get_item_id``.
    """
    COLLECTION: str = None # type: ignore
    STATE_VERSION: str = None  # type: ignore
    STATE_CLASS: type[S] = None  # type: ignore
    ITEMS_KEY: str = None  # type: ignore

    def __init__(
        self,
        base_folder: typing.Optional[str] = None,
    ) -> None:
        self._storage = self._create_storage(self.COLLECTION, base_folder)
        self._cache: cachetools.TTLCache[str, list[T]] = cachetools.TTLCache(
            maxsize=1024,
            ttl=12 * 60 * 60,
        )

    @staticmethod
    def _create_storage(
        collection: str,
        base_folder: typing.Optional[str] = None,
    ) -> base_storage.BaseLocalCollectionStorage:
        return base_storage.BaseLocalCollectionStorage(
            collection=collection,
            base_folder=base_folder,
        )

    @abc.abstractmethod
    def _get_item_id(self, item: T) -> str:
        """Return the unique identifier of a model instance."""

    def _get_wallet_private_key(self, address: str) -> str:
        wallet = community_authentication.CommunityAuthentication.instance().get_wallet(address)
        return wallet.private_key

    def _get_cached_items(self, address: str) -> list[T] | None:
        cached = self._cache.get(address)
        if cached is None:
            return None
        return list(cached)

    def _set_cached_items(self, address: str, items: list[T]) -> None:
        self._cache[address] = list(items)

    def _items_from_state(self, state: state_model.StateModel) -> list[T]:
        """Deserialize a decrypted state dict via STATE_CLASS and extract items."""
        return getattr(state, self.ITEMS_KEY) or []

    def _items_to_state(self, items: list[T]) -> state_model.StateModel:
        """Construct a STATE_CLASS instance from items and serialize it."""
        return self.STATE_CLASS(    # pylint: disable=not-callable
            **{
                "version": self.STATE_VERSION,
                self.ITEMS_KEY: items
            },
        )

    def _refresh_cache(self, address: str) -> list[T]:
        wallet_private_key = self._get_wallet_private_key(address)
        try:
            persisted_state = self._storage.load_state(address, wallet_private_key, self.STATE_CLASS)
        except collection_errors.CollectionNoDataError:
            items: list[T] = []
        else:
            items = self._items_from_state(persisted_state)
        self._set_cached_items(address, items)
        return items

    def _persist_and_cache(self, address: str, items: list[T]) -> None:
        wallet_private_key = self._get_wallet_private_key(address)
        state = self._items_to_state(items)
        self._storage.save_state(address, wallet_private_key, state)
        self._set_cached_items(address, items)

    # -- public CRUD --

    def list_items_encrypted(self, address: str) -> dict[str, str]:
        """Return the raw encrypted blob from disk, bypassing cache and decryption.

        Raises ``CollectionNoDataError`` when no file exists for ``address``.
        """
        return self._storage.load_items_encrypted(address)

    def list_items(self, address: str) -> list[T]:
        cached = self._get_cached_items(address)
        if cached is not None:
            return cached
        return self._refresh_cache(address)

    def get_item(self, address: str, item_id: str) -> T:
        for item in self.list_items(address):
            if self._get_item_id(item) == item_id:
                return item
        raise collection_errors.ItemNotFoundError(
            f"Item {item_id} not found for address {address}"
        )

    def create_item(self, address: str, item: T) -> T:
        items = self._refresh_cache(address)
        item_id = self._get_item_id(item)
        if any(self._get_item_id(existing) == item_id for existing in items):
            raise collection_errors.DuplicateItemError(
                f"Item {item_id} already exists for address {address}"
            )
        items.append(item)
        self._persist_and_cache(address, items)
        return item

    def update_item(self, address: str, item: T) -> T:
        items = self._refresh_cache(address)
        item_id = self._get_item_id(item)
        for index, existing in enumerate(items):
            if self._get_item_id(existing) == item_id:
                items[index] = item
                self._persist_and_cache(address, items)
                return item
        raise collection_errors.ItemNotFoundError(
            f"Item {item_id} not found for address {address}"
        )

    def delete_item(self, address: str, item_id: str) -> None:
        items = self._refresh_cache(address)
        remaining = [item for item in items if self._get_item_id(item) != item_id]
        if len(remaining) == len(items):
            raise collection_errors.ItemNotFoundError(
                f"Item {item_id} not found for address {address}"
            )
        self._persist_and_cache(address, remaining)
