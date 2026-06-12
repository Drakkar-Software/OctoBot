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

import octobot_sync.sync.collection_backend.abstract_local_collection_provider as abstract_provider
import octobot_sync.sync.collection_backend.base_local_collection_storage as base_storage
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_backend.state_model as state_model
import octobot_sync.sync.collection_backend.tolerant_state_loading as tolerant_state_loading


T = typing.TypeVar("T")
S = typing.TypeVar("S", bound=state_model.StateModel)


class BaseLocalCollectionProvider(
    abstract_provider.AbstractLocalCollectionProvider[S],
    typing.Generic[T, S],
    abc.ABC,
):
    """
    Generic provider exposing CRUD operations on typed pydantic model items ``T``.

    Items are grouped per wallet address and persisted via a BaseLocalCollectionStorage
    inside a typed pydantic state model ``S`` (with version + items list keyed by
    ``ITEMS_KEY``).  Subclasses must set the class variables and implement
    ``_get_item_id``.  The full state envelope is cached per address so updates to
    one collection field preserve other fields on save.
    """
    ITEMS_KEY: str = None  # type: ignore
    MODEL_SANITIZERS: typing.ClassVar[
        typing.Optional[dict[type, tolerant_state_loading.ModelSanitizer]]
    ] = None
    MODEL_FALLBACKS: typing.ClassVar[
        typing.Optional[dict[type, tolerant_state_loading.ModelFallback]]
    ] = None

    @staticmethod
    def _create_storage(
        collection: str,
        base_folder: typing.Optional[str] = None,
    ) -> base_storage.BaseLocalCollectionStorage:
        return base_storage.BaseLocalCollectionStorage(
            collection=collection,
            base_folder=base_folder,
        )

    def _setup_caches(self) -> None:
        self._cache: cachetools.TTLCache[str, S] = cachetools.TTLCache(
            maxsize=self._CACHE_MAXSIZE,
            ttl=self._CACHE_TTL_SECONDS,
        )

    @abc.abstractmethod
    def _get_item_id(self, item: T) -> str:
        """Return the unique identifier of a model instance."""

    def _get_item_id_for_key(self, items_key: str, item: typing.Any) -> str:
        if items_key != self.ITEMS_KEY:
            raise collection_errors.UnsupportedItemsKeyError(
                f"Unsupported items key {items_key!r} for {self.__class__.__name__}"
            )
        return self._get_item_id(item)

    def _get_cached_state(self, address: str) -> S | None:
        return self._cache.get(address)

    def _set_cached_state(self, address: str, state: S) -> None:
        self._cache[address] = state

    def _empty_state(self) -> S:
        return typing.cast(
            S,
            self.STATE_CLASS(    # pylint: disable=not-callable
                version=self.STATE_VERSION,
                **{self.ITEMS_KEY: []},
            ),
        )

    def _items_from_state(self, state: state_model.StateModel, items_key: str) -> list:
        return getattr(state, items_key) or []

    def _replace_state_items(self, state: S, items_key: str, items: list) -> S:
        return typing.cast(S, state.model_copy(update={items_key: items}))

    def _load_state(self, address: str) -> S:
        cached_state = self._get_cached_state(address)
        if cached_state is not None:
            return cached_state
        wallet_private_key = self._get_wallet_private_key(address)
        try:
            persisted_state = typing.cast(
                S,
                self._storage.load_state(
                    address,
                    wallet_private_key,
                    self.STATE_CLASS,
                    model_sanitizers=self.MODEL_SANITIZERS,
                    model_fallbacks=self.MODEL_FALLBACKS,
                ),
            )
        except collection_errors.CollectionNoDataError:
            persisted_state = self._empty_state()
        self._set_cached_state(address, persisted_state)
        return persisted_state

    def _save_state(self, address: str, state: S) -> None:
        wallet_private_key = self._get_wallet_private_key(address)
        self._storage.save_state(address, wallet_private_key, state)
        self._set_cached_state(address, state)

    def _list_items_for_key(self, address: str, items_key: str) -> list:
        state = self._load_state(address)
        return list(self._items_from_state(state, items_key))

    def _get_item_for_key(self, address: str, items_key: str, item_id: str) -> typing.Any:
        for item in self._list_items_for_key(address, items_key):
            if self._get_item_id_for_key(items_key, item) == item_id:
                return item
        raise collection_errors.ItemNotFoundError(
            f"Item {item_id} not found for address {address} in {items_key!r}"
        )

    def _create_item_for_key(self, address: str, items_key: str, item: typing.Any) -> typing.Any:
        state = self._load_state(address)
        items = list(self._items_from_state(state, items_key))
        item_id = self._get_item_id_for_key(items_key, item)
        if any(self._get_item_id_for_key(items_key, existing) == item_id for existing in items):
            raise collection_errors.DuplicateItemError(
                f"Item {item_id} already exists for address {address} in {items_key!r}"
            )
        items.append(item)
        self._save_state(address, self._replace_state_items(state, items_key, items))
        return item

    def _update_item_for_key(self, address: str, items_key: str, item: typing.Any) -> typing.Any:
        state = self._load_state(address)
        items = list(self._items_from_state(state, items_key))
        item_id = self._get_item_id_for_key(items_key, item)
        for index, existing in enumerate(items):
            if self._get_item_id_for_key(items_key, existing) == item_id:
                items[index] = item
                self._save_state(address, self._replace_state_items(state, items_key, items))
                return item
        raise collection_errors.ItemNotFoundError(
            f"Item {item_id} not found for address {address} in {items_key!r}"
        )

    def _delete_item_for_key(self, address: str, items_key: str, item_id: str) -> None:
        state = self._load_state(address)
        items = list(self._items_from_state(state, items_key))
        remaining = [
            item for item in items
            if self._get_item_id_for_key(items_key, item) != item_id
        ]
        if len(remaining) == len(items):
            raise collection_errors.ItemNotFoundError(
                f"Item {item_id} not found for address {address} in {items_key!r}"
            )
        self._save_state(address, self._replace_state_items(state, items_key, remaining))

    # -- public CRUD --

    def list_items_encrypted(self, address: str) -> dict[str, str]:
        """Return the raw encrypted blob from disk, bypassing cache and decryption.

        Raises ``CollectionNoDataError`` when no file exists for ``address``.
        """
        return self._storage.load_items_encrypted(address)

    def list_items(self, address: str) -> list[T]:
        return self._list_items_for_key(address, self.ITEMS_KEY)

    def get_item(self, address: str, item_id: str) -> T:
        return self._get_item_for_key(address, self.ITEMS_KEY, item_id)

    def create_item(self, address: str, item: T) -> T:
        return self._create_item_for_key(address, self.ITEMS_KEY, item)

    def update_item(self, address: str, item: T) -> T:
        return self._update_item_for_key(address, self.ITEMS_KEY, item)

    def delete_item(self, address: str, item_id: str) -> None:
        self._delete_item_for_key(address, self.ITEMS_KEY, item_id)
