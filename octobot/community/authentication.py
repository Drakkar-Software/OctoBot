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

import octobot_commons.constants as commons_constants


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

    def __init__(self, authentication_url, username=None, password=None):
        self.authentication_url = authentication_url

        self._auth_token = None
        self._refresh_token = None
        self._expire_at = None
        self._session = requests.Session()

        if None not in (username, password):
            self.login(username, password)

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

    @authenticated
    def get(self, url, params=None, **kwargs):
        return self._session.get(url, params=params, **kwargs)

    @authenticated
    def post(self, url, data=None, json=None, **kwargs):
        return self._session.post(url, data=data, json=json, **kwargs)

    def ensure_token_validity(self):
        if None in (self._auth_token, self._refresh_token, self._expire_at):
            raise AuthenticationRequired()
        if time.time() >= self._expire_at:
            self._refresh_auth()

    def _refresh_auth(self):
        params = {
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
        }
        resp = requests.post(self.authentication_url, params=params)
        self._handle_auth_result(resp)

    def _handle_auth_result(self, resp):
        if resp.status_code == 200:
            json_resp = resp.json()
            self._auth_token = json_resp["access_token"]
            self._refresh_token = json_resp["refresh_token"]
            self._expire_at = time.time() + json_resp["expires_in"] - CommunityAuthentication.ALLOWED_TIME_DELAY
            self._refresh_session()
        elif resp.status_code == 400:
            raise FailedAuthentication("Invalid login on password.")
        else:
            raise FailedAuthentication(f"Error code: {resp.status_code}")

    def _refresh_session(self):
        self._session.headers.update(
            {
                CommunityAuthentication.AUTHORIZATION_HEADER: f"Bearer {self._auth_token}"
            }
        )

    def _reset_tokens(self):
        self._auth_token = None
        self._refresh_token = None
        self._expire_at = None
        self._session.headers.pop(CommunityAuthentication.AUTHORIZATION_HEADER, None)


class FailedAuthentication(Exception):
    """
    Raised upon authentication failure
    """


class AuthenticationRequired(Exception):
    """
    Raised when an authentication is required
    """
