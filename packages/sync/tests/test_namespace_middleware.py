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

"""Tests for NamespaceRewriteMiddleware."""

import pytest

from octobot_sync.app import NamespaceRewriteMiddleware


def _make_scope(path: str, raw_path: bytes | None = None, scope_type: str = "http") -> dict:
    scope = {"type": scope_type, "path": path}
    if raw_path is not None:
        scope["raw_path"] = raw_path
    return scope


async def _call(middleware: NamespaceRewriteMiddleware, scope: dict) -> dict:
    captured = {}

    async def inner(s, receive, send):
        captured.update(s)

    await middleware(scope, None, None)
    # The inner app is the one that receives the (possibly rewritten) scope.
    # We need to capture via a different approach: pass a capturing inner app.
    return captured


async def _run(namespaces: list[str], scope: dict) -> dict:
    captured = {}

    async def inner(s, receive, send):
        captured.update(s)

    mw = NamespaceRewriteMiddleware(inner, namespaces=namespaces)
    await mw(scope, None, None)
    return captured


async def test_namespace_path_rewritten():
    result = await _run(["octobot"], _make_scope("/octobot/v1/push/x"))
    assert result["path"] == "/v1/octobot/push/x"


async def test_namespace_raw_path_rewritten():
    result = await _run(
        ["octobot"],
        _make_scope("/octobot/v1/push/x", raw_path=b"/octobot/v1/push/x"),
    )
    assert result["path"] == "/v1/octobot/push/x"
    assert result["raw_path"] == b"/v1/octobot/push/x"


async def test_non_namespace_path_unchanged():
    result = await _run(["octobot"], _make_scope("/v1/push/x"))
    assert result["path"] == "/v1/push/x"


async def test_health_path_unchanged():
    result = await _run(["octobot"], _make_scope("/health"))
    assert result["path"] == "/health"


async def test_exact_prefix_match():
    result = await _run(["octobot"], _make_scope("/octobot/v1"))
    assert result["path"] == "/v1/octobot"


async def test_non_http_scope_unchanged():
    scope = {"type": "lifespan", "path": "/octobot/v1/push/x"}
    result = await _run(["octobot"], scope)
    assert result["path"] == "/octobot/v1/push/x"


async def test_multiple_namespaces():
    result_a = await _run(["foo", "bar"], _make_scope("/foo/v1/push/x"))
    assert result_a["path"] == "/v1/foo/push/x"

    result_b = await _run(["foo", "bar"], _make_scope("/bar/v1/push/x"))
    assert result_b["path"] == "/v1/bar/push/x"


async def test_raw_path_none_not_set():
    scope = {"type": "http", "path": "/octobot/v1/push/x"}
    result = await _run(["octobot"], scope)
    assert result["path"] == "/v1/octobot/push/x"
    assert "raw_path" not in result


async def test_with_root_path_from_starlette_mount():
    # Starlette Mount sets root_path to the stripped prefix but leaves path unchanged.
    # Middleware must compute effective_path = path - root_path before matching.
    scope = {"type": "http", "path": "/sync/octobot/v1/push/x", "root_path": "/sync"}
    result = await _run(["octobot"], scope)
    # new effective = /v1/octobot/push/x, so new path = /sync + /v1/octobot/push/x
    assert result["path"] == "/sync/v1/octobot/push/x"
    assert result["root_path"] == "/sync"


async def test_with_root_path_non_namespace_unchanged():
    # /health doesn't match any namespace prefix; path must be left as-is.
    scope = {"type": "http", "path": "/sync/health", "root_path": "/sync"}
    result = await _run(["octobot"], scope)
    assert result["path"] == "/sync/health"


async def test_starlette_mount_full_routing():
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Mount
    from starlette.testclient import TestClient

    async def inner_asgi(scope, receive, send):
        assert scope["path"] == "/sync/v1/octobot/push/x"
        resp = PlainTextResponse("ok")
        await resp(scope, receive, send)

    mw = NamespaceRewriteMiddleware(inner_asgi, namespaces=["octobot"])
    outer = Starlette(routes=[Mount("/sync", app=mw)])
    client = TestClient(outer, raise_server_exceptions=True)
    resp = client.get("/sync/octobot/v1/push/x")
    assert resp.status_code == 200
