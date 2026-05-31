#  Drakkar-Software OctoBot-Sync
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

"""Tests for SignedPathMiddleware.

The middleware strips any prefix that appears before the leading /v1/ segment
and clears root_path so the cap resolver sees exactly what the client signed.
"""

import pytest

from octobot_sync.app import SignedPathMiddleware


def _make_scope(
    path: str,
    root_path: str = "",
    raw_path: bytes | None = None,
    scope_type: str = "http",
) -> dict:
    scope = {"type": scope_type, "path": path, "root_path": root_path}
    if raw_path is not None:
        scope["raw_path"] = raw_path
    return scope


async def _run(scope: dict) -> dict:
    captured = {}

    async def inner(s, receive, send):
        captured.update(s)

    mw = SignedPathMiddleware(inner)
    await mw(scope, None, None)
    return captured


async def test_strips_prefix_before_v1():
    """When mounted at /sync, the /sync prefix must be stripped."""
    result = await _run(_make_scope("/sync/v1/octobot/push/x", root_path="/sync"))
    assert result["path"] == "/v1/octobot/push/x"
    assert result["root_path"] == ""


async def test_strips_mount_prefix_combined_with_root_path():
    """root_path + path together must find /v1/ and keep from there."""
    result = await _run(_make_scope("/v1/octobot/pull/y", root_path=""))
    assert result["path"] == "/v1/octobot/pull/y"


async def test_path_without_v1_unchanged():
    """A path that has no /v1/ segment is passed through unchanged."""
    result = await _run(_make_scope("/health"))
    assert result["path"] == "/health"


async def test_bare_v1_path_unchanged():
    """/v1/... paths without a mount prefix are passed through unchanged."""
    result = await _run(_make_scope("/v1/octobot/push/data"))
    assert result["path"] == "/v1/octobot/push/data"


async def test_non_http_scope_unchanged():
    scope = {"type": "lifespan", "path": "/v1/push/x"}
    result = await _run(scope)
    # Non-http scopes must not be touched
    assert result["path"] == "/v1/push/x"


async def test_raw_path_updated_when_present():
    scope = _make_scope(
        "/sync/v1/octobot/push/x",
        root_path="/sync",
        raw_path=b"/sync/v1/octobot/push/x",
    )
    result = await _run(scope)
    assert result["path"] == "/v1/octobot/push/x"
    assert result["raw_path"] == b"/v1/octobot/push/x"


async def test_raw_path_not_set_when_not_in_scope():
    scope = _make_scope("/prefix/v1/octobot/pull/z", root_path="/prefix")
    # raw_path not provided in scope
    assert "raw_path" not in scope
    result = await _run(scope)
    assert result["path"] == "/v1/octobot/pull/z"
    assert "raw_path" not in result


async def test_health_after_mount_unchanged():
    """A /health path under a mounted app must not be mangled."""
    result = await _run(_make_scope("/sync/health", root_path="/sync"))
    assert result["path"] == "/sync/health"


async def test_root_path_cleared_after_strip():
    """After stripping, root_path must be reset to empty string."""
    result = await _run(_make_scope("/mount/v1/octobot/pull/x", root_path="/mount"))
    assert result["root_path"] == ""
