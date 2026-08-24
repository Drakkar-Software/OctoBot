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
import octobot.community.wallet_backend.errors as wallet_backend_errors
import octobot_sync.sync.collection_providers.user_account_provider as account_provider_module


class TestListCollectableWalletIds:
    def test_returns_only_wallets_registered_locally(self):
        provider = mock.Mock(spec=account_provider_module.AccountProvider)
        provider.list_registered_wallet_ids.return_value = [
            "wallet-known",
            "wallet-missing",
        ]
        community_auth = mock.Mock()
        community_auth.get_wallet_by_user_id.side_effect = lambda wallet_id: (
            mock.Mock()
            if wallet_id == "wallet-known"
            else (_ for _ in ()).throw(wallet_backend_errors.WalletNotFoundError("missing"))
        )
        with mock.patch.object(
            community_authentication.CommunityAuthentication,
            "instance",
            return_value=community_auth,
        ):
            result = account_provider_module.AccountProvider.list_collectable_wallet_ids(provider)
        assert result == ["wallet-known"]

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
