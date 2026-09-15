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

"""End-to-end integration of octobot_sync.artifacts against a real in-process dk
namespace: a real starfish_spaces Session, a real TOFU role enricher
(starfish_sharing.make_registry_role_enricher), and a real starfish_server app
mounted under /sync.
"""

import asyncio
import re
from unittest import mock

import httpx
import pytest
from fastapi import FastAPI

from starfish_sdk import StarfishClient
import starfish_sdk.types
from starfish_server.config.schema import (
    SyncConfig,
    CollectionConfig,
    NamespaceConfig,
    AppendOnlyConfig,
)
from starfish_sharing import make_registry_role_enricher
from starfish_spaces.client import ClientOpts, DeviceKeys
from starfish_spaces.session import BuildSessionOpts, Session, build_session

import octobot_sync.app as sync_app
import octobot_sync.constants as constants
import octobot_sync.artifacts as artifacts


class MemoryObjectStore:
    """Minimal in-memory AbstractObjectStore (every method takes *, context=None)."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get_string(self, key, *, context=None):
        return self._store.get(key)

    async def put(self, key, body, *, content_type=None, cache_control=None, context=None):
        self._store[key] = body

    async def list_keys(self, prefix, *, start_after=None, limit=None, context=None):
        keys = sorted(k for k in self._store if k.startswith(prefix))
        if start_after:
            keys = [k for k in keys if k > start_after]
        return keys[:limit] if limit else keys

    async def delete(self, key, *, context=None):
        self._store.pop(key, None)

    async def delete_many(self, keys, *, context=None):
        for k in keys:
            self._store.pop(k, None)


_DK_NAMESPACE = "dk"

_DK_CONFIG = SyncConfig(
    version=1,
    collections=[],
    namespaces={
        _DK_NAMESPACE: NamespaceConfig(
            collections=[
                # No "spaces" or "objindex" collection: artifacts.py never touches either
                # (see its module docstring). maxBodyBytes on these two matches the real
                # deployed values (131_072 / 65_536), not MAX_BODY_SIZE_PRIVATE.
                CollectionConfig(
                    name="spaceregistry",
                    storagePath="spaces/{spaceId}/_access",
                    readRoles=["space:member"],
                    writeRoles=["space:owner"],
                    encryption="none",
                    maxBodyBytes=131_072,
                ),
                CollectionConfig(
                    name="spacekeyring",
                    storagePath="spaces/{spaceId}/_keyring",
                    readRoles=["space:member"],
                    writeRoles=["space:owner"],
                    encryption="none",
                    maxBodyBytes=65_536,
                ),
                # Mirrors Infra/sync/server/drakkar_sync/apps/dk_spaces/collections.py's
                # "artifact-events" collection exactly.
                CollectionConfig(
                    name="artifact-events",
                    storagePath="spaces/{spaceId}/artifact/versions/{version}/events",
                    readRoles=["space:member"],
                    writeRoles=["space:owner"],
                    encryption="delegated",
                    appendOnly=AppendOnlyConfig(type="by_timestamp", requireAuthorSignature=True),
                    maxBodyBytes=constants.MAX_BODY_SIZE_SIGNAL,
                ),
            ]
        ),
    },
)


def _make_dk_role_enricher(store: MemoryObjectStore):
    return make_registry_role_enricher(
        store,
        id_param="spaceId",
        registry_path="spaces/{id}/_access",
        owner_role="space:owner",
        member_role="space:member",
        allow_tofu=True,
        id_pattern=re.compile(r"^[a-zA-Z0-9_-]+$"),
    )


# Well-known Anvil/Hardhat account #1 (0x7099...79C8) — public, safe to embed in tests.
_PRIV = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
# Well-known Anvil/Hardhat account #2 (0x3C44...93BC), matches tests/e2e/conftest.py's
# OTHER_PRIVATE_KEY — a second, distinct identity used as the copy-trading copier.
_COPIER_PRIV = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"


@pytest.fixture
def store():
    return MemoryObjectStore()


@pytest.fixture
def dk_app(store):
    inner = sync_app.create_app(
        store,
        sync_config=_DK_CONFIG,
        role_enricher=_make_dk_role_enricher(store),
    )
    outer = FastAPI()
    outer.mount("/sync", inner)  # mount exactly as node_api does
    return outer


async def _build_session(dk_app, private_key: str) -> Session:
    """A real starfish_spaces Session for `private_key`, wired to the in-process dk_app.

    starfish_spaces.session.build_session builds its own StarfishClients internally with
    no transport-injection hook, so starfish_spaces.session.make_space_client is
    monkeypatched for the duration of this call. Callable more than once per test (a
    fresh Session for the same identity, or a second identity for a copier).
    """
    transport = httpx.ASGITransport(app=dk_app)

    from octobot_sync.auth.provider import derive_root_identity
    import starfish_spaces.client as spaces_client_module
    import starfish_spaces.session as spaces_session_module

    root = derive_root_identity(private_key)
    keys: DeviceKeys = {
        "edPriv": root.keys.ed_priv,
        "edPub": root.keys.ed_pub,
        "kemPriv": root.keys.kem_priv,
        "kemPub": root.keys.kem_pub,
    }
    client_opts: ClientOpts = {"baseUrl": "http://test/sync", "namespace": _DK_NAMESPACE}

    def _make_space_client(cap, ed_priv_hex, opts):
        return StarfishClient(
            opts["baseUrl"],
            cap_provider=spaces_client_module.cap_provider_for(cap, ed_priv_hex),
            namespace=opts.get("namespace"),
            timeout=float(opts.get("timeout", 30.0)),
            client=httpx.AsyncClient(transport=transport),
        )

    original = spaces_session_module.make_space_client
    spaces_session_module.make_space_client = _make_space_client
    try:
        return await build_session(
            BuildSessionOpts(user_id=root.user_id, keys=keys, client_opts=client_opts)
        )
    finally:
        spaces_session_module.make_space_client = original


@pytest.fixture
async def artifact_session(dk_app):
    session = await _build_session(dk_app, _PRIV)
    yield session
    await session.content_client.close()
    await session.account_client.close()


class TestPublishAndPullArtifactEvent:
    @pytest.mark.asyncio
    async def test_round_trips_a_sealed_signed_event(self, artifact_session):
        space_id = artifacts.artifact_space_id("space-1")
        payload = {"kind": "test", "value": 1000.0}

        push_result = await artifacts.publish_artifact_event(
            artifact_session, space_id, "1.0.0", payload, ts=1000
        )
        assert push_result.hash

        pulled = await artifacts.pull_artifact_events(artifact_session, space_id, "1.0.0", last=10)
        assert pulled == [payload]

    @pytest.mark.asyncio
    async def test_two_events_are_returned_in_append_order(self, artifact_session):
        space_id = artifacts.artifact_space_id("space-2")
        first = {"kind": "test", "value": 1000.0}
        second = {"kind": "test", "value": 2000.0}

        await artifacts.publish_artifact_event(artifact_session, space_id, "1.0.0", first, ts=1000)
        await artifacts.publish_artifact_event(artifact_session, space_id, "1.0.0", second, ts=2000)

        pulled = await artifacts.pull_artifact_events(artifact_session, space_id, "1.0.0", last=10)
        assert pulled == [first, second]

    @pytest.mark.asyncio
    async def test_pull_of_an_unknown_space_returns_empty(self, artifact_session):
        space_id = artifacts.artifact_space_id("no-such-space")
        pulled = await artifacts.pull_artifact_events(artifact_session, space_id, "1.0.0", last=10)
        assert pulled == []

    @pytest.mark.asyncio
    async def test_reuses_the_same_space_across_publishes(self, artifact_session):
        space_id = artifacts.artifact_space_id("space-3")

        await artifacts.publish_artifact_event(artifact_session, space_id, "1.0.0", {"a": 1}, ts=1000)
        # Real server round-trip: confirms the space's _access doc persisted server-side.
        created_again = await artifacts.ensure_artifact_space(artifact_session, space_id)
        assert created_again is False

    @pytest.mark.asyncio
    async def test_ensure_artifact_space_reports_created_then_reused(self, artifact_session):
        # Regression test: a missing JSON doc pulls as 200 OK with an empty dict, not a
        # 404/exception. ensure_artifact_space originally treated "the pull didn't raise" as
        # "already exists" — confirmed against the real deployed dk_spaces server. Must use
        # a never-touched space id to catch this.
        space_id = artifacts.artifact_space_id("brand-new-never-published-space")

        created_first = await artifacts.ensure_artifact_space(artifact_session, space_id)
        assert created_first is True

        created_second = await artifacts.ensure_artifact_space(artifact_session, space_id)
        assert created_second is False

    @pytest.mark.asyncio
    async def test_a_fresh_session_for_the_same_identity_can_read_back_published_events(
        self, dk_app, artifact_session
    ):
        # artifact_session and this freshly-built one are two INDEPENDENT Session objects for
        # the same identity (_PRIV), simulating a bot restart. Proves decryption doesn't
        # depend on in-process state — it must be re-derivable from the private key plus a
        # fresh keyring pull.
        space_id = artifacts.artifact_space_id("space-fresh")
        payload = {"kind": "test", "value": 1000.0}
        await artifacts.publish_artifact_event(artifact_session, space_id, "1.0.0", payload, ts=1000)

        fresh_session = await _build_session(dk_app, _PRIV)
        try:
            pulled = await artifacts.pull_artifact_events(fresh_session, space_id, "1.0.0", last=10)
        finally:
            await fresh_session.content_client.close()
            await fresh_session.account_client.close()

        assert pulled == [payload]


class TestCopyTrading:
    """Publisher (_PRIV) grants a copier (_COPIER_PRIV, its own independent Session) access
    via grant_artifact_space_access — the known-identity path, not an invite link."""

    @pytest.mark.asyncio
    async def test_copier_read_raises_before_being_granted_access(
        self, dk_app, artifact_session
    ):
        space_id = artifacts.artifact_space_id("copy-space-gate")
        await artifacts.publish_artifact_event(artifact_session, space_id, "1.0.0", {"a": 1}, ts=1000)

        copier_session = await _build_session(dk_app, _COPIER_PRIV)
        try:
            with pytest.raises(starfish_sdk.types.StarfishHttpError) as excinfo:
                await artifacts.pull_artifact_events(copier_session, space_id, "1.0.0", last=10)
        finally:
            await copier_session.content_client.close()
            await copier_session.account_client.close()

        assert excinfo.value.status == 403

    @pytest.mark.asyncio
    async def test_copier_reads_the_event_after_being_granted_access(
        self, dk_app, artifact_session
    ):
        space_id = artifacts.artifact_space_id("copy-space-granted")
        payload = {"kind": "test", "value": 1000.0}
        await artifacts.publish_artifact_event(artifact_session, space_id, "1.0.0", payload, ts=1000)

        from octobot_sync.auth.provider import derive_root_identity

        copier_root = derive_root_identity(_COPIER_PRIV)
        copier_session = await _build_session(dk_app, _COPIER_PRIV)
        try:
            await artifacts.grant_artifact_space_access(
                artifact_session, space_id, copier_root.user_id, copier_root.keys.kem_pub
            )

            # owner_ed_pub is required here: without it, pull_artifact_events would treat
            # the copier as its own space owner and compute the wrong trusted-adder set.
            pulled = await artifacts.pull_artifact_events(
                copier_session, space_id, "1.0.0", last=10, owner_ed_pub=artifact_session.owner_ed_pub
            )
        finally:
            await copier_session.content_client.close()
            await copier_session.account_client.close()

        assert pulled == [payload]


class TestArtifactSpaceId:
    """Pure, no network — artifact_space_id must never depend on server state."""

    def test_is_deterministic_for_the_same_name(self):
        assert artifacts.artifact_space_id("name-x") == artifacts.artifact_space_id("name-x")

    def test_differs_across_names(self):
        assert artifacts.artifact_space_id("name-x") != artifacts.artifact_space_id("name-y")

    def test_matches_the_expected_shape(self):
        space_id = artifacts.artifact_space_id("name-x")
        assert space_id.startswith("sp-")
        digest = space_id.removeprefix("sp-")
        assert len(digest) == 32
        assert all(c in "0123456789abcdef" for c in digest)


class TestBodySizeLimit:
    """artifact-events caps at 65_536 bytes, 4x tighter than the old octobot/products path."""

    @pytest.mark.asyncio
    async def test_a_realistically_sized_payload_publishes_fine(self, artifact_session):
        space_id = artifacts.artifact_space_id("space-size-ok")
        payload = {
            "kind": "test",
            "snapshots": [{"value": i} for i in range(50)],
        }
        push_result = await artifacts.publish_artifact_event(
            artifact_session, space_id, "1.0.0", payload, ts=1000
        )
        assert push_result.hash

    @pytest.mark.asyncio
    async def test_a_payload_over_the_cap_is_rejected_with_a_clear_error(self, artifact_session):
        space_id = artifacts.artifact_space_id("space-too-big")
        payload = {
            "kind": "test",
            "snapshots": [{"value": i, "padding": "x" * 200} for i in range(400)],
        }
        with pytest.raises(starfish_sdk.types.StarfishHttpError) as excinfo:
            await artifacts.publish_artifact_event(artifact_session, space_id, "1.0.0", payload, ts=1000)
        assert excinfo.value.status in (400, 413)


class TestEnsureArtifactKeyring:
    @pytest.mark.asyncio
    async def test_a_fresh_keyring_makes_publishing_identity_able_to_decrypt(self, artifact_session):
        space_id = artifacts.artifact_space_id("space-keyring-fresh")
        await artifacts.ensure_artifact_space(artifact_session, space_id)

        # Nothing published yet: a missing keyring pulls as HTTP 200 + empty body, not a 404.
        assert await artifacts.open_artifact_encryptor(artifact_session, space_id) is None

        await artifacts.ensure_artifact_keyring(artifact_session, space_id)
        assert await artifacts.open_artifact_encryptor(artifact_session, space_id) is not None

    @pytest.mark.asyncio
    async def test_ensuring_an_existing_keyring_twice_is_a_no_op(self, artifact_session):
        space_id = artifacts.artifact_space_id("space-keyring-idempotent")
        await artifacts.ensure_artifact_space(artifact_session, space_id)
        await artifacts.ensure_artifact_keyring(artifact_session, space_id)

        # Must not raise, and the keyring must still be usable afterwards.
        await artifacts.ensure_artifact_keyring(artifact_session, space_id)
        assert await artifacts.open_artifact_encryptor(artifact_session, space_id) is not None


class TestOpenArtifactEncryptorPropagatesRealFailures:
    """Only a genuinely missing keyring (404, or 200+empty body) is treated as empty —
    anything else is a real failure the caller must see, not a silent None/[]."""

    @pytest.mark.asyncio
    async def test_a_non_404_pull_failure_propagates(self, artifact_session):
        space_id = artifacts.artifact_space_id("space-keyring-server-error")
        await artifacts.ensure_artifact_space(artifact_session, space_id)
        await artifacts.ensure_artifact_keyring(artifact_session, space_id)

        with mock.patch.object(
            artifact_session.content_client,
            "pull",
            mock.AsyncMock(side_effect=starfish_sdk.types.StarfishHttpError(500, "boom")),
        ):
            with pytest.raises(starfish_sdk.types.StarfishHttpError) as excinfo:
                await artifacts.open_artifact_encryptor(artifact_session, space_id)

        assert excinfo.value.status == 500


class TestEnsureArtifactSpaceConcurrency:
    @pytest.mark.asyncio
    async def test_two_concurrent_first_publishes_agree_on_a_single_creator(self, artifact_session):
        space_id = artifacts.artifact_space_id("space-cas-race")

        results = await asyncio.gather(
            artifacts.ensure_artifact_space(artifact_session, space_id),
            artifacts.ensure_artifact_space(artifact_session, space_id),
        )

        assert sorted(results) == [False, True]


class TestPublishArtifactEventMissingEncryptor:
    @pytest.mark.asyncio
    async def test_raises_a_clear_error_when_the_encryptor_cannot_be_opened(self, artifact_session):
        space_id = artifacts.artifact_space_id("space-no-encryptor")

        with mock.patch.object(artifacts, "open_artifact_encryptor", return_value=None):
            with pytest.raises(starfish_sdk.types.StarfishHttpError) as excinfo:
                await artifacts.publish_artifact_event(
                    artifact_session, space_id, "1.0.0", {"a": 1}, ts=1000
                )

        assert space_id in str(excinfo.value)
