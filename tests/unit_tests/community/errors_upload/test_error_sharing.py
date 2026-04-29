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
import io
import zipfile

import mock
import pytest

import octobot.community.errors_upload.error_sharing as error_sharing


pytestmark = pytest.mark.asyncio

_FAKE_CLIENT = mock.MagicMock()
_FAKE_ADDRESS = "0xdeadbeef"
_FAKE_SIGNER = mock.MagicMock()
_PUSH_RESULT = {"errorId": "test-salt", "errorSecret": "test-secret"}


def _make_zip_bytes(filenames: list[str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name in filenames:
            zf.writestr(name, f"log content of {name}")
    return buf.getvalue()


@pytest.fixture
def mock_client_and_address():
    with mock.patch.object(
        error_sharing,
        "_get_client_and_address",
        return_value=(_FAKE_CLIENT, _FAKE_ADDRESS, _FAKE_SIGNER),
    ):
        yield


@pytest.fixture
def mock_sync_manager():
    push_mock = mock.AsyncMock(return_value=_PUSH_RESULT)
    with mock.patch("octobot.community.errors_upload.error_sharing.SyncManager") as cls:
        cls.return_value.push = push_mock
        yield cls, push_mock


async def test_upload_error_returns_result(mock_sync_manager):
    cls, push_mock = mock_sync_manager
    error = ValueError("boom")

    result = await error_sharing.upload_error(_FAKE_CLIENT, _FAKE_ADDRESS, error)

    push_mock.assert_awaited_once()
    payload = push_mock.await_args[0][0]
    assert payload["message"] == "boom"
    assert payload["type"] == "ValueError"
    assert "traceback" in payload
    assert "id" in payload
    assert "timestamp" in payload
    assert result["errorId"] == _PUSH_RESULT["errorId"]
    assert result["errorSecret"] == _PUSH_RESULT["errorSecret"]


async def test_upload_error_with_context_and_error_id(mock_sync_manager):
    _, push_mock = mock_sync_manager
    error = RuntimeError("ctx error")
    ctx = {"workflow": "abc"}

    result = await error_sharing.upload_error(
        _FAKE_CLIENT, _FAKE_ADDRESS, error,
        context=ctx, error_id="fixed-id"
    )

    payload = push_mock.await_args[0][0]
    assert payload["id"] == "fixed-id"
    assert payload["context"] == ctx
    assert result is not None


async def test_upload_error_returns_none_on_push_failure():
    push_mock = mock.AsyncMock(side_effect=Exception("network error"))
    with mock.patch("octobot.community.errors_upload.error_sharing.SyncManager") as cls:
        cls.return_value.push = push_mock
        result = await error_sharing.upload_error(
            _FAKE_CLIENT, _FAKE_ADDRESS, ValueError("x")
        )
    assert result is None


async def test_share_logs_returns_none_when_no_client():
    with mock.patch.object(error_sharing, "_get_client_and_address", return_value=None):
        result = await error_sharing.share_logs("/tmp/export")
    assert result is None


async def test_share_logs_uses_make_archive_when_no_log_paths(mock_client_and_address, mock_sync_manager):
    _, push_mock = mock_sync_manager
    zip_bytes = _make_zip_bytes(["OctoBot.log"])

    with (
        mock.patch("octobot.community.errors_upload.error_sharing.shutil.make_archive") as make_archive,
        mock.patch("builtins.open", mock.mock_open(read_data=zip_bytes)),
        mock.patch("os.path.isfile", return_value=True),
        mock.patch("os.remove"),
    ):
        result = await error_sharing.share_logs("/tmp/export")

    make_archive.assert_called_once()
    payload = push_mock.await_args[0][0]
    assert payload["type"] == "logs"
    assert payload["logs_zip_b64"] == base64.b64encode(zip_bytes).decode("ascii")
    assert result["errorId"] == _PUSH_RESULT["errorId"]


async def test_share_logs_zips_provided_log_paths(mock_client_and_address, mock_sync_manager, tmp_path):
    _, push_mock = mock_sync_manager

    log_file = tmp_path / "abc-123.log"
    log_file.write_text("automation log line")
    missing_file = str(tmp_path / "missing.log")

    result = await error_sharing.share_logs(
        str(tmp_path / "export"),
        log_paths=[str(log_file), missing_file],
    )

    payload = push_mock.await_args[0][0]
    zip_bytes = base64.b64decode(payload["logs_zip_b64"])
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()

    assert "abc-123.log" in names
    assert "missing.log" not in names
    assert result["errorId"] == _PUSH_RESULT["errorId"]


async def test_share_logs_with_log_paths_skips_make_archive(mock_client_and_address, mock_sync_manager, tmp_path):
    log_file = tmp_path / "wf.log"
    log_file.write_text("wf log")

    with mock.patch("octobot.community.errors_upload.error_sharing.shutil.make_archive") as make_archive:
        await error_sharing.share_logs(
            str(tmp_path / "export"),
            log_paths=[str(log_file)],
        )

    make_archive.assert_not_called()


async def test_share_logs_with_empty_log_paths(mock_client_and_address, mock_sync_manager, tmp_path):
    _, push_mock = mock_sync_manager

    result = await error_sharing.share_logs(
        str(tmp_path / "export"),
        log_paths=[],
    )

    payload = push_mock.await_args[0][0]
    zip_bytes = base64.b64decode(payload["logs_zip_b64"])
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert zf.namelist() == []
    assert result is not None


async def test_share_logs_returns_none_on_push_failure(mock_client_and_address, tmp_path):
    log_file = tmp_path / "wf.log"
    log_file.write_text("wf log")

    push_mock = mock.AsyncMock(side_effect=Exception("push failed"))
    with mock.patch("octobot.community.errors_upload.error_sharing.SyncManager") as cls:
        cls.return_value.push = push_mock
        result = await error_sharing.share_logs(
            str(tmp_path / "export"),
            log_paths=[str(log_file)],
        )

    assert result is None
