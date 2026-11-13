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
import hashlib
import json
import mimetypes
import os
import pathlib
import sys

import aiohttp.web as web
import cryptography.hazmat.primitives.asymmetric.ed25519 as ed25519

_NODE_API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _NODE_API_DIR not in sys.path:
    sys.path.insert(0, _NODE_API_DIR)

import mobile_ui
import mobile_ui.constants as constants

DEFAULT_TEST_SEQUENCE = 1_700_000_000
_next_test_sequence = DEFAULT_TEST_SEQUENCE


def generate_keypair() -> tuple[ed25519.Ed25519PrivateKey, str]:
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key_b64 = base64.b64encode(
        private_key.public_key().public_bytes_raw()
    ).decode("ascii")
    return private_key, public_key_b64


def file_entry(path: str, content: bytes) -> dict:
    return {
        "path": path,
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


def sign_manifest(
    private_key: ed25519.Ed25519PrivateKey,
    version: str,
    files: list[dict],
    *,
    sequence: int | None = None,
    signature_override: str | None = None,
) -> dict:
    global _next_test_sequence
    if sequence is None:
        sequence = _next_test_sequence
        _next_test_sequence += 1
    manifest = {
        "schema": constants.MANIFEST_SCHEMA,
        "sequence": sequence,
        "version": version,
        "files": files,
        "signature": signature_override or "",
    }
    if signature_override is None:
        manifest["signature"] = base64.b64encode(
            private_key.sign(mobile_ui.signed_payload(manifest))  # type: ignore[arg-type]
        ).decode("ascii")
    return manifest


class MobileUiTestServerState:
    def __init__(self) -> None:
        self.file_requests: list[str] = []
        self.manifest: dict = {}
        self.file_contents: dict[tuple[str, str], bytes] = {}
        self.fail_manifest = False

    def reset_requests(self) -> None:
        self.file_requests = []


def build_application(state: MobileUiTestServerState) -> web.Application:
    async def manifest_handler(_request: web.Request) -> web.Response:
        if state.fail_manifest:
            raise web.HTTPNotFound()
        return web.json_response(state.manifest)

    async def file_handler(request: web.Request) -> web.Response:
        version = request.match_info["version"]
        path = request.match_info["path"]
        state.file_requests.append(path)
        content = state.file_contents.get((version, path))
        if content is None:
            raise web.HTTPNotFound()
        if path.endswith(".html"):
            content_type = "text/html"
        elif path.endswith(".js"):
            content_type = "text/javascript"
        elif path.endswith(".png"):
            content_type = "image/png"
        else:
            content_type = "application/octet-stream"
        return web.Response(body=content, content_type=content_type)

    app = web.Application()
    app.router.add_get(f"/{constants.MANIFEST_FILE_NAME}", manifest_handler)
    app.router.add_get("/{version}/{path:.+}", file_handler)
    return app

_GOLDEN_FIXTURE_DIR = os.path.dirname(os.path.abspath(__file__))
GOLDEN_BUCKET_FIXTURE_PATH = os.path.join(
    _GOLDEN_FIXTURE_DIR, "fixtures", "mobile2_golden_bucket.json"
)


def load_golden_bucket() -> dict:
    with open(GOLDEN_BUCKET_FIXTURE_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def materialize_bucket(
    root: pathlib.Path,
    manifest: dict,
    files: dict[str, bytes],
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / constants.MANIFEST_FILE_NAME
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    version = manifest["version"]
    for relative_path, content in files.items():
        target = root / version / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def materialize_golden_bucket(root: pathlib.Path) -> dict:
    golden = load_golden_bucket()
    decoded_files: dict[str, bytes] = {}
    for relative_path, content_b64 in golden["files"].items():
        decoded_files[relative_path] = base64.b64decode(content_b64)
    materialize_bucket(root, golden["manifest"], decoded_files)
    return golden


def build_directory_application(root: pathlib.Path) -> web.Application:
    root_resolved = root.resolve()

    async def manifest_handler(_request: web.Request) -> web.Response:
        manifest_path = root / constants.MANIFEST_FILE_NAME
        if not manifest_path.is_file():
            raise web.HTTPNotFound()
        return web.json_response(json.loads(manifest_path.read_text(encoding="utf-8")))

    async def file_handler(request: web.Request) -> web.Response:
        version = request.match_info["version"]
        path = request.match_info["path"]
        target = (root / version / path).resolve()
        if not target.is_relative_to(root_resolved):
            raise web.HTTPNotFound()
        if not target.is_file():
            raise web.HTTPNotFound()
        content = target.read_bytes()
        guessed, _encoding = mimetypes.guess_type(str(target))
        content_type = guessed or "application/octet-stream"
        return web.Response(body=content, content_type=content_type)

    app = web.Application()
    app.router.add_get(f"/{constants.MANIFEST_FILE_NAME}", manifest_handler)
    app.router.add_get("/{version}/{path:.+}", file_handler)
    return app

