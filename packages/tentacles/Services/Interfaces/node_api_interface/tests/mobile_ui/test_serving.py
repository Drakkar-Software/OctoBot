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

import hashlib
import json
import os

import fastapi
import pytest
from fastapi.testclient import TestClient

import tentacles.Services.Interfaces.node_api_interface.mobile_ui as mobile_ui
import tentacles.Services.Interfaces.node_api_interface.mobile_ui.constants as constants


def _write_installed_bundle(root, version: str, files: dict[str, bytes]) -> None:
    version_dir = root / constants.VERSION_DIR_NAME / version
    version_dir.mkdir(parents=True, exist_ok=True)
    manifest_files = []
    for relative_path, content in files.items():
        target = version_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        manifest_files.append(
            {
                "path": relative_path,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            }
        )
    manifest = {
        "schema": constants.MANIFEST_SCHEMA,
        "version": version,
        "files": manifest_files,
        "signature": "test",
    }
    (version_dir / constants.INSTALLED_MANIFEST_FILE_NAME).write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (root / constants.CURRENT_FILE_NAME).write_text(
        json.dumps({"version": version}), encoding="utf-8"
    )


@pytest.fixture()
def bundle_files():
    return {
        "index.html": b"<html>mobile</html>",
        "_expo/static/js/web/entry-abc.js": b"console.log(1);",
        "assets/logo.png": b"PNG",
    }


@pytest.fixture()
def mobile_app(tmp_path, bundle_files):
    version = "abcd1234abcd1234"
    _write_installed_bundle(tmp_path, version, bundle_files)
    app = fastapi.FastAPI()
    app.state.mobile_ui_store = mobile_ui.MobileUiStore(
        tmp_path, "http://unused", "unused"
    )
    mobile_ui.add_mobile_ui_routes(app)
    return app, version


def test_first_slice_examples(mobile_app):
    app, _version = mobile_app
    client = TestClient(app)
    index = client.get("/mobile")
    assert index.status_code == 200
    assert index.text == "<html>mobile</html>"
    assert index.headers["Cache-Control"] == constants.CACHE_CONTROL_NO_CACHE

    js = client.get("/mobile/_expo/static/js/web/entry-abc.js")
    assert js.status_code == 200
    assert "javascript" in js.headers["Content-Type"]
    assert js.headers["Cache-Control"] == constants.CACHE_CONTROL_IMMUTABLE

    spa = client.get("/mobile/some/deep/route")
    assert spa.status_code == 200
    assert spa.text == "<html>mobile</html>"

    missing = client.get("/mobile/_expo/static/js/web/missing.js")
    assert missing.status_code == 404


def test_not_installed_returns_503(tmp_path):
    app = fastapi.FastAPI()
    app.state.mobile_ui_store = mobile_ui.MobileUiStore(tmp_path, "", "")
    mobile_ui.add_mobile_ui_routes(app)
    client = TestClient(app)
    response = client.get("/mobile")
    assert response.status_code == 503
    assert "not installed" in response.text.lower()


def test_mobile_root_slash(mobile_app):
    app, _ = mobile_app
    client = TestClient(app)
    assert client.get("/mobile/").status_code == 200


def test_traversal_blocked(mobile_app, tmp_path, bundle_files):
    app, version = mobile_app
    secret = tmp_path / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    client = TestClient(app)
    assert client.get("/mobile/..%2f..%2fsecret.txt").status_code == 404
    assert client.get("/mobile/%2e%2e/x").status_code == 404
    assert client.get("/mobile/foo" + chr(92) + "bar").status_code == 404


def test_secret_beside_version_not_reachable(mobile_app, tmp_path):
    app, version = mobile_app
    side = tmp_path / constants.VERSION_DIR_NAME / "secret.txt"
    side.write_text("nope", encoding="utf-8")
    client = TestClient(app)
    assert client.get("/mobile/secret.txt").status_code in (200, 404)
    # file is outside active version dir; SPA fallback may return index
    response = client.get("/mobile/secret.txt")
    if response.status_code == 200:
        assert response.text == "<html>mobile</html>"


def test_js_content_type_ignores_mimetypes_registry(mobile_app, monkeypatch):
    app, _ = mobile_app
    monkeypatch.setattr("mimetypes.guess_type", lambda *_args, **_kwargs: ("text/plain", None))
    client = TestClient(app)
    response = client.get("/mobile/_expo/static/js/web/entry-abc.js")
    assert "javascript" in response.headers["Content-Type"]


def test_large_file_streamed_intact(tmp_path, bundle_files):
    big = os.urandom(3 * 1024 * 1024)
    files = dict(bundle_files)
    files["big.bin"] = big
    version = "dddddddddddddddd"
    _write_installed_bundle(tmp_path, version, files)
    app = fastapi.FastAPI()
    app.state.mobile_ui_store = mobile_ui.MobileUiStore(tmp_path, "http://unused", "unused")
    mobile_ui.add_mobile_ui_routes(app)
    client = TestClient(app)
    response = client.get("/mobile/big.bin")
    assert response.status_code == 200
    assert hashlib.sha256(response.content).hexdigest() == hashlib.sha256(big).hexdigest()


def test_hot_swap_current_json(mobile_app, tmp_path, bundle_files):
    app, version1 = mobile_app
    client = TestClient(app)
    assert "mobile" in client.get("/mobile").text

    version2 = "cccccccccccccccc"
    files2 = {"index.html": b"<html>v2</html>"}
    _write_installed_bundle(tmp_path, version2, files2)
    (tmp_path / constants.CURRENT_FILE_NAME).write_text(
        json.dumps({"version": version2}), encoding="utf-8"
    )
    assert "v2" in client.get("/mobile").text
