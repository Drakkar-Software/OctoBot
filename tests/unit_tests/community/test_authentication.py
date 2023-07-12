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
import asyncio
import contextlib

import pytest
import pytest_asyncio
import mock
import requests
import aiohttp

import octobot.community as community
import octobot.constants as constants
import octobot_commons.authentication as authentication
import octobot_commons.configuration

AUTH_URL = "https://oh.fake/auth"
AUTH_RETURN = {
    "access_token": "1",
    "refresh_token": "2",
    "expires_in": 3600,
}
EMAIL_RETURN = {
    "email": "plop"
}
AUTH_HEADER_RETURN = {
    community.CommunityAuthentication.SESSION_HEADER: "helloooo",
}


class MockedResponse:
    def __init__(self, status_code=200, json=None, headers={}):
        self.status_code = status_code
        self.json_resp = json
        self.headers = headers

    def json(self):
        return self.json_resp


@pytest.fixture
def auth():
    community.IdentifiersProvider.use_production()
    authenticator = community.CommunityAuthentication(AUTH_URL, None)
    authenticator.supabase_client = mock.Mock(
        sign_in=mock.AsyncMock(),
        sign_in_with_otp_token=mock.AsyncMock(),
        sign_out=mock.Mock(),
        auth=mock.Mock(_storage_key="_storage_key"),
        close=mock.AsyncMock(),
    )
    return authenticator


@pytest_asyncio.fixture
async def logged_in_auth(auth):
    auth.user_account.has_user_data = mock.Mock(return_value=True)
    auth.user_account.get_email = mock.Mock(return_value="plop")
    return auth


def test_constructor():
    with mock.patch.object(community.CommunityAuthentication, "login", mock.Mock()) as login_mock:
        community.IdentifiersProvider.use_production()
        community.CommunityAuthentication(AUTH_URL, None)
        auth = community.CommunityAuthentication(AUTH_URL, None)
        login_mock.assert_not_called()
        assert not auth.user_account.supports.is_supporting()
        assert auth.initialized_event is None


@pytest.mark.asyncio
async def test_login(auth):
    resp_mock = mock.Mock()
    with mock.patch.object(community.CommunityAuthentication, "_reset_tokens", mock.Mock()) as reset_mock, \
            mock.patch.object(community.CommunityAuthentication, "_ensure_community_url", mock.Mock()) \
            as _ensure_community_url_mock, \
            mock.patch.object(community.CommunityAuthentication, "_ensure_email", mock.Mock()) \
            as _ensure_email_mock, \
            mock.patch.object(community.CommunityAuthentication, "_on_account_updated", mock.AsyncMock()) \
            as _on_account_updated_mock, \
            mock.patch.object(community.CommunityAuthentication, "is_logged_in", mock.Mock()) \
            as is_logged_in_mock, \
            mock.patch.object(community.CommunityAuthentication, "on_signed_in", mock.AsyncMock()) \
            as on_signed_in_mock:
        await auth.login("username", "password")
        reset_mock.assert_called_once()
        _ensure_community_url_mock.assert_called_once()
        _ensure_email_mock.assert_called_once()
        _on_account_updated_mock.assert_called_once()
        is_logged_in_mock.assert_called_once()
        on_signed_in_mock.assert_called_once()
        auth.supabase_client.sign_in.assert_awaited_once_with("username", "password")
        auth.supabase_client.sign_in_with_otp_token.assert_not_called()
        auth.supabase_client.sign_in.reset_mock()
        await auth.login(None, None, password_token="password_t")
        auth.supabase_client.sign_in.assert_not_called()
        auth.supabase_client.sign_in_with_otp_token.assert_awaited_once_with("password_t")

def test_logout(auth):
    with mock.patch.object(community.CommunityAuthentication, "_reset_tokens", mock.Mock()) as reset_mock, \
         mock.patch.object(community.CommunityAuthentication, "remove_login_detail", mock.Mock()) as remove_mock:
        auth.logout()
        reset_mock.assert_called_once()
        remove_mock.assert_called_once()
        auth.supabase_client.sign_out.assert_called_once()


def test_get_logged_in_email_authenticated(logged_in_auth):
    assert logged_in_auth.get_logged_in_email() == "plop"


def test_get_logged_in_email_unauthenticated(auth):
    with pytest.raises(authentication.AuthenticationRequired):
        auth.get_logged_in_email()


def test_can_authenticate(auth):
    assert auth.can_authenticate() is True


def test_ensure_community_url(auth):
    with mock.patch.object(auth, "can_authenticate", mock.Mock(return_value=False)) as can_authenticate_mock:
        with pytest.raises(authentication.UnavailableError):
            auth._ensure_community_url()
        can_authenticate_mock.assert_called_once()
    with mock.patch.object(auth, "can_authenticate", mock.Mock(return_value=True)) as can_authenticate_mock:
        auth._ensure_community_url()
        can_authenticate_mock.assert_called_once()


def test_is_logged_in(auth):
    auth.user_account.has_user_data = mock.Mock(return_value=False)
    assert auth.is_logged_in() is False
    auth.supabase_client.is_signed_in.assert_called_once()
    auth.user_account.has_user_data.assert_called_once()
    auth.user_account.has_user_data = mock.Mock(return_value=True)
    assert auth.is_logged_in() is True


def test_remove_login_detail(auth):
    with mock.patch.object(auth, "_reset_login_token", mock.Mock()) as _reset_login_token_mock, \
            mock.patch.object(auth, "_save_bot_id", mock.Mock()) as _save_bot_id_mock:
        auth.remove_login_detail()
        _reset_login_token_mock.assert_called_once()
        _save_bot_id_mock.assert_called_once()


def test_reset_login_token(auth):
    with mock.patch.object(octobot_commons.configuration.Configuration, "save", mock.Mock()) as save_mock:
        auth.configuration_storage.configuration = octobot_commons.configuration.Configuration("", "")
        auth.configuration_storage.configuration.config = {
            constants.CONFIG_COMMUNITY: {
                "_storage_key": "plop"
            }
        }
        auth._reset_login_token()
        assert auth.configuration_storage.configuration.config[constants.CONFIG_COMMUNITY]["_storage_key"] == ""
        save_mock.assert_called_once_with()


def test_get_saved_bot_id(auth):
    assert auth._get_saved_bot_id() is None
    auth.configuration_storage.configuration = octobot_commons.configuration.Configuration("", "")
    auth.configuration_storage.configuration.config = {
        constants.CONFIG_COMMUNITY: {
            constants.CONFIG_COMMUNITY_BOT_ID: "bid"
        }
    }
    assert auth._get_saved_bot_id() == "bid"


def test_authenticated(auth):
    @authentication.authenticated
    def mock_func(*_):
        pass
    with mock.patch.object(auth, "ensure_token_validity", mock.Mock()) as ensure_token_validity_mock:
        mock_func(auth)
        ensure_token_validity_mock.assert_called_once()


def test_update_supports(auth):
    with mock.patch.object(community.CommunitySupports, "from_community_dict", mock.Mock()) as from_community_dict_mock:
        auth._update_supports(400, {})
        from_community_dict_mock.assert_not_called()
        auth._update_supports(200, {})
        from_community_dict_mock.assert_called_once_with({})


# TODO restore test when implemented
@pytest.mark.asyncio
async def _test_auth_and_fetch_supports(auth):
    with mock.patch.object(auth, "_async_try_auto_login", mock.AsyncMock()) as _async_try_auto_login_mock:
        with mock.patch.object(auth, "is_logged_in", mock.Mock(return_value=False)) as is_logged_in_mock:
            auth.initialized_event = asyncio.Event()
            await auth._initialize_account()
            _async_try_auto_login_mock.assert_called_once()
            is_logged_in_mock.assert_called_once()
            assert auth.initialized_event.is_set()
            _async_try_auto_login_mock.reset_mock()
        with mock.patch.object(auth, "is_logged_in", mock.Mock(return_value=True)) as is_logged_in_mock, \
                mock.patch.object(auth, "_update_supports", mock.Mock()) as _update_supports_mock:
            resp_mock = mock.AsyncMock()
            resp_mock.status = 200
            resp_mock.json = mock.AsyncMock(return_value="plop")

            @contextlib.asynccontextmanager
            async def async_get(*_, **__):
                yield resp_mock

            auth._aiohttp_gql_session = mock.AsyncMock()
            auth._aiohttp_gql_session.get = async_get
            auth.initialized_event = asyncio.Event()
            await auth._initialize_account()
            _async_try_auto_login_mock.assert_called_once()
            is_logged_in_mock.assert_called_once()
            _update_supports_mock.assert_called_once_with(200, "plop")
            assert auth.initialized_event.is_set()


# TODO restore test when implemented
def _test_public_update_supports(auth):
    with mock.patch.object(auth, "get", mock.Mock(return_value=MockedResponse(status_code=200, json=AUTH_RETURN))) \
        as get_mock, \
         mock.patch.object(auth, "_update_supports", mock.Mock()) as _update_supports_mock:
        auth.update_supports()
        get_mock.assert_called_once()
        _update_supports_mock.assert_called_once_with(200, AUTH_RETURN)


def test_is_initialized(auth):
    assert auth.is_initialized() is False
    auth.initialized_event = asyncio.Event()
    assert auth.is_initialized() is False
    auth.initialized_event.set()
    assert auth.is_initialized() is True


def test_init_account(auth):
    with mock.patch.object(asyncio, "create_task", mock.Mock(return_value="task")) as create_task_mock, \
            mock.patch.object(auth, "_initialize_account", mock.Mock(return_value="coro")) \
            as _auth_and_fetch_account_mock:
        auth.init_account()
        create_task_mock.assert_called_once_with("coro")
        _auth_and_fetch_account_mock.assert_called_once()
        assert auth._fetch_account_task == "task"


@pytest.mark.asyncio
async def test_stop(auth):
    auth._fetch_account_task = mock.Mock()
    auth._fetch_account_task.cancel = mock.Mock()
    auth._fetch_account_task.done = mock.Mock(return_value=True)
    await auth.stop()
    auth.supabase_client.close.assert_awaited_once()
    auth.supabase_client.close.reset_mock()
    auth._fetch_account_task.cancel.assert_not_called()
    auth._fetch_account_task.done = mock.Mock(return_value=False)

    await auth.stop()
    auth.supabase_client.close.assert_awaited_once()
    auth._fetch_account_task.cancel.assert_called_once()

    auth.supabase_client.close.reset_mock()
    auth._fetch_account_task.cancel.reset_mock()
    await auth.stop()
    auth.supabase_client.close.assert_awaited_once()
    auth._fetch_account_task.cancel.assert_called_once()
