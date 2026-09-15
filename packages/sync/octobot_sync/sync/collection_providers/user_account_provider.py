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

import octobot.community.authentication as community_authentication
import octobot.community.wallet_backend.errors as wallet_backend_errors
import octobot_commons.logging as commons_logging
import octobot_commons.singleton.singleton_class as singleton_class
import octobot_sync.constants as sync_constants
import octobot_protocol.models as protocol_models
import octobot_sync.enums as sync_enums

import octobot_sync.sync.collection_backend.base_local_collection_provider as base_provider
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers.validation.exchange_account_identity as exchange_account_identity


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

    def _empty_state(self) -> protocol_models.AccountsState:
        return protocol_models.AccountsState(
            version=self.STATE_VERSION,
            accounts=[],
            exchange_configs=[],
        )

    def _assert_unique_exchange_account_identity(
        self,
        user_id: str,
        account: protocol_models.Account,
        *,
        exclude_account_id: str | None = None,
    ) -> None:
        state = self._load_state(user_id)
        exchange_account_identity.assert_unique_exchange_account_identity(
            user_id,
            account,
            self._items_from_state(state, self.ITEMS_KEY),
            self._items_from_state(state, self.EXCHANGE_CONFIGS_KEY),
            exclude_account_id=exclude_account_id,
        )

    def create_item(self, user_id: str, item: protocol_models.Account) -> protocol_models.Account:
        self._assert_unique_exchange_account_identity(user_id, item)
        return super().create_item(user_id, item)

    def update_item(self, user_id: str, item: protocol_models.Account) -> protocol_models.Account:
        self._assert_unique_exchange_account_identity(user_id, item, exclude_account_id=item.id)
        return super().update_item(user_id, item)

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

    def list_registered_wallet_ids(self) -> list[str]:
        return self._storage.list_wallet_storage_keys()

    def list_collectable_wallet_ids(self) -> list[str]:
        logger = commons_logging.get_logger(self.__class__.__name__)
        community_auth = community_authentication.CommunityAuthentication.instance()
        collectable_wallet_ids = []
        for wallet_id in self.list_registered_wallet_ids():
            try:
                community_auth.get_wallet_by_user_id(wallet_id)
            except wallet_backend_errors.WalletNotFoundError:
                logger.debug(
                    "Skipping wallet %s: not registered locally",
                    wallet_id,
                )
                continue
            collectable_wallet_ids.append(wallet_id)
        return collectable_wallet_ids
