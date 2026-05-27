#  Drakkar-Software OctoBot-Sync
#  Copyright (c) Drakkar-Software, All rights reserved.
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

import datetime

import octobot_sync.sync.collection_backend.base_local_collection_storage as base_storage_module
import octobot_sync.sync.collection_providers.user_account_authentication_provider as auth_provider_module
import octobot_sync.constants as sync_constants
import octobot_protocol.models as protocol_models
import octobot_sync.enums as sync_enums


class TestAccountAuthenticationProviderCollection:
    def test_collection_is_user_accounts_auth(self):
        assert (
            auth_provider_module.AccountAuthenticationProvider.COLLECTION
            == sync_enums.Collections.USER_ACCOUNTS_AUTH.value
        )

    def test_storage_collection_matches(self, tmp_path):
        provider = auth_provider_module.AccountAuthenticationProvider(base_folder=str(tmp_path))
        assert provider._storage.collection == sync_enums.Collections.USER_ACCOUNTS_AUTH.value

    def test_storage_is_base_local_collection_storage(self, tmp_path):
        provider = auth_provider_module.AccountAuthenticationProvider(base_folder=str(tmp_path))
        assert isinstance(provider._storage, base_storage_module.BaseLocalCollectionStorage)


class TestAccountAuthenticationProviderStateFormat:
    def test_state_version_matches_constant(self):
        assert (
            auth_provider_module.AccountAuthenticationProvider.STATE_VERSION
            == sync_constants.USER_ACCOUNTS_AUTH_STATE_VERSION
        )

    def test_state_class_is_accounts_authentication_state(self):
        assert (
            auth_provider_module.AccountAuthenticationProvider.STATE_CLASS
            is protocol_models.AccountsAuthenticationState
        )

    def test_items_key_is_account_authentication(self):
        assert auth_provider_module.AccountAuthenticationProvider.ITEMS_KEY == "account_authentication"


class TestAccountAuthenticationProviderGetItemId:
    def test_returns_authentication_id(self, tmp_path):
        provider = auth_provider_module.AccountAuthenticationProvider(base_folder=str(tmp_path))
        authentication = protocol_models.AccountAuthentication(
            id="auth-1",
            api_key="key",
            api_secret="secret",
        )
        assert provider._get_item_id(authentication) == "auth-1"
