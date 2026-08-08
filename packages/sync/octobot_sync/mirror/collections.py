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

"""Node collections the space-mirror can offer — the Python-side mirror of
``octobot_client_ts/src/client/mirror/collections.ts``. Ids are the SAME wire
collection names as the node's own sync layer
(``octobot_sync.enums.Collections``/``TemporaryCollections``) and the
website-pairing grant — one identifier space across both writers, the settings
UI, and the grant.

``visibility`` is who can ever reach a collection's mirrored copy:

- ``"private"`` — the wallet's own devices only, sealed under the space
  keyring. A pairing grant can never include it.
- ``"shared"`` — sealed under the node's OWN keyring, so a per-node grant
  reaches exactly that collection (the website-pairing flow).
- ``"public"`` — world-readable plaintext. Nothing is ``"public"`` today.

``user-accounts-auth`` is intentionally absent — never a configurable
mirror-eligible collection, at any layer, on any platform.
"""

from __future__ import annotations

from typing import Literal, NamedTuple

MirrorVisibility = Literal["private", "shared", "public"]

MirrorStorageTier = Literal["private", "isolated", "public"]


class MirrorCollection(NamedTuple):
    id: str
    default_enabled: bool
    visibility: MirrorVisibility


MIRROR_COLLECTIONS: tuple[MirrorCollection, ...] = (
    MirrorCollection("user-accounts", True, "shared"),
    MirrorCollection("user-data", True, "shared"),
    MirrorCollection("user-strategies", True, "shared"),
    MirrorCollection("user-accounts-trading", False, "shared"),
    MirrorCollection("user-settings", False, "private"),
)

DEFAULT_MIRROR_COLLECTIONS: list[str] = [c.id for c in MIRROR_COLLECTIONS if c.default_enabled]

# ONE space per wallet, holding every mirrored collection whatever its
# visibility. This used to be three spaces, one per visibility, because a space
# keyring is space-wide and a space:member grant reaches every enc node in the
# space. Per-node keyrings (the "isolated" tier) make that unnecessary: a grant
# now reaches exactly one node. Must match the TS side's MIRROR_SPACE_NAME.
MIRROR_SPACE_NAME = "octobot-mirror"


def is_known_mirror_collection(collection_id: str) -> bool:
    return any(c.id == collection_id for c in MIRROR_COLLECTIONS)


def mirror_visibility_for(collection_id: str) -> MirrorVisibility:
    """An UNKNOWN id resolves to ``"private"`` — the safe end of the enum, so a
    typo'd or stale collection id can never read as grant-reachable or
    world-readable."""
    for collection in MIRROR_COLLECTIONS:
        if collection.id == collection_id:
            return collection.visibility
    return "private"


def is_third_party_eligible(collection_id: str) -> bool:
    """DERIVED from ``visibility``, not a stored field: "can a pairing grant
    ever reach this collection"."""
    return mirror_visibility_for(collection_id) != "private"


def is_public_mirror_collection(collection_id: str) -> bool:
    return mirror_visibility_for(collection_id) == "public"


def is_isolated_mirror_collection(collection_id: str) -> bool:
    """Whether the node is sealed under its own per-node keyring — the
    grantable ones."""
    return mirror_visibility_for(collection_id) == "shared"


def mirror_tier_for(collection_id: str) -> MirrorStorageTier:
    """The ``SpaceMirrorCollection.tier`` handed to the mirror channel."""
    visibility = mirror_visibility_for(collection_id)
    if visibility == "public":
        return "public"
    if visibility == "shared":
        return "isolated"
    return "private"


# Where one collection's node content lives. Must stay identical to the TS
# side's `mirrorDocPath`, or the writer and the website-side reader disagree on
# the path.
#
# `objinv` is the odd shape (`objects/n/{node_id}/content`) because it is
# per-node-scoped server-side: read roles `space:member` OR `cap:read:objinv`,
# which is what lets a per-node grant holder fetch it without space membership.
# `objdoc` has no cap fallback at all, which is why the isolated tier cannot
# use it. `objpub` is the world-readable plaintext one.
#
# No collision with ordinary user documents: the mirror uses its own dedicated
# space, and node ids are minted by `create_node`, never a collection id.
def mirrordoc_path(collection_id: str, space_id: str, node_id: str) -> str:
    visibility = mirror_visibility_for(collection_id)
    if visibility == "public":
        return f"spaces/{space_id}/objects/pub/{node_id}"
    if visibility == "shared":
        return f"spaces/{space_id}/objects/n/{node_id}/content"
    return f"spaces/{space_id}/objects/docs/{node_id}"


def mirrordoc_pull_path(collection_id: str, space_id: str, node_id: str) -> str:
    return f"/pull/{mirrordoc_path(collection_id, space_id, node_id)}"


def mirrordoc_push_path(collection_id: str, space_id: str, node_id: str) -> str:
    return f"/push/{mirrordoc_path(collection_id, space_id, node_id)}"
