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

import base64
import json

import pytest

import octobot_sync.constants as sync_constants
import octobot_sync.crypto as sync_crypto
import octobot_sync.errors as sync_errors


_TEST_PRIVATE_KEY = "private-key-alpha"
_OTHER_PRIVATE_KEY = "private-key-beta"
_TEST_COLLECTION = "user-data"


class TestBlobKeyConstants:
    def test_hkdf_salt_stable(self):
        assert sync_constants.HKDF_SALT_STRING == "octobot-starfish-identity-v1"

    def test_iv_and_data_key_names(self):
        assert sync_constants.BLOB_IV_KEY == "iv"
        assert sync_constants.BLOB_DATA_KEY == "data"

    def test_iv_length_matches_starfish(self):
        assert sync_constants.IV_BYTES == 12


class TestEncryptBytesToBlobDict:
    def test_round_trip_with_decrypt_blob_dict_to_bytes(self):
        plaintext = b'{"version":"1"}'
        blob = sync_crypto.encrypt_bytes_to_blob_dict(plaintext, _TEST_PRIVATE_KEY, _TEST_COLLECTION)
        assert set(blob.keys()) == {sync_constants.BLOB_IV_KEY, sync_constants.BLOB_DATA_KEY}
        decrypted_bytes = sync_crypto.decrypt_blob_dict_to_bytes(blob, _TEST_PRIVATE_KEY, _TEST_COLLECTION)
        assert decrypted_bytes == plaintext

    def test_same_plaintext_differs_across_encrypts(self):
        plaintext = b'{"k":"identical"}'
        first = sync_crypto.encrypt_bytes_to_blob_dict(plaintext, _TEST_PRIVATE_KEY, _TEST_COLLECTION)
        second = sync_crypto.encrypt_bytes_to_blob_dict(plaintext, _TEST_PRIVATE_KEY, _TEST_COLLECTION)
        assert first[sync_constants.BLOB_IV_KEY] != second[sync_constants.BLOB_IV_KEY]
        assert first[sync_constants.BLOB_DATA_KEY] != second[sync_constants.BLOB_DATA_KEY]


class TestDecryptBlobDictToBytes:
    def test_wrong_private_key_raises_decrypt_error(self):
        payload = b'{"secret":true}'
        blob = sync_crypto.encrypt_bytes_to_blob_dict(payload, _TEST_PRIVATE_KEY, _TEST_COLLECTION)
        with pytest.raises(sync_errors.OctobotSyncCryptoDecryptError):
            sync_crypto.decrypt_blob_dict_to_bytes(blob, _OTHER_PRIVATE_KEY, _TEST_COLLECTION)

    def test_missing_iv_key_raises_format_error(self):
        blob = {sync_constants.BLOB_DATA_KEY: "YQ=="}
        with pytest.raises(sync_errors.OctobotSyncCryptoFormatError):
            sync_crypto.decrypt_blob_dict_to_bytes(blob, _TEST_PRIVATE_KEY, _TEST_COLLECTION)

    def test_invalid_base64_raises_format_error(self):
        blob = {
            sync_constants.BLOB_IV_KEY: "%%%not-base64%%%",
            sync_constants.BLOB_DATA_KEY: "%%%not-base64%%%",
        }
        with pytest.raises(sync_errors.OctobotSyncCryptoFormatError):
            sync_crypto.decrypt_blob_dict_to_bytes(blob, _TEST_PRIVATE_KEY, _TEST_COLLECTION)

    def test_tampered_ciphertext_raises_decrypt_error(self):
        payload = b'{"x":1}'
        blob = sync_crypto.encrypt_bytes_to_blob_dict(payload, _TEST_PRIVATE_KEY, _TEST_COLLECTION)
        raw_cipher = bytearray(base64.b64decode(blob[sync_constants.BLOB_DATA_KEY]))
        raw_cipher[0] ^= 0xFF
        blob[sync_constants.BLOB_DATA_KEY] = base64.b64encode(bytes(raw_cipher)).decode("ascii")
        with pytest.raises(sync_errors.OctobotSyncCryptoDecryptError):
            sync_crypto.decrypt_blob_dict_to_bytes(blob, _TEST_PRIVATE_KEY, _TEST_COLLECTION)


class TestEncryptUtf8JsonToWire:
    def test_round_trip_with_decrypt_wire_to_utf8_json(self):
        plain = '{"ok":true}'
        wire = sync_crypto.encrypt_utf8_json_to_wire(plain, _TEST_PRIVATE_KEY, _TEST_COLLECTION)
        envelope = json.loads(wire)
        assert set(envelope.keys()) == {sync_constants.BLOB_IV_KEY, sync_constants.BLOB_DATA_KEY}
        decrypted = sync_crypto.decrypt_wire_to_utf8_json(wire, _TEST_PRIVATE_KEY, _TEST_COLLECTION)
        assert decrypted == plain


class TestDecryptWireToUtf8Json:
    def test_invalid_json_raises_format_error(self):
        with pytest.raises(sync_errors.OctobotSyncCryptoFormatError):
            sync_crypto.decrypt_wire_to_utf8_json("not json", _TEST_PRIVATE_KEY, _TEST_COLLECTION)

    def test_json_array_raises_format_error(self):
        with pytest.raises(sync_errors.OctobotSyncCryptoFormatError):
            sync_crypto.decrypt_wire_to_utf8_json("[1,2]", _TEST_PRIVATE_KEY, _TEST_COLLECTION)


class TestSha256Hex:
    def test_known_vector(self):
        # Standard SHA-256 of the empty string.
        assert sync_crypto.sha256_hex("") == (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )

    def test_deterministic(self):
        assert sync_crypto.sha256_hex("payload") == sync_crypto.sha256_hex("payload")

    def test_distinct_inputs_produce_distinct_hashes(self):
        assert sync_crypto.sha256_hex("payload-a") != sync_crypto.sha256_hex("payload-b")

    def test_unicode_payload(self):
        # UTF-8 encoding must be used — non-ASCII must not raise.
        assert sync_crypto.sha256_hex("héllo 🌍") == sync_crypto.sha256_hex("héllo 🌍")
