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

"""Node-side space-mirror writer — writer-only, per the space-mirror pairing
design's Python-parity finding (no invite minting, no revocation, no
session-less reads happen here; those all stay in `octobot_client_ts`, which
has full feature parity with `starfish-spaces`).

Built directly on `starfish_spaces` (the published, actively-maintained
Python port of the same spaces domain `octobot_client_ts` targets on the TS
side) rather than any local/vendored copy — there is no gap to work around
here, unlike an earlier vendored fork this module used to depend on.

NOT independently verified against a live server in this session — this
module has been typechecked/read-reviewed and unit-tested only at the
pure-logic layer (`plan.py`) plus the isolated `_pull_hash_or_none` helper
(`packages/sync/tests/mirror/test_writer_pull_hash_or_none.py`). Verify this
file end-to-end in a real dev environment before relying on it.

Deliberately bypasses `starfish_spaces.space_access.get_node_access` for the
actual content read/write — that function's `enc`-node branch requires a
PRE-CACHED space-member cap entry (`get_space_access_entry`) that nothing in
this module populates for a space's own OWNER on first creation. Since
`session.content_client`'s cap is already `owner_scope()` (full owner access
to ALL spaces, confirmed by reading `starfish_spaces.session`), and
`objdoc`'s `write_roles` includes `space:owner` (an identity-based role,
satisfied regardless of the cap's own `collections` scope — the server-side
role enricher checks `_access.owner == caller identity`, not cap contents),
using `session.content_client`/`session.spaces_keyring_client` directly for
both the keyring and the content push works correctly without depending on
the cached-cap path at all.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional, TypedDict

import octobot_commons.logging as logging
from starfish_sdk import StarfishHttpError
from starfish_sdk.types import ConflictError
from starfish_spaces.client import ClientOpts, DeviceKeys, open_encryptor, owner_ensure_keyring
from starfish_spaces.nodes import create_node
from starfish_spaces.object_index import read_object_tree
from starfish_spaces.registry import create_space, read_spaces
from starfish_spaces.session import BuildSessionOpts, Session, build_session, owner_trusted_adders

import octobot_sync.constants as sync_constants
from octobot_sync.mirror.collections import (
    MIRROR_SPACE_PRIVATE_NAME,
    MIRROR_SPACE_SHARED_NAME,
    is_known_mirror_collection,
    mirror_space_name_for,
    mirrordoc_pull_path,
    mirrordoc_push_path,
)
from octobot_sync.mirror.plan import ExistingMirrorNode, plan_mirror_sync


class DerivedIdentity(TypedDict):
    """The `{userId, keys}` shape `build_mirror_session` expects — same shape
    a wallet-derived root identity resolves to on the TS side."""

    userId: str
    keys: DeviceKeys


async def build_mirror_session(
    derived: DerivedIdentity, sync_url: str, name: str = "octobot-node-mirror"
) -> Session:
    """Build the `starfish_spaces` `Session` the writer uses.

    `sync_url` is the SAME sync-server URL `create_sync_client`
    (`octobot_sync.client`) already targets — there is NO separate "DK
    server" host: `dk` is just another namespace mounted on the same
    drakkar_sync server the node's own `octobot` namespace already lives on
    (confirmed against the TS-side precedent, `octobot_client_ts`/
    `octobot-sdk`'s `dkOrigin = config.dkSpaces?.syncBaseUrl ??
    config.syncBaseUrl` — DK spaces default to the SAME base URL unless
    explicitly overridden). So this only needs to swap the namespace from
    the node's own (`octobot_sync.constants.SYNC_NAMESPACE`) to `'dk'` —
    reuse whatever URL the node already resolves for `create_sync_client`,
    don't invent a second config value for it. Unlike the vendored package
    this module used to depend on, `starfish_spaces.build_session` takes
    `client_opts` explicitly per call rather than through a global
    `configure_*` singleton, so that base URL has to be threaded through
    here rather than configured once at process startup.

    `derived` is the SAME wallet identity octobot_sync's own
    `WalletCapProvider`/`derive_root_identity` already derives (same
    `octobot:sync-bootstrap` challenge) — build it with
    `derived_identity_for_mirror()` below, so the node writes into the SAME
    mirror space the wallet's other devices (mobile, in no-node mode) would
    use.
    """
    client_opts: ClientOpts = {
        "baseUrl": f"{sync_url.rstrip('/')}/{sync_constants.SYNC_MOUNT_PATH}",
        "namespace": "dk",
    }
    return await build_session(
        BuildSessionOpts(
            user_id=derived["userId"],
            keys=derived["keys"],
            client_opts=client_opts,
            name=name,
        )
    )


def derived_identity_for_mirror(private_key: str) -> DerivedIdentity:
    """Convert octobot_sync's own wallet-derived root identity
    (`starfish_identities.RootIdentity`, from `derive_root_identity()`) into
    the `DerivedIdentity` TypedDict shape `build_mirror_session()` expects.

    `RootIdentity.keys` is a flat `RootKeyPair(ed_priv, ed_pub, kem_priv,
    kem_pub)` of hex strings (confirmed by reading the installed
    `starfish_identities` package directly, and matching the exact field
    access `WalletCapProvider.get_cap()` already uses in
    `octobot_sync/auth/provider.py`).
    """
    from octobot_sync.auth.provider import derive_root_identity

    root = derive_root_identity(private_key)
    return DerivedIdentity(
        userId=root.user_id,
        keys={
            "edPriv": root.keys.ed_priv,
            "edPub": root.keys.ed_pub,
            "kemPriv": root.keys.kem_priv,
            "kemPub": root.keys.kem_pub,
        },
    )


async def find_or_create_mirror_space(session: Session, name: str) -> dict[str, Any]:
    """Find one of the wallet's dedicated mirror spaces by name, creating it
    on first use. Pass `MIRROR_SPACE_SHARED_NAME` or
    `MIRROR_SPACE_PRIVATE_NAME` — see `collections.py` for why there are two.
    """
    doc = await read_spaces(session.spaces_registry_client, session)
    for space in doc.spaces:
        if space.get("name") == name:
            return space
    return await create_space(session, name)


async def _open_mirror_encryptor(session: Session, space_id: str) -> Any:
    collection_name = session.layout.keyring_name(space_id)
    trusted_adders = owner_trusted_adders(session)
    await owner_ensure_keyring(
        session.spaces_keyring_client,
        session.keys,
        collection_name,
        session.layout.keyring_pull(space_id),
        session.layout.keyring_push(space_id),
        trusted_adders,
    )
    return await open_encryptor(
        session.spaces_keyring_client,
        collection_name,
        session.keys["kemPriv"],
        trusted_adders,
    )


async def _find_or_create_mirror_node(
    session: Session,
    space_id: str,
    existing: Optional[ExistingMirrorNode],
    collection_id: str,
) -> ExistingMirrorNode:
    if existing is not None:
        return existing
    # access:'space', not 'invite': 'invite' resolves per-node access through an
    # isolated per-node keyring that nothing here seeds ("This node has no keyring
    # yet"). 'space' resolves through the space-wide keyring `_open_mirror_encryptor`
    # already opens via `owner_ensure_keyring` above. Mirrors the TS writer's identical
    # fix (packages/client/octobot_client_ts/src/client/mirror/writer.ts) — keep both
    # in sync, a node created with the wrong value here is broken for any reader.
    node = await create_node(
        session,
        space_id,
        {"type": collection_id, "title": collection_id, "access": "space", "enc": True},
    )
    return ExistingMirrorNode(id=node.id, type=node.type)


async def _pull_hash_or_none(client: Any, path: str) -> Optional[str]:
    """The existing doc's hash at `path`, or `None` if nothing's published
    there yet. `StarfishClient.pull()` raises `StarfishHttpError` on any
    non-200 (never returns `None` for "not found") and returns a
    `PullResult` dataclass (`.data`/`.hash`, not dict keys) on success.

    Both starfish-server implementations (TS and Python) answer a genuinely
    missing document with HTTP 200 and `{data: {}, hash: ""}` — never a 404
    — so the 404 branch below only ever fires for an unknown route/collection,
    not a missing document. `hash == ""` is the real "nothing published here"
    signal; truthy-checking `.data` instead (the previous version of this
    function) is wrong, because a collection this writer itself CLEARED
    (`_clear_mirror_node` writes `{}`) has empty `data` but a real, non-empty
    `hash` — that false-negative made every subsequent write to a disabled
    collection push `base_hash=None` against a doc the server knows exists,
    a guaranteed 409 that repeated forever. See
    `packages/sync/tests/mirror/test_writer_pull_hash_or_none.py`."""
    try:
        result = await client.pull(path)
    except StarfishHttpError as exc:
        if exc.status == 404:
            return None
        raise
    return result.hash if result.hash else None


async def _write_mirror_node(session: Session, space_id: str, node_id: str, data: Any) -> None:
    """CAS-write a raw (uncurated) projection into one mirror node — no
    field-allowlist, no merge: whatever `data` is IS the node's content
    after this call (see the space-mirror design's "fidelity = raw"
    decision)."""
    encryptor = await _open_mirror_encryptor(session, space_id)
    pull_path = mirrordoc_pull_path(space_id, node_id)
    push_path = mirrordoc_push_path(space_id, node_id)
    base_hash = await _pull_hash_or_none(session.spaces_keyring_client, pull_path)
    sealed = encryptor.encrypt(data if isinstance(data, dict) else {"value": data})
    await session.spaces_keyring_client.push(push_path, sealed, base_hash=base_hash)


async def _clear_mirror_node(session: Session, space_id: str, node_id: str) -> None:
    """Clear a disabled collection's mirror node content — the user said
    they don't want it synced, so stale private data must not sit there
    encrypted under the space key indefinitely (same "clear, don't just
    stop" convention `unpairWebsite()` uses on the TS side)."""
    await _write_mirror_node(session, space_id, node_id, {})


async def _sync_one_space(
    session: Session,
    space_name: str,
    enabled_collection_ids: list[str],
    read_source_collection: Callable[[str], Awaitable[Any]],
) -> dict[str, Any]:
    has_any_for_this_space = any(
        is_known_mirror_collection(cid) and mirror_space_name_for(cid) == space_name
        for cid in enabled_collection_ids
    )
    if not has_any_for_this_space:
        doc = await read_spaces(session.spaces_registry_client, session)
        if not any(s.get("name") == space_name for s in doc.spaces):
            return {"space_id": None, "created": [], "written": [], "cleared": []}

    space = await find_or_create_mirror_space(session, space_name)
    space_id = space["id"]
    tree = await read_object_tree(session.content_client, session, space_id)
    existing_nodes = [
        ExistingMirrorNode(id=n.id, type=n.type)
        for n in tree
        if is_known_mirror_collection(n.type)
    ]

    collections_for_this_space = [
        cid for cid in enabled_collection_ids
        if is_known_mirror_collection(cid) and mirror_space_name_for(cid) == space_name
    ]
    plan = plan_mirror_sync(existing_nodes, collections_for_this_space)
    existing_by_type = {n.type: n for n in existing_nodes}

    # Each collection's write/clear is isolated in its own try/except so one
    # collection's conflict (a real tamper, or a residual instance of the
    # false-conflict `_pull_hash_or_none` bug now fixed above, or any other
    # per-document push failure) can't abort every OTHER collection still
    # queued in this same cycle — the previous unhandled-exception behavior
    # meant one bad collection silently blocked every collection after it,
    # in both spaces, every cycle, until fixed. `written`/`cleared` below
    # only ever list what genuinely succeeded, so a caller inspecting the
    # summary sees the truth, not an optimistic plan.
    written: list[str] = []
    for collection_id in plan.to_write:
        try:
            node = await _find_or_create_mirror_node(
                session, space_id, existing_by_type.get(collection_id), collection_id
            )
            data = await read_source_collection(collection_id)
            await _write_mirror_node(session, space_id, node.id, data)
            written.append(collection_id)
        except (ConflictError, StarfishHttpError) as exc:
            logging.get_logger("MirrorWriter").exception(
                f"cloud mirror: failed to write '{collection_id}' in space '{space_name}': {exc}"
            )

    cleared: list[str] = []
    for node in plan.to_clear:
        try:
            await _clear_mirror_node(session, space_id, node.id)
            cleared.append(node.type)
        except (ConflictError, StarfishHttpError) as exc:
            logging.get_logger("MirrorWriter").exception(
                f"cloud mirror: failed to clear '{node.type}' in space '{space_name}': {exc}"
            )

    return {
        "space_id": space_id,
        "created": plan.to_create,
        "written": written,
        "cleared": cleared,
    }


async def sync_cloud_mirror(
    session: Session,
    enabled_collection_ids: list[str],
    read_source_collection: Callable[[str], Awaitable[Any]],
) -> dict[str, Any]:
    """One full cloud-mirror sync cycle across BOTH mirror spaces (shared +
    private). Callers (the scheduler hook) gate this behind the
    `cloud_sync_enabled` setting themselves — this function does no such
    gating on its own, it assumes it was only called because the setting is
    on. Mirrors `octobot_client_ts/src/client/mirror/writer.ts::
    syncCloudMirror` exactly (same two-space routing, same plan-then-apply
    shape) so both writers behave identically against the same server.
    """
    shared = await _sync_one_space(
        session, MIRROR_SPACE_SHARED_NAME, enabled_collection_ids, read_source_collection
    )
    private = await _sync_one_space(
        session, MIRROR_SPACE_PRIVATE_NAME, enabled_collection_ids, read_source_collection
    )
    return {
        "shared_space_id": shared["space_id"],
        "private_space_id": private["space_id"],
        "created": [*shared["created"], *private["created"]],
        "written": [*shared["written"], *private["written"]],
        "cleared": [*shared["cleared"], *private["cleared"]],
    }
