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

import mock
import postgrest
import pytest

import octobot_commons.configuration as commons_configuration
import octobot_commons.authentication as authentication
import octobot.community as community
import octobot.community.supabase_backend as supabase_backend
import octobot.community.errors as community_errors
import octobot.community.supabase_backend.enums as supabase_backend_enums
from additional_tests.supabase_backend_tests import authenticated_client_1, authenticated_client_2, \
    admin_client, anon_client, get_backend_api_creds, skip_if_no_service_key, get_backend_client_creds, \
    get_backend_client_auth_key, get_backend_client_expired_jwt_token


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_get_user(authenticated_client_1):
    user = await authenticated_client_1.get_user()
    assert all(
        attribute.value in user
        for attribute in supabase_backend_enums.UserKeys
    )


async def test_get_auth_key(authenticated_client_1, anon_client):
    user_auth_key = authenticated_client_1._get_auth_key()
    assert user_auth_key != authenticated_client_1.supabase_key

    anon_auth_key = anon_client._get_auth_key()
    assert anon_auth_key == anon_client.supabase_key


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
    subscribed_products_urls = await authenticated_client_1.fetch_subscribed_products_urls()
    assert all(
        (isinstance(val, str) or val is None)
        for val in subscribed_products_urls
    )


async def test_sign_in_with_otp_token(authenticated_client_1, skip_if_no_service_key, admin_client):
    # generate OTP token
    user = await authenticated_client_1.get_user()
    res = await admin_client.auth.admin.generate_link({"email": user["email"], "type": "magiclink"})
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
            community.ASyncConfigurationStorage(config)
        )
        saved_session = "saved_session"
        await supabase_client.auth._storage.set_item(supabase_client.auth._storage_key, saved_session)
        # wrong token
        with pytest.raises(authentication.AuthenticationError):
            await supabase_client.sign_in_with_otp_token("1234")
        # save session has not been removed
        assert await supabase_client.auth._storage.get_item(supabase_client.auth._storage_key) == saved_session

        await supabase_client.sign_in_with_otp_token(token)
        # save session has been updated
        updated_session = await supabase_client.auth._storage.get_item(supabase_client.auth._storage_key)
        assert updated_session != saved_session

        # ensure new supabase_client is bound to the same user as the previous client
        user = await supabase_client.get_user()
        assert user == await authenticated_client_1.get_user()

        # already consumed token
        with pytest.raises(authentication.AuthenticationError):
            await supabase_client.sign_in_with_otp_token(token)
        assert await supabase_client.auth._storage.get_item(supabase_client.auth._storage_key) == updated_session
    finally:
        if supabase_client:
            await supabase_client.aclose()


async def test_sign_in_with_auth_token():
    # create new client
    backend_url, backend_key = get_backend_api_creds()
    email, _ = get_backend_client_creds(1)

    config = commons_configuration.Configuration("", "")
    config.config = {}
    supabase_client = None
    try:
        supabase_client = community.CommunitySupabaseClient(
            backend_url,
            backend_key,
            community.ASyncConfigurationStorage(config)
        )
        saved_session = "saved_session"
        await supabase_client.auth._storage.set_item(supabase_client.auth._storage_key, saved_session)
        # wrong configs
        with pytest.raises(authentication.AuthenticationError):
            await supabase_client.get_otp_with_auth_key("", "")
        with pytest.raises(authentication.AuthenticationError):
            await supabase_client.get_otp_with_auth_key(None, "")
        with pytest.raises(authentication.AuthenticationError):
            await supabase_client.get_otp_with_auth_key(email, None)
        with pytest.raises(authentication.AuthenticationError):
            await supabase_client.get_otp_with_auth_key(email, "1234")
        assert await supabase_client.auth._storage.get_item(supabase_client.auth._storage_key) == saved_session
        token = await supabase_client.get_otp_with_auth_key(email, get_backend_client_auth_key(1))
        # ensure token is valid

        await supabase_client.sign_in_with_otp_token(token)
        # save session has been updated
        updated_session = await supabase_client.auth._storage.get_item(supabase_client.auth._storage_key)
        assert updated_session != saved_session

        # ensure new supabase_client is bound to the same user as the previous client
        user = await supabase_client.get_user()
        assert user[supabase_backend_enums.UserKeys.EMAIL.value] == email

        # already consumed token
        with pytest.raises(authentication.AuthenticationError):
            await supabase_client.sign_in_with_otp_token(token)
        assert await supabase_client.auth._storage.get_item(supabase_client.auth._storage_key) == updated_session
    finally:
        if supabase_client:
            await supabase_client.aclose()


async def test_expired_jwt_token(authenticated_client_1):
    initial_email = (await authenticated_client_1.get_user())[supabase_backend_enums.UserKeys.EMAIL.value]

    # refreshing session is working
    await authenticated_client_1.refresh_session()
    # does not raise
    bots = await authenticated_client_1.fetch_bots()
    assert (await authenticated_client_1.get_user())[supabase_backend_enums.UserKeys.EMAIL.value] == initial_email

    # use expired jwt token
    expired_jwt_token = get_backend_client_expired_jwt_token(1)

    # simulate auth using this token
    session = mock.Mock(access_token=expired_jwt_token)
    authenticated_client_1._listen_to_auth_events(
       "SIGNED_IN", session
    )

    # now raising "APIError: JWT expired" which is converted into community_errors.AuthenticationError
    with pytest.raises(authentication.AuthenticationError):
        await authenticated_client_1.fetch_bots()
