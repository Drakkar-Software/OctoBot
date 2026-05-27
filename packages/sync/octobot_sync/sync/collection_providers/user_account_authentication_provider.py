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


import octobot_commons.singleton.singleton_class as singleton_class
import octobot_sync.constants as sync_constants
import octobot_protocol.models as protocol_models
import octobot_sync.enums as sync_enums

import octobot_sync.sync.collection_backend.base_local_collection_provider as base_provider
import octobot_sync.sync.collection_backend.errors as collection_errors


class AccountAuthenticationProvider(
    base_provider.BaseLocalCollectionProvider[
        protocol_models.AccountAuthentication,
        protocol_models.AccountsAuthenticationState,
    ],
    singleton_class.Singleton,
):
    """
    Singleton provider exposing CRUD operations on AccountAuthentication models.

    Authentication credentials are grouped per wallet address and persisted as an encrypted
    AccountsAuthenticationState envelope. All CRUD logic lives in the base class.
    """
    COLLECTION = sync_enums.Collections.USER_ACCOUNTS_AUTH.value
    STATE_VERSION = sync_constants.USER_ACCOUNTS_AUTH_STATE_VERSION
    STATE_CLASS = protocol_models.AccountsAuthenticationState
    ITEMS_KEY = "account_authentication"

    def _get_item_id(self, item: protocol_models.AccountAuthentication) -> str:
        # Wallet-scoped auth file holds a single credentials entry (no account_id on model).
        return "wallet"

    def get_item(self, address: str, item_id: str) -> protocol_models.AccountAuthentication:
        items = self.list_items(address)
        if not items:
            raise collection_errors.ItemNotFoundError(
                f"Authentication not found for address {address}"
            )
        return items[0]
