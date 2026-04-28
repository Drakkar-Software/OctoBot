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
import hashlib
import hmac
import secrets
import threading
import typing

import octobot_commons.cryptography.encryption as commons_encryption

import octobot_sync.chain as sync_chain
from octobot.community.wallet_backend.wallet_storage import (
    DedicatedFileWalletStorage,
    WalletStorage,
    build_wallet_storage,
)

_PBKDF2_ITERATIONS = 600_000
_PBKDF2_ALG = "sha256"


def _hash_passphrase(passphrase: str) -> str:
    """Hash a passphrase with PBKDF2-HMAC-SHA256 for storage. Format: salt_b64:key_b64."""
    salt = secrets.token_bytes(32)
    key = hashlib.pbkdf2_hmac(_PBKDF2_ALG, passphrase.encode(), salt, _PBKDF2_ITERATIONS)
    return base64.b64encode(salt).decode() + ":" + base64.b64encode(key).decode()


def _verify_passphrase_hash(passphrase: str, stored: str) -> bool:
    """Constant-time verify of a PBKDF2 passphrase hash created by _hash_passphrase."""
    try:
        salt_b64, key_b64 = stored.split(":")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(key_b64)
        actual = hashlib.pbkdf2_hmac(_PBKDF2_ALG, passphrase.encode(), salt, _PBKDF2_ITERATIONS)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


class WalletBackend:
    def __init__(self, sync_storage, logger, storage: typing.Optional[WalletStorage] = None):
        self._sync_storage = sync_storage
        self.logger = logger
        # threading.Lock is sufficient because wallet mutations only occur in the single
        # API process. Consumer-only worker processes (--consumer_only) never modify the
        # wallet list. If multiple API processes ever share config.json (e.g. behind a
        # load balancer), upgrade to fcntl.flock() for cross-process safety.
        self._wallet_lock = threading.Lock()
        self._storage: WalletStorage = storage if storage is not None else build_wallet_storage(sync_storage)
        if isinstance(self._storage, DedicatedFileWalletStorage):
            migrated = self._storage.migrate_from_config_if_needed()
            if migrated:
                self.logger.info(
                    f"Migrated {len(migrated)} wallet(s) from config.json "
                    f"to {self._storage._path}"
                )

    def _get_node_wallets_list(self) -> list:
        return self._storage.load()

    def _save_node_wallets_list(self, node_wallets: list) -> None:
        self._storage.save(node_wallets)

    def _build_entry_fields(self, private_key_hex: str, passphrase: str) -> dict:
        return {
            "private_key": private_key_hex,
            "passphrase_hash": _hash_passphrase(passphrase),
        }

    def _wallet_from_entry(self, entry: dict) -> sync_chain.Wallet:
        return sync_chain.Wallet(private_key=entry["private_key"], address=entry["address"])

    def _decrypt_legacy_keystore(self, keystore: dict, passphrase: str) -> sync_chain.Wallet:
        """Decrypt a legacy PBKDF2+AES entry. Used only for one-time migration."""
        encrypted_key = base64.b64decode(keystore["encrypted_key"])
        salt = base64.b64decode(keystore["salt"])
        iv = base64.b64decode(keystore["iv"])
        address = keystore["address"]
        key_bytes = commons_encryption.pbkdf2_decrypt_aes_key(encrypted_key, passphrase, salt, iv)
        return sync_chain.Wallet(private_key=key_bytes.hex(), address=address)

    def _migrate_legacy_entry(self, entry: dict, private_key_hex: str, passphrase: str) -> None:
        """Rewrite a legacy PBKDF2 entry to the new plaintext-key + passphrase-hash format."""
        normalized = entry["address"]
        with self._wallet_lock:
            node_wallets = self._get_node_wallets_list()
            for w in node_wallets:
                if w.get("address", "") == normalized:
                    w.pop("encrypted_key", None)
                    w.pop("salt", None)
                    w.pop("iv", None)
                    w["private_key"] = private_key_hex
                    w["passphrase_hash"] = _hash_passphrase(passphrase)
                    self._save_node_wallets_list(node_wallets)
                    return

    def _find_wallet_entry(self, address: str) -> typing.Optional[dict]:
        # Addresses are stored lowercase; normalize input to match
        normalized = address.lower()
        for entry in self._get_node_wallets_list():
            if entry.get("address", "") == normalized:
                return entry
        return None

    def list_wallets(self) -> list:
        """Return public wallet info (no key material)."""
        return [
            {"address": e["address"], "name": e.get("name"), "is_admin": e.get("is_admin", False)}
            for e in self._get_node_wallets_list()
        ]

    def create_wallet(
        self,
        name: typing.Optional[str],
        passphrase: str,
        is_admin: bool = False,
    ) -> sync_chain.Wallet:
        wallet = sync_chain.create_evm_wallet()
        return self._add_wallet_entry(wallet.private_key, wallet.address, name, passphrase, is_admin)

    def import_wallet(
        self,
        private_key: str,
        passphrase: str,
        name: typing.Optional[str],
        is_admin: bool = False,
    ) -> sync_chain.Wallet:
        try:
            address = sync_chain.address_from_evm_key(private_key)
        except Exception as err:
            raise ValueError(f"Invalid EVM private key: {err}") from err
        return self._add_wallet_entry(private_key, address, name, passphrase, is_admin)

    def _add_wallet_entry(
        self,
        private_key: str,
        address: str,
        name: typing.Optional[str],
        passphrase: str,
        is_admin: bool,
    ) -> sync_chain.Wallet:
        if len(passphrase) < 8:
            raise ValueError("Passphrase must be at least 8 characters")
        normalized = address.lower()
        with self._wallet_lock:
            node_wallets = self._get_node_wallets_list()
            if any(e.get("address", "") == normalized for e in node_wallets):
                raise ValueError(f"Wallet {address} already exists")
            if is_admin and any(e.get("is_admin") for e in node_wallets):
                raise ValueError("An admin wallet already exists")
            entry = {
                "address": normalized,  # always store lowercase
                "name": name or None,
                "is_admin": is_admin,
                **self._build_entry_fields(private_key.removeprefix("0x"), passphrase),
            }
            node_wallets.append(entry)
            self._save_node_wallets_list(node_wallets)
        return sync_chain.Wallet(private_key=private_key, address=address)

    def authenticate(self, address: str, passphrase: str) -> dict:
        """Verify passphrase and return wallet metadata in a single storage read.

        Returns {"is_admin": bool, "name": Optional[str]}.
        Migrates legacy PBKDF2 entries on first call.
        Raises KeyError if wallet not found, ValueError if passphrase incorrect.
        """
        entry = self._find_wallet_entry(address)
        if entry is None:
            raise KeyError(f"Wallet {address} not found")
        if "encrypted_key" in entry:
            try:
                wallet = self._decrypt_legacy_keystore(entry, passphrase)
                self._migrate_legacy_entry(entry, wallet.private_key, passphrase)
            except Exception as err:
                raise ValueError("Invalid passphrase") from err
        elif not _verify_passphrase_hash(passphrase, entry.get("passphrase_hash", "")):
            raise ValueError("Invalid passphrase")
        return {"is_admin": entry.get("is_admin", False), "name": entry.get("name")}

    def verify_wallet_passphrase(self, address: str, passphrase: str) -> bool:
        try:
            self.authenticate(address, passphrase)
            return True
        except (KeyError, ValueError):
            return False

    def decrypt_wallet_by_address(self, address: str, passphrase: str) -> sync_chain.Wallet:
        entry = self._find_wallet_entry(address)
        if entry is None:
            raise KeyError(f"Wallet {address} not found")
        if "encrypted_key" in entry:
            wallet = self._decrypt_legacy_keystore(entry, passphrase)
            self._migrate_legacy_entry(entry, wallet.private_key, passphrase)
            return wallet
        if not _verify_passphrase_hash(passphrase, entry.get("passphrase_hash", "")):
            raise ValueError("Invalid passphrase")
        return self._wallet_from_entry(entry)

    def get_wallet_for_bot(self, address: str) -> sync_chain.Wallet:
        """Return wallet without passphrase verification — for bot auto-unlock at startup.

        Raises ValueError if the entry is still in legacy encrypted format; the operator
        must log in once to trigger automatic migration before auto-unlock works.
        """
        entry = self._find_wallet_entry(address)
        if entry is None:
            raise KeyError(f"Wallet {address} not found")
        if "encrypted_key" in entry:
            raise ValueError(
                f"Wallet {address} is in legacy encrypted format; "
                "log in once to migrate to the new format"
            )
        return self._wallet_from_entry(entry)

    def remove_wallet(self, address: str) -> None:
        normalized = address.lower()
        with self._wallet_lock:
            node_wallets = self._get_node_wallets_list()
            if len(node_wallets) <= 1:
                raise ValueError("Cannot remove the last wallet")
            entry = next((e for e in node_wallets if e.get("address", "") == normalized), None)
            if entry is None:
                raise KeyError(f"Wallet {address} not found")
            if entry.get("is_admin"):
                raise ValueError("Cannot remove the admin wallet")
            self._save_node_wallets_list([e for e in node_wallets if e.get("address", "") != normalized])

    def rename_wallet(self, address: str, name: typing.Optional[str]) -> None:
        normalized = address.lower()
        with self._wallet_lock:
            node_wallets = self._get_node_wallets_list()
            for entry in node_wallets:
                if entry.get("address", "") == normalized:
                    entry["name"] = name or None
                    self._save_node_wallets_list(node_wallets)
                    return
        raise KeyError(f"Wallet {address} not found")

    def is_admin_wallet(self, address: str) -> bool:
        entry = self._find_wallet_entry(address)
        return bool(entry and entry.get("is_admin"))

    def get_wallet_name(self, address: str) -> typing.Optional[str]:
        entry = self._find_wallet_entry(address)
        return entry.get("name") if entry else None
