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

import octobot.community as community

AUTH_URL = "https://oh.fake/auth"
AUTH_RETURN = {
    "access_token": "1",
    "refresh_token": "2",
    "expires_in": 3600,
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


def test_constructor():
    with mock.patch.object(community.CommunityAuthentication, "login", mock.Mock()) as login_mock:
        community.CommunityAuthentication(AUTH_URL)
        login_mock.assert_not_called()
        community.CommunityAuthentication(AUTH_URL, "username", "password")
        login_mock.assert_called_with("username", "password")


def test_login():
    with mock.patch.object(community.CommunityAuthentication, "_reset_tokens", mock.Mock()) as reset_mock, \
            mock.patch.object(community.CommunityAuthentication, "_handle_auth_result", mock.Mock()) \
            as auth_res_mock, \
            mock.patch.object(requests, "post", mock.Mock(return_value="1")) as post_mock:
        auth = community.CommunityAuthentication(AUTH_URL)
        auth.login("username", "password")
        reset_mock.assert_called_once()
        post_mock.assert_called_once()
        auth_res_mock.assert_called_once_with("1")


def test_logout():
    with mock.patch.object(community.CommunityAuthentication, "_reset_tokens", mock.Mock()) as reset_mock:
        community.CommunityAuthentication(AUTH_URL).logout()
        reset_mock.assert_called_once()


def test_reset_tokens():
    auth = community.CommunityAuthentication(AUTH_URL)
    auth._auth_token = "1"
    auth._refresh_token = "1"
    auth._expire_at = "1"
    auth._session.headers[community.CommunityAuthentication.AUTHORIZATION_HEADER] = "1"
    auth._reset_tokens()
    assert auth._auth_token is auth._refresh_token is auth._expire_at is None
    assert community.CommunityAuthentication.AUTHORIZATION_HEADER not in auth._session.headers


def test_refresh_session():
    auth = community.CommunityAuthentication(AUTH_URL)
    auth._auth_token = "1"
    assert community.CommunityAuthentication.AUTHORIZATION_HEADER not in auth._session.headers
    auth._refresh_session()
    assert auth._session.headers[community.CommunityAuthentication.AUTHORIZATION_HEADER] == f"Bearer 1"


def test_get_unauthenticated():
    auth = community.CommunityAuthentication(AUTH_URL)
    with pytest.raises(community.AuthenticationRequired):
        auth.get("url")


def test_get_authenticated(logged_in_auth):
    with mock.patch.object(logged_in_auth._session, "get", mock.Mock(return_value="plop")):
        assert logged_in_auth.get("") == "plop"


def test_post_unauthenticated():
    auth = community.CommunityAuthentication(AUTH_URL)
    with pytest.raises(community.AuthenticationRequired):
        auth.post("url")


def test_post_authenticated(logged_in_auth):
    with mock.patch.object(logged_in_auth._session, "post", mock.Mock(return_value="plop")):
        assert logged_in_auth.post("") == "plop"


def test_ensure_token_validity():
    with pytest.raises(community.AuthenticationRequired):
        community.CommunityAuthentication(AUTH_URL).ensure_token_validity()
    with pytest.raises(community.AuthenticationRequired):
        auth = community.CommunityAuthentication(AUTH_URL)
        auth._auth_token = "1"
        auth._refresh_token = "1"
        auth._expire_at = None
        community.CommunityAuthentication(AUTH_URL).ensure_token_validity()
    with pytest.raises(community.AuthenticationRequired):
        auth = community.CommunityAuthentication(AUTH_URL)
        auth._auth_token = "1"
        auth._refresh_token = "1"
        auth._expire_at = "1"
        auth._reset_tokens()
        community.CommunityAuthentication(AUTH_URL).ensure_token_validity()
    auth = community.CommunityAuthentication(AUTH_URL)
    auth._auth_token = "1"
    auth._refresh_token = "1"
    # refresh required
    auth._expire_at = 1
    with mock.patch.object(auth, "_refresh_auth", mock.Mock()) as refresh_mock:
        auth.ensure_token_validity()
        refresh_mock.assert_called_once()
    # refresh not required
    auth._expire_at = time.time() + 10
    with mock.patch.object(auth, "_refresh_auth", mock.Mock()) as refresh_mock:
        auth.ensure_token_validity()
        refresh_mock.assert_not_called()


def test_refresh_auth():
    auth = community.CommunityAuthentication(AUTH_URL)
    with mock.patch.object(requests, "post", mock.Mock(return_value="plop")), \
         mock.patch.object(auth, "_handle_auth_result", mock.Mock()) as handle_result_mock:
        auth._refresh_auth()
        assert handle_result_mock.called_once_with("plop")


def test_handle_auth_result():
    auth = community.CommunityAuthentication(AUTH_URL)
    with mock.patch.object(auth, "_refresh_session", mock.Mock()) as refresh_mock:
        with pytest.raises(community.FailedAuthentication):
            auth._handle_auth_result(MockedResponse(status_code=400))
        refresh_mock.assert_not_called()
        with pytest.raises(community.FailedAuthentication):
            auth._handle_auth_result(MockedResponse(status_code=500))
        refresh_mock.assert_not_called()
        with mock.patch.object(time, "time", mock.Mock(return_value=10)):
            auth._handle_auth_result(MockedResponse(status_code=200, json=AUTH_RETURN))
            assert auth._auth_token == AUTH_RETURN["access_token"]
            assert auth._refresh_token == AUTH_RETURN["refresh_token"]
            assert auth._expire_at == AUTH_RETURN["expires_in"] + 10 - \
                   community.CommunityAuthentication.ALLOWED_TIME_DELAY
            refresh_mock.assert_called_once()


def test_authenticated():
    @community.authenticated
    def mock_func(*_):
        pass
    auth = community.CommunityAuthentication(AUTH_URL)
    with mock.patch.object(auth, "ensure_token_validity", mock.Mock()) as ensure_token_validity_mock:
        mock_func(auth)
        ensure_token_validity_mock.assert_called_once()
