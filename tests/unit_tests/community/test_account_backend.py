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
import datetime
import json

import mock
import pytest

import octobot.community.authentication as community_authentication
import octobot.community.account_backend.errors as account_backend_errors
from octobot.community.account_backend.account_provider import (
    AccountProvider,
)
from octobot.community.account_backend.account_storage import (
    AccountStorage,
)
from octobot_protocol.models.account import Account

_TEST_WALLET_ADDRESS = "0xaaabbbcccddd"
_TEST_WALLET_ADDRESS_ALT = "0xaaabbbccc001"
_TEST_WALLET_ADDRESS_OTHER = "0xaaabbbccc002"


class TestAccountStorage:
    def test_load_returns_empty_when_file_absent(self, tmp_path):
        storage = AccountStorage(base_folder=str(tmp_path))
        assert storage.load_accounts(_TEST_WALLET_ADDRESS, "private-key") == []

    def test_save_and_load_round_trip_encrypted(self, tmp_path):
        storage = AccountStorage(base_folder=str(tmp_path))
        accounts = [
            {"id": "a1", "name": "Account 1", "is_simulated": False},
            {"id": "a2", "name": "Account 2", "is_simulated": True},
        ]
        storage.save_accounts(_TEST_WALLET_ADDRESS, "private-key", accounts)
        loaded = storage.load_accounts(_TEST_WALLET_ADDRESS, "private-key")
        assert loaded == accounts

    def test_wrong_wallet_key_raises_on_load(self, tmp_path):
        storage = AccountStorage(base_folder=str(tmp_path))
        accounts = [{"id": "a1", "name": "Account 1", "is_simulated": False}]
        storage.save_accounts(_TEST_WALLET_ADDRESS, "private-key", accounts)

        with pytest.raises(account_backend_errors.AccountDecryptionError):
            storage.load_accounts(_TEST_WALLET_ADDRESS, "other-private-key")

    def test_atomic_write_leaves_no_tmp_file(self, tmp_path):
        storage = AccountStorage(base_folder=str(tmp_path))
        storage.save_accounts(_TEST_WALLET_ADDRESS, "private-key", [])
        base = tmp_path / "accounts"
        for child in base.rglob("*"):
            assert not child.name.endswith(".tmp")

    def test_invalid_format_raises(self, tmp_path):
        storage = AccountStorage(base_folder=str(tmp_path))
        base = tmp_path / "accounts"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"{_TEST_WALLET_ADDRESS}.json"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"unexpected": "structure"}, handle)

        with pytest.raises(account_backend_errors.AccountFileFormatError):
            storage.load_accounts(_TEST_WALLET_ADDRESS, "private-key")


class TestAccountProvider:
    def _make_account(self, account_id: str, name: str = "Account", is_simulated: bool = False) -> Account:
        return Account(
            id=account_id,
            name=name,
            is_simulated=is_simulated,
            created_at=datetime.datetime.now(datetime.UTC),
            updated_at=None,
            details=None,
        )

    def _patch_wallet(self, private_key: str):
        wallet = mock.Mock()
        wallet.private_key = private_key
        auth = mock.Mock()
        auth.get_wallet.return_value = wallet
        return mock.patch.object(
            community_authentication.CommunityAuthentication,
            "instance",
            return_value=auth,
        )

    def test_create_list_and_get_account(self, tmp_path):
        # Use a dedicated storage rooted at tmp_path/accounts
        storage = AccountStorage(base_folder=str(tmp_path))
        provider = AccountProvider(storage=storage)

        account = self._make_account("acc-1", "First")
        with self._patch_wallet("private-key"):
            created = provider.create_account(_TEST_WALLET_ADDRESS, account)
        assert created.id == "acc-1"

        with self._patch_wallet("private-key"):
            listed = provider.list_accounts(_TEST_WALLET_ADDRESS)
        assert len(listed) == 1
        assert listed[0].id == "acc-1"

        with self._patch_wallet("private-key"):
            fetched = provider.get_account(_TEST_WALLET_ADDRESS, "acc-1")
        assert fetched.name == "First"

    def test_duplicate_create_rejected(self, tmp_path):
        storage = AccountStorage(base_folder=str(tmp_path))
        provider = AccountProvider(storage=storage)

        account = self._make_account("acc-1")
        with self._patch_wallet("private-key"):
            provider.create_account(_TEST_WALLET_ADDRESS, account)
        with pytest.raises(account_backend_errors.DuplicateAccountError):
            with self._patch_wallet("private-key"):
                provider.create_account(_TEST_WALLET_ADDRESS, account)

    def test_update_existing_account(self, tmp_path):
        storage = AccountStorage(base_folder=str(tmp_path))
        provider = AccountProvider(storage=storage)

        account = self._make_account("acc-1", "First")
        with self._patch_wallet("private-key"):
            provider.create_account(_TEST_WALLET_ADDRESS, account)

        updated = self._make_account("acc-1", "Renamed")
        with self._patch_wallet("private-key"):
            provider.update_account(_TEST_WALLET_ADDRESS, updated)

        with self._patch_wallet("private-key"):
            fetched = provider.get_account(_TEST_WALLET_ADDRESS, "acc-1")
        assert fetched.name == "Renamed"

    def test_update_missing_account_raises(self, tmp_path):
        storage = AccountStorage(base_folder=str(tmp_path))
        provider = AccountProvider(storage=storage)

        account = self._make_account("missing")
        with pytest.raises(account_backend_errors.AccountNotFoundError):
            with self._patch_wallet("private-key"):
                provider.update_account(_TEST_WALLET_ADDRESS, account)

    def test_delete_account(self, tmp_path):
        storage = AccountStorage(base_folder=str(tmp_path))
        provider = AccountProvider(storage=storage)

        account = self._make_account("acc-1")
        with self._patch_wallet("private-key"):
            provider.create_account(_TEST_WALLET_ADDRESS, account)

        with self._patch_wallet("private-key"):
            provider.delete_account(_TEST_WALLET_ADDRESS, "acc-1")
        with self._patch_wallet("private-key"):
            assert provider.list_accounts(_TEST_WALLET_ADDRESS) == []

    def test_delete_missing_account_raises(self, tmp_path):
        storage = AccountStorage(base_folder=str(tmp_path))
        provider = AccountProvider(storage=storage)

        with pytest.raises(account_backend_errors.AccountNotFoundError):
            with self._patch_wallet("private-key"):
                provider.delete_account(_TEST_WALLET_ADDRESS, "missing")

    def test_isolation_between_addresses(self, tmp_path):
        storage = AccountStorage(base_folder=str(tmp_path))
        provider = AccountProvider(storage=storage)

        with self._patch_wallet("private-key-1"):
            provider.create_account(_TEST_WALLET_ADDRESS_ALT, self._make_account("acc-1"))
        with self._patch_wallet("private-key-2"):
            provider.create_account(_TEST_WALLET_ADDRESS_OTHER, self._make_account("acc-2"))

        with self._patch_wallet("private-key-1"):
            accounts_1 = provider.list_accounts(_TEST_WALLET_ADDRESS_ALT)
        with self._patch_wallet("private-key-2"):
            accounts_2 = provider.list_accounts(_TEST_WALLET_ADDRESS_OTHER)

        assert {a.id for a in accounts_1} == {"acc-1"}
        assert {a.id for a in accounts_2} == {"acc-2"}

