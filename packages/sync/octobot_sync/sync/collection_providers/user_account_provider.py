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

import octobot_commons.singleton.singleton_class as singleton_class
import octobot_sync.constants as sync_constants
import octobot_protocol.models as protocol_models
import octobot_sync.enums as sync_enums

import octobot_sync.sync.collection_backend.base_local_collection_provider as base_provider
import octobot_sync.sync.collection_backend.errors as collection_errors


class AccountProvider(
    base_provider.BaseLocalCollectionProvider[protocol_models.Account, protocol_models.AccountsState],
    singleton_class.Singleton
):
    """
    Singleton provider exposing CRUD on accounts and exchange configs.

    Both collections share one encrypted AccountsState file and one in-memory
    cache entry per wallet address.
    """
    COLLECTION = sync_enums.Collections.USER_ACCOUNTS.value
    STATE_VERSION = sync_constants.EXCHANGE_ACCOUNTS_STATE_VERSION
    STATE_CLASS = protocol_models.AccountsState
    ITEMS_KEY = "accounts"
    EXCHANGE_CONFIGS_KEY = "exchange_configs"

    def _get_item_id(self, item: protocol_models.Account) -> str:
        return item.id

    def _get_item_id_for_key(self, items_key: str, item: typing.Any) -> str:
        if items_key == self.ITEMS_KEY:
            return self._get_item_id(item)
        if items_key == self.EXCHANGE_CONFIGS_KEY:
            return item.id
        raise collection_errors.UnsupportedItemsKeyError(
            f"Unsupported items key {items_key!r} for {self.__class__.__name__}"
        )

    def list_accounts(self, address: str) -> list[protocol_models.Account]:
        return self.list_items(address)

    def get_account(self, address: str, account_id: str) -> protocol_models.Account:
        return self.get_item(address, account_id)

    def create_account(self, address: str, account: protocol_models.Account) -> protocol_models.Account:
        return self.create_item(address, account)

    def update_account(self, address: str, account: protocol_models.Account) -> protocol_models.Account:
        return self.update_item(address, account)

    def delete_account(self, address: str, account_id: str) -> None:
        self.delete_item(address, account_id)

    def list_exchange_configs(self, address: str) -> list[protocol_models.ExchangeConfig]:
        return self._list_items_for_key(address, self.EXCHANGE_CONFIGS_KEY)

    def get_exchange_config(
        self,
        address: str,
        config_id: str,
    ) -> protocol_models.ExchangeConfig:
        return self._get_item_for_key(address, self.EXCHANGE_CONFIGS_KEY, config_id)

    def create_exchange_config(
        self,
        address: str,
        exchange_config: protocol_models.ExchangeConfig,
    ) -> protocol_models.ExchangeConfig:
        return self._create_item_for_key(address, self.EXCHANGE_CONFIGS_KEY, exchange_config)

    def update_exchange_config(
        self,
        address: str,
        exchange_config: protocol_models.ExchangeConfig,
    ) -> protocol_models.ExchangeConfig:
        return self._update_item_for_key(address, self.EXCHANGE_CONFIGS_KEY, exchange_config)

    def delete_exchange_config(self, address: str, config_id: str) -> None:
        self._delete_item_for_key(address, self.EXCHANGE_CONFIGS_KEY, config_id)
