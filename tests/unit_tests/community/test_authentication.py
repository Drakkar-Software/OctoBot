#  Drakkar-Software OctoBot
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
import pytest
import mock
import requests
import time
import os
import aiohttp

import octobot.constants as constants
import octobot.community as community
import octobot_commons.authentication as authentication
import octobot_commons.configuration
import octobot_commons.constants as commons_constants

AUTH_URL = os.getenv("COMMUNITY_SERVER_URL", "https://oh.fake/auth")
AUTH_RETURN = {
    "access_token": "1",
    "refresh_token": "2",
    "expires_in": 3600,
}
EMAIL_RETURN = {
    "data": {
        "attributes": {
             "email": "plop"
        }
    }
}


class MockedResponse:
    def __init__(self, status_code=200, json=None):
        self.status_code = status_code
        self.json_resp = json

    def json(self):
        return self.json_resp


@pytest.fixture
def logged_in_auth():
    with mock.patch.object(requests, "post", mock.Mock(return_value=MockedResponse(json=AUTH_RETURN))):
        auth = community.CommunityAuthentication(AUTH_URL)
        auth.login("username", "login")
        return auth


@pytest.fixture
def auth():
    return community.CommunityAuthentication(AUTH_URL)


def test_constructor():
    with mock.patch.object(community.CommunityAuthentication, "login", mock.Mock()) as login_mock:
        community.CommunityAuthentication(AUTH_URL)
        login_mock.assert_not_called()
        community.CommunityAuthentication(AUTH_URL, "username", "password")
        login_mock.assert_called_with("username", "password")


def test_login(auth):
    with mock.patch.object(community.CommunityAuthentication, "_reset_tokens", mock.Mock()) as reset_mock, \
            mock.patch.object(community.CommunityAuthentication, "_handle_auth_result", mock.Mock()) \
            as auth_res_mock, \
            mock.patch.object(requests, "post", mock.Mock(return_value="1")) as post_mock:
        auth.login("username", "password")
        reset_mock.assert_called_once()
        post_mock.assert_called_once()
        auth_res_mock.assert_called_once_with("1")


def test_logout(auth):
    with mock.patch.object(community.CommunityAuthentication, "_reset_tokens", mock.Mock()) as reset_mock, \
         mock.patch.object(community.CommunityAuthentication, "clear_cache", mock.Mock()) as clear_cache_mock, \
         mock.patch.object(community.CommunityAuthentication, "remove_login_detail", mock.Mock()) as remove_mock:
        auth.logout()
        reset_mock.assert_called_once()
        clear_cache_mock.assert_called_once()
        remove_mock.assert_called_once()


def test_clear_cache(auth):
    auth._cache["1"] = 1
    auth.clear_cache()
    assert auth._cache == {}


def test_reset_tokens(auth):
    auth._auth_token = "1"
    auth.refresh_token = "1"
    auth._expire_at = "1"
    auth._session.headers[community.CommunityAuthentication.AUTHORIZATION_HEADER] = "1"
    auth._session.headers[community.CommunityAuthentication.IDENTIFIER_HEADER] = "2"
    auth._reset_tokens()
    assert auth._auth_token is auth.refresh_token is auth._expire_at is None
    assert community.CommunityAuthentication.AUTHORIZATION_HEADER not in auth._session.headers
    assert community.CommunityAuthentication.IDENTIFIER_HEADER in auth._session.headers


@pytest.mark.asyncio
async def test_refresh_session(auth):
    auth._auth_token = "1"
    auth._session.headers[community.CommunityAuthentication.IDENTIFIER_HEADER] = "3"
    auth.identifier = "4"
    assert community.CommunityAuthentication.AUTHORIZATION_HEADER not in auth._session.headers
    auth._refresh_session()
    assert auth._session.headers[community.CommunityAuthentication.AUTHORIZATION_HEADER] == f"Bearer 1"
    assert auth._session.headers[community.CommunityAuthentication.IDENTIFIER_HEADER] == "4"
    assert auth._aiohttp_session is None
    auth._aiohttp_session = aiohttp.ClientSession()
    with mock.patch.object(auth, "_update_aiohttp_session_headers", mock.Mock()) as update_aiohttp_session_headers_mock:
        auth._refresh_session()
        update_aiohttp_session_headers_mock.assert_called_once()
    await auth._aiohttp_session.close()


@pytest.mark.asyncio
async def test_update_aiohttp_session_headers(auth):
    auth._aiohttp_session = aiohttp.ClientSession()
    auth._auth_token = "1"
    auth._aiohttp_session.headers[community.CommunityAuthentication.IDENTIFIER_HEADER] = "3"
    auth.identifier = "4"
    auth._update_aiohttp_session_headers()
    assert auth._aiohttp_session.headers[community.CommunityAuthentication.AUTHORIZATION_HEADER] == f"Bearer 1"
    assert auth._aiohttp_session.headers[community.CommunityAuthentication.IDENTIFIER_HEADER] == "4"
    await auth._aiohttp_session.close()


def test_get_logged_in_email_authenticated(logged_in_auth):
    with mock.patch.object(logged_in_auth._session, "get", mock.Mock(return_value=MockedResponse(json="plop"))):
        with pytest.raises(TypeError):
            logged_in_auth.get_logged_in_email()
    with mock.patch.object(logged_in_auth._session, "get", mock.Mock(return_value=MockedResponse(json=EMAIL_RETURN))):
        assert logged_in_auth.get_logged_in_email() == "plop"


def test_get_logged_in_email_unauthenticated(auth):
    with pytest.raises(authentication.AuthenticationRequired):
        auth.get_logged_in_email()


def test_can_authenticate(auth):
    assert auth.can_authenticate()
    auth.authentication_url = constants.DEFAULT_COMMUNITY_URL + auth.authentication_url
    assert auth.can_authenticate() is False


def test_get_unauthenticated(auth):
    with pytest.raises(authentication.AuthenticationRequired):
        auth.get("url")


@pytest.mark.asyncio
async def test_get_aiohttp_session(auth):
    assert auth._aiohttp_session is None
    with mock.patch.object(auth, "_update_aiohttp_session_headers", mock.Mock()) as \
         _update_aiohttp_session_headers_mock:
        session = auth.get_aiohttp_session()
        assert isinstance(auth._aiohttp_session, aiohttp.ClientSession)
        _update_aiohttp_session_headers_mock.assert_called_once()
        assert auth._aiohttp_session is session
        session_2 = auth.get_aiohttp_session()
        assert session_2 is session
        await session.close()


def test_ensure_community_url(auth):
    with mock.patch.object(auth, "can_authenticate", mock.Mock(return_value=False)) as can_authenticate_mock:
        with pytest.raises(authentication.UnavailableError):
            auth._ensure_community_url()
        can_authenticate_mock.assert_called_once()
    with mock.patch.object(auth, "can_authenticate", mock.Mock(return_value=True)) as can_authenticate_mock:
        auth._ensure_community_url()
        can_authenticate_mock.assert_called_once()


def test_get_authenticated(logged_in_auth):
    with mock.patch.object(logged_in_auth._session, "get", mock.Mock(return_value="plop")) as requests_get_mock:
        assert logged_in_auth.get("") == "plop"
        requests_get_mock.assert_called_with("", params=None)
        assert logged_in_auth.get("", params={"1": 1}, t=1) == "plop"
        requests_get_mock.assert_called_with("", params={"1": 1}, t=1)


def test_get_authenticated_with_cache(logged_in_auth):
    with mock.patch.object(logged_in_auth._session, "get", mock.Mock(return_value="plop")) as requests_get_mock:
        # with 1 cached request
        assert logged_in_auth.get("", allow_cache=True) == "plop"
        requests_get_mock.assert_called_once()
        assert logged_in_auth._cache[""] == "plop"
        for _ in range(10):
            # uses cached value, does not make a new request
            assert logged_in_auth.get("", allow_cache=True) == "plop"
        requests_get_mock.assert_called_once()
        requests_get_mock.reset_mock()

        # with 2 cached requests
        assert logged_in_auth.get("1", allow_cache=True) == "plop"
        requests_get_mock.assert_called_once()
        assert logged_in_auth._cache[""] == "plop"
        assert logged_in_auth._cache["1"] == "plop"
        for _ in range(10):
            # uses cached value, does not make a new request
            assert logged_in_auth.get("", allow_cache=True) == "plop"
            assert logged_in_auth.get("1", allow_cache=True) == "plop"
        requests_get_mock.assert_called_once()
        requests_get_mock.reset_mock()

        assert logged_in_auth.get("", allow_cache=False) == "plop"
        requests_get_mock.assert_called_once()
        requests_get_mock.reset_mock()

        # without cache allowed but available cache
        assert all(c in logged_in_auth._cache for c in ("", "1"))
        assert logged_in_auth.get("", allow_cache=False) == "plop"
        requests_get_mock.assert_called_once()
        requests_get_mock.reset_mock()
        assert logged_in_auth.get("1", allow_cache=False) == "plop"
        requests_get_mock.assert_called_once()

        # set cache
        logged_in_auth.clear_cache()
        assert logged_in_auth._cache == {}
        assert logged_in_auth.get("", allow_cache=True) == "plop"
        assert logged_in_auth.get("1", allow_cache=True) == "plop"
        assert all(c in logged_in_auth._cache for c in ("", "1"))
        requests_get_mock.reset_mock()
        for _ in range(10):
            # uses cached value, does not make a new request
            assert logged_in_auth.get("", allow_cache=True) == "plop"
            assert logged_in_auth.get("1", allow_cache=True) == "plop"
        requests_get_mock.assert_not_called()
        requests_get_mock.reset_mock()


def test_post_unauthenticated(auth):
    with pytest.raises(authentication.AuthenticationRequired):
        auth.post("url")


def test_post_authenticated(logged_in_auth):
    with mock.patch.object(logged_in_auth._session, "post", mock.Mock(return_value="plop")) as requests_post_mock:
        assert logged_in_auth.post("") == "plop"
        requests_post_mock.assert_called_with("", data=None, json=None)
        assert logged_in_auth.post("", data={"1": 1}, t=1) == "plop"
        requests_post_mock.assert_called_with("", data={"1": 1}, json=None, t=1)
        assert logged_in_auth.post("", json={"1": 1}) == "plop"
        requests_post_mock.assert_called_with("", data=None, json={"1": 1})


def test_is_logged_in(auth):
    assert auth.is_logged_in() is False
    auth._auth_token = "1"
    auth.refresh_token = "1"
    auth._expire_at = None
    assert auth.is_logged_in() is False
    auth._expire_at = "1"
    assert auth.is_logged_in() is True


def test_ensure_token_validity():
    with pytest.raises(authentication.AuthenticationRequired):
        community.CommunityAuthentication(AUTH_URL).ensure_token_validity()
    with pytest.raises(authentication.AuthenticationRequired):
        auth = community.CommunityAuthentication(AUTH_URL)
        auth._auth_token = "1"
        auth.refresh_token = "1"
        auth._expire_at = None
        community.CommunityAuthentication(AUTH_URL).ensure_token_validity()
    with pytest.raises(authentication.AuthenticationRequired):
        auth = community.CommunityAuthentication(AUTH_URL)
        auth._auth_token = "1"
        auth.refresh_token = "1"
        auth._expire_at = "1"
        auth._reset_tokens()
        community.CommunityAuthentication(AUTH_URL).ensure_token_validity()
    auth = community.CommunityAuthentication(AUTH_URL)
    with mock.patch.object(auth, "is_logged_in", mock.Mock(return_value=False)) as is_logged_in_mock, \
         mock.patch.object(auth, "_try_auto_login", mock.Mock()) as _try_auto_login_mock:
        with pytest.raises(authentication.AuthenticationRequired):
            auth.ensure_token_validity()
        assert is_logged_in_mock.call_count == 2
        _try_auto_login_mock.assert_called_once()
    with mock.patch.object(auth, "_try_auto_login", mock.Mock()) as _try_auto_login_mock:
        with pytest.raises(authentication.AuthenticationRequired):
            auth.ensure_token_validity()
        _try_auto_login_mock.assert_called_once()
    auth = community.CommunityAuthentication(AUTH_URL)
    auth._auth_token = "1"
    auth.refresh_token = "1"
    # refresh required
    auth._expire_at = 1
    with mock.patch.object(auth, "_refresh_auth", mock.Mock()) as refresh_mock, \
         mock.patch.object(auth, "_try_auto_login", mock.Mock()) as _try_auto_login_mock:
        auth.ensure_token_validity()
        refresh_mock.assert_called_once()
        _try_auto_login_mock.assert_not_called()
    # refresh not required
    auth._expire_at = time.time() + 10
    with mock.patch.object(auth, "_refresh_auth", mock.Mock()) as refresh_mock:
        auth.ensure_token_validity()
        refresh_mock.assert_not_called()
    with mock.patch.object(auth, "ensure_token_validity", mock.Mock()) as ensure_mock:
        auth.ensure_token_validity()
        ensure_mock.assert_called_once()


def test_remove_login_detail(auth):
    with mock.patch.object(auth, "_save_login_token", mock.Mock()) as update_mock:
        auth.remove_login_detail()
        update_mock.assert_called_once_with("")


def test_save_login_token(auth):
    with mock.patch.object(octobot_commons.configuration.Configuration, "save", mock.Mock()) as save_mock:
        auth._save_login_token("plop")
        save_mock.assert_not_called()
        auth.edited_config = octobot_commons.configuration.Configuration("", "")
        auth.edited_config.config = {}
        auth._save_login_token("plop")
        assert auth.edited_config.config[commons_constants.CONFIG_COMMUNITY_TOKEN] == "plop"
        save_mock.assert_called_once_with()


def test_try_auto_login(auth):
    with mock.patch.object(auth, "_auto_login", mock.Mock()) as _auto_login_mock:
        auth._try_auto_login()
        _auto_login_mock.assert_not_called()
        auth.edited_config = octobot_commons.configuration.Configuration("", "")
        auth.edited_config.config = {
            commons_constants.CONFIG_COMMUNITY_TOKEN: "plop"
        }
        auth._try_auto_login()
        _auto_login_mock.assert_called_once_with("plop")


def test_auto_login(auth):
    with mock.patch.object(auth, "_refresh_auth", mock.Mock()) as _refresh_auth_mock:
        auth._auto_login("1")
        assert auth.refresh_token == "1"
        _refresh_auth_mock.assert_called_once()
    auth.refresh_token = None
    with mock.patch.object(auth, "_refresh_auth", mock.Mock(side_effect=authentication.FailedAuthentication())) as \
            _refresh_auth_mock, \
         mock.patch.object(auth, "logout", mock.Mock()) as logout_mock:
        auth._auto_login("1")
        assert auth.refresh_token == "1"
        _refresh_auth_mock.assert_called_once()
        logout_mock.assert_called_once()
    auth.refresh_token = None
    with mock.patch.object(auth, "_refresh_auth", mock.Mock(side_effect=Exception())) as \
            _refresh_auth_mock, \
         mock.patch.object(auth, "logout", mock.Mock()) as logout_mock, \
         mock.patch.object(auth, "logger", mock.Mock()) as logger_mock:
        auth._auto_login("1")
        assert auth.refresh_token == "1"
        _refresh_auth_mock.assert_called_once()
        logger_mock.exception.assert_called_once()
        logout_mock.assert_not_called()


def test_refresh_auth(auth):
    with mock.patch.object(requests, "post", mock.Mock(return_value="plop")), \
         mock.patch.object(auth, "_handle_auth_result", mock.Mock()) as handle_result_mock:
        auth._refresh_auth()
        assert handle_result_mock.called_once_with("plop")


def test_handle_auth_result(auth):
    with mock.patch.object(auth, "_refresh_session", mock.Mock()) as refresh_mock:
        with pytest.raises(authentication.FailedAuthentication):
            auth._handle_auth_result(MockedResponse(status_code=400))
        refresh_mock.assert_not_called()
        with pytest.raises(authentication.AuthenticationError):
            auth._handle_auth_result(MockedResponse(status_code=500))
        refresh_mock.assert_not_called()
        with mock.patch.object(time, "time", mock.Mock(return_value=10)):
            auth._handle_auth_result(MockedResponse(status_code=200, json=AUTH_RETURN))
            assert auth._auth_token == AUTH_RETURN["access_token"]
            assert auth.refresh_token == AUTH_RETURN["refresh_token"]
            assert auth._expire_at == AUTH_RETURN["expires_in"] + 10 - \
                   community.CommunityAuthentication.ALLOWED_TIME_DELAY
            refresh_mock.assert_called_once()


def test_authenticated(auth):
    @authentication.authenticated
    def mock_func(*_):
        pass
    with mock.patch.object(auth, "ensure_token_validity", mock.Mock()) as ensure_token_validity_mock:
        mock_func(auth)
        ensure_token_validity_mock.assert_called_once()
