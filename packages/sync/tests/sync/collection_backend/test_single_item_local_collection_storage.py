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

import pydantic
import pytest

import octobot_sync.constants as sync_constants
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_backend.single_item_local_collection_storage as single_item_storage_module

_TEST_WALLET = "0xaaabbbcccddd"
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


_SAMPLE_STATE = _TestState(
    version="1.0.0",
    items=[_TestItem(id="item-1", label="First")],
)


def _make_storage(tmp_path, collection="test-single-item"):
    return single_item_storage_module.SingleItemLocalCollectionStorage(
        collection=collection,
        base_folder=str(tmp_path),
    )


def _identifier(wallet: str = _TEST_WALLET, account_id: str = _TEST_ACCOUNT_ID) -> str:
    return f"{wallet}/{account_id}"


class TestSingleItemLocalCollectionStorageFilePath:
    def test_nested_path_for_wallet_and_account_id(self, tmp_path):
        storage = _make_storage(tmp_path)
        identifier = _identifier("0xwallet", "acc-1")

        path = storage._file_path(identifier)

        assert path == tmp_path / "test-single-item" / "0xwallet" / "acc-1.json"

    def test_sanitizes_path_segments(self, tmp_path):
        storage = _make_storage(tmp_path)
        unsafe_wallet = "../0xwallet"
        unsafe_account_id = "..\\acc-1"
        identifier = f"{unsafe_wallet}/{unsafe_account_id}"

        path = storage._file_path(identifier)

        sanitized_parts = [
            storage._sanitize_storage_key(part)
            for part in identifier.split("/")
            if part
        ]
        expected_path = tmp_path / "test-single-item"
        for directory_part in sanitized_parts[:-1]:
            expected_path = expected_path / directory_part
        expected_path = expected_path / f"{sanitized_parts[-1]}.json"

        assert path == expected_path
        assert ".." not in path.as_posix()


class TestSingleItemLocalCollectionStorageLoadState:
    def test_raises_no_data_when_file_absent(self, tmp_path):
        storage = _make_storage(tmp_path)
        identifier = _identifier()

        with pytest.raises(collection_errors.CollectionNoDataError, match="identifier"):
            storage.load_state(identifier, _TEST_PRIVATE_KEY, _TestState)


class TestSingleItemLocalCollectionStorageSaveState:
    def test_round_trip_encrypted_with_composite_identifier(self, tmp_path):
        storage = _make_storage(tmp_path)
        identifier = _identifier()

        storage.save_state(identifier, _TEST_PRIVATE_KEY, _SAMPLE_STATE)
        loaded = storage.load_state(identifier, _TEST_PRIVATE_KEY, _TestState)

        assert loaded == _SAMPLE_STATE

    def test_separate_identifiers_use_separate_files(self, tmp_path):
        storage = _make_storage(tmp_path)
        first_identifier = _identifier(_TEST_WALLET, "acc-1")
        second_identifier = _identifier(_TEST_WALLET, "acc-2")
        first_state = _TestState(version="1.0.0", items=[_TestItem(id="first")])
        second_state = _TestState(version="1.0.0", items=[_TestItem(id="second")])

        storage.save_state(first_identifier, _TEST_PRIVATE_KEY, first_state)
        storage.save_state(second_identifier, _TEST_PRIVATE_KEY, second_state)

        assert storage.load_state(first_identifier, _TEST_PRIVATE_KEY, _TestState) == first_state
        assert storage.load_state(second_identifier, _TEST_PRIVATE_KEY, _TestState) == second_state


class TestSingleItemLocalCollectionStorageLoadItemsEncrypted:
    def test_returns_iv_and_data_keys_after_save(self, tmp_path):
        storage = _make_storage(tmp_path)
        identifier = _identifier()

        storage.save_state(identifier, _TEST_PRIVATE_KEY, _SAMPLE_STATE)
        blob = storage.load_items_encrypted(identifier)

        assert set(blob.keys()) == {sync_constants.BLOB_IV_KEY, sync_constants.BLOB_DATA_KEY}
