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
import asyncio
import contextlib
import json
import time
import requests
import aiohttp

import octobot.constants as constants
import octobot.community.community_supports as community_supports
import octobot_commons.constants as commons_constants
import octobot_commons.authentication as authentication


class CommunityAuthentication(authentication.Authenticator):
    """
    Authentication utility
    """
    ALLOWED_TIME_DELAY = 1 * commons_constants.MINUTE_TO_SECONDS
    AUTHORIZATION_HEADER = "Authorization"
    IDENTIFIER_HEADER = "Identifier"
    REFRESH_TOKEN = "refresh_token"
    GRANT_TYPE = "grant_type"

    def __init__(self, authentication_url, username=None, password=None, config=None):
        super().__init__()
        self.authentication_url = authentication_url
        self.refresh_token = None
        self.edited_config = config
        self.identifier = None
        self.supports = community_supports.CommunitySupports()

        self._auth_token = None
        self._expire_at = None
        self._session = requests.Session()
        self._aiohttp_session = None
        self._cache = {}
        self._fetch_supports_task = None

        if username and password:
            self.login(username, password)

    def get_logged_in_email(self):
        return self.get(constants.OCTOBOT_COMMUNITY_ACCOUNT_URL).json()["data"]["attributes"]["email"]

    def get_packages(self):
        return self.get(constants.OCTOBOT_COMMUNITY_PACKAGES_URL).json()["data"]

    def update_supports(self):
        resp = self.get(constants.OCTOBOT_COMMUNITY_SUPPORTS_URL)
        self._update_supports(resp.status_code, resp.json())

    def is_initialized(self):
        return self._fetch_supports_task is not None and self._fetch_supports_task.done()

    def init_supports(self):
        self.initialized_event = asyncio.Event()
        self._fetch_supports_task = asyncio.create_task(self._auth_and_fetch_supports())

    def can_authenticate(self):
        return "todo" not in self.authentication_url

    def login(self, username, password):
        self._ensure_community_url()
        self._reset_tokens()
        params = {
            "username": username,
            "password": password,
            "grant_type": "password",
        }
        resp = requests.post(self.authentication_url, params=params)
        try:
            self._handle_auth_result(resp.status_code, resp.json())
        except json.JSONDecodeError as e:
            raise authentication.FailedAuthentication(e)
        if self.is_logged_in():
            self.update_supports()

    def logout(self):
        self._reset_tokens()
        self.clear_cache()
        self.remove_login_detail()

    def clear_cache(self):
        self._cache = {}

    @authentication.authenticated
    def get(self, url, params=None, allow_cache=False, **kwargs):
        if allow_cache:
            if url not in self._cache:
                self._cache[url] = self._session.get(url, params=params, **kwargs)
            return self._cache[url]
        else:
            return self._session.get(url, params=params, **kwargs)

    @authentication.authenticated
    def post(self, url, data=None, json=None, **kwargs):
        return self._session.post(url, data=data, json=json, **kwargs)

    def is_logged_in(self):
        return bool(self._auth_token and self.refresh_token and self._expire_at)

    def ensure_token_validity(self):
        if not self.is_logged_in():
            # try to login with saved token if available
            self._try_auto_login()
            if not self.is_logged_in():
                # still not logged in: raise
                raise authentication.AuthenticationRequired()
        if time.time() >= self._expire_at:
            self._refresh_auth()

    def remove_login_detail(self):
        self._save_login_token("")
        self.logger.debug("Removed community login data")

    def get_aiohttp_session(self, should_update_headers=True):
        if self._aiohttp_session is None:
            self._aiohttp_session = aiohttp.ClientSession()
            if should_update_headers:
                self._update_aiohttp_session_headers()
        return self._aiohttp_session

    async def stop(self):
        if self.is_initialized():
            self._fetch_supports_task.cancel()
        if self._aiohttp_session is not None:
            await self._aiohttp_session.close()

    def _update_supports(self, resp_status, json_data):
        if resp_status == 200:
            self.supports = community_supports.CommunitySupports.from_community_dict(json_data)
            self.logger.debug(f"Fetched supports data.")
        else:
            self.logger.error(f"Error when fetching community support, "
                              f"error code: {resp_status}")

    async def _auth_and_fetch_supports(self):
        try:
            await self._async_try_auto_login()
            if not self.is_logged_in():
                return
            async with self._aiohttp_session.get(constants.OCTOBOT_COMMUNITY_SUPPORTS_URL) as resp:
                self._update_supports(resp.status, await resp.json())
        except Exception as e:
            self.logger.exception(e, True, f"Error when fetching community supports: {e})")
        finally:
            self.initialized_event.set()

    def _save_login_token(self, value):
        if self.edited_config is not None:
            self.edited_config.config[commons_constants.CONFIG_COMMUNITY_TOKEN] = value
            self.edited_config.save()

    def get_token(self):
        if self.edited_config is not None:
            return self.edited_config.config.get(commons_constants.CONFIG_COMMUNITY_TOKEN, "")
        return None

    def _try_auto_login(self):
        token = self.get_token()
        if token:
            # try to login using config data
            self._auto_login(token)

    async def _async_try_auto_login(self):
        token = self.get_token()
        if token:
            # try to login using config data
            await self._async_auto_login(token)

    @contextlib.contextmanager
    def _auth_handler(self, token):
        self.refresh_token = token
        try:
            yield
        except authentication.FailedAuthentication as e:
            self.logger.warning(f"Invalid authentication details, please re-authenticate. {e}")
            self.logout()
        except authentication.UnavailableError:
            raise
        except Exception as e:
            self.logger.exception(e, True, f"Error when trying to refresh community login: {e}")

    def _auto_login(self, token):
        with self._auth_handler(token):
            self._refresh_auth()

    async def _async_auto_login(self, token):
        with self._auth_handler(token):
            await self._async_refresh_auth()

    @contextlib.contextmanager
    def _auth_context(self):
        params = {
            CommunityAuthentication.REFRESH_TOKEN: self.refresh_token,
            CommunityAuthentication.GRANT_TYPE: CommunityAuthentication.REFRESH_TOKEN,
        }
        self._ensure_community_url()
        try:
            yield params
        except requests.ConnectionError as e:
            raise authentication.UnavailableError from e

    def _refresh_auth(self):
        with self._auth_context() as params:
            resp = requests.post(self.authentication_url, params=params)
            self._handle_auth_result(resp.status_code, resp.json())

    async def _async_refresh_auth(self):
        with self._auth_context() as params:
            async with self.get_aiohttp_session(should_update_headers=False).post(self.authentication_url,
                                                                                  params=params) as resp:
                self._handle_auth_result(resp.status, await resp.json())

    def _ensure_community_url(self):
        if not self.can_authenticate():
            raise authentication.UnavailableError("Community url required")

    def _handle_auth_result(self, status_code, json_resp):
        if status_code == 200:
            self._auth_token = json_resp["access_token"]
            self.refresh_token = json_resp[CommunityAuthentication.REFRESH_TOKEN]
            self._expire_at = time.time() + json_resp["expires_in"] - CommunityAuthentication.ALLOWED_TIME_DELAY
            self._refresh_session()
            self._save_login_token(self.refresh_token)
        elif status_code == 400:
            raise authentication.FailedAuthentication("Invalid username or password.")
        else:
            raise authentication.AuthenticationError(f"Error code: {status_code}")

    def _refresh_session(self):
        self._session.headers.update(self._get_headers())

        if self._aiohttp_session is not None:
            self._update_aiohttp_session_headers()

    def _update_aiohttp_session_headers(self):
        self._aiohttp_session.headers.update(self._get_headers())

    def _get_headers(self):
        headers = {
            CommunityAuthentication.AUTHORIZATION_HEADER: f"Bearer {self._auth_token}"
        }
        if self.identifier is not None:
            headers[CommunityAuthentication.IDENTIFIER_HEADER] = self.identifier
        return headers

    def _reset_tokens(self):
        self._auth_token = None
        self.refresh_token = None
        self._expire_at = None
        self._session.headers.pop(CommunityAuthentication.AUTHORIZATION_HEADER, None)
