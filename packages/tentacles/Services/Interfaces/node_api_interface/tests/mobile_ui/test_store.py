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

import asyncio
import json
import os
import sys

import aiohttp.web as web
import pytest
from aiohttp.test_utils import TestServer

_NODE_API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _NODE_API_DIR not in sys.path:
    sys.path.insert(0, _NODE_API_DIR)
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

import mobile_ui
import mobile_ui.enums as enums
import mobile_ui.errors as errors

import mobile_ui_test_server as test_server


@pytest.fixture()
def keypair():
    return test_server.generate_keypair()


def _bundle_files(version: str):
    index = b"<html>mobile</html>"
    js = b"console.log('entry');"
    logo = b"\x89PNG"
    files = [
        test_server.file_entry("index.html", index),
        test_server.file_entry("_expo/static/js/web/entry-abc.js", js),
        test_server.file_entry("assets/logo.png", logo),
    ]
    contents = {
        (version, "index.html"): index,
        (version, "_expo/static/js/web/entry-abc.js"): js,
        (version, "assets/logo.png"): logo,
    }
    return files, contents


async def _run_with_server(state, coroutine):
    app = test_server.build_application(state)
    async with TestServer(app) as server:
        base_url = str(server.make_url("")).rstrip("/")
        return await coroutine(base_url)


@pytest.mark.asyncio
async def test_first_install(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version = "abcd1234abcd1234"
    files, contents = _bundle_files(version)
    state = test_server.MobileUiTestServerState()
    state.manifest = test_server.sign_manifest(private_key, version, files)
    state.file_contents = contents

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        await store.install()
        status = store.get_status()
        assert status["state"] == enums.MobileUiState.READY
        assert status["installed_version"] == version
        active = store.active_directory()
        assert active is not None
        assert (active / "index.html").read_bytes() == contents[(version, "index.html")]
        assert (tmp_path / "current.json").read_text(encoding="utf-8") == json.dumps(
            {"version": version}, separators=(",", ":")
        )

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_second_install_same_version_skips_downloads(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version = "abcd1234abcd1234"
    files, contents = _bundle_files(version)
    state = test_server.MobileUiTestServerState()
    state.manifest = test_server.sign_manifest(private_key, version, files)
    state.file_contents = contents

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        await store.install()
        state.reset_requests()
        await store.install()
        assert state.file_requests == []

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_new_version_reuses_unchanged_file(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version1 = "1111111111111111"
    version2 = "2222222222222222"
    index = b"<html>v</html>"
    js = b"same-js"
    logo1 = b"logo-v1"
    logo2 = b"logo-v2"
    files1 = [
        test_server.file_entry("index.html", index),
        test_server.file_entry("_expo/static/js/web/entry-abc.js", js),
        test_server.file_entry("assets/logo.png", logo1),
    ]
    files2 = [
        test_server.file_entry("index.html", index),
        test_server.file_entry("_expo/static/js/web/entry-abc.js", js),
        test_server.file_entry("assets/logo.png", logo2),
    ]
    state = test_server.MobileUiTestServerState()
    state.file_contents = {
        (version1, "index.html"): index,
        (version1, "_expo/static/js/web/entry-abc.js"): js,
        (version1, "assets/logo.png"): logo1,
        (version2, "index.html"): index,
        (version2, "_expo/static/js/web/entry-abc.js"): js,
        (version2, "assets/logo.png"): logo2,
    }

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        state.manifest = test_server.sign_manifest(private_key, version1, files1)
        await store.install()
        state.manifest = test_server.sign_manifest(private_key, version2, files2)
        state.reset_requests()
        await store.install()
        assert "_expo/static/js/web/entry-abc.js" not in state.file_requests
        assert "assets/logo.png" in state.file_requests

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_bad_signature(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version = "abcd1234abcd1234"
    files, contents = _bundle_files(version)
    state = test_server.MobileUiTestServerState()
    state.manifest = test_server.sign_manifest(
        private_key, version, files, signature_override="invalid"
    )
    state.file_contents = contents

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        with pytest.raises(errors.SignatureError):
            await store.install()

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_tampered_file_keeps_previous_version(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version1 = "aaaaaaaaaaaaaaaa"
    version2 = "bbbbbbbbbbbbbbbb"
    files1, contents1 = _bundle_files(version1)
    index2 = b"<html>two</html>"
    js2 = b"tampered"
    logo_bytes = contents1[(version1, "assets/logo.png")]
    files2 = [
        test_server.file_entry("index.html", index2),
        test_server.file_entry("_expo/static/js/web/entry-abc.js", js2),
        test_server.file_entry("assets/logo.png", logo_bytes),
    ]
    state = test_server.MobileUiTestServerState()
    state.file_contents = dict(contents1)
    state.file_contents[(version2, "index.html")] = index2
    state.file_contents[(version2, "_expo/static/js/web/entry-abc.js")] = js2
    state.file_contents[(version2, "assets/logo.png")] = contents1[(version1, "assets/logo.png")]

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        state.manifest = test_server.sign_manifest(private_key, version1, files1)
        await store.install()
        before = (tmp_path / "current.json").read_text(encoding="utf-8")
        state.manifest = test_server.sign_manifest(private_key, version2, files2)
        wrong_js = b"not-the-manifest-hash"
        state.file_contents[(version2, "_expo/static/js/web/entry-abc.js")] = wrong_js
        with pytest.raises(errors.FileIntegrityError):
            await store.install()
        assert (tmp_path / "current.json").read_text(encoding="utf-8") == before
        assert not any(
            path.name.startswith(mobile_ui.constants.TMP_DIR_PREFIX)
            for path in tmp_path.iterdir()
        )

    await _run_with_server(state, run)



@pytest.mark.asyncio
async def test_manifest_404(tmp_path, keypair):
    _, public_key_b64 = keypair
    state = test_server.MobileUiTestServerState()
    state.fail_manifest = True

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        with pytest.raises(errors.ManifestFetchError):
            await store.install()

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_manifest_unreachable_keeps_ready(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version = "cccccccccccccccc"
    files, contents = _bundle_files(version)
    state = test_server.MobileUiTestServerState()
    state.manifest = test_server.sign_manifest(private_key, version, files)
    state.file_contents = contents

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        await store.install()
        state.fail_manifest = True
        await store._run_install()
        status = store.get_status()
        assert status["state"] == enums.MobileUiState.READY
        assert status["last_error"] == enums.MobileUiErrorCode.MANIFEST_FETCH_FAILED

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_unconfigured_store(tmp_path):
    store = mobile_ui.MobileUiStore(tmp_path, "", "")
    assert store.get_status()["state"] == enums.MobileUiState.NOT_CONFIGURED
    with pytest.raises(errors.MobileUiNotConfiguredError):
        await store.install()


@pytest.mark.asyncio
async def test_html_response_for_js_rejected(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version = "dddddddddddddddd"
    index = b"<html></html>"
    files = [
        test_server.file_entry("index.html", index),
        test_server.file_entry("bad.js", b"ignored"),
    ]
    state = test_server.MobileUiTestServerState()
    state.manifest = test_server.sign_manifest(private_key, version, files)
    state.file_contents = {
        (version, "index.html"): index,
        (version, "bad.js"): b"<html>error</html>",
    }

    async def file_handler(request: web.Request) -> web.Response:
        version_name = request.match_info["version"]
        path = request.match_info["path"]
        if path == "bad.js":
            return web.Response(body=b"<html>err</html>", content_type="text/html")
        content = state.file_contents.get((version_name, path))
        if content is None:
            raise web.HTTPNotFound()
        return web.Response(body=content)

    async def run(_base_url: str):
        app = web.Application()
        app.router.add_get(
            f"/{mobile_ui.constants.MANIFEST_FILE_NAME}",
            lambda _request: web.json_response(state.manifest),
        )
        app.router.add_get("/{version}/{path:.+}", file_handler)
        async with TestServer(app) as server:
            url = str(server.make_url("")).rstrip("/")
            store = mobile_ui.MobileUiStore(tmp_path, url, public_key_b64)
            with pytest.raises(errors.FileDownloadError):
                await store.install()

    await run("")


@pytest.mark.asyncio
async def test_start_install_concurrent_single_task(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version = "eeeeeeeeeeeeeeee"
    files, contents = _bundle_files(version)
    state = test_server.MobileUiTestServerState()
    state.manifest = test_server.sign_manifest(private_key, version, files)
    state.file_contents = contents

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        status1 = store.start_install()
        status2 = store.start_install()
        assert status1["state"] == enums.MobileUiState.INSTALLING
        assert status2["state"] == enums.MobileUiState.INSTALLING
        if store._install_task is not None:
            await store._install_task
        assert store.get_status()["state"] == enums.MobileUiState.READY

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_prune_keeps_active_and_previous(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    versions = [
        "ffffffffffffffff",
        "0000000000000000",
        "8888888888888888",
    ]
    state = test_server.MobileUiTestServerState()

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        for version in versions:
            files, contents = _bundle_files(version)
            state.manifest = test_server.sign_manifest(private_key, version, files)
            for key, value in contents.items():
                state.file_contents[key] = value
            await store.install()
        versions_dir = tmp_path / mobile_ui.constants.VERSION_DIR_NAME
        remaining = {path.name for path in versions_dir.iterdir() if path.is_dir()}
        assert remaining == {"0000000000000000", "8888888888888888"}

    await _run_with_server(state, run)


def test_active_directory_rejects_bad_current_json(tmp_path):
    store = mobile_ui.MobileUiStore(tmp_path, "http://example", "key")
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / mobile_ui.constants.CURRENT_FILE_NAME).write_text(
        json.dumps({"version": "../x"}), encoding="utf-8"
    )
    assert store.active_directory() is None


def test_active_directory_requires_manifest(tmp_path):
    store = mobile_ui.MobileUiStore(tmp_path, "http://example", "key")
    version = "ffffffffffffffff"
    version_dir = tmp_path / mobile_ui.constants.VERSION_DIR_NAME / version
    version_dir.mkdir(parents=True)
    (version_dir / "index.html").write_text("x", encoding="utf-8")
    (tmp_path / mobile_ui.constants.CURRENT_FILE_NAME).write_text(
        json.dumps({"version": version}), encoding="utf-8"
    )
    assert store.active_directory() is None


@pytest.mark.asyncio
async def test_rollback_lower_sequence_rejected(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version1 = "1111111111111111"
    version2 = "2222222222222222"
    files1, contents1 = _bundle_files(version1)
    files2, contents2 = _bundle_files(version2)
    state = test_server.MobileUiTestServerState()
    state.file_contents = {**contents1, **contents2}

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        state.manifest = test_server.sign_manifest(
            private_key, version1, files1, sequence=100
        )
        await store.install()
        before_current = (tmp_path / mobile_ui.constants.CURRENT_FILE_NAME).read_text(
            encoding="utf-8"
        )
        latest_before = store.latest_version
        state.manifest = test_server.sign_manifest(
            private_key, version2, files2, sequence=99
        )
        state.reset_requests()
        with pytest.raises(Exception) as exc_info:
            await store.install()
        assert exc_info.value.code == "rollback_rejected"
        assert store.last_error == enums.MobileUiErrorCode.ROLLBACK_REJECTED
        assert (tmp_path / mobile_ui.constants.CURRENT_FILE_NAME).read_text(
            encoding="utf-8"
        ) == before_current
        assert store.latest_version == latest_before

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_rollback_equal_sequence_different_version(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version1 = "aaaaaaaaaaaaaaaa"
    version2 = "bbbbbbbbbbbbbbbb"
    files1, contents1 = _bundle_files(version1)
    files2, contents2 = _bundle_files(version2)
    state = test_server.MobileUiTestServerState()
    state.file_contents = {**contents1, **contents2}

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        state.manifest = test_server.sign_manifest(
            private_key, version1, files1, sequence=200
        )
        await store.install()
        state.manifest = test_server.sign_manifest(
            private_key, version2, files2, sequence=200
        )
        with pytest.raises(Exception) as exc_info:
            await store.install()
        assert exc_info.value.code == "rollback_rejected"

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_equal_sequence_same_version_skips(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version = "cccccccccccccccc"
    files, contents = _bundle_files(version)
    state = test_server.MobileUiTestServerState()
    state.manifest = test_server.sign_manifest(
        private_key, version, files, sequence=300
    )
    state.file_contents = contents

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        await store.install()
        state.reset_requests()
        await store.install()
        assert state.file_requests == []

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_higher_sequence_installs(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version1 = "dddddddddddddddd"
    version2 = "eeeeeeeeeeeeeeee"
    files1, contents1 = _bundle_files(version1)
    files2, contents2 = _bundle_files(version2)
    state = test_server.MobileUiTestServerState()
    state.file_contents = {**contents1, **contents2}

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        state.manifest = test_server.sign_manifest(
            private_key, version1, files1, sequence=400
        )
        await store.install()
        state.manifest = test_server.sign_manifest(
            private_key, version2, files2, sequence=500
        )
        await store.install()
        assert store.get_status()["installed_version"] == version2

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_check_for_update_newer_manifest(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version1 = "ffffffffffffffff"
    version2 = "0000000000000001"
    files1, contents1 = _bundle_files(version1)
    files2, contents2 = _bundle_files(version2)
    state = test_server.MobileUiTestServerState()
    state.file_contents = {**contents1, **contents2}

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        state.manifest = test_server.sign_manifest(
            private_key, version1, files1, sequence=600
        )
        await store.install()
        versions_before = list(
            (tmp_path / mobile_ui.constants.VERSION_DIR_NAME).iterdir()
        )
        state.manifest = test_server.sign_manifest(
            private_key, version2, files2, sequence=700
        )
        state.reset_requests()
        status = await store.check_for_update()
        assert status["update_available"] is True
        assert status["latest_version"] == version2
        assert status["installed_version"] == version1
        assert status["last_error"] is None
        assert state.file_requests == []
        versions_after = list(
            (tmp_path / mobile_ui.constants.VERSION_DIR_NAME).iterdir()
        )
        assert versions_before == versions_after

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_check_for_update_same_version(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version = "1212121212121212"
    files, contents = _bundle_files(version)
    state = test_server.MobileUiTestServerState()
    state.manifest = test_server.sign_manifest(
        private_key, version, files, sequence=800
    )
    state.file_contents = contents

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        await store.install()
        status = await store.check_for_update()
        assert status["update_available"] is False
        assert status["last_error"] is None

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_check_unreachable_manifest(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version = "3434343434343434"
    files, contents = _bundle_files(version)
    state = test_server.MobileUiTestServerState()
    state.manifest = test_server.sign_manifest(private_key, version, files)
    state.file_contents = contents

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        await store.install()
        state.fail_manifest = True
        status = await store.check_for_update()
        assert status["state"] == enums.MobileUiState.READY
        assert status["last_error"] == enums.MobileUiErrorCode.MANIFEST_FETCH_FAILED

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_check_bad_signature_keeps_latest(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version = "5656565656565656"
    files, contents = _bundle_files(version)
    state = test_server.MobileUiTestServerState()
    state.manifest = test_server.sign_manifest(private_key, version, files, sequence=900)
    state.file_contents = contents

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        await store.install()
        store.latest_version = version
        state.manifest = test_server.sign_manifest(
            private_key, "7777777777777777", files, signature_override="bad"
        )
        status = await store.check_for_update()
        assert status["last_error"] == enums.MobileUiErrorCode.SIGNATURE_INVALID
        assert store.latest_version == version

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_check_while_install_running(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version = "7878787878787878"
    files, contents = _bundle_files(version)
    state = test_server.MobileUiTestServerState()
    state.manifest = test_server.sign_manifest(private_key, version, files)
    state.file_contents = contents

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        store.start_install()
        assert store._install_task is not None
        status = await store.check_for_update()
        assert status["state"] == enums.MobileUiState.INSTALLING
        if store._install_task is not None:
            await store._install_task

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_check_unconfigured(tmp_path):
    store = mobile_ui.MobileUiStore(tmp_path, "", "")
    status = await store.check_for_update()
    assert status["state"] == enums.MobileUiState.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_check_not_installed_sets_latest(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version = "9090909090909090"
    files, contents = _bundle_files(version)
    state = test_server.MobileUiTestServerState()
    state.manifest = test_server.sign_manifest(private_key, version, files, sequence=1000)
    state.file_contents = contents

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        status = await store.check_for_update()
        assert status["state"] == enums.MobileUiState.NOT_INSTALLED
        assert status["latest_version"] == version

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_comma_separated_public_key_installs(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version = "abababababababab"
    files, contents = _bundle_files(version)
    state = test_server.MobileUiTestServerState()
    state.manifest = test_server.sign_manifest(private_key, version, files)
    state.file_contents = contents
    wrong = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, f" {wrong} , {public_key_b64} ")
        await store.install()
        assert store.get_status()["state"] == enums.MobileUiState.READY

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_only_wrong_keys_signature_invalid(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version = "cdcdcdcdcdcdcdcd"
    files, contents = _bundle_files(version)
    state = test_server.MobileUiTestServerState()
    state.manifest = test_server.sign_manifest(private_key, version, files)
    state.file_contents = contents
    _, other_pub = test_server.generate_keypair()

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, other_pub)
        with pytest.raises(Exception) as exc_info:
            await store.install()
        assert exc_info.value.code == "signature_invalid"

    await _run_with_server(state, run)


@pytest.mark.asyncio
async def test_schema1_installed_does_not_block_install(tmp_path, keypair):
    private_key, public_key_b64 = keypair
    version_old = "efefefefefefefef"
    version_new = "1212121212131212"
    files_old, contents_old = _bundle_files(version_old)
    files_new, contents_new = _bundle_files(version_new)
    state = test_server.MobileUiTestServerState()
    state.file_contents = {**contents_old, **contents_new}

    async def run(base_url: str):
        store = mobile_ui.MobileUiStore(tmp_path, base_url, public_key_b64)
        state.manifest = test_server.sign_manifest(
            private_key, version_old, files_old, sequence=1100
        )
        await store.install()
        active = store.active_directory()
        assert active is not None
        schema1 = {
            "schema": 1,
            "version": version_old,
            "files": files_old,
            "signature": "x",
        }
        (active / mobile_ui.constants.INSTALLED_MANIFEST_FILE_NAME).write_text(
            json.dumps(schema1), encoding="utf-8"
        )
        state.manifest = test_server.sign_manifest(
            private_key, version_new, files_new, sequence=1200
        )
        await store.install()
        assert store.get_status()["installed_version"] == version_new

    await _run_with_server(state, run)
