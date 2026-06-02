#  Drakkar-Software OctoBot-Sync
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

import typing

import cachetools
import mock
import pydantic

import octobot.community.authentication as community_authentication
import octobot_sync.sync.collection_backend.abstract_local_collection_provider as abstract_provider_module
import octobot_sync.sync.collection_backend.base_local_collection_storage as base_storage_module
import octobot_sync.sync.collection_backend.single_item_local_collection_storage as single_item_storage_module

_TEST_ADDRESS = "0xaaabbbcccddd"
_TEST_PRIVATE_KEY = "private-key"


class _TestState(pydantic.BaseModel):
    version: str


class _TestAbstractProvider(abstract_provider_module.AbstractLocalCollectionProvider[_TestState]):
    COLLECTION = "test-abstract"
    STATE_VERSION = "1.0.0"
    STATE_CLASS = _TestState

    @staticmethod
    def _create_storage(
        collection: str,
        base_folder: typing.Optional[str] = None,
    ) -> base_storage_module.BaseLocalCollectionStorage:
        return single_item_storage_module.SingleItemLocalCollectionStorage(
            collection=collection,
            base_folder=base_folder,
        )

    def _setup_caches(self) -> None:
        self._state_cache: cachetools.TTLCache[tuple[str, str], _TestState] = cachetools.TTLCache(
            maxsize=self._CACHE_MAXSIZE,
            ttl=self._CACHE_TTL_SECONDS,
        )


def _make_provider(tmp_path):
    return _TestAbstractProvider(base_folder=str(tmp_path))


def _patch_wallet(private_key: str = _TEST_PRIVATE_KEY):
    wallet = mock.Mock()
    wallet.private_key = private_key
    auth = mock.Mock()
    auth.get_wallet.return_value = wallet
    return mock.patch.object(
        community_authentication.CommunityAuthentication,
        "instance",
        return_value=auth,
    )


class TestAbstractLocalCollectionProviderInit:
    def test_creates_storage_via_create_storage(self, tmp_path):
        provider = _make_provider(tmp_path)

        assert isinstance(provider._storage, single_item_storage_module.SingleItemLocalCollectionStorage)
        assert provider._storage.collection == "test-abstract"
        assert provider._storage._root == tmp_path / "test-abstract"

    def test_calls_setup_caches(self, tmp_path):
        provider = _make_provider(tmp_path)

        assert hasattr(provider, "_state_cache")
        assert isinstance(provider._state_cache, cachetools.TTLCache)


class TestAbstractLocalCollectionProviderGetWalletPrivateKey:
    def test_returns_wallet_private_key_from_community_authentication(self, tmp_path):
        provider = _make_provider(tmp_path)

        with _patch_wallet("expected-private-key"):
            private_key = provider._get_wallet_private_key(_TEST_ADDRESS)

        assert private_key == "expected-private-key"
