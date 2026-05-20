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

import mock
import pydantic

import octobot_sync.constants as sync_constants
import octobot.community.authentication as community_authentication
import octobot_sync.sync.collection_backend.single_item_local_collection_provider as single_item_provider_module
import octobot_sync.sync.collection_backend.single_item_local_collection_storage as single_item_storage_module

_TEST_ADDRESS = "0xaaabbbcccddd"
_TEST_ACCOUNT_ID = "acc-1"
_TEST_PRIVATE_KEY = "private-key"


class _TestItem(pydantic.BaseModel):
    id: str
    label: typing.Optional[str] = None


class _TestState(pydantic.BaseModel):
    version: str
    items: typing.Optional[list[_TestItem]] = None

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> typing.Optional["_TestState"]:
        return cls.model_validate_json(json_str)


class _TestSingleItemProvider(
    single_item_provider_module.SingleItemLocalCollectionProvider[_TestState]
):
    COLLECTION = "test-single-item"
    STATE_VERSION = "1.0.0"
    STATE_CLASS = _TestState


_SAMPLE_STATE = _TestState(
    version="1.0.0",
    items=[_TestItem(id="item-1", label="First")],
)


def _make_provider(tmp_path):
    return _TestSingleItemProvider(base_folder=str(tmp_path))


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


class TestSingleItemLocalCollectionProviderCreateStorage:
    def test_storage_is_single_item_local_collection_storage(self, tmp_path):
        provider = _make_provider(tmp_path)
        assert isinstance(provider._storage, single_item_storage_module.SingleItemLocalCollectionStorage)


class TestSingleItemLocalCollectionProviderBuildIdentifier:
    def test_joins_sanitized_wallet_and_account_id(self, tmp_path):
        provider = _make_provider(tmp_path)
        unsafe_address = "../0xwallet"
        unsafe_account_id = "..\\acc-1"

        identifier = provider._build_identifier(unsafe_address, unsafe_account_id)

        expected_identifier = (
            f"{provider._storage._sanitize_address(unsafe_address)}/"
            f"{provider._storage._sanitize_address(unsafe_account_id)}"
        )
        assert identifier == expected_identifier
        assert ".." not in identifier


class TestSingleItemLocalCollectionProviderLoadState:
    def test_returns_cached_state_without_second_disk_read(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.save_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID, _SAMPLE_STATE)

        with mock.patch.object(
            provider._storage,
            "load_state",
            wraps=provider._storage.load_state,
        ) as load_state_mock:
            with _patch_wallet():
                first_load = provider.load_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID)
                second_load = provider.load_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID)

        assert first_load == _SAMPLE_STATE
        assert second_load == _SAMPLE_STATE
        load_state_mock.assert_not_called()


class TestSingleItemLocalCollectionProviderSaveState:
    def test_persists_and_updates_cache(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.save_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID, _SAMPLE_STATE)

        cached_state = provider._get_cached_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID)
        assert cached_state == _SAMPLE_STATE

        identifier = provider._build_identifier(_TEST_ADDRESS, _TEST_ACCOUNT_ID)
        persisted_state = provider._storage.load_state(identifier, _TEST_PRIVATE_KEY, _TestState)
        assert persisted_state == _SAMPLE_STATE


class TestSingleItemLocalCollectionProviderLoadStateEncrypted:
    def test_reads_encrypted_blob_for_account_id(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.save_state(_TEST_ADDRESS, _TEST_ACCOUNT_ID, _SAMPLE_STATE)

        blob = provider.load_state_encrypted(_TEST_ADDRESS, _TEST_ACCOUNT_ID)

        assert set(blob.keys()) == {sync_constants.BLOB_IV_KEY, sync_constants.BLOB_DATA_KEY}
        assert "First" not in blob[sync_constants.BLOB_DATA_KEY]
