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

"""Maps a mirror-eligible collection id to the node's own local read for it —
the `read_source_collection` callback `writer.sync_cloud_mirror` needs.

**Only three of the four mirror-eligible collections are wired here.**
`user-data` (automations + user_actions, per the space-mirror design's
architecture table) has NO corresponding class in
`octobot_sync.sync.collection_providers` — grepped for `USER_DATA` across
`packages/`: it's registered as a server-side sync collection
(`octobot_sync/enums.py`, `sync/collections.py`, `server.py`) but its
node-local *source* data lives in a different subsystem (most likely
`octobot_node.scheduler.workflows.user_action_workflow`/automation execution
state, which this package has no visibility into) that wasn't located in
this session. `read_source_collection("user-data", ...)` raises
`NotImplementedError` until that's found and wired — DO NOT guess a fallback
here; an empty/wrong mirror for `user-data` would be worse than a loud
failure that's obviously incomplete.
"""

from __future__ import annotations

from typing import Any

from octobot_sync.sync.collection_providers.user_account_provider import AccountProvider
from octobot_sync.sync.collection_providers.user_account_trading_provider import (
    AccountTradingProvider,
)
from octobot_sync.sync.collection_providers.user_strategy_provider import StrategyProvider


def _read_user_accounts(user_id: str) -> dict[str, Any]:
    provider = AccountProvider.instance()
    return {
        "accounts": [item.model_dump(mode="json") for item in provider.list_accounts(user_id)],
        "exchange_configs": [
            item.model_dump(mode="json") for item in provider.list_exchange_configs(user_id)
        ],
    }


def _read_user_accounts_trading(user_id: str) -> dict[str, Any]:
    provider = AccountTradingProvider.instance()
    return {
        "items": [item.model_dump(mode="json") for item in provider.list_items(user_id)],
    }


def _read_user_strategies(user_id: str) -> dict[str, Any]:
    provider = StrategyProvider.instance()
    return {
        "items": [item.model_dump(mode="json") for item in provider.list_items(user_id)],
    }


def _read_user_data(user_id: str) -> dict[str, Any]:
    raise NotImplementedError(
        "user-data has no wired local collection source yet — see this module's "
        "docstring. Do not enable it in DEFAULT_MIRROR_COLLECTIONS/settings until fixed."
    )


_READERS = {
    "user-accounts": _read_user_accounts,
    "user-accounts-trading": _read_user_accounts_trading,
    "user-strategies": _read_user_strategies,
    "user-data": _read_user_data,
}


async def read_node_collection(collection_id: str, user_id: str) -> dict[str, Any]:
    """The concrete `read_source_collection` callback for the node writer —
    synchronous local-disk reads under the hood, wrapped `async` only to
    match `writer.sync_cloud_mirror`'s callback signature (it's written
    generically so a future truly-async source, or the mobile equivalent,
    fits the same shape)."""
    try:
        reader = _READERS[collection_id]
    except KeyError as exc:
        raise ValueError(f"No local collection reader for {collection_id!r}") from exc
    return reader(user_id)
