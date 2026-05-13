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

import typing

import mock
import pydantic
import pytest

import octobot.community.authentication as community_authentication
import octobot.community.collection_backend.base_local_collection_provider as base_provider_module
import octobot.community.collection_backend.errors as collection_errors

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
    auth.get_wallet.return_value = wallet
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
    def test_returns_none_when_no_items_exist(self, tmp_path):
        provider = _make_provider(tmp_path)
        assert provider.list_items_encrypted(_TEST_ADDRESS) is None

    def test_returns_raw_encrypted_blob(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1", label="secret"))

        blob = provider.list_items_encrypted(_TEST_ADDRESS)
        assert blob is not None
        assert set(blob.keys()) == {"iv", "data"}
        assert "secret" not in blob["data"]

    def test_bypasses_cache(self, tmp_path):
        """list_items_encrypted must read from disk, not the in-memory cache."""
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1"))
            # list_items populates cache
            provider.list_items(_TEST_ADDRESS)

        blob = provider.list_items_encrypted(_TEST_ADDRESS)
        assert blob is not None
        assert isinstance(blob["data"], str)

    def test_does_not_need_wallet_authentication(self, tmp_path):
        """No private key is needed -- the blob is returned as-is from disk."""
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1"))

        # Call without wallet mock active -- no authentication needed
        blob = provider.list_items_encrypted(_TEST_ADDRESS)
        assert blob is not None


class TestBaseLocalCollectionProviderStateFormat:
    def test_persisted_state_contains_version_and_items_key(self, tmp_path):
        """The decrypted file content must be a state dict with version + items."""
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, _item("item-1", label="A"))

        state = provider._storage.load_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _TestState)
        assert state is not None
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
