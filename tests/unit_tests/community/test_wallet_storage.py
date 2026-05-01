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
import os
from unittest import mock

import pytest

import octobot.constants as constants
from octobot.community.wallet_backend.wallet_storage import (
    ConfigJsonWalletStorage,
    DedicatedFileWalletStorage,
    EnvVarWalletStorage,
    build_wallet_storage,
)

_SAMPLE_WALLETS = [
    {"address": "0xabc", "private_key": "aabbcc", "passphrase_hash": "salt1:hash1", "name": "Alice", "is_admin": True},
    {"address": "0xdef", "private_key": "ddeeff", "passphrase_hash": "salt2:hash2", "name": None, "is_admin": False},
]


class TestConfigJsonWalletStorage:
    def _make_sync_storage(self, initial: dict = None):
        store = {}
        if initial:
            store.update(initial)
        s = mock.MagicMock()
        s.get_item.side_effect = lambda key: store.get(key)
        s.set_item.side_effect = lambda key, val: store.update({key: val})
        return s, store

    def test_load_returns_empty_when_key_absent(self):
        s, _ = self._make_sync_storage()
        assert ConfigJsonWalletStorage(s).load() == []

    def test_load_returns_wallet_list(self):
        blob = {constants.CHAIN_TYPE: {constants.CHAIN_NETWORK: _SAMPLE_WALLETS}}
        s, _ = self._make_sync_storage({constants.CONFIG_COMMUNITY_WALLETS: blob})
        result = ConfigJsonWalletStorage(s).load()
        assert result == _SAMPLE_WALLETS

    def test_save_write_back_preserves_other_keys(self):
        other_data = {"community": {"bot_id": "abc123"}}
        s, store = self._make_sync_storage({constants.CONFIG_COMMUNITY_WALLETS: dict(other_data)})
        ConfigJsonWalletStorage(s).save(_SAMPLE_WALLETS)
        written = store[constants.CONFIG_COMMUNITY_WALLETS]
        assert written[constants.CHAIN_TYPE][constants.CHAIN_NETWORK] == _SAMPLE_WALLETS
        assert written["community"] == other_data["community"]

    def test_save_then_load_round_trip(self):
        s, _ = self._make_sync_storage()
        storage = ConfigJsonWalletStorage(s)
        storage.save(_SAMPLE_WALLETS)
        assert storage.load() == _SAMPLE_WALLETS


class TestDedicatedFileWalletStorage:
    def test_load_returns_empty_when_file_absent(self, tmp_path):
        storage = DedicatedFileWalletStorage(str(tmp_path / "wallets.json"))
        assert storage.load() == []

    def test_save_and_load_round_trip(self, tmp_path):
        path = tmp_path / "wallets.json"
        storage = DedicatedFileWalletStorage(str(path))
        storage.save(_SAMPLE_WALLETS)
        assert storage.load() == _SAMPLE_WALLETS

    def test_save_is_atomic_no_tmp_remains(self, tmp_path):
        path = tmp_path / "wallets.json"
        storage = DedicatedFileWalletStorage(str(path))
        storage.save(_SAMPLE_WALLETS)
        assert not (tmp_path / "wallets.tmp").exists()
        assert path.exists()

    def test_save_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "a" / "b" / "wallets.json"
        storage = DedicatedFileWalletStorage(str(nested))
        storage.save(_SAMPLE_WALLETS)
        assert nested.exists()

class TestEnvVarWalletStorage:
    _ENV = "TEST_OCTOBOT_NODE_WALLETS"

    def test_load_returns_empty_when_env_absent(self):
        os.environ.pop(self._ENV, None)
        assert EnvVarWalletStorage(self._ENV).load() == []

    def test_load_parses_valid_base64_json(self):
        encoded = base64.b64encode(json.dumps(_SAMPLE_WALLETS).encode()).decode()
        with mock.patch.dict(os.environ, {self._ENV: encoded}):
            result = EnvVarWalletStorage(self._ENV).load()
        expected = [dict(w, address=w["address"].lower()) for w in _SAMPLE_WALLETS]
        assert result == expected

    def test_load_raises_on_malformed_base64(self):
        with mock.patch.dict(os.environ, {self._ENV: "!!!not_base64!!!"}):
            with pytest.raises(ValueError, match=self._ENV):
                EnvVarWalletStorage(self._ENV).load()

    def test_load_raises_when_payload_is_object_not_array(self):
        encoded = base64.b64encode(json.dumps({"key": "val"}).encode()).decode()
        with mock.patch.dict(os.environ, {self._ENV: encoded}):
            with pytest.raises(ValueError, match="JSON array"):
                EnvVarWalletStorage(self._ENV).load()

    def test_save_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            EnvVarWalletStorage(self._ENV).save(_SAMPLE_WALLETS)


class TestBuildWalletStorage:
    def _build(self, backend: str, **env):
        env_patch = {**env, "OCTOBOT_WALLET_STORAGE_BACKEND": backend}
        sync_storage = mock.MagicMock()
        with mock.patch.dict(os.environ, env_patch):
            with mock.patch.object(constants, "WALLET_STORAGE_BACKEND", backend):
                return build_wallet_storage(sync_storage)

    def test_config_backend(self):
        assert isinstance(self._build("config"), ConfigJsonWalletStorage)

    def test_empty_string_defaults_to_config(self):
        assert isinstance(self._build(""), ConfigJsonWalletStorage)

    def test_file_backend(self, tmp_path):
        with mock.patch.object(constants, "WALLET_STORAGE_BACKEND", "file"):
            with mock.patch.object(constants, "WALLET_FILE_PATH", str(tmp_path / "w.json")):
                result = build_wallet_storage(mock.MagicMock())
        assert isinstance(result, DedicatedFileWalletStorage)

    def test_env_backend(self):
        with mock.patch.object(constants, "WALLET_STORAGE_BACKEND", "env"):
            result = build_wallet_storage(mock.MagicMock())
        assert isinstance(result, EnvVarWalletStorage)

    def test_unknown_backend_raises(self):
        with mock.patch.object(constants, "WALLET_STORAGE_BACKEND", "s3"):
            with pytest.raises(ValueError, match="s3"):
                build_wallet_storage(mock.MagicMock())
