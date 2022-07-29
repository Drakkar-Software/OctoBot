#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2021 Drakkar-Software, All rights reserved.
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
import base64
import contextlib
import json
import requests
import aiohttp

import octobot.constants as constants
import octobot.community.community_supports as community_supports
import octobot.community.feeds as community_feeds
import octobot_commons.constants as commons_constants
import octobot_commons.authentication as authentication


class CommunityAuthentication(authentication.Authenticator):
    """
    Authentication utility
    """
    ALLOWED_TIME_DELAY = 1 * commons_constants.MINUTE_TO_SECONDS
    LOGIN_TIMEOUT = 20
    AUTHORIZATION_HEADER = "authorization"
    SESSION_HEADER = "X-Session"
    GQL_AUTHORIZATION_HEADER = "Authorization"
    USER_DATA_CONTENT = "content"

    def __init__(self, authentication_url, feed_url, config=None):
        super().__init__()
        self.authentication_url = authentication_url
        self.feed_url = feed_url
        self.edited_config = config
        self.supports = community_supports.CommunitySupports()
        self.initialized_event = None

        self._profile_raw_data = None
        self._community_token = self._get_encoded_community_token()
        self._gql_access_token = None
        self.gql_user_id = None
        self._auth_token = None
        self._session = requests.Session()
        self._aiohttp_session = None
        self._cache = {}
        self._fetch_supports_task = None
        self._fetch_device_uuid_task = None
        self._community_feed = None
        self._login_completed = None

        self._update_sessions_headers()

    def get_logged_in_email(self):
        if self._profile_raw_data:
            return self._profile_raw_data["email"]
        raise authentication.AuthenticationRequired()

    def get_packages(self):
        try:
            #TODO
            return []
            return self.get(constants.OCTOBOT_COMMUNITY_PACKAGES_URL).json()["data"]
        except json.JSONDecodeError:
            return []

    async def update_supports(self):
        self._update_supports(200, self._supports_mock())
        return
        # TODO use real support fetch when implemented
        async with self._aiohttp_session.get(constants.OCTOBOT_COMMUNITY_SUPPORTS_URL) as resp:
            self._update_supports(resp.status, await resp.json())

    def is_initialized(self):
        return self._fetch_supports_task is not None and self._fetch_supports_task.done()

    def init_supports(self):
        self.initialized_event = asyncio.Event()
        self._fetch_supports_task = asyncio.create_task(self._auth_and_fetch_supports())

    def _create_community_feed_if_necessary(self) -> bool:
        if self._community_feed is None:
            self._community_feed = community_feeds.community_feed_factory(
                self.feed_url,
                self,
                constants.COMMUNITY_FEED_DEFAULT_TYPE
            )
            return True
        return False

    async def _ensure_init_community_feed(self):
        if self._create_community_feed_if_necessary():
            await self._community_feed.start()

    async def _ensure_community_feed_device_uuid(self):
        self._create_community_feed_if_necessary()
        await self._community_feed.get_or_fetch_device_uuid()

    async def register_feed_callback(self, channel_type, callback, identifier=None):
        await self._ensure_init_community_feed()
        await self._community_feed.register_feed_callback(channel_type, callback, identifier=identifier)

    async def send(self, message, channel_type, identifier=None):
        """
        Sends a message
        """
        await self._ensure_init_community_feed()
        await self._community_feed.send(message, channel_type, identifier)

    @staticmethod
    def _build_gql_request_body(query, variables, operation_name):
        request_body = {
            "query": query
        }
        if variables is not None:
            request_body["variables"] = variables
        if operation_name is not None:
            request_body["operationName"] = operation_name
        return request_body

    async def async_graphql_query(self, query, variables=None, operation_name=None, allow_retry_on_expired_token=True):
        try:
            async with self._authenticated_qgl_session() as session:
                resp = await session.post(
                    f"{constants.COMMUNITY_GQL_BACKEND_API_URL}",
                    json=self._build_gql_request_body(query, variables, operation_name)
                )
                if resp.status == 401:
                    # access token expired
                    raise authentication.AuthenticationRequired
                json_resp = await resp.json()
                if errors := json_resp.get("errors"):
                    raise RuntimeError(f"Error when running graphql query: {errors[0].get('message', errors)}")
                return resp
        except authentication.AuthenticationRequired:
            if allow_retry_on_expired_token:
                return await self.async_graphql_query(query, variables=variables, operation_name=operation_name,
                                                      allow_retry_on_expired_token=False)
            else:
                raise

    @contextlib.asynccontextmanager
    async def _authenticated_qgl_session(self):
        await self.gql_login_if_required()
        session = self.get_aiohttp_session()
        try:
            session.headers[self.GQL_AUTHORIZATION_HEADER] = f"Bearer {self._gql_access_token}"
            yield session
        except authentication.AuthenticationRequired:
            # reset token to force re-login
            self._gql_access_token = None
            raise
        finally:
            session.headers.pop(self.GQL_AUTHORIZATION_HEADER)

    async def wait_for_login_if_processing(self):
        if self._profile_raw_data is None and self._login_completed is not None:
            # ensure login details have been fetched
            await asyncio.wait_for(self._login_completed.wait(), self.LOGIN_TIMEOUT)

    async def gql_login_if_required(self):
        await self.wait_for_login_if_processing()
        try:
            token = self._profile_raw_data[self.USER_DATA_CONTENT]["graph_token"]
        except KeyError:
            raise authentication.AuthenticationRequired("Authentication required")
        async with self.get_aiohttp_session().get(constants.COMMUNITY_GQL_AUTH_URL, json={"key": token}) as resp:
            json_resp = await resp.json()
            if resp.status == 200:
                self._gql_access_token = json_resp["access_token"]
                self.gql_user_id = json_resp["user_id"]
            else:
                raise authentication.FailedAuthentication(f"Failed to authenticate to graphql server: "
                                                          f"status: {resp.status}, data: {json_resp}")

    def can_authenticate(self):
        return "todo" not in self.authentication_url

    async def login(self, username, password):
        self._ensure_community_url()
        self._reset_tokens()
        params = {
            "email": username,
            "password": password,
        }
        resp = self._session.post(self.authentication_url, json=params)
        try:
            self._handle_auth_result(resp.status_code, resp.json(), resp.headers)
        except json.JSONDecodeError as e:
            raise authentication.FailedAuthentication(e)
        if self.is_logged_in():
            await self.update_supports()
            await self._update_feed_device_uuid()

    async def _update_feed_device_uuid(self):
        if self._fetch_device_uuid_task is None or self._fetch_device_uuid_task.done():
            self._fetch_device_uuid_task = asyncio.create_task(self._ensure_community_feed_device_uuid())

    def logout(self):
        self._reset_tokens()
        self.clear_cache()
        self.remove_login_detail()
        if self._fetch_device_uuid_task is not None and not self._fetch_device_uuid_task.done():
            self._fetch_device_uuid_task.cancel()
            self._fetch_device_uuid_task = None
        self._create_community_feed_if_necessary()
        self._community_feed.remove_device_details()
        # TODO stop community feed if running and restart it on login ?

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
    def download(self, url, target_file, params=None, **kwargs):
        with self._session.get(url, stream=True, params=params, **kwargs) as r:
            r.raise_for_status()
            with open(target_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return target_file

    @authentication.authenticated
    def post(self, url, data=None, json=None, **kwargs):
        return self._session.post(url, data=data, json=json, **kwargs)

    def is_logged_in(self):
        return bool(self._auth_token)

    def ensure_token_validity(self):
        if not self.is_logged_in():
            # try to login with saved token if available
            self._try_auto_login()
            if not self.is_logged_in():
                # still not logged in: raise
                raise authentication.AuthenticationRequired()

    def remove_login_detail(self):
        self._profile_raw_data = None
        self._save_login_token("")
        self.logger.debug("Removed community login data")

    def get_aiohttp_session(self):
        if self._aiohttp_session is None:
            self._aiohttp_session = aiohttp.ClientSession()
            self._update_sessions_headers()
        return self._aiohttp_session

    async def stop(self):
        if self.is_initialized():
            self._fetch_supports_task.cancel()
        if self._fetch_device_uuid_task is not None and not self._fetch_device_uuid_task.done():
            self._fetch_device_uuid_task.cancel()
        if self._aiohttp_session is not None:
            await self._aiohttp_session.close()

    def _update_supports(self, resp_status, json_data):
        if resp_status == 200:
            self.supports = community_supports.CommunitySupports.from_community_dict(json_data)
            self.logger.debug(f"Fetched supports data.")
        else:
            self.logger.error(f"Error when fetching community support, "
                              f"error code: {resp_status}")

    def _supports_mock(self):
        return {
            "data": {
                "attributes": {
                    "support_role": "OctoBot tester"
                }
            }
        }

    async def _auth_and_fetch_supports(self):
        try:
            await self._async_try_auto_login()
            if not self.is_logged_in():
                return
            await self.update_supports()
        except Exception as e:
            self.logger.exception(e, True, f"Error when fetching community supports: {e})")
        finally:
            self.initialized_event.set()

    def _save_login_token(self, value):
        if self.edited_config is not None:
            self.edited_config.config[commons_constants.CONFIG_COMMUNITY_TOKEN] = value
            self.edited_config.save()

    def _get_saved_token(self):
        if self.edited_config is not None:
            return self.edited_config.config.get(commons_constants.CONFIG_COMMUNITY_TOKEN, "")
        return None

    def _try_auto_login(self):
        self._auth_token = self._get_saved_token()
        if self._auth_token:
            # try to login using config data
            self._auto_login()

    async def _async_try_auto_login(self):
        self._auth_token = self._get_saved_token()
        if self._auth_token:
            # try to login using config data
            await self._async_auto_login()

    @contextlib.contextmanager
    def _auth_handler(self):
        try:
            yield
        except authentication.FailedAuthentication as e:
            self.logger.warning(f"Invalid authentication details, please re-authenticate. {e}")
            self.logout()
        except authentication.UnavailableError:
            raise
        except Exception as e:
            self.logger.exception(e, True, f"Error when trying to refresh community login: {e}")

    def _auto_login(self):
        with self._auth_handler():
            self._check_auth()

    async def _async_auto_login(self):
        with self._auth_handler():
            await self._async_check_auth()

    @contextlib.contextmanager
    def _auth_context(self):
        self._ensure_community_url()
        try:
            yield
        except (requests.ConnectionError, aiohttp.ClientConnectionError) as e:
            raise authentication.UnavailableError from e

    def _check_auth(self):
        with self._auth_context():
            with self._session.get(f"{constants.COMMUNITY_BACKEND_API_URL}/account") as resp:
                self._handle_auth_result(resp.status_code, resp.json(), resp.headers)

    async def _async_check_auth(self):
        if self._login_completed is None:
            self._login_completed = asyncio.Event()
        self._login_completed.clear()
        with self._auth_context():
            async with self.get_aiohttp_session().get(f"{constants.COMMUNITY_BACKEND_API_URL}/account") as resp:
                try:
                    self._handle_auth_result(resp.status, await resp.json(), resp.headers)
                finally:
                    self._login_completed.set()

    def _ensure_community_url(self):
        if not self.can_authenticate():
            raise authentication.UnavailableError("Community url required")

    def _handle_auth_result(self, status_code, json_resp, reps_headers):
        if status_code == 200 and json_resp is not None:
            if new_token := reps_headers.get(self.SESSION_HEADER):
                self._auth_token = new_token
                self._save_login_token(self._auth_token)
                self._update_sessions_headers()
            self._profile_raw_data = json_resp
        elif json_resp is None and status_code < 500:
            if json_resp is not None:
                if error := json_resp.get("error", None):
                    raise authentication.FailedAuthentication(f"Error when authenticating: {error['message']}")
            raise authentication.FailedAuthentication("Invalid username or password." if self._auth_token is None else
                                                      "Token expired. Please re-login to your community account")
        else:
            raise authentication.AuthenticationError(f"Error code: {status_code}")

    def _update_sessions_headers(self):
        headers = self.get_headers()
        self._session.headers.update(headers)
        if self._aiohttp_session is not None:
            self._aiohttp_session.headers.update(headers)

    def get_headers(self):
        headers = {
            CommunityAuthentication.AUTHORIZATION_HEADER: f"Basic {self._community_token}",
        }
        if self._auth_token is not None:
            headers[CommunityAuthentication.SESSION_HEADER] = self._auth_token
        return headers

    def _reset_tokens(self):
        self._auth_token = None
        self._gql_access_token = None
        self.gql_user_id = None
        self._session.headers.pop(CommunityAuthentication.SESSION_HEADER, None)
        if self._aiohttp_session is not None:
            self._aiohttp_session.headers.pop(CommunityAuthentication.SESSION_HEADER, None)

    @staticmethod
    def _get_encoded_community_token():
        return base64.encodebytes(constants.COMMUNITY_TOKEN.encode()).decode().strip()
