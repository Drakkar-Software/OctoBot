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

"""Pure planning step for one cloud-mirror sync cycle — Python port of
``octobot_client_ts/src/client/mirror/plan.ts``. No network I/O, no
starfish dependency at all, so it's testable directly (see
``tests/mirror/test_plan.py``) without any of the Python-environment
constraints the actual writer (``writer.py``) has.
"""

from __future__ import annotations

from typing import NamedTuple

from octobot_sync.mirror.collections import is_known_mirror_collection


class ExistingMirrorNode(NamedTuple):
    id: str
    type: str


class MirrorSyncPlan(NamedTuple):
    to_create: list[str]
    to_write: list[str]
    to_clear: list[ExistingMirrorNode]


def plan_mirror_sync(
    existing_nodes: list[ExistingMirrorNode],
    enabled_collection_ids: list[str],
) -> MirrorSyncPlan:
    """Given the space's current object tree and the set of collections the
    user has enabled, decide what the writer needs to do this cycle."""
    enabled = {cid for cid in enabled_collection_ids if is_known_mirror_collection(cid)}
    existing_by_type = {n.type: n for n in existing_nodes}

    to_create: list[str] = []
    to_write: list[str] = []
    for collection_id in enabled:
        to_write.append(collection_id)
        if collection_id not in existing_by_type:
            to_create.append(collection_id)

    to_clear = [n for n in existing_nodes if is_known_mirror_collection(n.type) and n.type not in enabled]

    return MirrorSyncPlan(to_create=to_create, to_write=to_write, to_clear=to_clear)
