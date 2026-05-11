#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot Node is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import datetime

import cachetools
import octobot_commons.constants as commons_constants
import octobot_commons.singleton.singleton_class as singleton_class
import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors

_DEFAULT_MAX_SIZE = 1_000
_DEFAULT_TTL_SECONDS = commons_constants.DAYS_TO_SECONDS


def _detach_user_action(user_action: protocol_models.UserAction) -> protocol_models.UserAction:
    # Step: return an independent copy so callers cannot mutate cached instances.
    cloned = protocol_models.UserAction.from_json(user_action.to_json())
    if cloned is None:
        raise node_errors.UserActionError("Failed to clone UserAction from JSON.")
    return cloned


class UserActionsProvider(singleton_class.Singleton):
    """
    Singleton in-memory CRUD for protocol UserAction models, partitioned by ``wallet_address``.

    Each wallet has its own ``TTLCache`` keyed by ``UserAction.id`` (ids are unique per wallet).

    Use ``UserActionsProvider.instance(maxsize=..., ttl_seconds=...)`` for the shared
    process instance (constructor args apply only on first ``instance()`` call).

    Storage uses ``cachetools.TTLCache`` per wallet: entries expire after ``ttl_seconds`` from
    last read or write on that key (successful ``get_user_action`` refreshes TTL).

    Intended for single-process use (e.g. one async app); no cross-thread locking.
    """

    def __init__(
        self,
        *,
        maxsize: int = _DEFAULT_MAX_SIZE,
        ttl_seconds: float = _DEFAULT_TTL_SECONDS,
    ) -> None:
        self._maxsize = maxsize
        self._ttl_seconds = ttl_seconds
        self._caches: dict[str, cachetools.TTLCache[str, protocol_models.UserAction]] = {}

    def _cache_for(self, wallet_address: str) -> cachetools.TTLCache[str, protocol_models.UserAction]:
        cache_for_wallet = self._caches.get(wallet_address)
        if cache_for_wallet is None:
            cache_for_wallet = cachetools.TTLCache(maxsize=self._maxsize, ttl=self._ttl_seconds)
            self._caches[wallet_address] = cache_for_wallet
        return cache_for_wallet

    def create_user_action(
        self,
        wallet_address: str,
        user_action: protocol_models.UserAction,
    ) -> protocol_models.UserAction:
        # Step: reject duplicate ids within this wallet, stamp timestamps, store detached copy.
        cache_for_wallet = self._cache_for(wallet_address)
        if user_action.id in cache_for_wallet:
            raise node_errors.DuplicateUserActionError(
                f"User action {user_action.id!r} already exists for wallet {wallet_address!r}."
            )
        now = _utc_now()
        created_at = user_action.created_at if user_action.created_at is not None else now
        updated_at = user_action.updated_at if user_action.updated_at is not None else now
        stored = protocol_models.UserAction(
            id=user_action.id,
            status=user_action.status,
            created_at=created_at,
            updated_at=updated_at,
            configuration=user_action.configuration,
            result=user_action.result,
        )
        cache_for_wallet[stored.id] = stored
        return _detach_user_action(stored)

    def get_user_action(self, wallet_address: str, user_action_id: str) -> protocol_models.UserAction:
        # Step: load from this wallet's cache or map miss to a typed error.
        cache_for_wallet = self._cache_for(wallet_address)
        try:
            stored = cache_for_wallet[user_action_id]
        except KeyError as exc:
            raise node_errors.UserActionNotFoundError(
                f"User action {user_action_id!r} not found for wallet {wallet_address!r}."
            ) from exc
        return _detach_user_action(stored)

    def list_user_actions(self, wallet_address: str) -> list[protocol_models.UserAction]:
        # Step: snapshot values for one wallet, stable sort for tests and UI.
        def sort_key(entry: protocol_models.UserAction) -> tuple[datetime.datetime, str]:
            created = entry.created_at
            if created is None:
                return (datetime.datetime.min.replace(tzinfo=datetime.UTC), entry.id)
            if created.tzinfo is None:
                created = created.replace(tzinfo=datetime.UTC)
            return (created, entry.id)

        cache_for_wallet = self._caches.get(wallet_address)
        if cache_for_wallet is None:
            return []
        ordered = sorted(cache_for_wallet.values(), key=sort_key)
        return [_detach_user_action(entry) for entry in ordered]

    def update_user_action(
        self,
        wallet_address: str,
        user_action: protocol_models.UserAction,
    ) -> protocol_models.UserAction:
        # Step: require existing row in this wallet; replace fields; keep prior created_at when incoming omits it.
        cache_for_wallet = self._cache_for(wallet_address)
        try:
            existing = cache_for_wallet[user_action.id]
        except KeyError as exc:
            raise node_errors.UserActionNotFoundError(
                f"User action {user_action.id!r} not found for wallet {wallet_address!r}."
            ) from exc
        created_at = (
            user_action.created_at
            if user_action.created_at is not None
            else existing.created_at
        )
        stored = protocol_models.UserAction(
            id=user_action.id,
            status=user_action.status,
            created_at=created_at,
            updated_at=_utc_now(),
            configuration=user_action.configuration,
            result=user_action.result,
        )
        cache_for_wallet[stored.id] = stored
        return _detach_user_action(stored)

    def delete_user_action(self, wallet_address: str, user_action_id: str) -> None:
        # Step: remove key in this wallet's cache or raise if absent.
        cache_for_wallet = self._cache_for(wallet_address)
        try:
            del cache_for_wallet[user_action_id]
        except KeyError as exc:
            raise node_errors.UserActionNotFoundError(
                f"User action {user_action_id!r} not found for wallet {wallet_address!r}."
            ) from exc


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)
