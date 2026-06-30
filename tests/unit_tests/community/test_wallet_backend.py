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

import pytest
from unittest import mock

from octobot.community.wallet_backend.community_wallet import WalletBackend, WalletEntry
from octobot.community.wallet_backend.errors import InvalidPrivateKeyError, WalletAlreadyExistsError


# BIP-39 test mnemonic (well-known test vector)
_TEST_MNEMONIC = "test test test test test test test test test test test junk"
# Expected address for default derivation path m/44'/60'/0'/0/0
_TEST_MNEMONIC_ADDRESS = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"


def _make_backend():
    wallet_store = []
    storage = mock.MagicMock()
    storage.load.side_effect = lambda: list(wallet_store)
    storage.save.side_effect = lambda wallets: wallet_store.__setitem__(slice(None), wallets)
    logger = mock.MagicMock()
    sync_storage = mock.MagicMock()
    return WalletBackend(sync_storage, logger, storage=storage), wallet_store


class TestCreateWallet:
    def test_create_wallet_generates_mnemonic_and_stores_seed(self):
        backend, saved = _make_backend()
        wallet = backend.create_wallet(name="Alice", passphrase="passphrase123")
        assert wallet.address
        assert wallet.private_key
        # Seed must be stored in the entry
        assert len(saved) == 1
        entry = WalletEntry(**saved[0])
        assert entry.seed is not None
        assert len(entry.seed.split()) >= 12

    def test_create_wallet_entry_address_is_lowercase(self):
        backend, saved = _make_backend()
        backend.create_wallet(name=None, passphrase="passphrase123")
        # The stored entry address must be normalized to lowercase
        entry = WalletEntry(**saved[0])
        assert entry.address == entry.address.lower()


class TestImportWalletFromSeed:
    def test_import_from_known_mnemonic_derives_correct_address(self):
        backend, saved = _make_backend()
        wallet = backend.import_wallet_from_seed(
            seed=_TEST_MNEMONIC,
            passphrase="passphrase123",
            name="Test",
        )
        assert wallet.address.lower() == _TEST_MNEMONIC_ADDRESS

    def test_import_from_seed_stores_seed_in_entry(self):
        backend, saved = _make_backend()
        backend.import_wallet_from_seed(
            seed=_TEST_MNEMONIC,
            passphrase="passphrase123",
            name=None,
        )
        assert len(saved) == 1
        entry = WalletEntry(**saved[0])
        assert entry.seed == _TEST_MNEMONIC

    def test_import_from_seed_strips_whitespace(self):
        backend, saved = _make_backend()
        backend.import_wallet_from_seed(
            seed=f"  {_TEST_MNEMONIC}  ",
            passphrase="passphrase123",
            name=None,
        )
        entry = WalletEntry(**saved[0])
        assert entry.seed == _TEST_MNEMONIC

    def test_import_from_invalid_seed_raises(self):
        backend, _ = _make_backend()
        with pytest.raises(InvalidPrivateKeyError):
            backend.import_wallet_from_seed(
                seed="not a valid mnemonic at all xyz",
                passphrase="passphrase123",
                name=None,
            )

    def test_import_duplicate_seed_raises(self):
        backend, _ = _make_backend()
        backend.import_wallet_from_seed(_TEST_MNEMONIC, "passphrase123", name=None)
        with pytest.raises(WalletAlreadyExistsError):
            backend.import_wallet_from_seed(_TEST_MNEMONIC, "passphrase456", name=None)


class TestDecryptWalletEntryByAddress:
    def test_returns_entry_with_seed(self):
        backend, saved = _make_backend()
        backend.import_wallet_from_seed(_TEST_MNEMONIC, "passphrase123", name="Bob")
        entry = backend.decrypt_wallet_entry_by_address(_TEST_MNEMONIC_ADDRESS, "passphrase123")
        assert entry.seed == _TEST_MNEMONIC
        assert entry.private_key

    def test_entry_seed_is_none_for_key_imported_wallet(self):
        backend, _ = _make_backend()
        # Import via private key: no seed stored
        from octobot_sync.chain.evm import create_evm_wallet
        wallet = create_evm_wallet()
        backend.import_wallet(wallet.private_key, "passphrase123", name=None)
        entry = backend.decrypt_wallet_entry_by_address(wallet.address, "passphrase123")
        assert entry.seed is None
