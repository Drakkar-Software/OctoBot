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

"""Tests for `octobot_sync.mirror.writer._pull_hash_or_none` — the CAS-hash
lookup the mirror writer uses before every push. Adapted from the vendored
`packages/dkspaces/tests/test_pull_compat.py` (now deleted along with the
vendored `dk_spaces_sdk` package this module used to depend on), against the
REAL `starfish_sdk.StarfishClient.pull()` contract: it raises
`StarfishHttpError` on any non-200 (never returns `None` for "not found")
and returns a `starfish_protocol.types.PullResult` dataclass — `.data`/
`.hash` attributes, not dict keys — on success. Unlike the vendored
package's orphaned test, this one runs in CI (`packages/sync` is in
`.github/workflows/main.yml`'s test matrix)."""

import pytest
from starfish_protocol.types import PullResult
from starfish_sdk import StarfishHttpError

from octobot_sync.mirror.writer import _pull_hash_or_none


class _FakeClient:
    def __init__(self, result=None, error: Exception = None):
        self._result = result
        self._error = error
        self.pulled_paths: list[str] = []

    async def pull(self, path: str):
        self.pulled_paths.append(path)
        if self._error is not None:
            raise self._error
        return self._result


@pytest.mark.asyncio
async def test_returns_the_hash_for_a_real_document():
    client = _FakeClient(result=PullResult(data={"owner": "u1"}, hash="abc123", timestamp=1))
    assert await _pull_hash_or_none(client, "/pull/some/path") == "abc123"


@pytest.mark.asyncio
async def test_returns_none_on_a_404():
    client = _FakeClient(error=StarfishHttpError(404, "not found"))
    assert await _pull_hash_or_none(client, "/pull/some/path") is None


@pytest.mark.asyncio
async def test_reraises_a_non_404_http_error():
    client = _FakeClient(error=StarfishHttpError(403, "forbidden"))
    with pytest.raises(StarfishHttpError) as exc_info:
        await _pull_hash_or_none(client, "/pull/some/path")
    assert exc_info.value.status == 403


@pytest.mark.asyncio
async def test_a_cleared_but_existing_document_returns_its_real_hash_not_none():
    # Regression: this used to treat `data == {}` as "not found" and return
    # `None` even though `hash` is real and non-empty — exactly the shape
    # `_clear_mirror_node` itself produces (writes `{}` to disable a
    # collection). That false-negative made the NEXT write to the same node
    # push `base_hash=None` against a doc the server knows exists, a
    # guaranteed 409 that repeated forever. `hash` truthiness, not `data`
    # truthiness, is the real "does something exist here" signal — see both
    # starfish-server implementations, which answer a genuinely missing
    # document with `hash=""` (tested separately below), never a non-empty
    # hash alongside empty data.
    client = _FakeClient(result=PullResult(data={}, hash="abc123", timestamp=1))
    assert await _pull_hash_or_none(client, "/pull/some/path") == "abc123"


@pytest.mark.asyncio
async def test_a_genuinely_missing_document_has_an_empty_hash_and_returns_none():
    # The real "not found" shape both starfish-server implementations (TS
    # and Python) return for a document that was never written: HTTP 200,
    # `data={}`, `hash=""` — never a 404. This is the case `_pull_hash_or_none`
    # must treat as absent; the previous version got this right only by
    # accident, via the wrong signal (`data` emptiness).
    client = _FakeClient(result=PullResult(data={}, hash="", timestamp=1))
    assert await _pull_hash_or_none(client, "/pull/some/path") is None


@pytest.mark.asyncio
async def test_a_real_but_sparse_document_is_not_treated_as_absent():
    client = _FakeClient(result=PullResult(data={"spaces": [], "caps": {}}, hash="h1", timestamp=1))
    assert await _pull_hash_or_none(client, "/pull/some/path") == "h1"


@pytest.mark.asyncio
async def test_pulls_the_exact_path_given():
    client = _FakeClient(result=PullResult(data={"a": 1}, hash="h2", timestamp=1))
    await _pull_hash_or_none(client, "/pull/spaces/abc/_keyring")
    assert client.pulled_paths == ["/pull/spaces/abc/_keyring"]
