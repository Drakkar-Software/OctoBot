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
import datetime
import hashlib
import json
import os
import pathlib
import threading
import typing

import octobot_commons.cryptography.encryption as commons_encryption
import octobot_commons.user_root_folder_provider as user_root_folder_provider

import octobot.community.account_backend.errors as account_backend_errors


_ACCOUNTS_AAD = b"octobot-node-accounts"
_ACCOUNTS_BLOB_IV_KEY = "iv"
_ACCOUNTS_BLOB_DATA_KEY = "data"


def _accounts_payload_to_json_bytes(accounts: list[dict[str, typing.Any]]) -> bytes:
    """Serialize account dicts to JSON bytes (handles datetime values from protocol models)."""

    def default_json_value(value: typing.Any) -> typing.Any:
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        if isinstance(value, datetime.date):
            return value.isoformat()
        raise TypeError(
            f"Object of type {type(value).__name__} is not JSON serializable for accounts storage"
        )

    return json.dumps(accounts, default=default_json_value).encode("utf-8")


class AccountStorage:
    """
    Thread-safe, per-wallet-address account storage.

    Accounts for a given wallet address are stored encrypted under the user root
    (see ``UserRootFolderProvider``) at ``<user_root>/accounts/<address>.json``.
    """

    def __init__(self, base_folder: typing.Optional[str] = None) -> None:
        root = base_folder or user_root_folder_provider.get_user_root_folder()
        self._root = pathlib.Path(root) / "accounts"
        self._lock = threading.Lock()

    def _sanitize_address(self, address: str) -> str:
        # Basic filesystem-safe mapping while still recognizable.
        sanitized = address.strip()
        sanitized = sanitized.replace(os.sep, "_")
        sanitized = sanitized.replace("..", "_")
        return sanitized or "unknown"

    def _file_path(self, address: str) -> pathlib.Path:
        filename = f"{self._sanitize_address(address)}.json"
        return self._root / filename

    def _derive_aes_key(self, wallet_private_key: str) -> bytes:
        # Derive a 32-byte AES key from the wallet private key string using SHA-256.
        return hashlib.sha256(wallet_private_key.encode("utf-8")).digest()

    def _encrypt_accounts(
        self,
        accounts: list[dict[str, typing.Any]],
        wallet_private_key: str,
    ) -> dict[str, str]:
        aes_key = self._derive_aes_key(wallet_private_key)
        iv = commons_encryption.generate_iv()
        plaintext = _accounts_payload_to_json_bytes(accounts)
        ciphertext = commons_encryption.aes_gcm_encrypt(plaintext, aes_key, iv, _ACCOUNTS_AAD)
        return {
            _ACCOUNTS_BLOB_IV_KEY: base64.b64encode(iv).decode("ascii"),
            _ACCOUNTS_BLOB_DATA_KEY: base64.b64encode(ciphertext).decode("ascii"),
        }

    def _decrypt_accounts(
        self, blob: dict[str, typing.Any], wallet_private_key: str
    ) -> list[dict[str, typing.Any]]:
        try:
            aes_key = self._derive_aes_key(wallet_private_key)
            iv_b64 = blob[_ACCOUNTS_BLOB_IV_KEY]
            data_b64 = blob[_ACCOUNTS_BLOB_DATA_KEY]
        except KeyError as err:
            raise account_backend_errors.AccountFileFormatError(
                f"Missing key in accounts blob: {err}"
            ) from err

        try:
            iv = base64.b64decode(iv_b64)
            ciphertext = base64.b64decode(data_b64)
        except Exception as err:
            raise account_backend_errors.AccountFileFormatError(
                f"Invalid base64 in accounts blob: {err}"
            ) from err

        try:
            plaintext = commons_encryption.aes_gcm_decrypt(ciphertext, aes_key, iv, _ACCOUNTS_AAD)
        except Exception as err:
            raise account_backend_errors.AccountDecryptionError(
                "Failed to decrypt accounts data"
            ) from err

        try:
            decoded = json.loads(plaintext.decode("utf-8"))
        except Exception as err:
            raise account_backend_errors.AccountFileFormatError(
                f"Decrypted accounts payload is not valid JSON: {err}"
            ) from err

        if not isinstance(decoded, list):
            raise account_backend_errors.AccountFileFormatError(
                "Decrypted accounts payload must be a list"
            )
        return typing.cast(list[dict[str, typing.Any]], decoded)

    def load_accounts(
        self, address: str, wallet_private_key: str
    ) -> list[dict[str, typing.Any]]:
        """
        Load and decrypt the account list for a given wallet address.

        Returns an empty list when the file does not exist.
        """
        path = self._file_path(address)
        if not path.exists():
            return []
        with self._lock:
            with open(path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        if not isinstance(raw, dict):
            raise account_backend_errors.AccountFileFormatError(
                "Accounts file must contain an encrypted blob object"
            )
        return self._decrypt_accounts(raw, wallet_private_key)

    def save_accounts(
        self,
        address: str,
        wallet_private_key: str,
        accounts: list[dict[str, typing.Any]],
    ) -> None:
        """
        Encrypt and atomically persist the account list for a given wallet address.
        """
        path = self._file_path(address)
        path.parent.mkdir(parents=True, exist_ok=True)
        blob = self._encrypt_accounts(accounts, wallet_private_key)
        tmp_path = path.with_suffix(".tmp")

        with self._lock:
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(blob, handle, indent=2)
                # Ensure the temp file is fully written before rename: ``with``/close
                # flushes Python buffers, but ``os.fsync`` asks the OS to commit data
                # toward durable storage so a crash right after ``replace`` is less
                # likely to leave a truncated final file. ``flush`` first matches the
                # documented pattern when fsyncing a high-level file object.
                handle.flush()
                os.fsync(handle.fileno())
            tmp_path.replace(path)

