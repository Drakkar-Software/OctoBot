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
import pathlib
import secrets
import typing

import octobot_commons.cryptography.encryption as commons_encryption

import octobot.constants as constants

# fcntl is POSIX-only; on Windows the flock call is silently skipped
fcntl = None
try:
    import fcntl
except ImportError:
    pass

_WALLET_AAD = b"octobot-node-wallets"


def _resolve_aes_key() -> typing.Optional[bytes]:
    """Return the 32-byte AES key from OCTOBOT_WALLET_AES_KEY env var, or None if unset."""
    raw = constants.WALLET_AES_KEY
    if not raw:
        return None
    try:
        key = bytes.fromhex(raw)
    except ValueError:
        key = base64.b64decode(raw)
    if len(key) != 32:
        raise ValueError(
            "OCTOBOT_WALLET_AES_KEY must be a 32-byte key (64 hex chars or base64)"
        )
    return key


def _encrypt_wallets(wallets: list) -> dict:
    """AES-256-GCM encrypt a wallet list. Returns {"iv": ..., "data": ...}."""
    key = _resolve_aes_key()
    if key is None:
        raise ValueError("_encrypt_wallets called but OCTOBOT_WALLET_AES_KEY is not set")
    iv = secrets.token_bytes(12)
    plaintext = json.dumps(wallets).encode()
    ciphertext = commons_encryption.aes_gcm_encrypt(plaintext, key, iv, _WALLET_AAD)
    return {
        "iv": base64.b64encode(iv).decode(),
        "data": base64.b64encode(ciphertext).decode(),
    }


def _decrypt_wallets(blob: dict) -> list:
    """Decrypt {"iv": ..., "data": ...} envelope to a wallet list."""
    key = _resolve_aes_key()
    if key is None:
        raise ValueError(
            "Wallet data is AES-encrypted but OCTOBOT_WALLET_AES_KEY is not set"
        )
    iv = base64.b64decode(blob["iv"])
    ciphertext = base64.b64decode(blob["data"])
    plaintext = commons_encryption.aes_gcm_decrypt(ciphertext, key, iv, _WALLET_AAD)
    return json.loads(plaintext)


class WalletStorage:
    """Abstract base for wallet list persistence. Subclasses implement load/save."""

    def load(self) -> list:
        raise NotImplementedError

    def save(self, wallets: list) -> None:
        raise NotImplementedError


class ConfigJsonWalletStorage(WalletStorage):
    """Stores wallets inside config.json under the existing wallets key (default)."""

    def __init__(self, sync_storage):
        self._sync_storage = sync_storage

    def load(self) -> list:
        wallets = self._sync_storage.get_item(constants.CONFIG_COMMUNITY_WALLETS) or {}
        result = wallets.get(constants.CONFIG_COMMUNITY_NODE_WALLETS, [])
        if isinstance(result, dict) and "iv" in result:
            result = _decrypt_wallets(result)
        if not isinstance(result, list):
            raise ValueError(
                f"config.json {constants.CONFIG_COMMUNITY_NODE_WALLETS} must be a list, "
                f"got {type(result).__name__}"
            )
        for i, entry in enumerate(result):
            if not isinstance(entry, dict):
                raise ValueError(
                    f"config.json {constants.CONFIG_COMMUNITY_NODE_WALLETS}[{i}] must be a dict, "
                    f"got {type(entry).__name__}"
                )
        return result

    def save(self, wallets: list) -> None:
        blob = self._sync_storage.get_item(constants.CONFIG_COMMUNITY_WALLETS) or {}
        blob[constants.CONFIG_COMMUNITY_NODE_WALLETS] = (
            _encrypt_wallets(wallets) if _resolve_aes_key() is not None else wallets
        )
        self._sync_storage.set_item(constants.CONFIG_COMMUNITY_WALLETS, blob)


class DedicatedFileWalletStorage(WalletStorage):
    """Stores wallets in a standalone JSON file, separate from config.json.

    Writes are atomic (write to .tmp then rename) and use fcntl.flock on POSIX
    to guard against concurrent writes from multiple threads in the same process.
    The threading.Lock in WalletBackend already prevents concurrent in-process
    calls, so flock provides defence-in-depth only.

    Migration: on first use, if the target file is absent, wallets are copied
    from config.json automatically (call migrate_from_config_if_needed() at
    startup before any read/write).
    """

    _FILE_KEY = "node_wallets"

    def __init__(self, file_path: str, sync_storage=None):
        self._path = pathlib.Path(file_path)
        # sync_storage is only needed for the one-time migration
        self._sync_storage = sync_storage

    def load(self) -> list:
        if not self._path.exists():
            return []
        with open(self._path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Wallet file {self._path} must contain a JSON object")
        result = data.get(self._FILE_KEY, [])
        if isinstance(result, dict) and "iv" in result:
            result = _decrypt_wallets(result)
        for i, entry in enumerate(result):
            if not isinstance(entry, dict):
                raise ValueError(
                    f"Wallet file {self._path}[{i}] must be a dict, "
                    f"got {type(entry).__name__}"
                )
        return result

    def save(self, wallets: list) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        # Lock a dedicated lockfile rather than the tmp file itself.
        # open("w") truncates immediately, so locking on the same fd would only
        # serialize after both openers have already truncated — too late.
        lock_path = self._path.with_suffix(".lock")
        lock_fd = open(lock_path, "w")  # noqa: WPS515
        lock_acquired = False
        try:
            if fcntl is not None:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
                lock_acquired = True
            to_write = _encrypt_wallets(wallets) if _resolve_aes_key() is not None else wallets
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({self._FILE_KEY: to_write}, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(self._path)
        finally:
            if fcntl is not None and lock_acquired:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()

    def migrate_from_config_if_needed(self) -> typing.Optional[list]:
        """Copy wallets from config.json to this file on first boot.

        Returns the migrated list, or None if no migration was needed.
        Does not remove the data from config.json — rollback is possible by
        switching OCTOBOT_WALLET_STORAGE_BACKEND back to 'config'.
        """
        if self._path.exists() or self._sync_storage is None:
            return None
        existing = ConfigJsonWalletStorage(self._sync_storage).load()
        if not existing:
            return None
        self.save(existing)
        return existing


class EnvVarWalletStorage(WalletStorage):
    """Read-only storage that parses wallets from an environment variable.

    The variable must contain a base64-encoded JSON array of wallet objects.
    Any mutation attempt raises NotImplementedError — use this backend when
    wallets are pre-provisioned by an orchestrator (e.g. Kubernetes Secrets).

    To encode wallets for injection:
        import base64, json
        print(base64.b64encode(json.dumps(wallet_list).encode()).decode())
    """

    def __init__(self, env_var: str = constants.WALLET_ENV_VAR):
        self._env_var = env_var

    def load(self) -> list:
        raw = os.environ.get(self._env_var, "")
        if not raw:
            return []
        try:
            decoded = base64.b64decode(raw.encode())
            result = json.loads(decoded)
        except Exception as err:
            raise ValueError(
                f"Cannot parse {self._env_var}: {err}. "
                "Expected a base64-encoded JSON array of wallet objects."
            ) from err
        if not isinstance(result, list):
            raise ValueError(
                f"{self._env_var} must decode to a JSON array, got {type(result).__name__}"
            )
        _LEGACY_KEYS = {"address", "encrypted_key", "salt", "iv"}
        _NEW_KEYS = {"address", "private_key", "passphrase_hash"}
        for i, entry in enumerate(result):
            if not isinstance(entry, dict):
                raise ValueError(
                    f"{self._env_var}[{i}] must be a dict, got {type(entry).__name__}"
                )
            # Accept both legacy (PBKDF2) and new (plaintext + bcrypt) formats
            if not (_LEGACY_KEYS <= entry.keys() or _NEW_KEYS <= entry.keys()):
                raise ValueError(
                    f"{self._env_var}[{i}] must have either legacy keys "
                    f"{_LEGACY_KEYS} or new keys {_NEW_KEYS}"
                )
            if not isinstance(entry.get("address"), str):
                raise ValueError(
                    f"{self._env_var}[{i}].address must be a string, "
                    f"got {type(entry.get('address')).__name__}"
                )
            # Normalize address to match storage convention used everywhere else
            entry["address"] = entry["address"].lower()
        return result

    def save(self, wallets: list) -> None:
        raise NotImplementedError(
            f"EnvVarWalletStorage is read-only. "
            f"Set OCTOBOT_WALLET_STORAGE_BACKEND=config or =file to enable wallet mutations."
        )


def build_wallet_storage(sync_storage) -> WalletStorage:
    """Factory: select the wallet storage backend from OCTOBOT_WALLET_STORAGE_BACKEND."""
    backend = constants.WALLET_STORAGE_BACKEND.lower()
    if backend in ("config", ""):
        return ConfigJsonWalletStorage(sync_storage)
    if backend == "file":
        return DedicatedFileWalletStorage(
            file_path=constants.WALLET_FILE_PATH,
            sync_storage=sync_storage,
        )
    if backend == "env":
        return EnvVarWalletStorage()
    raise ValueError(
        f"Unknown OCTOBOT_WALLET_STORAGE_BACKEND value: {backend!r}. "
        "Valid values: 'config', 'file', 'env'."
    )
