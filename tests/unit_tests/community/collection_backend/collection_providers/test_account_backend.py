#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
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

import octobot.community.collection_backend.base_local_collection_storage as base_storage_module
import octobot.community.collection_providers.user_account_provider as account_provider_module
import octobot_node.constants as node_constants
import octobot_protocol.models as protocol_models
import octobot_sync.enums as sync_enums


class TestAccountProviderCollection:
    def test_collection_is_user_accounts(self):
        assert account_provider_module.AccountProvider.COLLECTION == sync_enums.Collections.USER_ACCOUNTS.value

    def test_storage_collection_matches(self, tmp_path):
        provider = account_provider_module.AccountProvider(base_folder=str(tmp_path))
        assert provider._storage.collection == sync_enums.Collections.USER_ACCOUNTS.value

    def test_storage_is_base_local_collection_storage(self, tmp_path):
        provider = account_provider_module.AccountProvider(base_folder=str(tmp_path))
        assert isinstance(provider._storage, base_storage_module.BaseLocalCollectionStorage)


class TestAccountProviderStateFormat:
    def test_state_version_matches_exchange_accounts_constant(self):
        assert account_provider_module.AccountProvider.STATE_VERSION == node_constants.EXCHANGE_ACCOUNTS_STATE_VERSION

    def test_state_class_is_accounts_state(self):
        assert account_provider_module.AccountProvider.STATE_CLASS is protocol_models.AccountsState

    def test_items_key_is_accounts(self):
        assert account_provider_module.AccountProvider.ITEMS_KEY == "accounts"


class TestAccountProviderGetItemId:
    def test_returns_account_id(self, tmp_path):
        provider = account_provider_module.AccountProvider(base_folder=str(tmp_path))
        account = protocol_models.Account(
            id="acc-42",
            name="Test",
            is_simulated=False,
        )
        assert provider._get_item_id(account) == "acc-42"
