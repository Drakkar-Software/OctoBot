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
the `read_source` callback the mirror channel needs (see `service.py`)."""

from __future__ import annotations

from typing import Any

from octobot_sync.sync.collection_backend.errors import CollectionNoDataError
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
    """Trading state is stored one file per account and carries no account id,
    so the id is re-attached here to match the wire shape the mobile writer
    produces (`AccountTradingWithAccountId`) — both writers feed the same
    mirror, so a reader must not see two shapes. Accounts that never traded
    have no file yet."""
    provider = AccountTradingProvider.instance()
    account_tradings: list[dict[str, Any]] = []
    for account in AccountProvider.instance().list_accounts(user_id):
        try:
            state = provider.load_state(user_id, account.id)
        except CollectionNoDataError:
            continue
        account_tradings.append(
            {
                "account_id": account.id,
                "account_trading": state.account_trading.model_dump(mode="json"),
            }
        )
    return {"account_tradings": account_tradings}


def _read_user_strategies(user_id: str) -> dict[str, Any]:
    provider = StrategyProvider.instance()
    return {
        "items": [item.model_dump(mode="json") for item in provider.list_items(user_id)],
    }


def _read_user_data(user_id: str) -> dict[str, Any]:
    """Automations and user actions have no local collection provider yet."""
    raise NotImplementedError("user-data has no wired local collection source yet")


_READERS = {
    "user-accounts": _read_user_accounts,
    "user-accounts-trading": _read_user_accounts_trading,
    "user-strategies": _read_user_strategies,
    "user-data": _read_user_data,
}


async def read_node_collection(collection_id: str, user_id: str) -> dict[str, Any]:
    """Async only to match the channel's `read_source` signature; the reads
    underneath are synchronous local-disk ones."""
    try:
        reader = _READERS[collection_id]
    except KeyError as exc:
        raise ValueError(f"No local collection reader for {collection_id!r}") from exc
    return reader(user_id)
