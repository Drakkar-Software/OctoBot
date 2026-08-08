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

"""The load-bearing property of the one-channel-per-collection design: a
sync triggered by a write to ONE collection must not clear the others.

Uses a fake SpacePort (no mocks) so this exercises the real
`SpaceMirrorChannel` + `plan_space_mirror`, not a restatement of the intent.
`service.py` itself is not imported — it pulls in the node's provider stack,
which needs a full OctoBot install; what is under test is the channel
topology service.py builds, reproduced here exactly.
"""

from __future__ import annotations

import pytest
from starfish_replica.channel import REPLICATOR_CTX
from starfish_replica.space import SpaceMirrorCollection, create_space_mirror_channel

from octobot_sync.mirror.collections import (
    MIRROR_COLLECTIONS,
    MIRROR_SPACE_NAME,
    mirror_tier_for,
    mirrordoc_path,
)


class FakeHandle:
    def __init__(self, space_id, node_id, encryptor=None):
        self.space_id = space_id
        self.node_id = node_id
        self.client = None
        self.encryptor = encryptor
        self.is_owner_open = False


class FakePort:
    """In-memory spaces/nodes/content."""

    def __init__(self):
        self.spaces: list[dict] = []
        self.nodes: dict[str, list[dict]] = {}
        self.content: dict[str, object] = {}
        self.isolated_access: list[tuple[str, str]] = []
        self._seq = 0

    async def read_spaces(self, session):
        return list(self.spaces)

    async def create_space(self, session, name):
        self._seq += 1
        space = {"id": f"sp-{self._seq}", "name": name}
        self.spaces.append(space)
        self.nodes[space["id"]] = []
        return space

    async def read_object_tree(self, session, space_id):
        return list(self.nodes.get(space_id, []))

    async def create_node(self, session, space_id, inp):
        self._seq += 1
        node = {"id": f"nd-{self._seq}", "type": inp["type"], "children": []}
        if inp.get("access") and inp["access"] != "space":
            node["access"] = inp["access"]
        if inp.get("enc"):
            node["enc"] = True
        self.nodes.setdefault(space_id, []).append(node)
        return node

    async def set_node_access(self, session, space_id, node_id, patch):
        pass

    async def get_node_access(self, session, space_id, node_id, node=None):
        return FakeHandle(space_id, node_id)

    async def get_isolated_node_access(self, session, space_id, node_id):
        self.isolated_access.append((space_id, node_id))
        return FakeHandle(space_id, node_id, encryptor=f"node-keyring:{node_id}")

    async def push_node_doc(self, handle, pull_path, push_path, mutator, node=None):
        key = f"{handle.space_id}:{handle.node_id}"
        nxt = mutator(self.content.get(key))
        if nxt is None:
            return
        self.content[key] = nxt

    # helpers
    def space_id(self):
        return self.spaces[0]["id"] if self.spaces else None

    def node_for(self, type_):
        return next(
            (n for n in self.nodes.get(self.space_id(), []) if n["type"] == type_), None
        )

    def content_for(self, type_):
        node = self.node_for(type_)
        return self.content.get(f"{self.space_id()}:{node['id']}") if node else None


class Session:
    user_id = "user-1"


def build_channels(port, enabled: list[str]):
    """EXACTLY the topology service.py builds: one channel per collection,
    each with a single-element registry."""
    return {
        c.id: create_space_mirror_channel(
            name=c.id,
            session=Session(),
            collections=[
                SpaceMirrorCollection(
                    id=c.id, space_name=MIRROR_SPACE_NAME, tier=mirror_tier_for(c.id)
                )
            ],
            enabled_ids=lambda cid=c.id: ([cid] if cid in enabled else []),
            read_source=_reader,
            doc_path=mirrordoc_path,
            change_detection="source-hash",
            port=port,
        )
        for c in MIRROR_COLLECTIONS
    }


async def _reader(cid, _ctx):
    return {"collection": cid}


async def test_syncing_one_collection_does_not_clear_the_others():
    # The whole reason for one channel per collection. A channel whose
    # registry lists every collection but whose enabled_ids names only one
    # would treat the rest as "known but disabled" and CLEAR them.
    port = FakePort()
    enabled = ["user-accounts", "user-strategies", "user-settings"]
    channels = build_channels(port, enabled)

    for cid in enabled:
        await channels[cid].sync(REPLICATOR_CTX)
    assert port.content_for("user-accounts") == {"collection": "user-accounts"}
    assert port.content_for("user-strategies") == {"collection": "user-strategies"}

    # A write to ONE collection re-syncs only it.
    await channels["user-accounts"].sync(REPLICATOR_CTX)

    assert port.content_for("user-strategies") == {"collection": "user-strategies"}
    assert port.content_for("user-settings") == {"collection": "user-settings"}
    assert channels["user-accounts"].result.cleared == []


async def test_all_collections_share_one_space():
    port = FakePort()
    enabled = [c.id for c in MIRROR_COLLECTIONS if c.id != "user-data"]
    channels = build_channels(port, enabled)
    for cid in enabled:
        await channels[cid].sync(REPLICATOR_CTX)

    assert len(port.spaces) == 1
    assert port.spaces[0]["name"] == MIRROR_SPACE_NAME


async def test_grantable_collections_get_their_own_keyring_and_private_ones_do_not():
    port = FakePort()
    enabled = ["user-accounts", "user-settings"]
    channels = build_channels(port, enabled)
    for cid in enabled:
        await channels[cid].sync(REPLICATOR_CTX)

    # user-accounts is "shared" -> isolated: invite+enc, own keyring.
    assert port.node_for("user-accounts")["access"] == "invite"
    assert (port.space_id(), port.node_for("user-accounts")["id"]) in port.isolated_access
    # user-settings is "private" -> space keyring, never a per-node one.
    assert "access" not in port.node_for("user-settings")
    assert (port.space_id(), port.node_for("user-settings")["id"]) not in port.isolated_access


async def test_disabling_a_collection_clears_only_its_own_node():
    port = FakePort()
    enabled = ["user-accounts", "user-strategies"]
    channels = build_channels(port, enabled)
    for cid in list(enabled):
        await channels[cid].sync(REPLICATOR_CTX)

    enabled.remove("user-accounts")
    await channels["user-accounts"].sync(REPLICATOR_CTX)

    assert port.content_for("user-accounts") == {}
    assert port.content_for("user-strategies") == {"collection": "user-strategies"}


async def test_unchanged_data_is_not_rewritten():
    # change_detection="source-hash": an event that did not actually change the
    # projection costs zero pushes.
    port = FakePort()
    enabled = ["user-accounts"]
    channels = build_channels(port, enabled)
    await channels["user-accounts"].sync(REPLICATOR_CTX)
    await channels["user-accounts"].sync(REPLICATOR_CTX)

    assert channels["user-accounts"].result.skipped == ["user-accounts"]
    assert channels["user-accounts"].result.written == []
