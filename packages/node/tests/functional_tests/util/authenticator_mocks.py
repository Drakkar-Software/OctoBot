#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
"""Shared authentication helpers for DBOS functional tests."""

import octobot.community.authentication as community_authentication_module
import octobot.community.local_authenticator as local_authenticator_module


def build_community_authentication(
    private_key: str,
    passphrase: str,
) -> community_authentication_module.CommunityAuthentication:
    """Return a non-singleton CommunityAuthentication with an imported wallet."""
    authentication_configuration = local_authenticator_module.get_stateless_configuration()
    instance = community_authentication_module.CommunityAuthentication(
        config=authentication_configuration,
        use_as_singleton=False,
    )
    instance.import_wallet(private_key, passphrase, None, True)
    return instance
