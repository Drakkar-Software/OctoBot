#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
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


@pytest_asyncio.fixture
async def logged_in_auth():
    community.IdentifiersProvider.use_production()
    auth = community.CommunityAuthentication(AUTH_URL, None)
    with mock.patch.object(auth._session, "post", mock.Mock(return_value=MockedResponse(
            json=EMAIL_RETURN, headers={auth.SESSION_HEADER: "hi"}))), \
            mock.patch.object(community.CommunityAuthentication, "update_supports", mock.AsyncMock()), \
            mock.patch.object(community.CommunityAuthentication, "update_selected_bot", mock.AsyncMock()):
        await auth.login("username", "login")
        return auth


@pytest.fixture
def auth():
    community.IdentifiersProvider.use_production()
    return community.CommunityAuthentication(AUTH_URL, None)


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
            mock.patch.object(community.CommunityAuthentication, "_handle_auth_result", mock.Mock()) \
            as auth_res_mock, \
            mock.patch.object(auth._session, "post", mock.Mock(return_value=resp_mock)) as post_mock, \
            mock.patch.object(community.CommunityAuthentication, "update_supports", mock.AsyncMock()) \
            as update_supports_mock, \
            mock.patch.object(community.CommunityAuthentication, "update_selected_bot", mock.AsyncMock()) \
            as update_selected_bot_mock:
        await auth.login("username", "password")
        reset_mock.assert_called_once()
        post_mock.assert_called_once()
        update_supports_mock.assert_not_called()
        update_selected_bot_mock.assert_not_called()
        auth_res_mock.assert_called_once_with(resp_mock.status_code, resp_mock.json(), resp_mock.headers)
        with mock.patch.object(community.CommunityAuthentication, "is_logged_in", mock.Mock(return_value=True)) \
                as is_logged_in_mock:
            await auth.login("username", "password")
            is_logged_in_mock.assert_called_once()
            update_supports_mock.assert_called_once()
            update_selected_bot_mock.assert_called_once()


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
    auth._session.headers[community.CommunityAuthentication.AUTHORIZATION_HEADER] = "1"
    auth._session.headers[community.CommunityAuthentication.SESSION_HEADER] = "2"
    auth._reset_tokens()
    assert auth._auth_token is None
    assert community.CommunityAuthentication.AUTHORIZATION_HEADER in auth._session.headers
    assert community.CommunityAuthentication.SESSION_HEADER not in auth._session.headers


@pytest.mark.asyncio
async def test_update_sessions_headers(auth):
    auth._auth_token = "1"
    headers_mock = {
        community.CommunityAuthentication.AUTHORIZATION_HEADER: f"Basic {auth._auth_token}",
        community.CommunityAuthentication.SESSION_HEADER: "4"
    }
    with mock.patch.object(community.CommunityAuthentication, "get_headers", mock.Mock(return_value=headers_mock)) \
         as get_headers_mock:
        auth._session.headers[community.CommunityAuthentication.SESSION_HEADER] = "3"
        assert community.CommunityAuthentication.AUTHORIZATION_HEADER in auth._session.headers
        auth._update_sessions_headers()
        get_headers_mock.assert_called_once()
        assert auth._session.headers[community.CommunityAuthentication.AUTHORIZATION_HEADER] == \
               f"Basic {auth._auth_token}"
        assert auth._session.headers[community.CommunityAuthentication.SESSION_HEADER] == "4"
        assert auth._aiohttp_session is None
        auth._aiohttp_session = aiohttp.ClientSession()
        auth._update_sessions_headers()
        assert auth._aiohttp_session.headers[community.CommunityAuthentication.AUTHORIZATION_HEADER] == \
               f"Basic {auth._auth_token}"
        assert auth._aiohttp_session.headers[community.CommunityAuthentication.SESSION_HEADER] == "4"
        await auth._aiohttp_session.close()


@pytest.mark.asyncio
async def test_get_headers(auth):
    auth._community_token = "1"
    assert auth.get_headers() == {
        community.CommunityAuthentication.AUTHORIZATION_HEADER: f"Basic {auth._community_token}"
    }
    auth._auth_token = "2"
    assert auth.get_headers() == {
        community.CommunityAuthentication.AUTHORIZATION_HEADER: f"Basic {auth._community_token}",
        community.CommunityAuthentication.SESSION_HEADER: auth._auth_token
    }


def test_get_logged_in_email_authenticated(logged_in_auth):
    assert logged_in_auth.get_logged_in_email() == "plop"


def test_get_logged_in_email_unauthenticated(auth):
    with pytest.raises(authentication.AuthenticationRequired):
        auth.get_logged_in_email()


def test_can_authenticate(auth):
    assert auth.can_authenticate()
    auth.authentication_url = "todo" + auth.authentication_url
    assert auth.can_authenticate() is False


def test_get_unauthenticated(auth):
    with pytest.raises(authentication.AuthenticationRequired):
        auth.get("url")


@pytest.mark.asyncio
async def test_get_aiohttp_session(auth):
    assert auth._aiohttp_session is None
    with mock.patch.object(auth, "_update_sessions_headers", mock.Mock()) as \
         _update_sessions_headers_mock:
        auth.get_aiohttp_session()
        _update_sessions_headers_mock.assert_called_once()
        _update_sessions_headers_mock.reset_mock()
        auth._aiohttp_session = None
        session = auth.get_aiohttp_session()
        assert isinstance(auth._aiohttp_session, aiohttp.ClientSession)
        _update_sessions_headers_mock.assert_called_once()
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
    assert auth.is_logged_in() is True
    auth._auth_token = None
    assert auth.is_logged_in() is False


def test_ensure_token_validity():
    with pytest.raises(authentication.AuthenticationRequired):
        community.CommunityAuthentication(AUTH_URL, None).ensure_token_validity()
    with pytest.raises(authentication.AuthenticationRequired):
        auth = community.CommunityAuthentication(AUTH_URL, None)
        auth._auth_token = "1"
        community.CommunityAuthentication(AUTH_URL, None).ensure_token_validity()
    with pytest.raises(authentication.AuthenticationRequired):
        auth = community.CommunityAuthentication(AUTH_URL, None)
        auth._auth_token = "1"
        auth._reset_tokens()
        community.CommunityAuthentication(AUTH_URL, None).ensure_token_validity()
    auth = community.CommunityAuthentication(AUTH_URL, None)
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
    auth = community.CommunityAuthentication(AUTH_URL, None)
    auth._auth_token = "1"
    with mock.patch.object(auth, "_check_auth", mock.Mock()) as refresh_mock, \
         mock.patch.object(auth, "_try_auto_login", mock.Mock()) as _try_auto_login_mock:
        auth.ensure_token_validity()
        refresh_mock.assert_not_called()
        _try_auto_login_mock.assert_not_called()


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
        assert auth.edited_config.config[constants.CONFIG_COMMUNITY][constants.CONFIG_COMMUNITY_TOKEN] == "plop"
        save_mock.assert_called_once_with()


def test_get_saved_token(auth):
    assert auth._get_saved_token() is None
    auth.edited_config = octobot_commons.configuration.Configuration("", "")
    auth.edited_config.config = {
        constants.CONFIG_COMMUNITY: {
            constants.CONFIG_COMMUNITY_TOKEN: "plop"
        }
    }
    assert auth._get_saved_token() == "plop"


def test_try_auto_login(auth):
    with mock.patch.object(auth, "_auto_login", mock.Mock()) as _auto_login_mock:
        with mock.patch.object(auth, "_get_saved_token", mock.Mock(return_value=None)) as get_token_mock:
            auth._try_auto_login()
            get_token_mock.assert_called_once()
            _auto_login_mock.assert_not_called()

        with mock.patch.object(auth, "_get_saved_token", mock.Mock(return_value="t")) as get_token_mock:
            auth._try_auto_login()
            get_token_mock.assert_called_once()
            _auto_login_mock.assert_called_once()


@pytest.mark.asyncio
async def test_async_try_auto_login(auth):
    with mock.patch.object(auth, "_async_auto_login", mock.AsyncMock()) as _async_auto_login_mock:
        with mock.patch.object(auth, "_get_saved_token", mock.Mock(return_value=None)) as get_token_mock:
            await auth._async_try_auto_login()
            get_token_mock.assert_called_once()
            _async_auto_login_mock.assert_not_called()

        with mock.patch.object(auth, "_get_saved_token", mock.Mock(return_value="t")) as get_token_mock:
            await auth._async_try_auto_login()
            get_token_mock.assert_called_once()
            _async_auto_login_mock.assert_called_once()


def test_auto_login(auth):
    with mock.patch.object(auth, "_check_auth", mock.Mock()) as _check_auth_mock:
        auth._auto_login()
        _check_auth_mock.assert_called_once()
    with mock.patch.object(auth, "_check_auth", mock.Mock(side_effect=authentication.FailedAuthentication())) as \
            _refresh_auth_mock, \
         mock.patch.object(auth, "logout", mock.Mock()) as logout_mock:
        auth._auto_login()
        _check_auth_mock.assert_called_once()
        logout_mock.assert_called_once()
    with mock.patch.object(auth, "_check_auth", mock.Mock(side_effect=Exception())) as \
            _check_auth_mock, \
         mock.patch.object(auth, "logout", mock.Mock()) as logout_mock, \
         mock.patch.object(auth, "logger", mock.Mock()) as logger_mock:
        auth._auto_login()
        _check_auth_mock.assert_called_once()
        logger_mock.exception.assert_called_once()
        logout_mock.assert_not_called()


@pytest.mark.asyncio
async def test_async_auto_login(auth):
    _auth_handler_mock = mock.Mock()

    @contextlib.contextmanager
    def _auth_handler_mock_context_manager(*args):
        _auth_handler_mock(*args)
        yield
    with mock.patch.object(auth, "_auth_handler", _auth_handler_mock_context_manager), \
            mock.patch.object(auth, "_async_check_auth", mock.AsyncMock()) as _async_check_auth_mock:
        await auth._async_auto_login()
        _auth_handler_mock.assert_called_once_with()
        _async_check_auth_mock.assert_called_once()


def test_check_auth(auth):
    resp_mock = mock.Mock()
    with mock.patch.object(requests, "post", mock.Mock(return_value=resp_mock)), \
         mock.patch.object(auth, "_handle_auth_result", mock.Mock()) as handle_result_mock:
        auth._check_auth()
        assert handle_result_mock.called_once_with(resp_mock.status_code, resp_mock.json(), resp_mock.headers)


@pytest.mark.asyncio
async def test_async_check_auth(auth):
    auth._aiohttp_session = mock.AsyncMock()
    resp_mock = mock.AsyncMock()
    resp_mock.status = 200
    resp_mock.json = mock.AsyncMock(return_value="plop")
    resp_mock.headers = {}

    @contextlib.asynccontextmanager
    async def async_get(*_, **__):
        yield resp_mock
    auth._aiohttp_session.get = async_get
    with mock.patch.object(auth, "_handle_auth_result", mock.Mock()) as handle_result_mock:
        await auth._async_check_auth()
        assert handle_result_mock.called_once_with(resp_mock.status_code, "plop", resp_mock.headers)


def test_handle_auth_result(auth):
    with mock.patch.object(auth, "_update_sessions_headers", mock.Mock()) as _update_sessions_headers_mock:
        with pytest.raises(authentication.FailedAuthentication):
            auth._handle_auth_result(400, MockedResponse().json(), MockedResponse().headers)
        with pytest.raises(authentication.FailedAuthentication):
            auth._handle_auth_result(400, MockedResponse("data").json(), MockedResponse().headers)
        _update_sessions_headers_mock.assert_not_called()
        with pytest.raises(authentication.AuthenticationError):
            auth._handle_auth_result(500, MockedResponse().json(), MockedResponse().headers)
        with pytest.raises(authentication.AuthenticationError):
            auth._handle_auth_result(500, MockedResponse("data").json(), MockedResponse().headers)
        _update_sessions_headers_mock.assert_not_called()
        auth._handle_auth_result(200, AUTH_RETURN, AUTH_HEADER_RETURN)
        assert auth._auth_token == AUTH_HEADER_RETURN[auth.SESSION_HEADER]
        _update_sessions_headers_mock.assert_called_once()


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
            await auth._auth_and_fetch_account()
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

            auth._aiohttp_session = mock.AsyncMock()
            auth._aiohttp_session.get = async_get
            auth.initialized_event = asyncio.Event()
            await auth._auth_and_fetch_account()
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
    auth._fetch_account_task = mock.Mock()
    auth._fetch_account_task.done = mock.Mock(return_value=False)
    assert auth.is_initialized() is False
    auth._fetch_account_task.done = mock.Mock(return_value=True)
    assert auth.is_initialized() is True


def test_init_account(auth):
    with mock.patch.object(asyncio, "create_task", mock.Mock(return_value="task")) as create_task_mock, \
            mock.patch.object(auth, "_auth_and_fetch_account", mock.Mock(return_value="coro")) \
            as _auth_and_fetch_account_mock:
        auth.init_account()
        assert isinstance(auth.initialized_event, asyncio.Event)
        create_task_mock.assert_called_once_with("coro")
        _auth_and_fetch_account_mock.assert_called_once()
        assert auth._fetch_account_task == "task"


@pytest.mark.asyncio
async def test_stop(auth):
    auth._fetch_account_task = mock.Mock()
    auth._fetch_account_task.cancel = mock.Mock()
    auth._fetch_account_task.done = mock.Mock(return_value=True)
    auth._restart_task = mock.Mock()
    auth._restart_task.cancel = mock.Mock()
    auth._aiohttp_session = mock.Mock()
    auth._aiohttp_session.close = mock.AsyncMock()
    with mock.patch.object(auth, "stop_feeds", mock.AsyncMock()) as stop_feeds_mock, \
         mock.patch.object(auth._restart_task, "done", mock.Mock(return_value=True)) as done_mock:
        await auth.stop()
        stop_feeds_mock.assert_called_once()
        done_mock.assert_called_once()
        auth._fetch_account_task.cancel.assert_not_called()
        auth._restart_task.cancel.assert_not_called()
        auth._aiohttp_session.close.reset_mock()
    auth._fetch_account_task.done = mock.Mock(return_value=False)
    with mock.patch.object(auth, "stop_feeds", mock.AsyncMock(side_effect=auth.stop_feeds)) as stop_feeds_mock, \
         mock.patch.object(auth._restart_task, "done", mock.Mock(return_value=False)) as done_mock:
        await auth.stop()
        stop_feeds_mock.assert_called_once()
        done_mock.assert_called_once()
        auth._fetch_account_task.cancel.assert_called_once()
        auth._restart_task.cancel.assert_called_once()
        auth._aiohttp_session.close.assert_called_once()

        auth._aiohttp_session = None
        auth._fetch_account_task.cancel.reset_mock()
        auth._restart_task.cancel.reset_mock()
        await auth.stop()
        auth._fetch_account_task.cancel.assert_called_once()
        auth._restart_task.cancel.assert_called_once()
