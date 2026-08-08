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

"""Event-triggered node-side cloud mirror — DRAFT. See docs/content/client-sdk/website-pairing.md."""

from __future__ import annotations

from typing import Callable, NamedTuple, Optional

import octobot_commons.logging as logging
import octobot_commons.singleton as singleton
from starfish_replica.channel import ChannelSchedule, ScheduledChannel
from starfish_replica.scheduler import ChannelScheduler
from starfish_replica.space import SpaceMirrorCollection, create_space_mirror_channel

from octobot_sync.mirror.collections import (
    MIRROR_COLLECTIONS,
    MIRROR_SPACE_NAME,
    mirror_tier_for,
    mirrordoc_path,
)
from octobot_sync.mirror.node_collections import read_node_collection
from octobot_sync.mirror.writer import build_mirror_session, derived_identity_for_mirror


class MirrorContext(NamedTuple):
    private_key: str
    sync_url: str
    enabled_collection_ids: list[str]


#: Resolves a wallet's mirror context, or None when it cannot mirror. Injected
#: by the node so this package stays free of the tentacles layer.
MirrorContextProvider = Callable[[str], Optional[MirrorContext]]


class MirrorService(singleton.Singleton):
    """One ChannelScheduler per wallet, one channel per collection — which is
    what makes `sync_now(collection_id)` safe: `plan_space_mirror` filters
    existing nodes by the channel's own registry, so a single-collection
    channel structurally cannot clear its siblings.

    Draft gaps: no coalescing (concurrent cycles can create duplicate nodes),
    no teardown, and `reconcile` does not clear a just-disabled collection.
    """

    def __init__(self):
        self._context_provider: Optional[MirrorContextProvider] = None
        self._schedulers: dict[str, ChannelScheduler] = {}

    def set_context_provider(self, provider: Optional[MirrorContextProvider]) -> None:
        self._context_provider = provider
        self._schedulers.clear()

    def _context(self, user_id: str) -> Optional[MirrorContext]:
        return self._context_provider(user_id) if self._context_provider else None

    def _enabled_ids(self, user_id: str) -> list[str]:
        context = self._context(user_id)
        return list(context.enabled_collection_ids) if context else []

    def _build_channel(self, session, user_id: str, collection_id: str) -> ScheduledChannel:
        return ScheduledChannel(
            channel=create_space_mirror_channel(
                name=collection_id,
                session=session,
                collections=[
                    SpaceMirrorCollection(
                        id=collection_id,
                        space_name=MIRROR_SPACE_NAME,
                        tier=mirror_tier_for(collection_id),
                    )
                ],
                enabled_ids=lambda: (
                    [collection_id] if collection_id in self._enabled_ids(user_id) else []
                ),
                read_source=lambda cid, _ctx: read_node_collection(cid, user_id),
                doc_path=mirrordoc_path,
                change_detection="source-hash",
            ),
            schedule=ChannelSchedule(triggers=[]),
        )

    async def _scheduler(self, user_id: str) -> Optional[ChannelScheduler]:
        if user_id in self._schedulers:
            return self._schedulers[user_id]
        context = self._context(user_id)
        if context is None:
            return None
        session = await build_mirror_session(
            derived_identity_for_mirror(context.private_key), context.sync_url
        )
        scheduler = ChannelScheduler(
            [self._build_channel(session, user_id, c.id) for c in MIRROR_COLLECTIONS]
        )
        self._schedulers[user_id] = scheduler
        return scheduler

    async def sync_now(self, collection_id: str, user_id: str) -> None:
        """Mirror ONE collection. Never raises: a mirror failure must not fail
        the local write that triggered it."""
        try:
            scheduler = await self._scheduler(user_id)
            if scheduler is not None:
                await scheduler.sync_now(collection_id)
        except Exception as err:  # pylint: disable=broad-except
            logging.get_logger(self.__class__.__name__).exception(
                err, True, f"Cloud mirror failed for {collection_id}: {err}"
            )

    def mirroring_user_ids(self) -> list[str]:
        """Wallets that have mirrored at least once this process."""
        return list(self._schedulers)

    async def reconcile(self, user_id: str) -> None:
        """Re-sync every enabled collection after a settings change."""
        for collection_id in self._enabled_ids(user_id):
            await self.sync_now(collection_id, user_id)
