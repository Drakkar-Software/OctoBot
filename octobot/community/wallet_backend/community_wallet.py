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
import dataclasses
import hashlib
import hmac
import secrets
import threading
import typing

import octobot_commons.dataclasses as commons_dataclasses
import octobot_sync.auth as sync_auth
import octobot_sync.chain as sync_chain
from octobot.community.wallet_backend.errors import (
    AdminWalletAlreadyExistsError,
    CannotRemoveAdminWalletError,
    CannotRemoveLastWalletError,
    InvalidPassphraseError,
    InvalidPrivateKeyError,
    PassphraseTooShortError,
    WalletAlreadyExistsError,
    WalletNotFoundError,
)
from octobot.community.wallet_backend.wallet_storage import (
    WalletStorage,
    build_wallet_storage,
)

_PBKDF2_ITERATIONS = 600_000
_PBKDF2_ALG = "sha256"


@dataclasses.dataclass
class WalletInfo(commons_dataclasses.FlexibleDataclass):
    address: str = ""
    name: typing.Optional[str] = None
    is_admin: bool = False


@dataclasses.dataclass
class WalletEntry(commons_dataclasses.FlexibleDataclass):
    address: str = ""
    name: typing.Optional[str] = None
    is_admin: bool = False
    private_key: str = ""
    passphrase_hash: str = ""


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

    def _get_node_wallets_list(self) -> list[WalletEntry]:
        return [WalletEntry.from_dict(e) for e in self._storage.load()]

    def _save_node_wallets_list(self, node_wallets: list[WalletEntry]) -> None:
        self._storage.save([dataclasses.asdict(e) for e in node_wallets])

    def _wallet_from_entry(self, entry: WalletEntry) -> sync_chain.Wallet:
        return sync_chain.Wallet(private_key=entry.private_key, address=entry.address)

    def _find_wallet_entry(self, address: str) -> typing.Optional[WalletEntry]:
        # Addresses are stored lowercase; normalize input to match
        normalized = address.lower()
        for entry in self._get_node_wallets_list():
            if entry.address == normalized:
                return entry
        return None

    def list_wallet_entries(self) -> list[WalletEntry]:
        """Return all wallet entries, including private key and passphrase hash."""
        return self._get_node_wallets_list()

    def list_wallets(self) -> list[WalletInfo]:
        """Return public wallet info (no key material)."""
        return [
            WalletInfo(address=e.address, name=e.name, is_admin=e.is_admin)
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
            raise InvalidPrivateKeyError(f"Invalid EVM private key: {err}") from err
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
            raise PassphraseTooShortError("Passphrase must be at least 8 characters")
        normalized = address.lower()
        with self._wallet_lock:
            node_wallets = self._get_node_wallets_list()
            if any(e.address == normalized for e in node_wallets):
                raise WalletAlreadyExistsError(f"Wallet {address} already exists")
            if is_admin and any(e.is_admin for e in node_wallets):
                raise AdminWalletAlreadyExistsError("An admin wallet already exists")
            entry = WalletEntry(
                address=normalized,
                name=name or None,
                is_admin=is_admin,
                private_key=private_key.removeprefix("0x"),
                passphrase_hash=_hash_passphrase(passphrase),
            )
            node_wallets.append(entry)
            self._save_node_wallets_list(node_wallets)
        return sync_chain.Wallet(private_key=private_key, address=address)

    def authenticate(self, address: str, passphrase: str) -> WalletInfo:
        """Verify passphrase and return wallet metadata in a single storage read.

        Returns WalletInfo with is_admin and name.
        Raises WalletNotFoundError if wallet not found, InvalidPassphraseError if passphrase incorrect.
        """
        entry = self._find_wallet_entry(address)
        if entry is None:
            raise WalletNotFoundError(f"Wallet {address} not found")
        if not _verify_passphrase_hash(passphrase, entry.passphrase_hash):
            raise InvalidPassphraseError("Invalid passphrase")
        return WalletInfo(is_admin=entry.is_admin, name=entry.name, address=entry.address)

    def verify_wallet_passphrase(self, address: str, passphrase: str) -> bool:
        try:
            self.authenticate(address, passphrase)
            return True
        except (WalletNotFoundError, InvalidPassphraseError):
            return False

    def decrypt_wallet_by_address(self, address: str, passphrase: str) -> sync_chain.Wallet:
        entry = self._find_wallet_entry(address)
        if entry is None:
            raise WalletNotFoundError(f"Wallet {address} not found")
        if not _verify_passphrase_hash(passphrase, entry.passphrase_hash):
            raise InvalidPassphraseError("Invalid passphrase")
        return self._wallet_from_entry(entry)

    def get_wallet_for_bot(self, address: str) -> sync_chain.Wallet:
        """Return wallet without passphrase verification — for bot auto-unlock at startup."""
        entry = self._find_wallet_entry(address)
        if entry is None:
            raise WalletNotFoundError(f"Wallet {address} not found")
        return self._wallet_from_entry(entry)

    def get_wallet_by_user_id(self, user_id: str) -> sync_chain.Wallet:
        """Return the wallet whose derived Starfish ``user_id`` matches *user_id*.

        Under cap-cert auth the storage identity is the Starfish user_id
        (sha256(rootEdPub)[:32]), not the EVM address — the address never
        reaches the wire. Resolve by re-deriving each local wallet's user_id
        with the SAME bootstrap challenge the client uses
        (octobot_sync.auth.derive_user_id). Linear in #local wallets, which is
        small; deterministic, so no cache is required.
        """
        for entry in self._get_node_wallets_list():
            if sync_auth.derive_user_id(entry.private_key) == user_id:
                return self._wallet_from_entry(entry)
        raise WalletNotFoundError(f"Wallet not found for user_id: {user_id}")

    def remove_wallet(self, address: str) -> None:
        normalized = address.lower()
        with self._wallet_lock:
            node_wallets = self._get_node_wallets_list()
            if len(node_wallets) <= 1:
                raise CannotRemoveLastWalletError("Cannot remove the last wallet")
            entry = next((e for e in node_wallets if e.address == normalized), None)
            if entry is None:
                raise WalletNotFoundError(f"Wallet {address} not found")
            if entry.is_admin:
                raise CannotRemoveAdminWalletError("Cannot remove the admin wallet")
            self._save_node_wallets_list([e for e in node_wallets if e.address != normalized])

    def rename_wallet(self, address: str, name: typing.Optional[str]) -> None:
        normalized = address.lower()
        with self._wallet_lock:
            node_wallets = self._get_node_wallets_list()
            for entry in node_wallets:
                if entry.address == normalized:
                    entry.name = name or None
                    self._save_node_wallets_list(node_wallets)
                    return
        raise WalletNotFoundError(f"Wallet {address} not found")

    def is_admin_wallet(self, address: str) -> bool:
        entry = self._find_wallet_entry(address)
        return bool(entry and entry.is_admin)

    def get_wallet_name(self, address: str) -> typing.Optional[str]:
        entry = self._find_wallet_entry(address)
        return entry.name if entry else None
