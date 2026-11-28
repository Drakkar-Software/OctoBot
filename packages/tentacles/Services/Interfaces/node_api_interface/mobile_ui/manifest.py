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
import re
import typing

import cryptography.exceptions as crypto_exceptions
import cryptography.hazmat.primitives.asymmetric.ed25519 as ed25519

try:
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.constants as constants
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.errors as errors
except ImportError:
    import mobile_ui.constants as constants  # type: ignore[no-redef]
    import mobile_ui.errors as errors  # type: ignore[no-redef]


class ManifestFile(typing.TypedDict):
    path: str
    sha256: str
    size: int


class Manifest(typing.TypedDict):
    schema: int
    sequence: int
    version: str
    files: list[ManifestFile]
    signature: str


_VERSION_RE = re.compile(constants.VERSION_PATTERN)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def validate_relative_path(path: str) -> None:
    if not path:
        raise errors.ManifestInvalidError("file path is empty")
    if path.startswith("/"):
        raise errors.ManifestInvalidError("file path must be relative")
    if chr(92) in path:
        raise errors.ManifestInvalidError("file path must use forward slashes")
    if ":" in path:
        raise errors.ManifestInvalidError("file path must not contain ':'")
    if any(ord(character) == 0 for character in path):
        raise errors.ManifestInvalidError("file path must not contain NUL")
    segments = path.split("/")
    for segment in segments:
        if segment in ("", ".", ".."):
            raise errors.ManifestInvalidError("invalid path segment in file path")


def signed_payload(manifest: Manifest) -> bytes:
    """Return UTF-8 bytes signed by the publisher.

    Canonical JSON: sort_keys=True, separators=(",", ":"), only schema, sequence,
    version, files (each file object has exactly path, sha256, size with int sizes).
    """
    payload_object = {
        "schema": manifest["schema"],
        "sequence": manifest["sequence"],
        "version": manifest["version"],
        "files": manifest["files"],
    }
    return json.dumps(
        payload_object,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def verify_signature(manifest: Manifest, public_key_b64: str) -> None:
    try:
        public_key_bytes = base64.b64decode(public_key_b64, validate=True)
    except Exception as exc:
        raise errors.SignatureError("invalid public key encoding") from exc
    if len(public_key_bytes) != 32:
        raise errors.SignatureError("public key must be 32 raw Ed25519 bytes")
    try:
        signature_bytes = base64.b64decode(manifest["signature"], validate=True)
    except Exception as exc:
        raise errors.SignatureError("invalid signature encoding") from exc
    public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
    try:
        public_key.verify(signature_bytes, signed_payload(manifest))
    except crypto_exceptions.InvalidSignature as exc:
        raise errors.SignatureError("manifest signature verification failed") from exc


def parse_public_keys(raw: str) -> list[str]:
    if not raw:
        return []
    return [
        part.strip()
        for part in raw.split(constants.PUBLIC_KEY_SEPARATOR)
        if part.strip()
    ]


def verify_signature_any(manifest: Manifest, public_keys_b64: list[str]) -> None:
    if not public_keys_b64:
        raise errors.SignatureError("no public key configured")
    last_failure: errors.SignatureError | None = None
    for public_key_b64 in public_keys_b64:
        try:
            verify_signature(manifest, public_key_b64)
            return
        except errors.SignatureError as exc:
            last_failure = exc
            continue
    if last_failure is not None:
        raise errors.SignatureError("manifest signature verification failed") from last_failure
    raise errors.SignatureError("manifest signature verification failed")


def parse_and_validate(raw: dict) -> Manifest:
    if not isinstance(raw, dict):
        raise errors.ManifestInvalidError("manifest must be a JSON object")
    if raw.get("schema") != constants.MANIFEST_SCHEMA:
        raise errors.ManifestInvalidError("unsupported manifest schema")
    sequence = raw.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int):
        raise errors.ManifestInvalidError("invalid manifest sequence")
    if sequence < constants.MIN_SEQUENCE or sequence > constants.MAX_SEQUENCE:
        raise errors.ManifestInvalidError("invalid manifest sequence")
    version = raw.get("version")
    if not isinstance(version, str) or not _VERSION_RE.fullmatch(version):
        raise errors.ManifestInvalidError("invalid manifest version")
    files_raw = raw.get("files")
    if not isinstance(files_raw, list):
        raise errors.ManifestInvalidError("manifest files must be a list")
    if len(files_raw) > constants.MAX_FILES:
        raise errors.ManifestInvalidError("too many files in manifest")
    signature = raw.get("signature")
    if not isinstance(signature, str) or not signature:
        raise errors.ManifestInvalidError("manifest signature is required")

    files: list[ManifestFile] = []
    seen_paths_lower: set[str] = set()
    total_bytes = 0
    has_index = False
    for entry in files_raw:
        if not isinstance(entry, dict):
            raise errors.ManifestInvalidError("manifest file entry must be an object")
        keys = set(entry.keys())
        if keys != {"path", "sha256", "size"}:
            raise errors.ManifestInvalidError("manifest file entry has invalid keys")
        path = entry["path"]
        sha256 = entry["sha256"]
        size = entry["size"]
        if not isinstance(path, str):
            raise errors.ManifestInvalidError("file path must be a string")
        validate_relative_path(path)
        path_lower = path.lower()
        if path_lower in seen_paths_lower:
            raise errors.ManifestInvalidError("duplicate file path in manifest")
        seen_paths_lower.add(path_lower)
        if not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256):
            raise errors.ManifestInvalidError("invalid sha256 in manifest")
        if not isinstance(size, int) or size < 0:
            raise errors.ManifestInvalidError("invalid file size in manifest")
        total_bytes += size
        if total_bytes > constants.MAX_TOTAL_BYTES:
            raise errors.ManifestInvalidError("manifest total size exceeds cap")
        if path == "index.html":
            has_index = True
        files.append({"path": path, "sha256": sha256, "size": size})

    if not has_index:
        raise errors.ManifestInvalidError("manifest must include index.html")

    manifest: Manifest = {
        "schema": constants.MANIFEST_SCHEMA,
        "sequence": sequence,
        "version": version,
        "files": files,
        "signature": signature,
    }
    return manifest
