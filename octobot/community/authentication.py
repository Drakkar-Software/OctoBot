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
import functools
import time
import requests

import octobot.constants as constants
import octobot_commons.constants as commons_constants
import octobot_commons.logging as bot_logging


def authenticated(func):
    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        self.ensure_token_validity()
        return func(self, *args, **kwargs)
    return wrapped


class CommunityAuthentication:
    """
    Authentication utility
    """
    ALLOWED_TIME_DELAY = 1 * commons_constants.MINUTE_TO_SECONDS
    AUTHORIZATION_HEADER = "Authorization"
    IDENTIFIER_HEADER = "Identifier"
    REFRESH_TOKEN = "refresh_token"
    GRANT_TYPE = "grant_type"

    def __init__(self, authentication_url, username=None, password=None, config=None):
        self.logger = bot_logging.get_logger(self.__class__.__name__)
        self.authentication_url = authentication_url
        self.refresh_token = None
        self.edited_config = config
        self.identifier = None

        self._auth_token = None
        self._expire_at = None
        self._session = requests.Session()
        self._cache = {}

        if username and password:
            self.login(username, password)

    def get_logged_in_email(self):
        return self.get(constants.OCTOBOT_COMMUNITY_ACCOUNT_URL).json()["data"]["attributes"]["email"]

    def get_packages(self):
        return self.get(constants.OCTOBOT_COMMUNITY_PACKAGES_URL).json()["data"]

    def login(self, username, password):
        self._reset_tokens()
        params = {
            "username": username,
            "password": password,
            "grant_type": "password",
        }
        resp = requests.post(self.authentication_url, params=params)
        self._handle_auth_result(resp)

    def logout(self):
        self._reset_tokens()
        self.clear_cache()
        self.remove_login_detail()

    def clear_cache(self):
        self._cache = {}

    @authenticated
    def get(self, url, params=None, allow_cache=False, **kwargs):
        if allow_cache:
            if url not in self._cache:
                self._cache[url] = self._session.get(url, params=params, **kwargs)
            return self._cache[url]
        else:
            return self._session.get(url, params=params, **kwargs)

    @authenticated
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
                raise AuthenticationRequired()
        if time.time() >= self._expire_at:
            self._refresh_auth()

    def remove_login_detail(self):
        self._save_login_token("")
        self.logger.debug("Removed community login data")

    def _save_login_token(self, value):
        if self.edited_config is not None:
            self.edited_config.config[commons_constants.CONFIG_COMMUNITY_TOKEN] = value
            self.edited_config.save()

    def _try_auto_login(self):
        if self.edited_config is not None:
            token = self.edited_config.config.get(commons_constants.CONFIG_COMMUNITY_TOKEN, "")
            if token:
                # try to login using config data
                self._auto_login(token)

    def _auto_login(self, token):
        self.refresh_token = token
        try:
            self._refresh_auth()
        except FailedAuthentication:
            self.logout()
        except Exception as e:
            self.logger.exception(e, True, f"Error when trying to refresh community login: {e}")

    def _refresh_auth(self):
        params = {
            CommunityAuthentication.REFRESH_TOKEN: self.refresh_token,
            CommunityAuthentication.GRANT_TYPE: CommunityAuthentication.REFRESH_TOKEN,
        }
        resp = requests.post(self.authentication_url, params=params)
        self._handle_auth_result(resp)

    def _handle_auth_result(self, resp):
        if resp.status_code == 200:
            json_resp = resp.json()
            self._auth_token = json_resp["access_token"]
            self.refresh_token = json_resp[CommunityAuthentication.REFRESH_TOKEN]
            self._expire_at = time.time() + json_resp["expires_in"] - CommunityAuthentication.ALLOWED_TIME_DELAY
            self._refresh_session()
            self._save_login_token(self.refresh_token)
        elif resp.status_code == 400:
            raise FailedAuthentication("Invalid username or password.")
        else:
            raise AuthenticationError(f"Error code: {resp.status_code}")

    def _refresh_session(self):
        self._session.headers.update(
            {
                CommunityAuthentication.AUTHORIZATION_HEADER: f"Bearer {self._auth_token}",
                CommunityAuthentication.IDENTIFIER_HEADER: self.identifier
            }
        )

    def _reset_tokens(self):
        self._auth_token = None
        self.refresh_token = None
        self._expire_at = None
        self._session.headers.pop(CommunityAuthentication.AUTHORIZATION_HEADER, None)


class FailedAuthentication(Exception):
    """
    Raised upon authentication failure
    """


class AuthenticationError(Exception):
    """
    Raised upon authentication technical error, not on login/password issues
    """


class AuthenticationRequired(Exception):
    """
    Raised when an authentication is required
    """
