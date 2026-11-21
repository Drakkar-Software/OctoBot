#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
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

import cryptography.hazmat.primitives.asymmetric.ed25519 as ed25519
import pytest

import tentacles.Services.Interfaces.node_api_interface.mobile_ui as mobile_ui
import tentacles.Services.Interfaces.node_api_interface.mobile_ui.constants as constants
import tentacles.Services.Interfaces.node_api_interface.mobile_ui.errors as errors

from . import mobile_ui_test_server as test_server

DEFAULT_SEQUENCE = test_server.DEFAULT_TEST_SEQUENCE


def _sign_manifest(raw: dict, private_key: ed25519.Ed25519PrivateKey) -> dict:
    manifest_body = {
        "schema": raw["schema"],
        "sequence": raw["sequence"],
        "version": raw["version"],
        "files": raw["files"],
    }
    signed = dict(raw)
    signed["signature"] = base64.b64encode(
        private_key.sign(mobile_ui.signed_payload(manifest_body))  # type: ignore[arg-type]
    ).decode("ascii")
    return signed


@pytest.fixture()
def keypair():
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key_b64 = base64.b64encode(
        private_key.public_key().public_bytes_raw()
    ).decode("ascii")
    return private_key, public_key_b64


def _valid_files():
    return [
        {"path": "index.html", "sha256": "a" * 64, "size": 10},
    ]


def _base_raw(version: str = "abcd1234", sequence: int = DEFAULT_SEQUENCE) -> dict:
    return {
        "schema": constants.MANIFEST_SCHEMA,
        "sequence": sequence,
        "version": version,
        "files": _valid_files(),
        "signature": "placeholder",
    }


class TestValidateRelativePath:
    @pytest.mark.parametrize(
        "path",
        [
            "",
            "/index.html",
            "foo" + chr(92) + "bar",
            "foo:bar",
            "a/../b",
            "a/./b",
            "a//b",
        ],
    )
    def test_rejects_invalid_paths(self, path):
        with pytest.raises(errors.ManifestInvalidError):
            mobile_ui.validate_relative_path(path)

    def test_accepts_posix_relative(self):
        mobile_ui.validate_relative_path("_expo/static/js/web/entry-abc.js")


class TestParseAndValidate:
    def test_valid_manifest(self, keypair):
        private_key, public_key_b64 = keypair
        version = "abcd1234"
        raw = _base_raw(version)
        raw = _sign_manifest(raw, private_key)
        manifest = mobile_ui.parse_and_validate(raw)
        mobile_ui.verify_signature(manifest, public_key_b64)
        assert manifest["version"] == version
        assert manifest["sequence"] == DEFAULT_SEQUENCE

    def test_wrong_schema(self, keypair):
        raw = _base_raw()
        raw["schema"] = 1
        with pytest.raises(errors.ManifestInvalidError):
            mobile_ui.parse_and_validate(raw)

    def test_bad_version(self, keypair):
        raw = _base_raw("NOT_HEX")
        with pytest.raises(errors.ManifestInvalidError):
            mobile_ui.parse_and_validate(raw)

    def test_missing_index_html(self, keypair):
        raw = _base_raw()
        raw["files"] = [{"path": "other.html", "sha256": "a" * 64, "size": 1}]
        with pytest.raises(errors.ManifestInvalidError):
            mobile_ui.parse_and_validate(raw)

    def test_duplicate_paths(self, keypair):
        raw = _base_raw()
        raw["files"] = [
            {"path": "index.html", "sha256": "a" * 64, "size": 1},
            {"path": "Index.html", "sha256": "b" * 64, "size": 1},
        ]
        with pytest.raises(errors.ManifestInvalidError):
            mobile_ui.parse_and_validate(raw)

    def test_bad_sha256(self, keypair):
        raw = _base_raw()
        raw["files"] = [{"path": "index.html", "sha256": "ZZ" * 32, "size": 1}]
        with pytest.raises(errors.ManifestInvalidError):
            mobile_ui.parse_and_validate(raw)

    def test_over_max_files(self, keypair):
        files = [
            {"path": f"file{i}.txt", "sha256": "a" * 64, "size": 0}
            for i in range(constants.MAX_FILES)
        ]
        files.append({"path": "index.html", "sha256": "b" * 64, "size": 0})
        raw = _base_raw()
        raw["files"] = files
        with pytest.raises(errors.ManifestInvalidError):
            mobile_ui.parse_and_validate(raw)

    def test_over_total_bytes(self, keypair):
        raw = _base_raw()
        raw["files"] = [
            {
                "path": "index.html",
                "sha256": "a" * 64,
                "size": constants.MAX_TOTAL_BYTES + 1,
            },
        ]
        with pytest.raises(errors.ManifestInvalidError):
            mobile_ui.parse_and_validate(raw)

    @pytest.mark.parametrize(
        "sequence_value",
        [None, 0, -1, True, 1.5, "100", constants.MAX_SEQUENCE + 1],
        ids=[
            "missing",
            "zero",
            "negative",
            "bool",
            "float",
            "string",
            "above_max",
        ],
    )
    def test_invalid_sequence_rejected(self, sequence_value):
        raw = _base_raw()
        if sequence_value is None:
            del raw["sequence"]
        else:
            raw["sequence"] = sequence_value
        with pytest.raises(Exception) as exc_info:
            mobile_ui.parse_and_validate(raw)
        assert exc_info.value.code == "manifest_invalid"


class TestVerifySignature:
    def test_tampered_payload_rejected(self, keypair):
        private_key, public_key_b64 = keypair
        raw = _base_raw()
        signed = _sign_manifest(raw, private_key)
        manifest = mobile_ui.parse_and_validate(signed)
        manifest["version"] = "deadbeef"
        with pytest.raises(errors.SignatureError):
            mobile_ui.verify_signature(manifest, public_key_b64)

    def test_tampered_sequence_rejected(self, keypair):
        private_key, public_key_b64 = keypair
        raw = _base_raw()
        signed = _sign_manifest(raw, private_key)
        manifest = mobile_ui.parse_and_validate(signed)
        manifest["sequence"] = manifest["sequence"] + 1
        with pytest.raises(Exception) as exc_info:
            mobile_ui.verify_signature(manifest, public_key_b64)
        assert exc_info.value.code == "signature_invalid"

    def test_wrong_public_key(self, keypair):
        private_key, _ = keypair
        other = ed25519.Ed25519PrivateKey.generate()
        other_pub = base64.b64encode(other.public_key().public_bytes_raw()).decode("ascii")
        raw = _base_raw()
        signed = _sign_manifest(raw, private_key)
        manifest = mobile_ui.parse_and_validate(signed)
        with pytest.raises(errors.SignatureError):
            mobile_ui.verify_signature(manifest, other_pub)

    def test_signed_payload_canonical(self, keypair):
        private_key, public_key_b64 = keypair
        files = [{"path": "index.html", "sha256": "c" * 64, "size": 5}]
        raw = _base_raw("ff00aa11", sequence=42)
        raw["files"] = files
        signed = _sign_manifest(raw, private_key)
        manifest = mobile_ui.parse_and_validate(signed)
        expected = json.dumps(
            {"schema": 2, "sequence": 42, "version": "ff00aa11", "files": files},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        payload = mobile_ui.signed_payload(manifest)
        assert payload == expected
        assert b'"sequence":' in payload
        mobile_ui.verify_signature(manifest, public_key_b64)


class TestParsePublicKeys:
    def test_single_key(self, keypair):
        _, public_key_b64 = keypair
        assert mobile_ui.parse_public_keys(public_key_b64) == [public_key_b64]

    def test_comma_separated_with_spaces(self, keypair):
        _, public_key_b64 = keypair
        other = ed25519.Ed25519PrivateKey.generate()
        other_pub = base64.b64encode(other.public_key().public_bytes_raw()).decode("ascii")
        raw = f" {other_pub} , {public_key_b64} "
        assert mobile_ui.parse_public_keys(raw) == [other_pub, public_key_b64]

    def test_empty_entries_dropped(self):
        assert mobile_ui.parse_public_keys("a,,b") == ["a", "b"]

    def test_empty_string(self):
        assert mobile_ui.parse_public_keys("") == []


class TestVerifySignatureAny:
    def _signed_manifest(self, keypair):
        private_key, public_key_b64 = keypair
        raw = _base_raw()
        signed = _sign_manifest(raw, private_key)
        return mobile_ui.parse_and_validate(signed), public_key_b64

    def test_second_key_matches(self, keypair):
        manifest, public_key_b64 = self._signed_manifest(keypair)
        other = ed25519.Ed25519PrivateKey.generate()
        other_pub = base64.b64encode(other.public_key().public_bytes_raw()).decode("ascii")
        mobile_ui.verify_signature_any(manifest, [other_pub, public_key_b64])

    def test_first_key_matches(self, keypair):
        manifest, public_key_b64 = self._signed_manifest(keypair)
        mobile_ui.verify_signature_any(manifest, [public_key_b64])

    def test_none_match(self, keypair):
        manifest, _ = self._signed_manifest(keypair)
        other = ed25519.Ed25519PrivateKey.generate()
        other_pub = base64.b64encode(other.public_key().public_bytes_raw()).decode("ascii")
        with pytest.raises(Exception) as exc_info:
            mobile_ui.verify_signature_any(manifest, [other_pub])
        assert exc_info.value.code == "signature_invalid"

    def test_empty_list(self, keypair):
        manifest, _ = self._signed_manifest(keypair)
        with pytest.raises(Exception) as exc_info:
            mobile_ui.verify_signature_any(manifest, [])
        assert exc_info.value.code == "signature_invalid"

    def test_malformed_first_skipped(self, keypair):
        manifest, public_key_b64 = self._signed_manifest(keypair)
        mobile_ui.verify_signature_any(manifest, ["not-a-valid-key!!!", public_key_b64])
