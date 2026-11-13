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
import copy
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

import fastapi
import pytest
from aiohttp.test_utils import TestServer
from fastapi.testclient import TestClient

_MOBILE_UI_TESTS = os.path.dirname(os.path.abspath(__file__))
if _MOBILE_UI_TESTS not in sys.path:
    sys.path.insert(0, _MOBILE_UI_TESTS)

import mobile_ui_test_server as test_server
import tentacles.Services.Interfaces.node_api_interface.mobile_ui as mobile_ui


def _golden_fixture() -> dict:
    return test_server.load_golden_bucket()


def _golden_file_bytes(golden: dict) -> dict[str, bytes]:
    return {
        path: base64.b64decode(content_b64)
        for path, content_b64 in golden["files"].items()
    }


def _assert_manifest_error(callable_obj, expected_code: str) -> None:
    with pytest.raises(mobile_ui.MobileUiError) as exc_info:
        callable_obj()
    assert exc_info.value.code.value == expected_code


def _assert_no_install(ui_dir: pathlib.Path) -> None:
    versions_dir = ui_dir / mobile_ui.constants.VERSION_DIR_NAME
    if versions_dir.exists():
        assert list(versions_dir.iterdir()) == []
    assert not (ui_dir / mobile_ui.constants.CURRENT_FILE_NAME).exists()


def _assert_install_error_status(store: mobile_ui.MobileUiStore, expected_code: str) -> None:
    status = store.get_status()
    assert status["state"] == mobile_ui.MobileUiState.ERROR
    assert status["last_error"] is not None
    assert status["last_error"].value == expected_code


def test_golden_fixture_self_consistent() -> None:
    golden = _golden_fixture()
    for entry in golden["manifest"]["files"]:
        content = base64.b64decode(golden["files"][entry["path"]])
        assert hashlib.sha256(content).hexdigest() == entry["sha256"]
        assert len(content) == entry["size"]


def test_golden_manifest_validates_and_verifies() -> None:
    golden = _golden_fixture()
    parsed = mobile_ui.parse_and_validate(golden["manifest"])
    mobile_ui.verify_signature(parsed, golden["publicKey"])


def test_golden_manifest_schema2() -> None:
    golden = _golden_fixture()
    manifest = golden["manifest"]
    assert manifest["schema"] == 2
    assert isinstance(manifest["sequence"], int) and not isinstance(manifest["sequence"], bool)


def test_golden_verify_signature_any() -> None:
    golden = _golden_fixture()
    parsed = mobile_ui.parse_and_validate(golden["manifest"])
    wrong = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    mobile_ui.verify_signature_any(parsed, [wrong, golden["publicKey"]])


@pytest.mark.parametrize(
    ("mutator", "expected_code", "use_verify"),
    [
        (
            lambda manifest: manifest["files"][0].__setitem__(
                "sha256", "0" * 64
            ),
            "signature_invalid",
            True,
        ),
        (
            lambda manifest: manifest.__setitem__("version", "deadbeefdeadbeef"),
            "signature_invalid",
            True,
        ),
        (
            lambda manifest: manifest.__setitem__("sequence", manifest["sequence"] + 1),
            "signature_invalid",
            True,
        ),
        (
            # pop index.html would fail parse with manifest_invalid; drop a non-index entry.
            lambda manifest: manifest["files"].pop(0),
            "signature_invalid",
            True,
        ),
        (
            lambda _manifest: None,
            "signature_invalid",
            "wrong_key",
        ),
        (
            lambda manifest: manifest["files"].append(
                {"path": "../escape", "sha256": "0" * 64, "size": 0}
            ),
            "manifest_invalid",
            False,
        ),
        (
            lambda manifest: manifest["files"].append(
                {
                    "path": "assets\\bad.txt",
                    "sha256": "0" * 64,
                    "size": 0,
                }
            ),
            "manifest_invalid",
            False,
        ),
    ],
    ids=[
        "sha256",
        "version",
        "sequence",
        "drop_file",
        "wrong_public_key",
        "path_dotdot",
        "path_backslash",
    ],
)
def test_golden_manifest_tamper(
    mutator,
    expected_code: str,
    use_verify,
) -> None:
    golden = _golden_fixture()
    manifest = copy.deepcopy(golden["manifest"])
    mutator(manifest)
    if use_verify is True:
        parsed = mobile_ui.parse_and_validate(manifest)
        _assert_manifest_error(
            lambda: mobile_ui.verify_signature(parsed, golden["publicKey"]),
            expected_code,
        )
    elif use_verify == "wrong_key":
        parsed = mobile_ui.parse_and_validate(manifest)
        _private_key, other_public_key = test_server.generate_keypair()
        _assert_manifest_error(
            lambda: mobile_ui.verify_signature(parsed, other_public_key),
            expected_code,
        )
    else:
        _assert_manifest_error(
            lambda: mobile_ui.parse_and_validate(manifest),
            expected_code,
        )


@pytest.mark.asyncio
async def test_golden_bucket_install_and_serve(tmp_path) -> None:
    bucket_dir = tmp_path / "bucket"
    ui_dir = tmp_path / "ui"
    golden = test_server.materialize_golden_bucket(bucket_dir)
    file_bytes = _golden_file_bytes(golden)
    version = golden["manifest"]["version"]

    async with TestServer(test_server.build_directory_application(bucket_dir)) as server:
        base_url = str(server.make_url("")).rstrip("/")
        store = mobile_ui.MobileUiStore(ui_dir, base_url, golden["publicKey"])
        await store.install()

    status = store.get_status()
    assert status["state"] == "ready"
    assert status["installed_version"] == version
    assert status["update_available"] is False

    active = store.active_directory()
    assert active is not None
    for relative_path, expected in file_bytes.items():
        assert (active / relative_path).read_bytes() == expected

    app = fastapi.FastAPI()
    app.state.mobile_ui_store = store
    mobile_ui.add_mobile_ui_routes(app)
    client = TestClient(app)

    index = client.get("/mobile/")
    assert index.status_code == 200
    assert index.content == file_bytes["index.html"]
    assert mobile_ui.constants.CACHE_CONTROL_NO_CACHE in index.headers.get(
        "Cache-Control", ""
    )

    js = client.get("/mobile/_expo/static/js/web/entry-abc.js")
    assert js.status_code == 200
    assert js.content == file_bytes["_expo/static/js/web/entry-abc.js"]
    assert "immutable" in js.headers.get("Cache-Control", "")

    scoped_asset = client.get("/mobile/assets/node_modules/@scope/pkg/a%20b.txt")
    assert scoped_asset.status_code == 200
    assert scoped_asset.content == file_bytes["assets/node_modules/@scope/pkg/a b.txt"]

    spa = client.get("/mobile/some/deep/link")
    assert spa.status_code == 200
    assert spa.content == file_bytes["index.html"]

    missing = client.get("/mobile/_expo/static/js/web/missing.js")
    assert missing.status_code == 404


@pytest.mark.parametrize(
    ("prepare_bucket", "store_public_key", "expected_code"),
    [
        ("flip_js_byte", None, "integrity_check_failed"),
        ("wrong_store_key", "other", "signature_invalid"),
        ("edit_manifest_sha256", None, "signature_invalid"),
    ],
    ids=["flip_byte", "wrong_key", "edited_manifest"],
)
@pytest.mark.asyncio
async def test_golden_install_tamper_rejected(
    tmp_path,
    prepare_bucket,
    store_public_key,
    expected_code,
) -> None:
    bucket_dir = tmp_path / "bucket"
    ui_dir = tmp_path / "ui"
    golden = test_server.materialize_golden_bucket(bucket_dir)
    js_rel = "_expo/static/js/web/entry-abc.js"
    version = golden["manifest"]["version"]

    if prepare_bucket == "flip_js_byte":
        js_path = bucket_dir / version / js_rel
        data = bytearray(js_path.read_bytes())
        data[0] ^= 0xFF
        js_path.write_bytes(bytes(data))
    elif prepare_bucket == "edit_manifest_sha256":
        manifest_path = bucket_dir / mobile_ui.constants.MANIFEST_FILE_NAME
        on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
        on_disk["files"][0]["sha256"] = "0" * 64
        manifest_path.write_text(json.dumps(on_disk), encoding="utf-8")

    public_key = golden["publicKey"]
    if store_public_key == "other":
        _private_key, public_key = test_server.generate_keypair()

    async with TestServer(test_server.build_directory_application(bucket_dir)) as server:
        base_url = str(server.make_url("")).rstrip("/")
        store = mobile_ui.MobileUiStore(ui_dir, base_url, public_key)
        with pytest.raises(mobile_ui.MobileUiError) as exc_info:
            await store.install()
        assert exc_info.value.code.value == expected_code

    _assert_no_install(ui_dir)
    _assert_install_error_status(store, expected_code)


@pytest.mark.asyncio
async def test_golden_bucket_update_flow(tmp_path) -> None:
    bucket_dir = tmp_path / "bucket"
    ui_dir = tmp_path / "ui"
    golden = test_server.materialize_golden_bucket(bucket_dir)
    version1 = golden["manifest"]["version"]
    file_bytes = _golden_file_bytes(golden)

    async with TestServer(test_server.build_directory_application(bucket_dir)) as server:
        base_url = str(server.make_url("")).rstrip("/")
        store = mobile_ui.MobileUiStore(ui_dir, base_url, golden["publicKey"])
        await store.install()

    private_key2, public_key2 = test_server.generate_keypair()
    version2 = "bbbbbbbbbbbbbbbb"
    updated_files = dict(file_bytes)
    updated_files["index.html"] = b"<html>updated</html>"
    manifest_files = [
        test_server.file_entry(path, content)
        for path, content in updated_files.items()
    ]
    manifest2 = test_server.sign_manifest(
        private_key2, version2, manifest_files, sequence=golden["manifest"]["sequence"] + 100
    )
    test_server.materialize_bucket(bucket_dir, manifest2, updated_files)

    async with TestServer(test_server.build_directory_application(bucket_dir)) as server:
        base_url = str(server.make_url("")).rstrip("/")
        store.update_base_url = base_url
        store.public_key = public_key2
        store.public_keys = mobile_ui.parse_public_keys(public_key2)
        await store.install()

    status = store.get_status()
    assert status["state"] == "ready"
    assert status["installed_version"] == version2

    versions_dir = ui_dir / mobile_ui.constants.VERSION_DIR_NAME
    remaining = {path.name for path in versions_dir.iterdir() if path.is_dir()}
    assert remaining == {version1, version2}

    app = fastapi.FastAPI()
    app.state.mobile_ui_store = store
    mobile_ui.add_mobile_ui_routes(app)
    client = TestClient(app)
    response = client.get("/mobile/")
    assert response.status_code == 200
    assert response.content == updated_files["index.html"]


def _mobile2_repo_dir() -> str | None:
    return os.environ.get("MOBILE2_REPO_DIR")


def _live_test_skip_reason() -> str | None:
    repo = _mobile2_repo_dir()
    if not repo:
        return "MOBILE2_REPO_DIR is not set"
    if shutil.which("node") is None:
        return "node executable not found (MOBILE2_REPO_DIR live publisher test)"
    cli_path = pathlib.Path(repo) / "scripts" / "mobile-ui" / "cli.mjs"
    if not cli_path.is_file():
        return f"MOBILE2_REPO_DIR publisher CLI missing at {cli_path}"
    return None


_LIVE_SKIP_REASON = _live_test_skip_reason()


@pytest.mark.asyncio
@pytest.mark.skipif(
    _LIVE_SKIP_REASON is not None,
    reason=_LIVE_SKIP_REASON or "MOBILE2_REPO_DIR is not set",
)
async def test_live_mobile2_publisher_bucket(tmp_path) -> None:
    repo = _mobile2_repo_dir()
    assert repo is not None
    run_root = tmp_path / "live"
    dist_dir = run_root / "dist"
    bucket_dir = run_root / "bucket"
    ui_dir = run_root / "ui"
    key_file = run_root / "publish.key"
    dist_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html>/mobile/</html>", encoding="utf-8")
    expo_dir = dist_dir / "_expo" / "static" / "js" / "web"
    expo_dir.mkdir(parents=True)
    (expo_dir / "entry-live.js").write_text("live();", encoding="utf-8")
    (dist_dir / "assets").mkdir()
    (dist_dir / "assets" / "a b.txt").write_text("live", encoding="utf-8")

    def run_publish() -> str:
        completed = subprocess.run(
            [
                "node",
                "scripts/mobile-ui/cli.mjs",
                "publish",
                "--dist",
                str(dist_dir.resolve()),
                "--out",
                str(bucket_dir.resolve()),
                "--key-file",
                str(key_file.resolve()),
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo,
        )
        public_key = None
        for line in completed.stdout.splitlines():
            if line.startswith("OCTOBOT_MOBILE_UI_PUBLIC_KEY="):
                public_key = line.split("=", 1)[1].strip()
        assert public_key
        return public_key

    public_key = run_publish()

    async with TestServer(test_server.build_directory_application(bucket_dir)) as server:
        base_url = str(server.make_url("")).rstrip("/")
        store = mobile_ui.MobileUiStore(ui_dir, base_url, public_key)
        await store.install()

    assert store.get_status()["state"] == "ready"
    app = fastapi.FastAPI()
    app.state.mobile_ui_store = store
    mobile_ui.add_mobile_ui_routes(app)
    client = TestClient(app)
    first_index = client.get("/mobile/")
    assert first_index.status_code == 200
    assert b"/mobile/" in first_index.content
    version1 = store.get_status()["installed_version"]

    (dist_dir / "index.html").write_text("<html>/mobile/ v2</html>", encoding="utf-8")
    run_publish()

    async with TestServer(test_server.build_directory_application(bucket_dir)) as server:
        store.update_base_url = str(server.make_url("")).rstrip("/")
        await store.install()

    version2 = store.get_status()["installed_version"]
    assert version2 != version1
    second_index = client.get("/mobile/")
    assert second_index.status_code == 200
    assert b"v2" in second_index.content
