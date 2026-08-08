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

"""Registry of the node collections the space mirror can offer — Python twin of
``octobot_client_ts/src/client/mirror/collections.ts``, same ids as the node's
own sync layer (``octobot_sync.enums.Collections``). ``user-accounts-auth`` is
deliberately absent: never mirror-eligible, on any platform.

Access model (visibility, storage tier, doc paths):
``docs/content/client-sdk/website-pairing.md``.
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

# One space per wallet holds every collection; the tier, not the space, is what
# separates audiences. Must match the TS side's MIRROR_SPACE_NAME.
MIRROR_SPACE_NAME = "octobot-mirror"


def is_known_mirror_collection(collection_id: str) -> bool:
    return any(c.id == collection_id for c in MIRROR_COLLECTIONS)


def mirror_visibility_for(collection_id: str) -> MirrorVisibility:
    """Unknown ids resolve to ``"private"``, the safe end of the enum."""
    for collection in MIRROR_COLLECTIONS:
        if collection.id == collection_id:
            return collection.visibility
    return "private"


def is_isolated_mirror_collection(collection_id: str) -> bool:
    """Sealed under its own per-node keyring, so a per-node grant reaches it."""
    return mirror_visibility_for(collection_id) == "shared"


def mirror_tier_for(collection_id: str) -> MirrorStorageTier:
    """The ``SpaceMirrorCollection.tier`` handed to the mirror channel."""
    visibility = mirror_visibility_for(collection_id)
    if visibility == "public":
        return "public"
    if visibility == "shared":
        return "isolated"
    return "private"


# Must stay byte-identical to the TS side's `mirrorDocPath`, or the writer and
# the website-side reader disagree on where a collection lives. Only `objinv`
# (`objects/n/.../content`) accepts a `cap:read` fallback, so it is the one tier
# a per-node grant holder can fetch without space membership.
def mirrordoc_path(collection_id: str, space_id: str, node_id: str) -> str:
    visibility = mirror_visibility_for(collection_id)
    if visibility == "public":
        return f"spaces/{space_id}/objects/pub/{node_id}"
    if visibility == "shared":
        return f"spaces/{space_id}/objects/n/{node_id}/content"
    return f"spaces/{space_id}/objects/docs/{node_id}"
