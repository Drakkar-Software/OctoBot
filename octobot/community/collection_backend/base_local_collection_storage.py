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
import json
import os
import pathlib
import threading
import typing

import octobot_commons.cryptography.encryption as commons_encryption
import octobot_commons.user_root_folder_provider as user_root_folder_provider

import octobot.community.collection_backend.errors as collection_errors
import octobot.community.collection_backend.state_model as state_model


_BLOB_IV_KEY = "iv"
_BLOB_DATA_KEY = "data"


class BaseLocalCollectionStorage:
    """
    Thread-safe, per-wallet-address encrypted collection storage.

    Items for a given wallet address are stored encrypted under the user root
    (see ``UserRootFolderProvider``) at ``<user_root>/<collection>/<address>.json``.
    """

    def __init__(self, collection: str, base_folder: typing.Optional[str] = None) -> None:
        root = base_folder or user_root_folder_provider.get_user_root_folder()
        self.collection = collection
        self._root = pathlib.Path(root) / collection
        self._aad = f"octobot-node-{collection}".encode()
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
        # Derive a 32-byte AES key from the wallet private key using HKDF(SHA-256).
        return commons_encryption.hkdf_derive_key(
            ikm=wallet_private_key.encode("utf-8"),
            salt=b"octobot-starfish-identity-v1",
            info=f"octobot-sync-{self.collection}".encode("utf-8"),
        )

    def _payload_to_json_bytes(self, payload: state_model.StateModel) -> bytes:
        """Serialize a state dict to JSON bytes (handles datetime values from protocol models)."""

        def default_json_value(value: typing.Any) -> typing.Any:
            if isinstance(value, datetime.datetime):
                return value.isoformat()
            if isinstance(value, datetime.date):
                return value.isoformat()
            raise TypeError(
                f"Object of type {type(value).__name__} is not JSON serializable for {self.collection} storage"
            )

        return payload.to_json().encode("utf-8")

    def _encrypt(
        self,
        payload: state_model.StateModel,
        wallet_private_key: str,
    ) -> dict[str, str]:
        aes_key = self._derive_aes_key(wallet_private_key)
        iv = commons_encryption.generate_iv()
        plaintext = self._payload_to_json_bytes(payload)
        ciphertext = commons_encryption.aes_gcm_encrypt(plaintext, aes_key, iv, self._aad)
        return {
            _BLOB_IV_KEY: base64.b64encode(iv).decode("ascii"),
            _BLOB_DATA_KEY: base64.b64encode(ciphertext).decode("ascii"),
        }

    def _decrypt(
        self, blob: dict[str, typing.Any], wallet_private_key: str, state_model: type[state_model.StateModel],
    ) -> state_model.StateModel | None:
        # Extract and validate blob keys
        try:
            aes_key = self._derive_aes_key(wallet_private_key)
            iv_b64 = blob[_BLOB_IV_KEY]
            data_b64 = blob[_BLOB_DATA_KEY]
        except KeyError as err:
            raise collection_errors.CollectionFileFormatError(
                f"Missing key in {self.collection} blob: {err}"
            ) from err

        # Decode base64 fields
        try:
            iv = base64.b64decode(iv_b64)
            ciphertext = base64.b64decode(data_b64)
        except Exception as err:
            raise collection_errors.CollectionFileFormatError(
                f"Invalid base64 in {self.collection} blob: {err}"
            ) from err

        # Decrypt ciphertext
        try:
            plaintext = commons_encryption.aes_gcm_decrypt(ciphertext, aes_key, iv, self._aad)
        except Exception as err:
            raise collection_errors.CollectionDecryptionError(
                f"Failed to decrypt {self.collection} data"
            ) from err

        # Parse decrypted JSON
        try:
            return state_model.from_json(plaintext.decode("utf-8"))
        except Exception as err:
            raise collection_errors.CollectionFileFormatError(
                f"Decrypted {self.collection} payload is not valid JSON: {err}"
            ) from err

    def _read_blob(self, address: str) -> dict[str, typing.Any] | None:
        """Read the raw encrypted blob from disk, or None when the file does not exist."""
        path = self._file_path(address)
        if not path.exists():
            return None
        with self._lock:
            with open(path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        if not isinstance(raw, dict):
            raise collection_errors.CollectionFileFormatError(
                f"{self.collection} file must contain an encrypted blob object"
            )
        return raw

    def load_state(
        self, address: str, wallet_private_key: str, state_model: type[state_model.StateModel],
    ) -> state_model.StateModel | None:
        """
        Load and decrypt the state dict for a given wallet address.

        Returns ``None`` when the file does not exist.
        """
        blob = self._read_blob(address)
        if blob is None:
            return None
        return self._decrypt(blob, wallet_private_key, state_model)

    def load_items_encrypted(self, address: str) -> dict[str, str] | None:
        """
        Read the encrypted blob for *address* directly from disk.

        Skips decryption entirely and returns the raw ``{"iv": ..., "data": ...}``
        dict as persisted, or ``None`` when no file exists for the address.
        """
        return self._read_blob(address)

    def save_state(
        self,
        address: str,
        wallet_private_key: str,
        state: state_model.StateModel,
    ) -> None:
        """
        Encrypt and atomically persist the state dict for a given wallet address.
        """
        path = self._file_path(address)
        path.parent.mkdir(parents=True, exist_ok=True)
        blob = self._encrypt(state, wallet_private_key)
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
