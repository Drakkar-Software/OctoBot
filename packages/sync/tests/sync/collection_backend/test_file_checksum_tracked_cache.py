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

import octobot_sync.sync.collection_backend.base_local_collection_storage as base_storage_module
import octobot_sync.sync.collection_backend.file_checksum_tracked_cache as file_checksum_tracked_cache_module

_CACHE_KEY = "user-1"
_STORAGE_KEY = "user-1"
_TEST_ADDRESS = "0xaaabbbcccddd"
_TEST_PRIVATE_KEY = "private-key"
_CHECKSUM_V1 = "checksum-v1"
_CHECKSUM_V2 = "checksum-v2"


class _TestItem(pydantic.BaseModel):
    id: str
    label: typing.Optional[str] = None

    def to_dict(self) -> dict[str, typing.Any]:
        return self.model_dump(exclude_none=True)

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> typing.Optional["_TestItem"]:
        return cls.model_validate_json(json_str)

    @classmethod
    def from_dict(cls, raw: dict[str, typing.Any]) -> typing.Optional["_TestItem"]:
        return cls.model_validate(raw)


class _TestState(pydantic.BaseModel):
    version: str
    items: typing.Optional[list[_TestItem]] = None

    def to_dict(self) -> dict[str, typing.Any]:
        result = {"version": self.version}
        if self.items is not None:
            result["items"] = [item.to_dict() for item in self.items]
        return result

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> typing.Optional["_TestState"]:
        return cls.model_validate_json(json_str)

    @classmethod
    def from_dict(cls, raw: dict[str, typing.Any]) -> typing.Optional["_TestState"]:
        return cls.model_validate(raw)


_SAMPLE_STATE = _TestState(
    version="1.0.0",
    items=[_TestItem(id="item-1", label="First")],
)


def _make_storage_mock(*, checksum: str = _CHECKSUM_V1) -> mock.Mock:
    storage = mock.Mock()
    storage.get_file_checksum = mock.Mock(return_value=checksum)
    return storage


def _make_real_storage(tmp_path) -> base_storage_module.BaseLocalCollectionStorage:
    return base_storage_module.BaseLocalCollectionStorage(
        collection="test-checksum-cache",
        base_folder=str(tmp_path),
    )


def _make_cache(
    storage: base_storage_module.BaseLocalCollectionStorage,
    *,
    maxsize: int = 10,
    ttl: float = 60.0,
) -> file_checksum_tracked_cache_module.FileChecksumTrackedCache[str, _TestState]:
    return file_checksum_tracked_cache_module.FileChecksumTrackedCache(
        storage,
        maxsize=maxsize,
        ttl=ttl,
    )


class TestFileChecksumTrackedCacheGetIfFresh:
    def test_returns_none_on_cache_miss(self):
        storage = _make_storage_mock()
        cache = _make_cache(storage)

        result = cache.get_if_fresh(_CACHE_KEY, _STORAGE_KEY)

        assert result is None
        storage.get_file_checksum.assert_not_called()

    def test_returns_state_when_checksum_matches(self):
        storage = _make_storage_mock(checksum=_CHECKSUM_V1)
        cache = _make_cache(storage)
        cache.set(_CACHE_KEY, _STORAGE_KEY, _SAMPLE_STATE)
        storage.get_file_checksum.reset_mock()

        result = cache.get_if_fresh(_CACHE_KEY, _STORAGE_KEY)

        assert result == _SAMPLE_STATE
        storage.get_file_checksum.assert_called_once_with(_STORAGE_KEY)

    def test_returns_none_and_evicts_when_checksum_changes(self):
        storage = _make_storage_mock(checksum=_CHECKSUM_V1)
        cache = _make_cache(storage)
        cache.set(_CACHE_KEY, _STORAGE_KEY, _SAMPLE_STATE)
        storage.get_file_checksum.return_value = _CHECKSUM_V2

        result = cache.get_if_fresh(_CACHE_KEY, _STORAGE_KEY)

        assert result is None
        assert _CACHE_KEY not in cache._cache

    def test_uses_storage_key_for_checksum_lookup(self):
        cache_key = ("user", "acc")
        storage_key = "user/acc"
        storage = _make_storage_mock(checksum=_CHECKSUM_V1)
        cache = _make_cache(storage)
        cache.set(cache_key, storage_key, _SAMPLE_STATE)
        storage.get_file_checksum.reset_mock()

        result = cache.get_if_fresh(cache_key, storage_key)

        assert result == _SAMPLE_STATE
        storage.get_file_checksum.assert_called_once_with(storage_key)


class TestFileChecksumTrackedCacheSet:
    def test_records_current_checksum_from_storage(self):
        storage = _make_storage_mock(checksum=_CHECKSUM_V1)
        cache = _make_cache(storage)

        cache.set(_CACHE_KEY, _STORAGE_KEY, _SAMPLE_STATE)

        envelope = cache._cache[_CACHE_KEY]
        assert envelope.state == _SAMPLE_STATE
        assert envelope.file_checksum == _CHECKSUM_V1
        storage.get_file_checksum.assert_called_once_with(_STORAGE_KEY)

    def test_subsequent_get_if_fresh_hits_without_recalling_set(self):
        storage = _make_storage_mock(checksum=_CHECKSUM_V1)
        cache = _make_cache(storage)
        cache.set(_CACHE_KEY, _STORAGE_KEY, _SAMPLE_STATE)
        storage.get_file_checksum.reset_mock()

        result = cache.get_if_fresh(_CACHE_KEY, _STORAGE_KEY)

        assert result == _SAMPLE_STATE
        storage.get_file_checksum.assert_called_once_with(_STORAGE_KEY)


class TestFileChecksumTrackedCacheRealStorage:
    def test_invalidates_when_backing_file_changes_on_disk(self, tmp_path):
        storage = _make_real_storage(tmp_path)
        cache = _make_cache(storage)
        storage.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, _SAMPLE_STATE)

        cache.set(_CACHE_KEY, _TEST_ADDRESS, _SAMPLE_STATE)

        envelope = cache._cache[_CACHE_KEY]
        assert len(envelope.file_checksum) == 64

        fresh_result = cache.get_if_fresh(_CACHE_KEY, _TEST_ADDRESS)
        assert fresh_result == _SAMPLE_STATE

        external_state = _TestState(
            version="1.0.0",
            items=[_TestItem(id="external", label="From disk")],
        )
        storage.save_state(_TEST_ADDRESS, _TEST_PRIVATE_KEY, external_state)

        stale_result = cache.get_if_fresh(_CACHE_KEY, _TEST_ADDRESS)

        assert stale_result is None
        assert _CACHE_KEY not in cache._cache
