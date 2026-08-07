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
website-pairing read-only-device grant — one identifier space across the
writer (here, and the TS one), the settings UI, and the read-only grant.

``visibility`` is who can ever reach a collection's mirrored copy, as one
closed three-value enum rather than a pile of independent booleans — the same
values, per collection, as the TS twin:

- ``"private"`` — the wallet's own devices only. A read-only pairing grant can
  never include it. ``user-settings`` is mirror-eligible (useful for syncing a
  wallet's own devices) but never offered to a paired third party.
- ``"shared"`` — still E2EE and member-gated, but reachable by a read-only
  pairing grant the user hands out (the website-pairing flow).
- ``"public"`` — world-readable plaintext at its storage URL. Nothing is
  ``"public"`` today; the value exists so a future explicitly-published
  collection has somewhere to land, with the space routing below already
  correct for it.

``is_third_party_eligible`` is DERIVED from this (``visibility != "private"``),
so callers that only care about the "can a grant reach it" axis are unaffected
by the split.

``user-accounts-auth`` is intentionally absent — never a configurable
mirror-eligible collection, at any layer, on any platform.
"""

from __future__ import annotations

from typing import Literal, NamedTuple

MirrorVisibility = Literal["private", "shared", "public"]


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

# ONE SPACE PER VISIBILITY, exactly like the TS side, for the same two
# independent reasons.
#
# private vs shared: a non-isolated `invite_to_node` grant covers the WHOLE
# space it's minted against (Python has no per-node-keyring support — see the
# space-mirror design's parity finding), so `user-settings` must never share a
# space with a third-party-eligible collection or ANY read-only grant would
# also reach it.
#
# shared vs public: Infra's `_project_objindex_public` lifts every node whose
# stored access is `"public"` into the world-readable `_index/objects/public`
# projection, KEYED BY spaceId. A public node parked in the shared space would
# therefore disclose the shared space's id — the same id a read-only grant
# holder is handed — to anonymous callers. A third space keeps the published id
# disjoint from the granted one.
MIRROR_SPACE_SHARED_NAME = "octobot-mirror"
MIRROR_SPACE_PRIVATE_NAME = "octobot-mirror-private"
MIRROR_SPACE_PUBLIC_NAME = "octobot-mirror-public"

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
    """DERIVED from ``visibility``, not a stored field: "can a read-only pairing
    grant ever reach this collection". Both non-private tiers qualify."""
    return mirror_visibility_for(collection_id) != "private"


def is_public_mirror_collection(collection_id: str) -> bool:
    return mirror_visibility_for(collection_id) == "public"


def mirror_space_name_for(collection_id: str) -> str:
    visibility = mirror_visibility_for(collection_id)
    if visibility == "public":
        return MIRROR_SPACE_PUBLIC_NAME
    if visibility == "shared":
        return MIRROR_SPACE_SHARED_NAME
    return MIRROR_SPACE_PRIVATE_NAME


# Mirror node content lives in `objdoc`, the generic private merge-doc — the
# canonical content location for a node created `access:"space", enc:True`,
# which is how the writer creates them (matching OctoBot strategy graphs and
# OctoVault page content). Must stay identical to the TS side's
# `mirror/collections.ts::mirrorDocPath` for the private/shared visibilities.
#
# There was briefly a dedicated `mirrordoc` collection, purely because `objdoc`
# was capped at 256 KiB and a raw `user-accounts-trading` projection does not
# fit. `objdoc` is now 10 MiB and `mirrordoc` is gone.
#
# PRIVATE/SHARED ONLY. The TS side additionally routes a `visibility:"public"`
# collection to `objects/pub/` (`objpub`, world-readable plaintext); this
# helper does not, because this package's writer only ever creates
# `access:"space", enc:True` nodes and only walks the shared/private spaces.
# Nothing is `"public"` today, so the two sides cannot disagree in practice —
# but a public collection must not be written by this writer until it grows
# that routing.
#
# No collision with ordinary user documents: the mirror uses its own dedicated
# spaces, and node ids are minted by `create_node`, never a collection id.
def mirrordoc_path(space_id: str, node_id: str) -> str:
    return f"spaces/{space_id}/objects/docs/{node_id}"


def mirrordoc_pull_path(space_id: str, node_id: str) -> str:
    return f"/pull/{mirrordoc_path(space_id, node_id)}"


def mirrordoc_push_path(space_id: str, node_id: str) -> str:
    return f"/push/{mirrordoc_path(space_id, node_id)}"
