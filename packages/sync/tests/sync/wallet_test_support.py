#  Drakkar-Software OctoBot-Sync
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.

import mock

import octobot.community.authentication as community_authentication

DEFAULT_TEST_PRIVATE_KEY = "private-key"


def patch_community_wallet(private_key: str = DEFAULT_TEST_PRIVATE_KEY):
    wallet = mock.Mock()
    wallet.private_key = private_key
    auth = mock.Mock()
    auth.get_wallet_by_user_id.return_value = wallet
    return mock.patch.object(
        community_authentication.CommunityAuthentication,
        "instance",
        return_value=auth,
    )
