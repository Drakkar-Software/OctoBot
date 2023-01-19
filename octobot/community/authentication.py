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
import base64
import contextlib
import json
import time
import datetime

import requests
import aiohttp

import octobot.constants as constants
import octobot.community.errors as errors
import octobot.community.identifiers_provider as identifiers_provider
import octobot.community.community_supports as community_supports
import octobot.community.startup_info as startup_info
import octobot.community.feeds as community_feeds
import octobot.community.graphql_requests as graphql_requests
import octobot.community.community_user_account as community_user_account
import octobot_commons.constants as commons_constants
import octobot_commons.authentication as authentication
import octobot_commons.configuration as commons_configuration


def _selected_bot_update(func):
    async def wrapper(*args, **kwargs):
        self = args[0]
        await self.gql_login_if_required()
        if self._update_bot_lock is None:
            self._update_bot_lock = asyncio.Lock()
        async with self._update_bot_lock:
            self.logger.debug(f"@selected_bot_update: entering {func.__name__}")
            updated_bot = await func(*args, **kwargs)
        self.logger.debug(f"@selected_bot_update: exited {func.__name__}")
        self.user_account.set_selected_bot_raw_data(updated_bot)
        return updated_bot

    return wrapper


class CommunityAuthentication(authentication.Authenticator):
    """
    Authentication utility
    """
    ALLOWED_TIME_DELAY = 1 * commons_constants.MINUTE_TO_SECONDS
    NEW_ACCOUNT_INITIALIZE_TIMEOUT = 1 * commons_constants.MINUTE_TO_SECONDS
    LOGIN_TIMEOUT = 20
    BOT_NOT_FOUND_RETRY_DELAY = 1
    AUTHORIZATION_HEADER = "authorization"
    SESSION_HEADER = "X-Session"
    GQL_AUTHORIZATION_HEADER = "Authorization"

    def __init__(self, feed_url, config=None):
        super().__init__()
        self.authentication_url = identifiers_provider.IdentifiersProvider.BACKEND_AUTH_URL
        self.feed_url = feed_url
        self.edited_config = config
        self.initialized_event = None

        self.user_account = community_user_account.CommunityUserAccount()
        self._community_token = self._get_encoded_community_token()
        self._auth_token = None
        self._backend_session = requests.Session()
        self._aiohttp_gql_session = None
        self._aiohttp_backend_session = None
        self._fetch_account_task = None
        self._restart_task = None
        self._community_feed = None
        self._login_completed = None
        self._update_bot_lock = None

        self._update_sessions_headers()

    @staticmethod
    def create(configuration: commons_configuration.Configuration):
        return CommunityAuthentication.instance(
            identifiers_provider.IdentifiersProvider.FEED_URL,
            config=configuration,
        )

    def update(self, configuration: commons_configuration.Configuration):
        self.edited_config = configuration
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

    def is_feed_connected(self):
        return self._community_feed is not None and self._community_feed.is_connected_to_remote_feed()

    def get_feed_last_message_time(self):
        if self._community_feed is None:
            return None
        return self._community_feed.last_message_time

    def get_deployment_url(self):
        return self.user_account.get_bot_deployment_url()

    def get_is_signal_receiver(self):
        if self._community_feed is None:
            return False
        return self._community_feed.is_signal_receiver

    def get_is_signal_emitter(self):
        if self._community_feed is None:
            return False
        return self._community_feed.is_signal_emitter

    def get_signal_community_url(self, signal_identifier):
        return f"{identifiers_provider.IdentifiersProvider.COMMUNITY_URL}/product/{signal_identifier}"

    async def update_supports(self):
        self._update_supports(200, self._supports_mock())
        return
        # TODO use real support fetch when implemented
        async with self._aiohttp_gql_session.get("supports_url") as resp:
            self._update_supports(resp.status, await resp.json())

    def ensure_async_loop(self):
        # elements should be bound to the current loop
        if self._aiohttp_gql_session is not None and self._aiohttp_gql_session.loop is not asyncio.get_event_loop():
            self._aiohttp_gql_session = None
        if self._aiohttp_backend_session is not None and self._aiohttp_backend_session.loop is not asyncio.get_event_loop():
            self._aiohttp_backend_session = None
        if self.initialized_event is not None and self.initialized_event._loop is not asyncio.get_event_loop():
            should_set = self.initialized_event.is_set()
            self.initialized_event = asyncio.Event()
            if should_set:
                self.initialized_event.set()

    def is_initialized(self):
        return self.initialized_event is not None and self.initialized_event.is_set()

    def init_account(self):
        self.initialized_event = asyncio.Event()
        self._fetch_account_task = asyncio.create_task(self._auth_and_fetch_account())

    async def async_init_account(self):
        self.init_account()
        await self._fetch_account_task

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
        session = self.get_gql_aiohttp_session()
        try:
            yield session
        except authentication.AuthenticationRequired:
            # reset token to force re-login
            self.user_account.gql_access_token = None
            if CommunityAuthentication.GQL_AUTHORIZATION_HEADER in session.headers:
                session.headers.pop(CommunityAuthentication.GQL_AUTHORIZATION_HEADER)
            raise

    async def wait_for_login_if_processing(self):
        if self._login_completed is not None:
            # ensure login details have been fetched
            await asyncio.wait_for(self._login_completed.wait(), self.LOGIN_TIMEOUT)

    async def gql_login_if_required(self):
        await self.wait_for_login_if_processing()
        if self.user_account.gql_access_token is not None:
            return
        try:
            token = self.user_account.get_graph_token()
        except (KeyError, TypeError) as e:
            raise authentication.AuthenticationRequired("Authentication required") from e
        async with self.get_aiohttp_session().post(
                identifiers_provider.IdentifiersProvider.GQL_AUTH_URL, json={"key": token}
        ) as resp:
            json_resp = await resp.json()
            if resp.status == 200:
                self.user_account.gql_access_token = json_resp["access_token"]
                self.user_account.gql_user_id = json_resp["user_id"]
                self._update_sessions_headers()
            else:
                raise authentication.FailedAuthentication(f"Failed to authenticate to graphql server: "
                                                          f"status: {resp.status}, data: {json_resp}")

    def can_authenticate(self):
        return "todo" not in self.authentication_url    # pylint: disable=E1135

    def must_be_authenticated_through_authenticator(self):
        return constants.IS_CLOUD_ENV

    async def login(self, email, password, password_token=None):
        self._ensure_email(email)
        self._ensure_community_url()
        self._reset_tokens()
        params = {
            "email": email,
        }
        if password_token:
            params["password_token"] = password_token
        else:
            params["password"] = password
        resp = self._backend_session.post(self.authentication_url, json=params)
        try:
            self._handle_auth_result(resp.status_code, resp.json(), resp.headers)
        except json.JSONDecodeError as e:
            raise authentication.FailedAuthentication(e)
        if self.is_logged_in():
            if self.initialized_event is None:
                self.initialized_event = asyncio.Event()
            await self._on_authenticated()
            self.initialized_event.set()

    async def register(self, email, password):
        if self.must_be_authenticated_through_authenticator():
            raise authentication.AuthenticationError("Creating a new account is not authorized on this environment.")
        # always logout before creating a new account
        self.logout()
        self._ensure_community_url()
        params = {
            "email": email,
            "password": password,
        }
        async with self.get_aiohttp_session().post(
                identifiers_provider.IdentifiersProvider.BACKEND_REGISTER_URL, json=params
        ) as resp:
            try:
                self._handle_register_result(resp.status, await resp.json(), resp.headers)
            except json.JSONDecodeError as e:
                raise authentication.FailedAuthentication(e)
        if self.is_logged_in():
            await self._on_register()

    async def _on_register(self):
        if self.initialized_event is None:
            self.initialized_event = asyncio.Event()
        t0 = time.time()
        try:
            while not self._is_new_account_fully_initialized() \
                    and time.time() - t0 < self.NEW_ACCOUNT_INITIALIZE_TIMEOUT:
                await self._async_check_auth()
        finally:
            if self._is_new_account_fully_initialized():
                self.logger.debug(f"New account has been fully initialized, now processing authenticated checkups")
                await self._on_authenticated()
                self.logger.debug(f"Authenticated checkups complete")
            else:
                self.logger.error(f"New account has not been fully initialized")
            self.initialized_event.set()

    def _is_new_account_fully_initialized(self):
        # required elements to be fully initialized
        try:
            self.user_account.get_graph_token()
        except (KeyError, TypeError):
            return False
        return True

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
            except errors.BotNotFoundError as e:
                # proceed to 2.
                self.logger.warning(str(e))
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
        self.user_account.set_all_user_bots_raw_data(
            self._get_self_hosted_bots(
                await self._fetch_bots()
            )
        )

    async def get_startup_info(self):
        if self.user_account.gql_bot_id is None:
            raise errors.BotError("No selected bot")
        return startup_info.StartupInfo.from_dict(
            await self._fetch_startup_info(
                self.user_account.gql_bot_id
            )
        )

    async def get_subscribed_profile_urls(self):
        subscribed_profiles = await self._fetch_subscribed_profiles()
        return [
            profile_data["url"]
            for profile_data in subscribed_profiles["data"]
        ]

    async def update_trades(self, trades: list):
        """
        Updates authenticated account trades
        """
        if not self.is_logged_in():
            return
        try:
            formatted_trades = [
                {
                    "date": self._get_graphql_formatted_time(trade.executed_time),
                    "exchange": trade.exchange_manager.exchange_name,
                    "price": str(trade.executed_price),
                    "quantity": str(trade.executed_quantity),
                    "symbol": trade.symbol,
                    "type": trade.trade_type.value,
                }
                for trade in trades
            ]
            await self._update_bot_trades(formatted_trades)
        except Exception as err:
            self.logger.exception(err, True, f"Error when updating community trades {err}")

    async def update_portfolio(self, current_value: dict, initial_value: dict,
                               unit: str, content: dict, history: dict, price_by_asset: dict):
        """
        Updates authenticated account portfolio
        """
        if not self.is_logged_in():
            return
        try:
            ref_market_current_value = current_value[unit]
            ref_market_initial_value = initial_value[unit]
            formatted_content = [
                {
                    "asset": key,
                    "quantity": str(quantity[commons_constants.PORTFOLIO_TOTAL]),
                    "value": str(quantity[commons_constants.PORTFOLIO_TOTAL] * float(price_by_asset.get(key, 0))),
                }
                for key, quantity in content.items()
            ]
            formatted_history = [
                {
                    "date": self._get_graphql_formatted_time(timestamp),
                    "value": str(value[unit])
                }
                for timestamp, value in history.items()
                if unit in value
            ]
            await self._update_bot_portfolio(
                ref_market_current_value, ref_market_initial_value, unit,
                formatted_content, formatted_history
            )
        except Exception as err:
            self.logger.exception(err, True, f"Error when updating community portfolio {err}")

    def _get_self_hosted_bots(self, bots):
        return [
            bot
            for bot in bots
            if self.user_account.is_self_hosted(bot)
        ]

    async def on_new_bot_select(self):
        await self._update_feed_device_uuid_and_restart_feed_if_necessary()

    async def _fetch_startup_info(self, bot_id):
        return await self._execute_request(graphql_requests.select_startup_info_query, bot_id)

    async def _fetch_subscribed_profiles(self):
        return await self._execute_request(graphql_requests.select_subscribed_profiles_query)

    async def _fetch_bots(self):
        return await self._execute_request(graphql_requests.select_bots_query)

    async def _fetch_bot(self, bot_id):
        return await self._execute_request(graphql_requests.select_bot_query, bot_id)

    async def create_new_bot(self):
        await self.gql_login_if_required()
        return await self._execute_request(graphql_requests.create_bot_query, not constants.IS_CLOUD_ENV)

    async def _create_new_bot_device(self, bot_id):
        await self._execute_request(graphql_requests.create_bot_device_query, bot_id)
        # issue with createBotDevice not always returning the created device, fetch bot again to fetch device with it
        return await self._fetch_bot(bot_id)

    async def _update_feed_device_uuid_and_restart_feed_if_necessary(self):
        if self._community_feed is None or not self.initialized_event.is_set():
            # only create a new community feed if necessary
            return
        if not (self._community_feed.is_using_bot_device(self.user_account) and self._community_feed.is_connected()):
            # Need to connect using the new uuid.

            # Reset restart task if running
            if self._restart_task is not None and not self._restart_task.done():
                self._restart_task.cancel()
                self._community_feed.remove_device_details()
            await self._ensure_bot_device()
            self._restart_task = asyncio.create_task(self._community_feed.restart())

    @_selected_bot_update
    async def update_bot_config_and_stats(self, profile_name, profitability):
        return await self._execute_request(
            graphql_requests.update_bot_config_and_stats_query,
            self.user_account.gql_bot_id,
            profile_name,
            profitability
        )

    @_selected_bot_update
    async def _update_bot_trades(self, trades):
        return await self._execute_request(
            graphql_requests.update_bot_trades_query,
            self.user_account.gql_bot_id,
            trades
        )

    @_selected_bot_update
    async def _update_bot_portfolio(self, current_value, initial_value, unit, content, history):
        return await self._execute_request(
            graphql_requests.update_bot_portfolio_query,
            self.user_account.gql_bot_id,
            current_value, initial_value, unit, content, history
        )

    async def _execute_request(self, request_factory, *args, **kwargs):
        query, variables, query_name = request_factory(*args, **kwargs)
        return await self.async_graphql_query(query, query_name, variables=variables, expected_code=200)

    def logout(self):
        """
        logout and remove saved auth details
        Warning: also call stop_feeds if feeds have to be stopped (not done here to keep method sync)
        """
        self._reset_tokens()
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

    def is_logged_in(self):
        return bool(self._auth_token and self.user_account.has_user_data())

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
        if self._aiohttp_backend_session is None:
            self._aiohttp_backend_session = aiohttp.ClientSession()
            self._update_sessions_headers()
        return self._aiohttp_backend_session

    def get_gql_aiohttp_session(self):
        if self._aiohttp_gql_session is None:
            self._aiohttp_gql_session = aiohttp.ClientSession()
            self._update_sessions_headers()
        return self._aiohttp_gql_session

    async def stop(self):
        self.logger.debug("Stopping ...")
        await self.stop_feeds()
        if self._fetch_account_task is not None and not self._fetch_account_task.done():
            self._fetch_account_task.cancel()
        if self._restart_task is not None and not self._restart_task.done():
            self._restart_task.cancel()
        if self._aiohttp_backend_session is not None:
            await self._aiohttp_backend_session.close()
        if self._aiohttp_gql_session is not None:
            await self._aiohttp_gql_session.close()
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

    async def _on_authenticated(self):
        await self.update_supports()
        await self.update_selected_bot()

    async def _auth_and_fetch_account(self):
        try:
            await self._async_try_auto_login()
            if not self.is_logged_in():
                return
            await self._on_authenticated()
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
        return constants.COMMUNITY_BOT_ID or self._get_value_in_config(constants.CONFIG_COMMUNITY_BOT_ID)

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
            with self._backend_session.get(f"{identifiers_provider.IdentifiersProvider.BACKEND_API_URL}/account") as resp:
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
        if constants.USER_ACCOUNT_EMAIL and email != constants.USER_ACCOUNT_EMAIL:
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

    def _handle_register_result(self, status_code, json_resp, reps_headers):
        if status_code == 200 and json_resp is not None:
            if "id" in json_resp:
                # successfully created account
                if new_token := reps_headers.get(self.SESSION_HEADER):
                    self._auth_token = new_token
                    self._save_login_token(self._auth_token)
                    self._update_sessions_headers()
                self.user_account.set_profile_raw_data(json_resp)
                return
            # error on create account
            error_messages = [
                f"{field}: {details['message']}"
                for field, details in json_resp.items()
            ]
            raise authentication.AuthenticationError(", ".join(error_messages))
        raise authentication.AuthenticationError(f"Unexpected error when creating account: code: {status_code} ({json_resp})")

    def _update_sessions_headers(self):
        backend_headers = self.get_backend_headers()
        self._backend_session.headers.update(backend_headers)
        if self._aiohttp_backend_session is not None:
            self._aiohttp_backend_session.headers.update(backend_headers)
        if self._aiohttp_gql_session is not None:
            self._aiohttp_gql_session.headers.update(self.get_gql_headers())

    def get_backend_headers(self):
        headers = {
            CommunityAuthentication.AUTHORIZATION_HEADER: f"Basic {self._community_token}",
        }
        if self._auth_token is not None:
            headers[CommunityAuthentication.SESSION_HEADER] = self._auth_token
        return headers

    def get_gql_headers(self):
        headers = {}
        if self.user_account.gql_access_token is not None:
            headers[CommunityAuthentication.GQL_AUTHORIZATION_HEADER] = f"Bearer {self.user_account.gql_access_token}"
        return headers

    def _reset_tokens(self):
        self._auth_token = None
        self.user_account.flush()
        self._backend_session.headers.pop(CommunityAuthentication.SESSION_HEADER, None)
        if self._aiohttp_backend_session is not None:
            self._aiohttp_backend_session.headers.pop(CommunityAuthentication.SESSION_HEADER, None)
        if self._aiohttp_gql_session is not None:
            self._aiohttp_gql_session.headers.pop(CommunityAuthentication.GQL_AUTHORIZATION_HEADER, None)

    @staticmethod
    def _get_encoded_community_token():
        return base64.encodebytes(identifiers_provider.IdentifiersProvider.BACKEND_PUBLIC_TOKEN.encode()).decode().strip()

    @staticmethod
    def _get_graphql_formatted_time(timestamp):
        return f"{datetime.datetime.utcfromtimestamp(timestamp).isoformat('T')}Z"
