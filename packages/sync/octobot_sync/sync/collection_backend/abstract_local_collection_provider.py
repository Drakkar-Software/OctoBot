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

import octobot.community.authentication as community_authentication
import octobot_sync.sync.collection_backend.base_local_collection_storage as base_storage
import octobot_sync.sync.collection_backend.state_model as state_model


S = typing.TypeVar("S", bound=state_model.StateModel)


class AbstractLocalCollectionProvider(typing.Generic[S], abc.ABC):
    """
    Shared base for local collection providers.

    Subclasses configure ``COLLECTION``, ``STATE_VERSION``, ``STATE_CLASS``,
    storage creation, and cache setup.
    """
    COLLECTION: str = None  # type: ignore
    STATE_VERSION: str = None  # type: ignore
    STATE_CLASS: type[S] = None  # type: ignore

    _CACHE_MAXSIZE = 1024
    _CACHE_TTL_SECONDS = 12 * 60 * 60

    def __init__(
        self,
        base_folder: typing.Optional[str] = None,
    ) -> None:
        self._storage = self._create_storage(self.COLLECTION, base_folder)
        self._setup_caches()

    @staticmethod
    @abc.abstractmethod
    def _create_storage(
        collection: str,
        base_folder: typing.Optional[str] = None,
    ) -> base_storage.BaseLocalCollectionStorage:
        """Return the storage backend for this provider."""

    @abc.abstractmethod
    def _setup_caches(self) -> None:
        """Initialize provider-specific TTL caches."""

    def _get_wallet_private_key(self, address: str) -> str:
        wallet = community_authentication.CommunityAuthentication.instance().get_wallet(address)
        return wallet.private_key
