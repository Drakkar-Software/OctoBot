#  This file is part of OctoBot Sync (https://github.com/Drakkar-Software/OctoBot)
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

"""Collection sync crypto: HKDF + AES-256-GCM per Starfish semantics, iv/data envelope.

Matches ``starfish_protocol.crypto._derive_key`` + Starfish AES-GCM (no associated data).
Plaintext bytes are encrypted as-is — no intermediate JSON encode/decode of the payload.
"""

import base64
import binascii
import json
import os
import typing

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

import octobot_sync.errors as sync_errors


BLOB_IV_KEY = "iv"
BLOB_DATA_KEY = "data"

HKDF_SALT_STRING = "octobot-starfish-identity-v1"

IV_BYTES = 12


def _derive_key(secret: str, salt: str, info: bytes) -> bytes:
    """Same HKDF parameters as ``starfish_protocol.crypto._derive_key``."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt.encode("utf-8"),
        info=info,
    )
    return hkdf.derive(secret.encode("utf-8"))


def _collection_aes_key(wallet_private_key: str, collection: str) -> bytes:
    return _derive_key(
        wallet_private_key,
        HKDF_SALT_STRING,
        f"octobot-sync-{collection}".encode("utf-8"),
    )


def _require_non_empty_secret(wallet_private_key: str) -> None:
    if not wallet_private_key:
        raise sync_errors.OctobotSyncCryptoFormatError(
            "Wallet private key must not be empty for sync encryption"
        )


def encrypt_bytes_to_blob_dict(
    plaintext: bytes,
    wallet_private_key: str,
    collection: str,
) -> dict[str, str]:
    """Encrypt arbitrary bytes with AES-256-GCM; return ``{iv, data}`` (base64 ASCII)."""
    _require_non_empty_secret(wallet_private_key)
    aes_key = _collection_aes_key(wallet_private_key, collection)
    initialization_vector = os.urandom(IV_BYTES)
    ciphertext = AESGCM(aes_key).encrypt(initialization_vector, plaintext, None)
    return {
        BLOB_IV_KEY: base64.b64encode(initialization_vector).decode("ascii"),
        BLOB_DATA_KEY: base64.b64encode(ciphertext).decode("ascii"),
    }


def decrypt_blob_dict_to_bytes(
    blob: dict[str, typing.Any],
    wallet_private_key: str,
    collection: str,
) -> bytes:
    """Decrypt a ``{iv, data}`` blob to the original plaintext bytes."""
    _require_non_empty_secret(wallet_private_key)
    try:
        iv_encoded = blob[BLOB_IV_KEY]
        data_encoded = blob[BLOB_DATA_KEY]
    except KeyError as err:
        raise sync_errors.OctobotSyncCryptoFormatError(
            f"Missing key in encrypted blob: {err}"
        ) from err

    try:
        initialization_vector = base64.b64decode(iv_encoded)
        ciphertext = base64.b64decode(data_encoded)
    except (binascii.Error, ValueError) as err:
        raise sync_errors.OctobotSyncCryptoFormatError(
            f"Invalid base64 in encrypted blob: {err}"
        ) from err

    if len(initialization_vector) != IV_BYTES:
        raise sync_errors.OctobotSyncCryptoFormatError(
            f"Invalid IV length: expected {IV_BYTES} bytes"
        )

    aes_key = _collection_aes_key(wallet_private_key, collection)
    try:
        return AESGCM(aes_key).decrypt(initialization_vector, ciphertext, None)
    except InvalidTag as err:
        raise sync_errors.OctobotSyncCryptoDecryptError(
            "Failed to decrypt collection payload"
        ) from err


def encrypt_utf8_json_to_wire(
    plaintext_json: str,
    wallet_private_key: str,
    collection: str,
) -> str:
    """Encrypt a UTF-8 text payload (typically JSON) and return a JSON document ``{iv, data}``."""
    blob_dict = encrypt_bytes_to_blob_dict(
        plaintext_json.encode("utf-8"),
        wallet_private_key,
        collection,
    )
    return json.dumps(blob_dict)


def decrypt_wire_to_utf8_json(
    wire_json: str,
    wallet_private_key: str,
    collection: str,
) -> str:
    """Parse outer JSON and decrypt payload bytes back to the original UTF-8 string."""
    try:
        blob_object = json.loads(wire_json)
    except json.JSONDecodeError as err:
        raise sync_errors.OctobotSyncCryptoFormatError(
            f"Encrypted payload is not valid JSON: {err}"
        ) from err

    if not isinstance(blob_object, dict):
        raise sync_errors.OctobotSyncCryptoFormatError(
            "Encrypted payload must be a JSON object"
        )

    plaintext_bytes = decrypt_blob_dict_to_bytes(blob_object, wallet_private_key, collection)
    try:
        return plaintext_bytes.decode("utf-8")
    except UnicodeDecodeError as err:
        raise sync_errors.OctobotSyncCryptoFormatError(
            f"Decrypted payload is not valid UTF-8: {err}"
        ) from err
