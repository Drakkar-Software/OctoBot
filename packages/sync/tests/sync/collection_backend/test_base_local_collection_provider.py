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
import pytest

import octobot_sync.constants as sync_constants
import octobot.community.authentication as community_authentication
import octobot_sync.sync.collection_backend.base_local_collection_provider as base_provider_module
import octobot_sync.sync.collection_backend.errors as collection_errors

_TEST_ADDRESS = "0xaaabbbcccddd"
_TEST_ADDRESS_ALT = "0xaaabbbccc001"
_TEST_ADDRESS_OTHER = "0xaaabbbccc002"
_TEST_PRIVATE_KEY = "private-key"


class _TestItem(pydantic.BaseModel):
    """Minimal pydantic item model for tests."""
    id: str
    label: typing.Optional[str] = None

    def to_dict(self) -> dict[str, typing.Any]:
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, raw: dict[str, typing.Any]) -> "_TestItem":
        return cls.model_validate(raw)

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> typing.Optional["_TestItem"]:
        return cls.model_validate_json(json_str)

class _TestState(pydantic.BaseModel):
    """Minimal pydantic state envelope for tests."""
    version: str
    items: typing.Optional[list[_TestItem]] = None

    def to_dict(self) -> dict[str, typing.Any]:
        result = {"version": self.version}
        if self.items is not None:
            result["items"] = [item.to_dict() for item in self.items]
        return result

    @classmethod
    def from_dict(cls, raw: dict[str, typing.Any]) -> "_TestState":
        return cls.model_validate(raw)

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> typing.Optional["_TestState"]:
        return cls.model_validate_json(json_str)

class _TestItemProvider(base_provider_module.BaseLocalCollectionProvider[_TestItem, _TestState]):
    """Minimal concrete provider backed by pydantic test models."""
    COLLECTION = "test-items"
    STATE_VERSION = "1.0.0"
    STATE_CLASS = _TestState
    ITEMS_KEY = "items"

    def _get_item_id(self, item: _TestItem) -> str:
        return item.id


def _make_provider(tmp_path):
    return _TestItemProvider(base_folder=str(tmp_path))


def _patch_wallet(private_key: str = _TEST_PRIVATE_KEY):
    wallet = mock.Mock()
    wallet.private_key = private_key
    auth = mock.Mock()
    auth.get_wallet_by_user_id.return_value = wallet
    return mock.patch.object(
        community_authentication.CommunityAuthentication,
        "instance",
        return_value=auth,
    )


def _item(item_id: str, label: str | None = None) -> _TestItem:
    return _TestItem(id=item_id, label=label)


class TestBaseLocalCollectionProviderCreateItem:
    def test_creates_and_returns_item(self, tmp_path):
        provider = _make_provider(tmp_path)
        item = _item("item-1", label="First")
        with _patch_wallet():
            created = provider.create_item(_TEST_ADDRESS, item)
        assert created == item

    def test_duplicate_raises(self, tmp_path):
        provider = _make_provider(tmp_path)
        item = _item("item-1")
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, item)
        with pytest.raises(collection_errors.DuplicateItemError):
            with _patch_wallet():
                provider.create_item(_TEST_ADDRESS, item)


class TestBaseLocalCollectionProviderListItems:
    def test_lists_created_items(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1"))
            provider.create_item(_TEST_ADDRESS, _item("item-2"))
            listed = provider.list_items(_TEST_ADDRESS)
        assert len(listed) == 2
        assert {entry.id for entry in listed} == {"item-1", "item-2"}


class TestBaseLocalCollectionProviderGetItem:
    def test_returns_matching_item(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1", label="First"))
            fetched = provider.get_item(_TEST_ADDRESS, "item-1")
        assert fetched.label == "First"

    def test_missing_item_raises(self, tmp_path):
        provider = _make_provider(tmp_path)
        with pytest.raises(collection_errors.ItemNotFoundError):
            with _patch_wallet():
                provider.get_item(_TEST_ADDRESS, "nonexistent")


class TestBaseLocalCollectionProviderUpdateItem:
    def test_updates_existing_item(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1", label="Original"))
            provider.update_item(_TEST_ADDRESS, _item("item-1", label="Updated"))
            fetched = provider.get_item(_TEST_ADDRESS, "item-1")
        assert fetched.label == "Updated"

    def test_missing_item_raises(self, tmp_path):
        provider = _make_provider(tmp_path)
        with pytest.raises(collection_errors.ItemNotFoundError):
            with _patch_wallet():
                provider.update_item(_TEST_ADDRESS, _item("nonexistent"))


class TestBaseLocalCollectionProviderDeleteItem:
    def test_deletes_existing_item(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1"))
            provider.delete_item(_TEST_ADDRESS, "item-1")
            listed = provider.list_items(_TEST_ADDRESS)
        assert listed == []

    def test_missing_item_raises(self, tmp_path):
        provider = _make_provider(tmp_path)
        with pytest.raises(collection_errors.ItemNotFoundError):
            with _patch_wallet():
                provider.delete_item(_TEST_ADDRESS, "nonexistent")


class TestBaseLocalCollectionProviderListItemsEncrypted:
    def test_raises_no_data_when_no_file_exists(self, tmp_path):
        provider = _make_provider(tmp_path)
        with pytest.raises(collection_errors.CollectionNoDataError):
            provider.list_items_encrypted(_TEST_ADDRESS)

    def test_returns_raw_encrypted_blob(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1", label="secret"))

        blob = provider.list_items_encrypted(_TEST_ADDRESS)
        assert set(blob.keys()) == {sync_constants.BLOB_IV_KEY, sync_constants.BLOB_DATA_KEY}
        assert "secret" not in blob[sync_constants.BLOB_DATA_KEY]

    def test_bypasses_cache(self, tmp_path):
        """list_items_encrypted must read from disk, not the in-memory cache."""
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1"))
            # list_items populates cache
            provider.list_items(_TEST_ADDRESS)

        blob = provider.list_items_encrypted(_TEST_ADDRESS)
        assert isinstance(blob[sync_constants.BLOB_DATA_KEY], str)

    def test_does_not_need_wallet_authentication(self, tmp_path):
        """No private key is needed -- the blob is returned as-is from disk."""
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1"))

        # Call without wallet mock active -- no authentication needed
        blob = provider.list_items_encrypted(_TEST_ADDRESS)
        assert set(blob.keys()) == {sync_constants.BLOB_IV_KEY, sync_constants.BLOB_DATA_KEY}


class TestBaseLocalCollectionProviderStateFormat:
    def test_persisted_state_contains_version_and_items_key(self, tmp_path):
        """The decrypted file content must be a state dict with version + items."""
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1", label="A"))

        state = provider._storage.load_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _TestState)
        assert state.version == "1.0.0"
        assert state.items is not None
        assert len(state.items) == 1
        assert state.items[0].id == "item-1"

    def test_version_matches_state_version_classvar(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1"))

        state = provider._storage.load_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _TestState)
        assert state.version == provider.STATE_VERSION

    def test_items_key_matches_classvar(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1"))

        state = provider._storage.load_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _TestState)
        assert state.items is not None
        assert isinstance(state.items, list)

    def test_empty_collection_persists_empty_items_list(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1"))
            provider.delete_item(_TEST_ADDRESS, "item-1")

        state = provider._storage.load_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _TestState)
        assert state.version == "1.0.0"
        assert state.items == []

    def test_state_is_valid_state_class_instance(self, tmp_path):
        """The persisted dict must round-trip through STATE_CLASS.from_dict."""
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1", label="test"))

        state_model = provider._storage.load_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _TestState)
        assert state_model.version == "1.0.0"
        assert len(state_model.items) == 1
        assert state_model.items[0].id == "item-1"
        assert state_model.items[0].label == "test"


class TestBaseLocalCollectionProviderAddressIsolation:
    def test_items_are_isolated_between_addresses(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet("key-1"):
            provider.create_item(_TEST_ADDRESS_ALT, _item("item-a"))
        with _patch_wallet("key-2"):
            provider.create_item(_TEST_ADDRESS_OTHER, _item("item-b"))

        with _patch_wallet("key-1"):
            items_alt = provider.list_items(_TEST_ADDRESS_ALT)
        with _patch_wallet("key-2"):
            items_other = provider.list_items(_TEST_ADDRESS_OTHER)

        assert [entry.id for entry in items_alt] == ["item-a"]
        assert [entry.id for entry in items_other] == ["item-b"]


class _MultiFieldTestState(pydantic.BaseModel):
    """State envelope with primary and secondary item lists for multi-field tests."""
    version: str
    items: typing.Optional[list[_TestItem]] = None
    secondary_items: typing.Optional[list[_TestItem]] = None

    def to_dict(self) -> dict[str, typing.Any]:
        result = {"version": self.version}
        if self.items is not None:
            result["items"] = [item.to_dict() for item in self.items]
        if self.secondary_items is not None:
            result["secondary_items"] = [item.to_dict() for item in self.secondary_items]
        return result

    @classmethod
    def from_dict(cls, raw: dict[str, typing.Any]) -> "_MultiFieldTestState":
        return cls.model_validate(raw)

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> typing.Optional["_MultiFieldTestState"]:
        return cls.model_validate_json(json_str)


class _MultiFieldTestItemProvider(
    base_provider_module.BaseLocalCollectionProvider[_TestItem, _MultiFieldTestState]
):
    COLLECTION = "test-multi-field-items"
    STATE_VERSION = "1.0.0"
    STATE_CLASS = _MultiFieldTestState
    ITEMS_KEY = "items"
    SECONDARY_ITEMS_KEY = "secondary_items"

    def _get_item_id(self, item: _TestItem) -> str:
        return item.id

    def _get_item_id_for_key(self, items_key: str, item: typing.Any) -> str:
        if items_key in (self.ITEMS_KEY, self.SECONDARY_ITEMS_KEY):
            return item.id
        return super()._get_item_id_for_key(items_key, item)


def _make_multi_field_provider(tmp_path):
    return _MultiFieldTestItemProvider(base_folder=str(tmp_path))


class TestBaseLocalCollectionProviderMultiFieldPersistence:
    def test_primary_create_preserves_secondary_list_on_disk(self, tmp_path):
        provider = _make_multi_field_provider(tmp_path)
        secondary_item = _item("secondary-1", label="Secondary")
        initial_state = _MultiFieldTestState(
            version=provider.STATE_VERSION,
            items=[],
            secondary_items=[secondary_item],
        )
        with _patch_wallet():
            provider._save_state(_TEST_ADDRESS, initial_state)
            provider.create_item(_TEST_ADDRESS, _item("item-1", label="Primary"))

        state = provider._storage.load_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _MultiFieldTestState)
        assert len(state.items) == 1
        assert state.items[0].id == "item-1"
        assert len(state.secondary_items) == 1
        assert state.secondary_items[0].id == "secondary-1"


class TestBaseLocalCollectionProviderKeyedCrud:
    def test_create_get_update_delete_secondary_item(self, tmp_path):
        provider = _make_multi_field_provider(tmp_path)
        secondary_key = provider.SECONDARY_ITEMS_KEY
        with _patch_wallet():
            created = provider._create_item_for_key(
                _TEST_ADDRESS,
                secondary_key,
                _item("secondary-1", label="Original"),
            )
            assert created.label == "Original"
            fetched = provider._get_item_for_key(_TEST_ADDRESS, secondary_key, "secondary-1")
            assert fetched.label == "Original"
            provider._update_item_for_key(
                _TEST_ADDRESS,
                secondary_key,
                _item("secondary-1", label="Updated"),
            )
            updated = provider._get_item_for_key(_TEST_ADDRESS, secondary_key, "secondary-1")
            assert updated.label == "Updated"
            provider._delete_item_for_key(_TEST_ADDRESS, secondary_key, "secondary-1")
            listed = provider._list_items_for_key(_TEST_ADDRESS, secondary_key)
        assert listed == []


class TestBaseLocalCollectionProviderGetItemIdForKey:
    def test_unknown_items_key_raises(self, tmp_path):
        provider = _make_provider(tmp_path)
        with pytest.raises(collection_errors.UnsupportedItemsKeyError):
            provider._get_item_id_for_key("unknown_key", _item("item-1"))

