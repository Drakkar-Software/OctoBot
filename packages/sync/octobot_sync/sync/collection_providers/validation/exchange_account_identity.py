#  Drakkar-Software OctoBot-Sync
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.


import typing

import octobot_protocol.models as protocol_models

import octobot_sync.sync.collection_backend.errors as collection_errors


class ExchangeAccountIdentity(typing.NamedTuple):
    remote_account_id: str
    exchange: str
    url: str | None
    sandboxed: bool


def _normalize_exchange_url(url: str | None) -> str | None:
    if url is None or url == "":
        return None
    return url


def _resolved_remote_account_id(
    account: protocol_models.Account,
    exchange_account: protocol_models.ExchangeAccount,
) -> str:
    remote_account_id = exchange_account.remote_account_id
    if remote_account_id:
        return remote_account_id
    return account.id


def _exchange_configs_by_id(
    exchange_configs: list[protocol_models.ExchangeConfig],
) -> dict[str, protocol_models.ExchangeConfig]:
    return {
        exchange_config.id: exchange_config
        for exchange_config in exchange_configs
    }


def _resolve_exchange_account_identity(
    account: protocol_models.Account,
    exchange_configs_by_id: dict[str, protocol_models.ExchangeConfig],
) -> ExchangeAccountIdentity | None:
    if account.is_simulated:
        return None
    account_specifics = account.specifics
    if account_specifics is None or account_specifics.actual_instance is None:
        return None
    if not isinstance(account_specifics.actual_instance, protocol_models.ExchangeAccount):
        return None

    exchange_account = account_specifics.actual_instance
    exchange_config_ids = exchange_account.exchange_config_ids
    if not exchange_config_ids:
        return None

    exchange_config = exchange_configs_by_id.get(exchange_config_ids[0])
    if exchange_config is None:
        return None

    return ExchangeAccountIdentity(
        remote_account_id=_resolved_remote_account_id(account, exchange_account),
        exchange=exchange_config.exchange,
        url=_normalize_exchange_url(exchange_config.url),
        sandboxed=exchange_config.sandboxed,
    )


def _find_conflicting_account(
    accounts: list[protocol_models.Account],
    exchange_configs_by_id: dict[str, protocol_models.ExchangeConfig],
    candidate_identity: ExchangeAccountIdentity,
    *,
    exclude_account_id: str | None = None,
) -> protocol_models.Account | None:
    for existing_account in accounts:
        if exclude_account_id is not None and existing_account.id == exclude_account_id:
            continue
        existing_identity = _resolve_exchange_account_identity(
            existing_account,
            exchange_configs_by_id,
        )
        if existing_identity == candidate_identity:
            return existing_account
    return None


def assert_unique_exchange_account_identity(
    user_id: str,
    account: protocol_models.Account,
    accounts: list[protocol_models.Account],
    exchange_configs: list[protocol_models.ExchangeConfig],
    *,
    exclude_account_id: str | None = None,
) -> None:
    exchange_configs_by_id = _exchange_configs_by_id(exchange_configs)
    identity = _resolve_exchange_account_identity(account, exchange_configs_by_id)
    if identity is None:
        return
    conflict = _find_conflicting_account(
        accounts,
        exchange_configs_by_id,
        identity,
        exclude_account_id=exclude_account_id,
    )
    if conflict is not None:
        raise collection_errors.DuplicateItemError(
            f"Exchange account identity {identity!r} already exists for user_id {user_id!r} "
            f"as account {conflict.id!r}"
        )
