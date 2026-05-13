#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
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

import base64
import json
import typing
import pydantic

import pytest

import octobot.community.collection_backend.base_local_collection_storage as base_storage_module
import octobot.community.collection_backend.errors as collection_errors

_TEST_ADDRESS = "0xaaabbbcccddd"
_TEST_PRIVATE_KEY = "private-key"

class TestItemModel(pydantic.BaseModel):
    id: str
    label: typing.Optional[str] = None
    secret: typing.Optional[str] = None

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> typing.Optional["TestItemModel"]:
        return cls.model_validate_json(json_str)

class TestStateModel(pydantic.BaseModel):
    """Minimal pydantic state envelope for tests."""
    version: str
    items: typing.Optional[list[TestItemModel]] = None

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> typing.Optional["TestStateModel"]:
        return cls.model_validate_json(json_str)


_SAMPLE_STATE = TestStateModel(
    version="1.0.0",
    items=[
        TestItemModel(id="item-1", label="First"),
        TestItemModel(id="item-2", label="Second"),
    ],
)


def _make_storage(tmp_path, collection="test-items"):
    return base_storage_module.BaseLocalCollectionStorage(
        collection=collection,
        base_folder=str(tmp_path),
    )


class TestBaseLocalCollectionStorageLoadState:
    def test_returns_none_when_file_absent(self, tmp_path):
        storage = _make_storage(tmp_path)
        assert storage.load_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, TestStateModel) is None


def _read_raw_blob(tmp_path, collection="test-items", address=_TEST_ADDRESS) -> dict:
    """Read the raw JSON blob from disk without decrypting."""
    path = tmp_path / collection / f"{address}.json"
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


class TestBaseLocalCollectionStorageSaveState:
    def test_round_trip_encrypted(self, tmp_path):
        storage = _make_storage(tmp_path)
        storage.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _SAMPLE_STATE)
        loaded = storage.load_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, TestStateModel)
        assert loaded == _SAMPLE_STATE

    def test_atomic_write_leaves_no_tmp_file(self, tmp_path):
        storage = _make_storage(tmp_path)
        storage.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, TestStateModel(version="1.0.0", items=[]))
        collection_dir = tmp_path / "test-items"
        for child in collection_dir.rglob("*"):
            assert not child.name.endswith(".tmp")


class TestBaseLocalCollectionStorageEncryption:
    def test_persisted_file_contains_only_iv_and_data_keys(self, tmp_path):
        storage = _make_storage(tmp_path)
        storage.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _SAMPLE_STATE)

        blob = _read_raw_blob(tmp_path)
        assert set(blob.keys()) == {"iv", "data"}

    def test_persisted_data_is_base64_encoded(self, tmp_path):
        storage = _make_storage(tmp_path)
        storage.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _SAMPLE_STATE)

        blob = _read_raw_blob(tmp_path)
        # Both fields must decode as valid base64 without error
        base64.b64decode(blob["iv"])
        base64.b64decode(blob["data"])

    def test_plaintext_values_not_present_in_persisted_file(self, tmp_path):
        storage = _make_storage(tmp_path)
        secret_label = "super-secret-label-1234"
        state = TestStateModel(version="1.0.0", items=[TestItemModel(id="x", label=secret_label)])
        storage.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, state)

        raw_text = (tmp_path / "test-items" / f"{_TEST_ADDRESS}.json").read_text(encoding="utf-8")
        assert secret_label not in raw_text

    def test_same_state_produces_different_ciphertext_on_each_save(self, tmp_path):
        """Each save generates a fresh IV, so ciphertexts must differ."""
        storage = _make_storage(tmp_path)

        storage.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _SAMPLE_STATE)
        first_blob = _read_raw_blob(tmp_path)

        storage.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _SAMPLE_STATE)
        second_blob = _read_raw_blob(tmp_path)

        assert first_blob["data"] != second_blob["data"], "ciphertext should differ due to fresh IV"
        assert first_blob["iv"] != second_blob["iv"], "IV should be randomized per save"

    def test_different_keys_produce_different_ciphertext(self, tmp_path):
        state = TestStateModel(version="1.0.0", items=[TestItemModel(id="item-1")])

        storage_a = _make_storage(tmp_path, collection="col-a")
        storage_a.save_state(_TEST_ADDRESS, "key-alpha", state)
        blob_a = _read_raw_blob(tmp_path, collection="col-a")

        storage_b = _make_storage(tmp_path, collection="col-b")
        storage_b.save_state(_TEST_ADDRESS, "key-beta", state)
        blob_b = _read_raw_blob(tmp_path, collection="col-b")

        assert blob_a["data"] != blob_b["data"]

    def test_tampered_ciphertext_raises_decryption_error(self, tmp_path):
        storage = _make_storage(tmp_path)
        storage.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _SAMPLE_STATE)

        # Corrupt one byte of the ciphertext
        blob = _read_raw_blob(tmp_path)
        raw_bytes = bytearray(base64.b64decode(blob["data"]))
        raw_bytes[0] ^= 0xFF
        blob["data"] = base64.b64encode(bytes(raw_bytes)).decode("ascii")

        path = tmp_path / "test-items" / f"{_TEST_ADDRESS}.json"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(blob, handle)

        with pytest.raises(collection_errors.CollectionDecryptionError):
            storage.load_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, TestStateModel)


class TestBaseLocalCollectionStorageDecrypt:
    def test_wrong_key_raises_decryption_error(self, tmp_path):
        storage = _make_storage(tmp_path)
        storage.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _SAMPLE_STATE)

        with pytest.raises(collection_errors.CollectionDecryptionError):
            storage.load_state(_TEST_ADDRESS, "wrong-private-key", TestStateModel)

    def test_invalid_blob_format_raises_file_format_error(self, tmp_path):
        storage = _make_storage(tmp_path)
        collection_dir = tmp_path / "test-items"
        collection_dir.mkdir(parents=True, exist_ok=True)
        path = collection_dir / f"{_TEST_ADDRESS}.json"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"unexpected": "structure"}, handle)

        with pytest.raises(collection_errors.CollectionFileFormatError):
            storage.load_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, TestStateModel)


class TestBaseLocalCollectionStorageLoadItemsEncrypted:
    def test_returns_none_when_file_absent(self, tmp_path):
        storage = _make_storage(tmp_path)
        assert storage.load_items_encrypted(_TEST_ADDRESS) is None

    def test_returns_raw_blob_with_iv_and_data(self, tmp_path):
        storage = _make_storage(tmp_path)
        storage.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _SAMPLE_STATE)

        blob = storage.load_items_encrypted(_TEST_ADDRESS)
        assert blob is not None
        assert set(blob.keys()) == {"iv", "data"}

    def test_returned_blob_matches_file_on_disk(self, tmp_path):
        storage = _make_storage(tmp_path)
        storage.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _SAMPLE_STATE)

        blob = storage.load_items_encrypted(_TEST_ADDRESS)
        on_disk = _read_raw_blob(tmp_path)
        assert blob == on_disk

    def test_does_not_contain_plaintext(self, tmp_path):
        storage = _make_storage(tmp_path)
        secret_value = "ultra-secret-payload-xyz"
        state = TestStateModel(version="1.0.0", items=[TestItemModel(id="s", secret=secret_value)])
        storage.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, state)

        blob = storage.load_items_encrypted(_TEST_ADDRESS)
        blob_text = json.dumps(blob)
        assert secret_value not in blob_text

    def test_does_not_require_private_key(self, tmp_path):
        """The encrypted read takes no key argument -- it just returns raw ciphertext."""
        storage = _make_storage(tmp_path)
        storage.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _SAMPLE_STATE)

        blob = storage.load_items_encrypted(_TEST_ADDRESS)
        assert blob is not None
        assert isinstance(blob["data"], str)
        assert len(blob["data"]) > 0


class TestBaseLocalCollectionStorageInit:
    def test_collection_attribute_is_set(self, tmp_path):
        storage = _make_storage(tmp_path, collection="my-collection")
        assert storage.collection == "my-collection"

    def test_root_path_uses_collection_name(self, tmp_path):
        storage = _make_storage(tmp_path, collection="my-collection")
        assert storage._root == tmp_path / "my-collection"

    def test_different_collections_are_isolated(self, tmp_path):
        storage_a = _make_storage(tmp_path, collection="col-a")
        storage_b = _make_storage(tmp_path, collection="col-b")
        state = TestStateModel(version="1.0.0", items=[TestItemModel(id="a1")])

        storage_a.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, state)
        storage_b.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, TestStateModel(version="1.0.0", items=[TestItemModel(id="b1")]))

        assert storage_a.load_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, TestStateModel) == state
        assert storage_b.load_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, TestStateModel) == TestStateModel(version="1.0.0", items=[TestItemModel(id="b1")])
