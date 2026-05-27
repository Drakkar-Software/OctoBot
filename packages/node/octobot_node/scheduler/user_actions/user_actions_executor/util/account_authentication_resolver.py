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

import octobot_protocol.models as protocol_models
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers

import octobot_node.errors as node_errors


def get_exchange_authentication(
    wallet_address: str,
    account: protocol_models.Account,
) -> protocol_models.AccountAuthentication | None:
    if account.is_simulated:
        return None
    account_specifics = account.specifics
    if account_specifics is None or account_specifics.actual_instance is None:
        raise node_errors.AccountAuthenticationNotFoundError(
            f"Account {account.id!r} has no specifics for authentication lookup."
        )
    if not isinstance(account_specifics.actual_instance, protocol_models.ExchangeAccount):
        raise node_errors.AccountAuthenticationNotFoundError(
            f"Account {account.id!r} is not an exchange account; cannot resolve authentication."
        )
    authentication_id = account.authentication_id
    if not authentication_id:
        raise node_errors.AccountAuthenticationNotFoundError(
            f"Account {account.id!r} has no authentication_id for authentication lookup."
        )
    try:
        authentication = collection_providers.AccountAuthenticationProvider.instance().get_item(
            wallet_address,
            authentication_id,
        )
    except collection_errors.ItemNotFoundError as err:
        raise node_errors.AccountAuthenticationNotFoundError(
            f"Authentication {authentication_id!r} for account {account.id!r} not found for address {wallet_address!r}: {err}"
        ) from err
    if not authentication.api_key or not authentication.api_secret:
        raise node_errors.AccountAuthenticationNotFoundError(
            f"Authentication for account {account.id!r} is missing api_key or api_secret."
        )
    return authentication
