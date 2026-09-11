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

import mock

import octobot.community.authentication as community_authentication
import octobot_sync.sync.collection_providers.user_account_provider as account_provider_module

_JOURNAL_PATCH = "octobot.community.node_journal.record_wallet_operation_failed"


class TestListCollectableWalletIds:
    def test_returns_only_wallets_registered_locally(self):
        provider = mock.Mock(spec=account_provider_module.AccountProvider)
        provider.list_registered_wallet_ids.return_value = [
            "wallet-known",
            "wallet-missing",
        ]
        community_auth = mock.Mock()
        community_auth.has_wallet_for_user_id.side_effect = lambda wallet_id: wallet_id == "wallet-known"
        with mock.patch.object(
            community_authentication.CommunityAuthentication,
            "instance",
            return_value=community_auth,
        ):
            result = account_provider_module.AccountProvider.list_collectable_wallet_ids(provider)
        assert result == ["wallet-known"]

    def test_skips_orphan_wallet_ids_without_journaling(self):
        provider = mock.Mock(spec=account_provider_module.AccountProvider)
        provider.list_registered_wallet_ids.return_value = [
            "wallet-known",
            "wallet-missing",
        ]
        community_auth = mock.Mock()
        community_auth.has_wallet_for_user_id.side_effect = lambda wallet_id: wallet_id == "wallet-known"
        with mock.patch.object(
            community_authentication.CommunityAuthentication,
            "instance",
            return_value=community_auth,
        ), mock.patch(_JOURNAL_PATCH) as record_mock:
            result = account_provider_module.AccountProvider.list_collectable_wallet_ids(provider)
        assert result == ["wallet-known"]
        record_mock.assert_not_called()

    def test_returns_empty_when_no_registered_wallets(self):
        provider = mock.Mock(spec=account_provider_module.AccountProvider)
        provider.list_registered_wallet_ids.return_value = []
        with mock.patch.object(
            community_authentication.CommunityAuthentication,
            "instance",
            return_value=mock.Mock(),
        ):
            result = account_provider_module.AccountProvider.list_collectable_wallet_ids(provider)
        assert result == []
