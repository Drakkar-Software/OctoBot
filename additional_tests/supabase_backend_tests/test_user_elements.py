#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
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
import time
import pytest

import octobot_commons.configuration as commons_configuration
import octobot_commons.authentication as authentication
import octobot.community as community
import octobot.community.errors as errors
import octobot.community.supabase_backend.enums as supabase_backend_enums
from additional_tests.supabase_backend_tests import authenticated_client_1, authenticated_client_2, \
    admin_client, get_backend_api_creds, skip_if_no_service_key


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_get_user(authenticated_client_1):
    user = await authenticated_client_1.get_user()
    assert all(
        attribute.value in user
        for attribute in supabase_backend_enums.UserKeys
    )


async def test_update_metadata(authenticated_client_1):
    user = await authenticated_client_1.get_user()
    previous_metadata = user[supabase_backend_enums.UserKeys.USER_METADATA.value]
    seed = time.time()
    metadata_update = {
        "hola": f"chica{seed}",
        "adios": f"chico{seed}",
        "plop": {
            "is": f"super{seed}",
        },
        "?": seed,
    }
    updated_user = await authenticated_client_1.update_metadata(metadata_update)
    updated_metadata = updated_user[supabase_backend_enums.UserKeys.USER_METADATA.value]
    assert updated_metadata != previous_metadata
    assert all(
        updated_metadata[key] == metadata_update[key]
        for key in metadata_update
    )


async def test_fetch_subscribed_products_urls(authenticated_client_1):
    assert await authenticated_client_1.fetch_subscribed_products_urls() == []


async def test_sign_in_with_otp_token(authenticated_client_1, skip_if_no_service_key, admin_client):
    # generate OTP token
    user = await authenticated_client_1.get_user()
    res = admin_client.auth.admin.generate_link({"email": user["email"], "type": "magiclink"})
    token = res.properties.hashed_token

    # create new client
    backend_url, backend_key = get_backend_api_creds()
    config = commons_configuration.Configuration("", "")
    config.config = {}
    supabase_client = None
    try:
        supabase_client = community.CommunitySupabaseClient(
            backend_url,
            backend_key,
            community.SyncConfigurationStorage(config)
        )

        # wrong token
        with pytest.raises(authentication.AuthenticationError):
            await supabase_client.sign_in_with_otp_token("1234")

        await supabase_client.sign_in_with_otp_token(token)

        # ensure new supabase_client is bound to the same user as the previous client
        user = await supabase_client.get_user()
        assert user == await authenticated_client_1.get_user()

        # already consumed token
        with pytest.raises(authentication.AuthenticationError):
            await supabase_client.sign_in_with_otp_token(token)
    finally:
        if supabase_client:
            await supabase_client.close()
