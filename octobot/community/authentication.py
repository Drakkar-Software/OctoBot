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
import base64
import contextlib
import json
import time

import requests
import aiohttp

import octobot.constants as constants
import octobot.community.errors as errors
import octobot.community.identifiers_provider as identifiers_provider
import octobot.community.community_supports as community_supports
import octobot.community.feeds as community_feeds
import octobot.community.graphql_requests as graphql_requests
import octobot.community.community_user_account as community_user_account
import octobot_commons.constants as commons_constants
import octobot_commons.authentication as authentication


class CommunityAuthentication(authentication.Authenticator):
    """
    Authentication utility
    """
    ALLOWED_TIME_DELAY = 1 * commons_constants.MINUTE_TO_SECONDS
    LOGIN_TIMEOUT = 20
    BOT_NOT_FOUND_RETRY_DELAY = 1
    AUTHORIZATION_HEADER = "authorization"
    SESSION_HEADER = "X-Session"
    GQL_AUTHORIZATION_HEADER = "Authorization"

    def __init__(self, authentication_url, feed_url, config=None):
        super().__init__()
        self.authentication_url = authentication_url
        self.feed_url = feed_url
        self.edited_config = config
        self.initialized_event = None

        self.user_account = community_user_account.CommunityUserAccount()
        self._community_token = self._get_encoded_community_token()
        self._auth_token = None
        self._session = requests.Session()
        self._aiohttp_session = None
        self._cache = {}
        self._fetch_account_task = None
        self._restart_task = None
        self._community_feed = None
        self._login_completed = None

        self._update_sessions_headers()

    def get_logged_in_email(self):
        if self.user_account.has_user_data():
            return self.user_account.get_email()
        raise authentication.AuthenticationRequired()

    def get_packages(self):
        try:
            #TODO
            return []
        except json.JSONDecodeError:
            return []

    async def update_supports(self):
        self._update_supports(200, self._supports_mock())
        return
        # TODO use real support fetch when implemented
        async with self._aiohttp_session.get("supports_url") as resp:
            self._update_supports(resp.status, await resp.json())

    def is_initialized(self):
        return self._fetch_account_task is not None and self._fetch_account_task.done()

    def init_account(self):
        self.initialized_event = asyncio.Event()
        self._fetch_account_task = asyncio.create_task(self._auth_and_fetch_account())

    async def _ensure_bot_device(self):
        try:
            self.user_account.get_selected_bot_device_uuid()
        except errors.NoBotDeviceError:
            bot_id = self.user_account.get_bot_id(self.user_account.get_selected_bot_raw_data())
            self.logger.info(f"Creating a bot device for current bot with id: {bot_id} (no associated bot device)")
            self.user_account.set_selected_bot_device_raw_data(await self._create_new_bot_device(bot_id))

    async def _create_community_feed_if_necessary(self) -> bool:
        if self._community_feed is None:
            self._community_feed = community_feeds.community_feed_factory(
                self.feed_url,
                self,
                constants.COMMUNITY_FEED_DEFAULT_TYPE
            )
            self._community_feed.associated_gql_bot_id = self.user_account.gql_bot_id
            return True
        return False

    async def _ensure_init_community_feed(self):
        await self._create_community_feed_if_necessary()
        if not self._community_feed.is_connected() and self._community_feed.can_connect():
            if self.initialized_event is not None and not self.initialized_event.is_set():
                await asyncio.wait_for(self.initialized_event.wait(), self.LOGIN_TIMEOUT)
            if not self.is_logged_in():
                raise authentication.AuthenticationRequired("You need to be authenticated to be able to "
                                                            "connect to signals")
            await self._ensure_bot_device()
            await self._community_feed.start()

    async def register_feed_callback(self, channel_type, callback, identifier=None):
        try:
            await self._ensure_init_community_feed()
            await self._community_feed.register_feed_callback(channel_type, callback, identifier=identifier)
        except errors.BotError as e:
            self.logger.error(f"Impossible to connect to community signals: {e}")

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

    async def async_graphql_query(self, query, query_name, variables=None, operation_name=None,
                                  expected_code=None, allow_retry_on_expired_token=True):
        try:
            async with self._authenticated_qgl_session() as session:
                t0 = time.time()
                self.logger.debug(f"starting {query_name} graphql query")
                resp = await session.post(
                    f"{identifiers_provider.IdentifiersProvider.GQL_BACKEND_API_URL}",
                    json=self._build_gql_request_body(query, variables, operation_name)
                )
                self.logger.debug(f"graphql query {query_name} done in {time.time() - t0} seconds")
                if resp.status == 401:
                    # access token expired
                    raise authentication.AuthenticationRequired
                json_resp = await resp.json()
                if errs := json_resp.get("errors"):
                    raise errors.RequestError(f"Error when running graphql query [{query_name}]: "
                                              f"{errs[0].get('message', errs)}")
                if expected_code is None or resp.status == expected_code:
                    return json_resp["data"][query_name]
                raise errors.StatusCodeRequestError(
                    f"Wrong status code running graphql query [{query_name}]: expected {expected_code}, "
                    f"got: {resp.status}. Text: {await resp.text()}")
        except authentication.AuthenticationRequired:
            if allow_retry_on_expired_token:
                return await self.async_graphql_query(
                    query, query_name, variables=variables, operation_name=operation_name,
                    expected_code=expected_code, allow_retry_on_expired_token=False)
            else:
                raise

    @contextlib.asynccontextmanager
    async def _authenticated_qgl_session(self):
        await self.gql_login_if_required()
        session = self.get_aiohttp_session()
        try:
            session.headers[self.GQL_AUTHORIZATION_HEADER] = f"Bearer {self.user_account.gql_access_token}"
            yield session
        except authentication.AuthenticationRequired:
            # reset token to force re-login
            self.user_account.gql_access_token = None
            raise
        finally:
            if self.GQL_AUTHORIZATION_HEADER in session.headers:
                session.headers.pop(self.GQL_AUTHORIZATION_HEADER)

    async def wait_for_login_if_processing(self):
        if self.user_account.has_user_data() is None and self._login_completed is not None:
            # ensure login details have been fetched
            await asyncio.wait_for(self._login_completed.wait(), self.LOGIN_TIMEOUT)

    async def gql_login_if_required(self):
        await self.wait_for_login_if_processing()
        if self.user_account.gql_access_token is not None:
            return
        try:
            token = self.user_account.get_graph_token()
        except KeyError as e:
            raise authentication.AuthenticationRequired("Authentication required") from e
        async with self.get_aiohttp_session().post(
                identifiers_provider.IdentifiersProvider.GQL_AUTH_URL, json={"key": token}
        ) as resp:
            json_resp = await resp.json()
            if resp.status == 200:
                self.user_account.gql_access_token = json_resp["access_token"]
                self.user_account.gql_user_id = json_resp["user_id"]
            else:
                raise authentication.FailedAuthentication(f"Failed to authenticate to graphql server: "
                                                          f"status: {resp.status}, data: {json_resp}")

    def can_authenticate(self):
        return "todo" not in self.authentication_url

    def must_be_authenticated_through_authenticator(self):
        return constants.IS_CLOUD_ENV

    async def login(self, email, password):
        self._ensure_email(email)
        self._ensure_community_url()
        self._reset_tokens()
        params = {
            "email": email,
            "password": password,
        }
        resp = self._session.post(self.authentication_url, json=params)
        try:
            self._handle_auth_result(resp.status_code, resp.json(), resp.headers)
        except json.JSONDecodeError as e:
            raise authentication.FailedAuthentication(e)
        if self.is_logged_in():
            await self.update_supports()
            await self.update_selected_bot()

    async def update_selected_bot(self):
        self.user_account.flush_bot_details()
        await self._load_bot_if_selected()
        if not self.user_account.has_selected_bot_data():
            self.logger.info(self.user_account.NO_SELECTED_BOT_DESC)

    async def _load_bot_if_selected(self):
        # 1. use user selected bot id if any
        if saved_uuid := self._get_saved_gql_bot_id():
            try:
                await self.select_bot(saved_uuid)
                return
            except errors.BotNotFoundError:
                # proceed to 2.
                pass
        # 2. fetch all user bots and create one if none, otherwise ask use for which one to use
        await self.load_user_bots()
        if len(self.user_account.get_all_user_bots_raw_data()) == 0:
            await self.select_bot(
                self.user_account.get_bot_id(
                    await self.create_new_bot()
                )
            )
        # more than one possible bot, can't auto-select one

    async def select_bot(self, bot_id):
        fetched_bot = await self._fetch_bot(bot_id)
        if fetched_bot is None:
            # retry after some time, if still None, there is an issue
            await asyncio.sleep(self.BOT_NOT_FOUND_RETRY_DELAY)
            fetched_bot = await self._fetch_bot(bot_id)
        if fetched_bot is None:
            raise errors.BotNotFoundError(f"Can't find bot with id: {bot_id}")
        self.user_account.set_selected_bot_raw_data(fetched_bot)
        bot_name = self.user_account.get_bot_name_or_id(self.user_account.get_selected_bot_raw_data())
        self.logger.debug(f"Selected bot '{bot_name}'")
        self.user_account.gql_bot_id = bot_id
        self._save_gql_bot_id(self.user_account.gql_bot_id)
        await self.on_new_bot_select()

    async def load_user_bots(self):
        self.user_account.set_all_user_bots_raw_data(await self._fetch_bots())

    async def on_new_bot_select(self):
        await self._update_feed_device_uuid_if_necessary()

    async def _fetch_bots(self):
        query, variables = graphql_requests.select_bots_query()
        return await self.async_graphql_query(query, "bots", variables=variables, expected_code=200)

    async def _fetch_bot(self, bot_id):
        query, variables = graphql_requests.select_bot_query(bot_id)
        return await self.async_graphql_query(query, "bot", variables=variables, expected_code=200)

    async def create_new_bot(self):
        await self.gql_login_if_required()
        query, variables = graphql_requests.create_bot_query(not constants.IS_CLOUD_ENV)
        return await self.async_graphql_query(query, "createBot", variables=variables, expected_code=200)

    async def _create_new_bot_device(self, bot_id):
        query, variables = graphql_requests.create_bot_device_query(bot_id)
        await self.async_graphql_query(query, "createBotDevice", variables=variables, expected_code=200)
        # issue with createBotDevice not always returning the created device, fetch bot again to fetch device with it
        return await self._fetch_bot(bot_id)

    async def _update_feed_device_uuid_if_necessary(self):
        if self._community_feed is None:
            # only create a new community feed if necessary
            return
        if self._community_feed.associated_gql_bot_id != self.user_account.gql_bot_id:
            # only device id changed, need to refresh uuid. Otherwise, it means that no feed was started with a
            # different uuid, no need to update
            # reset restart task if running
            if self._restart_task is not None and not self._restart_task.done():
                self._restart_task.cancel()
                self._community_feed.remove_device_details()
            if self._community_feed.is_connected() or not self._community_feed.can_connect():
                await self._ensure_bot_device()
                self._restart_task = asyncio.create_task(self._community_feed.restart())

    def logout(self):
        """
        logout and remove saved auth details
        Warning: also call stop_feeds if feeds have to be stopped (not done here to keep method sync)
        """
        self._reset_tokens()
        self.clear_cache()
        self.remove_login_detail()
        for task in (self._restart_task, self._fetch_account_task):
            if task is not None and not task.done():
                task.cancel()
        self._restart_task = self._fetch_account_task = None
        if self._community_feed is not None:
            self._community_feed.remove_device_details()

    async def stop_feeds(self):
        if self._community_feed is not None and self._community_feed.is_connected():
            await self._community_feed.stop()

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
        self.user_account.flush()
        self._save_login_token("")
        self._save_gql_bot_id("")
        self.logger.debug("Removed community login data")

    def get_aiohttp_session(self):
        if self._aiohttp_session is None:
            self._aiohttp_session = aiohttp.ClientSession()
            self._update_sessions_headers()
        return self._aiohttp_session

    async def stop(self):
        self.logger.debug("Stopping ...")
        await self.stop_feeds()
        if self._fetch_account_task is not None and not self._fetch_account_task.done():
            self._fetch_account_task.cancel()
        if self._restart_task is not None and not self._restart_task.done():
            self._restart_task.cancel()
        if self._aiohttp_session is not None:
            await self._aiohttp_session.close()
        self.logger.debug("Stopped")

    def _update_supports(self, resp_status, json_data):
        if resp_status == 200:
            self.user_account.supports = community_supports.CommunitySupports.from_community_dict(json_data)
            self.logger.debug(f"Fetched supports data.")
        else:
            self.logger.error(f"Error when fetching community support, "
                              f"error code: {resp_status}")

    def _supports_mock(self):
        return {
            "data": {
                "attributes": {
                    "support_role": self._get_support_role()
                }
            }
        }

    def _get_support_role(self):
        try:
            if self.user_account.get_has_donated():
                return community_supports.CommunitySupports.OCTOBOT_DONOR_ROLE
        except KeyError:
            pass
        return community_supports.CommunitySupports.DEFAULT_SUPPORT_ROLE

    async def _auth_and_fetch_account(self):
        try:
            await self._async_try_auto_login()
            if not self.is_logged_in():
                return
            await self.update_supports()
            await self.update_selected_bot()
        except authentication.UnavailableError as e:
            self.logger.exception(e, True, f"Error when fetching community supports, "
                                           f"please check your internet connection.")
        except Exception as e:
            self.logger.exception(e, True, f"Error when fetching community supports: {e}({e.__class__.__name__})")
        finally:
            self.initialized_event.set()

    def _save_login_token(self, value):
        self._save_value_in_config(constants.CONFIG_COMMUNITY_TOKEN, value)

    def _save_gql_bot_id(self, gql_bot_id):
        self._save_value_in_config(constants.CONFIG_COMMUNITY_BOT_ID, gql_bot_id)

    def _get_saved_token(self):
        return self._get_value_in_config(constants.CONFIG_COMMUNITY_TOKEN)

    def _get_saved_gql_bot_id(self):
        return self._get_value_in_config(constants.CONFIG_COMMUNITY_BOT_ID)

    def _save_value_in_config(self, key, value):
        if self.edited_config is not None:
            if constants.CONFIG_COMMUNITY not in self.edited_config.config:
                self.edited_config.config[constants.CONFIG_COMMUNITY] = {}
            self.edited_config.config[constants.CONFIG_COMMUNITY][key] = value
            self.edited_config.save()

    def _get_value_in_config(self, key):
        if self.edited_config is not None:
            try:
                return self.edited_config.config[constants.CONFIG_COMMUNITY][key]
            except KeyError:
                return ""
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
            with self._session.get(f"{identifiers_provider.IdentifiersProvider.BACKEND_API_URL}/account") as resp:
                self._handle_auth_result(resp.status_code, resp.json(), resp.headers)

    async def _async_check_auth(self):
        if self._login_completed is None:
            self._login_completed = asyncio.Event()
        self._login_completed.clear()
        with self._auth_context():
            async with self.get_aiohttp_session().get(
                    f"{identifiers_provider.IdentifiersProvider.BACKEND_API_URL}/account"
            ) as resp:
                try:
                    self._handle_auth_result(resp.status, await resp.json(), resp.headers)
                finally:
                    self._login_completed.set()

    def _ensure_email(self, email):
        if constants.USER_ACCOUNT_EMAIL is not None and email != constants.USER_ACCOUNT_EMAIL:
            raise authentication.AuthenticationError("The given email doesn't match the expected user email.")

    def _ensure_community_url(self):
        if not self.can_authenticate():
            raise authentication.UnavailableError("Community url required")

    def _handle_auth_result(self, status_code, json_resp, reps_headers):
        if status_code == 200 and json_resp is not None:
            if new_token := reps_headers.get(self.SESSION_HEADER):
                self._auth_token = new_token
                self._save_login_token(self._auth_token)
                self._update_sessions_headers()
            self.user_account.set_profile_raw_data(json_resp)
            return
        elif json_resp is None and status_code < 500:
            if json_resp is not None:
                if error := json_resp.get("error", None):
                    raise authentication.FailedAuthentication(f"Error when authenticating: {error['message']}")
            raise authentication.FailedAuthentication("Invalid username or password." if self._auth_token is None else
                                                      "Token expired. Please re-login to your community account")
        elif json_resp and status_code == 400:
            if error := json_resp.get("error", None):
                if "logged in" in error['message'].lower():
                    raise authentication.FailedAuthentication(f"Error when authenticating, please "
                                                              f"re-login to your community account")
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
        self.user_account.flush()
        self._session.headers.pop(CommunityAuthentication.SESSION_HEADER, None)
        if self._aiohttp_session is not None:
            self._aiohttp_session.headers.pop(CommunityAuthentication.SESSION_HEADER, None)

    @staticmethod
    def _get_encoded_community_token():
        return base64.encodebytes(identifiers_provider.IdentifiersProvider.BACKEND_PUBLIC_TOKEN.encode()).decode().strip()
