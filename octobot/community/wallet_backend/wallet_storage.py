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
import threading
import typing

import octobot_commons.cryptography.encryption as commons_encryption

import octobot.constants as constants
import octobot.enums as enums

_WALLET_AAD = b"octobot-node-wallets"

# Keys used in the AES-GCM encrypted envelope stored in wallet JSON blobs.
# iv  = initialization vector (12-byte nonce for AES-256-GCM)
# data = base64-encoded ciphertext + GCM authentication tag
_WALLET_BLOB_IV_KEY = "iv"
_WALLET_BLOB_DATA_KEY = "data"


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
    """AES-256-GCM encrypt a wallet list.

    Returns {_WALLET_BLOB_IV_KEY: <base64 nonce>, _WALLET_BLOB_DATA_KEY: <base64 ciphertext>}.
    """
    key = _resolve_aes_key()
    if key is None:
        raise ValueError("_encrypt_wallets called but OCTOBOT_WALLET_AES_KEY is not set")
    iv = secrets.token_bytes(12)
    plaintext = json.dumps(wallets).encode()
    ciphertext = commons_encryption.aes_gcm_encrypt(plaintext, key, iv, _WALLET_AAD)
    return {
        _WALLET_BLOB_IV_KEY: base64.b64encode(iv).decode(),
        _WALLET_BLOB_DATA_KEY: base64.b64encode(ciphertext).decode(),
    }


def _decrypt_wallets(blob: dict) -> list:
    """Decrypt {_WALLET_BLOB_IV_KEY: ..., _WALLET_BLOB_DATA_KEY: ...} envelope to a wallet list."""
    key = _resolve_aes_key()
    if key is None:
        raise ValueError(
            "Wallet data is AES-encrypted but OCTOBOT_WALLET_AES_KEY is not set"
        )
    iv = base64.b64decode(blob[_WALLET_BLOB_IV_KEY])
    ciphertext = base64.b64decode(blob[_WALLET_BLOB_DATA_KEY])
    plaintext = commons_encryption.aes_gcm_decrypt(ciphertext, key, iv, _WALLET_AAD)
    return json.loads(plaintext)


def _is_encrypted_blob(value: dict) -> bool:
    return _WALLET_BLOB_IV_KEY in value and _WALLET_BLOB_DATA_KEY in value


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
        result = wallets.get(constants.CHAIN_TYPE, {}).get(constants.CHAIN_NETWORK, [])
        if isinstance(result, dict) and _is_encrypted_blob(result):
            result = _decrypt_wallets(result)
        return result

    def save(self, wallets: list) -> None:
        blob = self._sync_storage.get_item(constants.CONFIG_COMMUNITY_WALLETS) or {}
        chain_blob = blob.setdefault(constants.CHAIN_TYPE, {})
        chain_blob[constants.CHAIN_NETWORK] = (
            _encrypt_wallets(wallets) if _resolve_aes_key() is not None else wallets
        )
        self._sync_storage.set_item(constants.CONFIG_COMMUNITY_WALLETS, blob)


class DedicatedFileWalletStorage(WalletStorage):
    """Stores wallets in a standalone JSON file, separate from config.json.

    Writes are atomic (write to .tmp then rename). Concurrent in-process saves
    are serialized by a threading.Lock, matching the model used by
    WalletBackend: only the single API process mutates the wallet list.
    """

    def __init__(self, file_path: str):
        self._path = pathlib.Path(file_path)
        self._lock = threading.Lock()

    def load(self) -> list:
        if not self._path.exists():
            return []
        with open(self._path, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = data.get(constants.CHAIN_TYPE, {}).get(constants.CHAIN_NETWORK, [])
        if isinstance(result, dict) and _is_encrypted_blob(result):
            result = _decrypt_wallets(result)
        return result

    def save(self, wallets: list) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        with self._lock:
            to_write = _encrypt_wallets(wallets) if _resolve_aes_key() is not None else wallets
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({constants.CHAIN_TYPE: {constants.CHAIN_NETWORK: to_write}}, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(self._path)


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
        if type(result) is not list:
            raise ValueError(
                f"{self._env_var} must decode to a JSON array, got {type(result).__name__}"
            )
        _REQUIRED_KEYS = {"address", "private_key", "passphrase_hash"}
        for i, entry in enumerate(result):
            if not (_REQUIRED_KEYS <= entry.keys()):
                raise ValueError(
                    f"{self._env_var}[{i}] must have keys {_REQUIRED_KEYS}"
                )
            if not entry.get("address", ""):
                raise ValueError(f"{self._env_var}[{i}].address must be a non-empty string")
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
    raw = constants.WALLET_STORAGE_BACKEND.lower()
    if not raw:
        return ConfigJsonWalletStorage(sync_storage)
    try:
        backend = enums.WalletStorageBackend(raw)
    except ValueError:
        raise ValueError(
            f"Unknown OCTOBOT_WALLET_STORAGE_BACKEND value: {constants.WALLET_STORAGE_BACKEND!r}. "
            f"Valid values: {[b.value for b in enums.WalletStorageBackend]}."
        )
    if backend == enums.WalletStorageBackend.CONFIG:
        return ConfigJsonWalletStorage(sync_storage)
    if backend == enums.WalletStorageBackend.FILE:
        return DedicatedFileWalletStorage(file_path=constants.WALLET_FILE_PATH)
    return EnvVarWalletStorage()
