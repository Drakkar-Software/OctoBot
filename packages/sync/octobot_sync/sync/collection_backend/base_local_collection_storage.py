#  Drakkar-Software OctoBot-Sync
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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


import datetime
import json
import os
import pathlib
import threading
import typing

import octobot_commons.user_root_folder_provider as user_root_folder_provider

import octobot_sync.crypto as sync_crypto
import octobot_sync.errors as sync_errors

import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_backend.state_model as state_model
import octobot_sync.sync.collection_backend.tolerant_state_loading as tolerant_state_loading


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
        self._lock = threading.Lock()

    def _sanitize_address(self, address: str) -> str:
        # Basic filesystem-safe mapping while still recognizable.
        sanitized = address.strip()
        sanitized = sanitized.replace(os.sep, "_")
        sanitized = sanitized.replace("..", "_")
        return sanitized or "unknown"

    def _file_path(self, storage_key: str) -> pathlib.Path:
        filename = f"{self._sanitize_address(storage_key)}.json"
        return self._root / filename

    def _missing_data_error(self, storage_key: str) -> collection_errors.CollectionNoDataError:
        return collection_errors.CollectionNoDataError(
            f"{self.collection} file does not exist for address {storage_key}"
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
        return sync_crypto.encrypt_bytes_to_blob_dict(
            self._payload_to_json_bytes(payload),
            wallet_private_key,
            self.collection,
        )

    def _decrypt(
        self,
        blob: dict[str, typing.Any],
        wallet_private_key: str,
        state_model: type[state_model.StateModel],
        *,
        strict: bool = False,
        model_sanitizers: typing.Optional[
            dict[type, tolerant_state_loading.ModelSanitizer]
        ] = None,
        model_fallbacks: typing.Optional[
            dict[type, tolerant_state_loading.ModelFallback]
        ] = None,
    ) -> state_model.StateModel:
        try:
            plaintext_bytes = sync_crypto.decrypt_blob_dict_to_bytes(
                blob,
                wallet_private_key,
                self.collection,
            )
        except sync_errors.OctobotSyncCryptoFormatError as err:
            raise collection_errors.CollectionFileFormatError(
                f"{self.collection} blob: {err}"
            ) from err
        except sync_errors.OctobotSyncCryptoDecryptError as err:
            raise collection_errors.CollectionDecryptionError(
                f"Failed to decrypt {self.collection} data"
            ) from err

        try:
            if strict:
                decrypted_state = state_model.from_json(plaintext_bytes.decode("utf-8"))
            else:
                decrypted_state = tolerant_state_loading.TolerantStateLoader(
                    state_model,
                    collection=self.collection,
                    model_sanitizers=model_sanitizers,
                    model_fallbacks=model_fallbacks,
                ).from_json(plaintext_bytes.decode("utf-8"))
        except Exception as err:
            raise collection_errors.CollectionFileFormatError(
                f"Decrypted {self.collection} payload is not valid JSON: {err}"
            ) from err

        if decrypted_state is None:
            raise collection_errors.CollectionFileFormatError(
                f"Decrypted {self.collection} payload did not produce a state model"
            )
        return decrypted_state

    def load_state(
        self,
        storage_key: str,
        wallet_private_key: str,
        state_model: type[state_model.StateModel],
        *,
        strict: bool = False,
        model_sanitizers: typing.Optional[
            dict[type, tolerant_state_loading.ModelSanitizer]
        ] = None,
        model_fallbacks: typing.Optional[
            dict[type, tolerant_state_loading.ModelFallback]
        ] = None,
    ) -> state_model.StateModel:
        """
        Load and decrypt the state dict for a given storage key.

        Raises ``CollectionNoDataError`` when the backing file does not exist.
        """
        blob = self._read_blob(storage_key)
        return self._decrypt(
            blob,
            wallet_private_key,
            state_model,
            strict=strict,
            model_sanitizers=model_sanitizers,
            model_fallbacks=model_fallbacks,
        )

    def _read_blob(self, storage_key: str) -> dict[str, typing.Any]:
        """Read the raw encrypted blob from disk.

        Raises ``CollectionNoDataError`` when the backing file does not exist.
        """
        path = self._file_path(storage_key)
        if not path.exists():
            raise self._missing_data_error(storage_key)
        with self._lock:
            with open(path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        if not isinstance(raw, dict):
            raise collection_errors.CollectionFileFormatError(
                f"{self.collection} file must contain an encrypted blob object"
            )
        return raw

    def load_items_encrypted(self, storage_key: str) -> dict[str, str]:
        """
        Read the encrypted blob for *storage_key* directly from disk.

        Skips decryption entirely and returns the raw ``{"iv": ..., "data": ...}``-style
        dict as persisted.

        Raises ``CollectionNoDataError`` when no file exists for the storage key.
        """
        return typing.cast(dict[str, str], self._read_blob(storage_key))

    def save_state(
        self,
        storage_key: str,
        wallet_private_key: str,
        state: state_model.StateModel,
    ) -> None:
        """
        Encrypt and atomically persist the state dict for a given storage key.
        """
        path = self._file_path(storage_key)
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
