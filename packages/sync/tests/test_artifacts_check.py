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

"""Tests for tests/artifacts_check.py's step composition and PASS/FAIL reporting.

artifacts_check.run_check builds its own session from a raw sync_url, so — unlike
test_integration_artifacts.py's ASGITransport fixture — this needs a real local
uvicorn server serving the same dk_app fixture.
"""

import asyncio

import pytest
import uvicorn

import octobot_commons.os_util as commons_os_util

import tests.test_integration_artifacts as integration_fixtures
import tests.artifacts_check as artifacts_check


# Well-known Hardhat test key #2 — public, safe to embed in tests.
_PRIV = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365"


@pytest.fixture
def store():
    return integration_fixtures.MemoryObjectStore()


@pytest.fixture
async def sync_url(store):
    """A real uvicorn server serving the same dk_app config as test_integration_artifacts.py."""
    app = integration_fixtures.sync_app.create_app(
        store,
        sync_config=integration_fixtures._DK_CONFIG,
        role_enricher=integration_fixtures._make_dk_role_enricher(store),
    )
    port = commons_os_util.find_first_free_listen_port_after_base("127.0.0.1", 31500, max_offset=256)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    serve_task = asyncio.create_task(server.serve())
    await asyncio.sleep(0.25)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        await serve_task


class TestRunCheck:
    @pytest.mark.asyncio
    async def test_all_steps_pass_and_report_correctly(self, sync_url, capsys):
        ok = await artifacts_check.run_check(_PRIV, sync_url, "check-artifact-1", "1.0.0")

        assert ok is True
        out = capsys.readouterr().out
        assert "[FAIL]" not in out
        for step in (
            "derive identity",
            "build session",
            "artifact space creation",
            "ensure keyring",
            "open encryptor (publish)",
            "seal payload",
            "publish (append)",
            "resolve space (pull)",
            "open encryptor (pull)",
            "event fetching (pull)",
            "unseal + round-trip",
        ):
            assert f"[PASS] {step}" in out

    @pytest.mark.asyncio
    async def test_reports_created_new_then_reused_existing(self, sync_url, capsys):
        await artifacts_check.run_check(_PRIV, sync_url, "check-artifact-2", "1.0.0")
        first_out = capsys.readouterr().out
        assert "created new" in first_out

        await artifacts_check.run_check(_PRIV, sync_url, "check-artifact-2", "1.0.0")
        second_out = capsys.readouterr().out
        assert "reused existing" in second_out

    @pytest.mark.asyncio
    async def test_fails_cleanly_on_an_unreachable_server(self, capsys):
        ok = await artifacts_check.run_check(
            _PRIV, "http://127.0.0.1:1", "check-artifact-3", "1.0.0"
        )

        assert ok is False
        out = capsys.readouterr().out
        assert "[FAIL]" in out
        assert "RESULT" not in out


class TestMain:
    @pytest.mark.asyncio
    async def test_returns_zero_on_success(self, sync_url, capsys):
        # async_main directly, not main(): main()'s own asyncio.run() would leave
        # sync_url's background uvicorn task (on this test's event loop) unpumped mid-test.
        exit_code = await artifacts_check.async_main(
            ["--private-key", _PRIV, "--sync-url", sync_url, "--artifact-name", "check-artifact-4"]
        )

        assert exit_code == 0
        assert "RESULT: all steps passed" in capsys.readouterr().out

    def test_returns_nonzero_on_failure(self, capsys):
        exit_code = artifacts_check.main(
            [
                "--private-key", _PRIV,
                "--sync-url", "http://127.0.0.1:1",
                "--artifact-name", "check-artifact-5",
            ]
        )

        assert exit_code == 1
        assert "RESULT: FAILED" in capsys.readouterr().out
