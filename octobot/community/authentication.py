#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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
import json
import time
import typing
import hashlib
import os
import decimal

import octobot.constants as constants
import octobot.enums as enums
import octobot.community.errors as errors
import octobot.community.identifiers_provider as identifiers_provider
import octobot.community.models.community_supports as community_supports
import octobot.community.models.startup_info as startup_info
import octobot.community.models.community_user_account as community_user_account
import octobot.community.models.community_public_data as community_public_data
import octobot.community.models.formatters as formatters
import octobot.community.models.strategy_data as strategy_data
import octobot.community.supabase_backend as supabase_backend
import octobot.community.supabase_backend.enums as backend_enums
import octobot.community.feeds as community_feeds
import octobot.community.tentacles_packages as community_tentacles_packages
import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.authentication as authentication
import octobot_commons.configuration as commons_configuration
import octobot_commons.profiles as commons_profiles
import octobot_trading.enums as trading_enums


def expired_session_retrier(func):
    async def expired_session_retrier_wrapper(*args, **kwargs):
        self = args[0]
        try:
            with supabase_backend.error_describer():
                return await func(*args, **kwargs)
        except (errors.SessionTokenExpiredError, errors.JWTExpiredError):
            try:
                with supabase_backend.error_describer():
                    self.logger.info(f"Expired session, trying to refresh token.")
                    await self.supabase_client.refresh_session()
                    return await func(*args, **kwargs)
            except (errors.SessionTokenExpiredError, errors.JWTExpiredError) as err:
                if await self.auto_reauthenticate():
                    self.logger.error(
                        f"Impossible to use default refresh token, using saved auth details instead."
                    )
                    return await func(*args, **kwargs)
                # can't refresh token: logout
                self.logger.warning(f"Expired session, please re-authenticate. {err}")
                await self.logout()
    return expired_session_retrier_wrapper

def _bot_data_update(func):
    @expired_session_retrier
    async def bot_data_update_wrapper(*args, raise_errors=False, **kwargs):
        self = args[0]
        if not self.is_logged_in_and_has_selected_bot():
            self.logger.debug(f"Skipping {func.__name__} update: no user selected bot.")
            return
        try:
            with supabase_backend.error_describer():
                self.logger.debug(f"bot_data_update: {func.__name__} initiated.")
                return await func(*args, **kwargs)
        except errors.SessionTokenExpiredError:
            # requried by expired_session_retrier
            raise
        except Exception as err:
            if raise_errors:
                raise err
            self.logger.exception(err, True, f"Error when calling {func.__name__} {err}")
        finally:
            self.logger.debug(f"bot_data_update: {func.__name__} completed.")
    return bot_data_update_wrapper


class CommunityAuthentication(authentication.Authenticator):
    """
    Authentication utility
    """
    ALLOWED_TIME_DELAY = 1 * commons_constants.MINUTE_TO_SECONDS
    NEW_ACCOUNT_INITIALIZE_TIMEOUT = 1 * commons_constants.MINUTE_TO_SECONDS
    LOGIN_TIMEOUT = 20
    MAX_UPLOADED_TRADES_COUNT = 100
    BOT_NOT_FOUND_RETRY_DELAY = 1
    AUTHORIZATION_HEADER = "authorization"
    SESSION_HEADER = "X-Session"
    GQL_AUTHORIZATION_HEADER = "Authorization"

    def __init__(self, config=None, backend_url=None, backend_key=None, use_as_singleton=True):
        super().__init__(use_as_singleton=use_as_singleton)
        self.config = config
        self.backend_url = backend_url or identifiers_provider.IdentifiersProvider.BACKEND_URL
        self.backend_key = backend_key or identifiers_provider.IdentifiersProvider.BACKEND_KEY
        self.configuration_storage = supabase_backend.ASyncConfigurationStorage(self.config)
        self.supabase_client = self._create_client()
        self.user_account = community_user_account.CommunityUserAccount()
        self.public_data = community_public_data.CommunityPublicData()
        self.successfully_fetched_tentacles_package_urls = False
        self.silent_auth = False
        self._community_feed = None

        self.initialized_event = None
        self._login_completed = None
        self._fetched_private_data = None
        self._startup_info = None

        self._fetch_account_task = None

    @staticmethod
    def create(configuration: commons_configuration.Configuration, **kwargs):
        return CommunityAuthentication.instance(
            config=configuration,
            **kwargs,
        )

    def update(self, configuration: commons_configuration.Configuration):
        self.configuration_storage.set_configuration(configuration)

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

    async def get_strategies(self, reload=False) -> list[strategy_data.StrategyData]:
        await self.init_public_data(reset=reload)
        return self.public_data.get_strategies(self._get_compatible_strategy_categories())

    async def get_strategy(self, strategy_id, reload=False) -> strategy_data.StrategyData:
        await self.init_public_data(reset=reload)
        return self.public_data.get_strategy(strategy_id)

    async def get_strategy_profile_data(
        self, strategy_id: str, product_slug: str = None
    ) -> commons_profiles.ProfileData:
        profile_data = await self.supabase_client.fetch_product_config(strategy_id, product_slug=product_slug)
        formatters.ensure_profile_data_exchanges_internal_name_and_type(profile_data)
        return profile_data

    def is_feed_connected(self):
        return self._community_feed is not None and self._community_feed.is_connected_to_remote_feed()

    def get_feed_last_message_time(self):
        if self._community_feed is None:
            return None
        return self._community_feed.last_message_time

    def has_filled_form(self, form_id):
        if not self.user_account.has_user_data():
            raise authentication.AuthenticationRequired()
        return form_id in self.user_account.get_filled_forms_ids()

    async def register_filled_form(self, form_id):
        if self.has_filled_form(form_id):
            return
        updated_filled_forms = self.user_account.get_filled_forms_ids()
        updated_filled_forms.append(form_id)
        await self._update_account_metadata({
            self.user_account.FILLED_FORMS: updated_filled_forms
        })

    def get_user_id(self):
        if not self.user_account.has_user_data():
            raise authentication.AuthenticationRequired()
        return self.user_account.get_user_id()

    def get_last_email_address_confirm_code_email_content(self) -> typing.Optional[str]:
        if not self.user_account.has_user_data():
            raise authentication.AuthenticationRequired()
        return self.user_account.last_email_address_confirm_code_email_content

    async def get_deployment_url(self):
        deployment_url_data = await self.supabase_client.fetch_deployment_url(
            self.user_account.get_selected_bot_deployment_id()
        )
        return self.user_account.get_bot_deployment_url(deployment_url_data)

    async def get_gpt_signal(
        self, exchange: str, symbol: str, time_frame: commons_enums.TimeFrames, candle_open_time: float, version: str
    ) -> str:
        return await self.supabase_client.fetch_gpt_signal(exchange, symbol, time_frame, candle_open_time, version)

    async def get_gpt_signals_history(
        self, exchange: typing.Union[str, None], symbol: str, time_frame: commons_enums.TimeFrames,
        first_open_time: float, last_open_time: float, version: str
    ) -> dict:
        return await self.supabase_client.fetch_gpt_signals_history(
            exchange, symbol, time_frame, first_open_time, last_open_time, version
        )

    def get_is_signal_receiver(self):
        if self._community_feed is None:
            return False
        return self._community_feed.is_signal_receiver

    def get_is_signal_emitter(self):
        if self._community_feed is None:
            return False
        return self._community_feed.is_signal_emitter

    def get_signal_community_url(self, signal_identifier):
        try:
            slug = self.public_data.get_product_slug(signal_identifier)
            return f"{identifiers_provider.IdentifiersProvider.COMMUNITY_URL}/strategies/{slug}"
        except KeyError:
            return identifiers_provider.IdentifiersProvider.COMMUNITY_URL

    async def update_supports(self):
        def _supports_mock():
            return {
                "data": {
                    "attributes": {
                        "support_role": self.user_account.get_support_role()
                    }
                }
            }
        self._update_supports(200, _supports_mock())
        # TODO use real support fetch when implemented

    async def update_is_hosting_enabled(self, enabled: bool):
        await self._update_account_metadata({
            self.user_account.HOSTING_ENABLED: enabled
        })

    def _create_client(self):
        return supabase_backend.CommunitySupabaseClient(
            self.backend_url,
            self.backend_key,
            self.configuration_storage
        )

    async def _re_create_client(self):
        self.supabase_client = self._create_client()
        self.logger.debug(f"Refreshing user session")
        self.supabase_client.event_loop = asyncio.get_event_loop()
        await self.supabase_client.refresh_session()
        await self._on_account_updated()

    async def ensure_async_loop(self):
        # elements should be bound to the current loop
        if not self.is_using_the_current_loop():
            if self._login_completed is not None:
                should_set = self._login_completed.is_set()
                self._login_completed = asyncio.Event()
                if should_set:
                    self._login_completed.set()
            if self._fetched_private_data is not None:
                should_set = self._fetched_private_data.is_set()
                self._fetched_private_data = asyncio.Event()
                if should_set:
                    self._fetched_private_data.set()
            # changed event loop: restart client
            await self.supabase_client.aclose()
            self.user_account.flush()
            await self._re_create_client()

    def is_using_the_current_loop(self):
        return self.supabase_client.event_loop is None \
            or self.supabase_client.event_loop is asyncio.get_event_loop()

    def is_initialized(self):
        return self.initialized_event is not None and self.initialized_event.is_set()

    def init_account(self, fetch_private_data):
        if fetch_private_data and self._fetched_private_data is None:
            self._fetched_private_data = asyncio.Event()
        self._fetch_account_task = asyncio.create_task(self._initialize_account(fetch_private_data=fetch_private_data))

    async def async_init_account(self, fetch_private_data):
        self.init_account(fetch_private_data)
        await self._fetch_account_task

    async def _create_community_feed_if_necessary(self) -> bool:
        if self._community_feed is None:
            # ensure mqtt_device_uuid is set
            self._community_feed = community_feeds.community_feed_factory(
                self,
                constants.COMMUNITY_FEED_DEFAULT_TYPE
            )
            return True
        return False

    async def _ensure_init_community_feed(
        self,
        stop_on_cfg_action: typing.Optional[enums.CommunityConfigurationActions]=None
    ):
        await self._create_community_feed_if_necessary()
        if not self._community_feed.is_connected() and self._community_feed.can_connect():
            if self.initialized_event is not None and not self.initialized_event.is_set():
                await asyncio.wait_for(self.initialized_event.wait(), self.LOGIN_TIMEOUT)
        await self._community_feed.start(stop_on_cfg_action)

    async def register_feed_callback(self, channel_type: commons_enums.CommunityChannelTypes, callback, identifier=None):
        try:
            await self._ensure_init_community_feed()
            await self._community_feed.register_feed_callback(channel_type, callback, identifier=identifier)
        except errors.BotError as e:
            self.logger.error(f"Impossible to connect to community signals: {e}")

    async def trigger_wait_for_email_address_confirm_code_email(self):
        if not self.get_owned_packages():
            raise errors.ExtensionRequiredError(
                f"The {constants.OCTOBOT_EXTENSION_PACKAGE_1_NAME} is required to use TradingView email alerts"
            )
        await self._ensure_init_community_feed(enums.CommunityConfigurationActions.EMAIL_CONFIRM_CODE)


    async def send(self, message, channel_type, identifier=None):
        """
        Sends a message
        """
        self.logger.debug("Sending is disabled.")

    async def wait_for_login_if_processing(self):
        if self._login_completed is not None and not self._login_completed.is_set():
            # ensure login details have been fetched
            await asyncio.wait_for(self._login_completed.wait(), self.LOGIN_TIMEOUT)

    async def wait_for_private_data_fetch_if_processing(self):
        await self.wait_for_login_if_processing()
        if self.is_logged_in() and self._fetched_private_data is not None and not self._fetched_private_data.is_set():
            # ensure login details have been fetched
            await asyncio.wait_for(
                self._fetched_private_data.wait(),
                supabase_backend.HTTP_RETRY_COUNT * constants.COMMUNITY_FETCH_TIMEOUT
            )

    def can_authenticate(self):
        return bool(
            identifiers_provider.IdentifiersProvider.BACKEND_URL
            and identifiers_provider.IdentifiersProvider.BACKEND_KEY
        )

    def must_be_authenticated_through_authenticator(self):
        return constants.IS_CLOUD_ENV

    async def login(
        self,
        email: str,
        password: typing.Optional[str],
        password_token: typing.Optional[str] = None,
        auth_key: typing.Optional[str] = None,
        minimal: bool = False
    ):
        self._ensure_email(email)
        self._ensure_community_url()
        self._reset_tokens()
        with self._login_process():
            if auth_key and not password_token:
                password_token = await self.supabase_client.get_otp_with_auth_key(email, auth_key)
            if password_token:
                await self.supabase_client.sign_in_with_otp_token(password_token)
            else:
                await self.supabase_client.sign_in(email, password)
            await self._on_account_updated()
        if self.is_logged_in():
            await self.on_signed_in(minimal=minimal)

    async def auto_reauthenticate(self) -> bool:
        if constants.IS_CLOUD_ENV and constants.USER_ACCOUNT_EMAIL and constants.USER_AUTH_KEY:
            self.logger.debug("Attempting auth key authentication")
            await self.login(
                constants.USER_ACCOUNT_EMAIL, None, auth_key=constants.USER_AUTH_KEY
            )
            return self.is_logged_in()
        return False

    async def register(self, email, password):
        if self.must_be_authenticated_through_authenticator():
            raise authentication.AuthenticationError("Creating a new account is not authorized on this environment.")
        # always logout before creating a new account
        await self.logout()
        self._ensure_community_url()
        with self._login_process():
            await self.supabase_client.sign_up(email, password)
            await self._on_account_updated()
        if self.is_logged_in():
            await self.on_signed_in()

    async def on_signed_in(self, minimal=False):
        if not self.silent_auth:
            self.logger.info(f"Signed in as {self.get_logged_in_email()}")
        await self._initialize_account(minimal=minimal)

    async def _update_account_metadata(self, metadata_update):
        await self.supabase_client.update_metadata(metadata_update)
        await self._on_account_updated()

    async def update_selected_bot(self):
        self.user_account.flush_bot_details()
        await self._load_bot_if_selected()
        if not self.user_account.has_selected_bot_data():
            self.logger.info(self.user_account.NO_SELECTED_BOT_DESC)

    async def _load_bot_if_selected(self):
        # 1. use user selected bot id if any
        if saved_bot_id := self._get_saved_bot_id():
            try:
                await self.select_bot(saved_bot_id)
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

    async def create_new_bot(self):
        deployment_type = backend_enums.DeploymentTypes.CLOUD if constants.IS_CLOUD_ENV \
            else backend_enums.DeploymentTypes.SELF_HOSTED
        return await self.supabase_client.create_bot(deployment_type)

    async def select_bot(self, bot_id):
        fetched_bot = await self.supabase_client.fetch_bot(bot_id)
        self.user_account.set_selected_bot_raw_data(fetched_bot)
        bot_name = self.user_account.get_bot_name_or_id(self.user_account.get_selected_bot_raw_data())
        self.logger.debug(f"Selected bot '{bot_name}'")
        self.user_account.bot_id = bot_id
        self._save_bot_id(self.user_account.bot_id)
        await self.on_new_bot_select()

    async def load_user_bots(self):
        self.user_account.set_all_user_bots_raw_data(
            self._get_self_hosted_bots(
                await self.supabase_client.fetch_bots()
            )
        )

    async def get_startup_info(self):
        if self._startup_info is None:
            self.user_account.ensure_selected_bot_id()
            self._startup_info = startup_info.StartupInfo.from_dict(
                await self.supabase_client.fetch_startup_info(
                    self.user_account.bot_id
                )
            )
        return self._startup_info

    async def get_subscribed_profile_urls(self):
        return await self.supabase_client.fetch_subscribed_products_urls()

    async def get_current_bot_products_subscription(self) -> dict:
        self.user_account.ensure_selected_bot_id()
        return await self.supabase_client.fetch_bot_products_subscription(
            self.user_account.get_selected_bot_deployment_id()
        )

    def get_owned_packages(self) -> list[str]:
        return self.user_account.owned_packages

    def has_open_source_package(self) -> bool:
        return (
            bool(self.get_owned_packages())
            or (not self.is_logged_in() and self.was_connected_with_remote_packages())
        )

    def has_owned_packages_to_install(self) -> bool:
        return self.user_account.has_pending_packages_to_install

    def is_logged_in_and_has_selected_bot(self):
        return (self.supabase_client.is_admin or self.is_logged_in()) and self.user_account.bot_id is not None

    async def refresh_selected_bot(self):
        self.user_account.set_selected_bot_raw_data(
            await self.supabase_client.fetch_bot(self.user_account.bot_id)
        )

    async def refresh_selected_bot_if_unset(self):
        if not self.user_account.has_selected_bot_data():
            self.user_account.set_selected_bot_raw_data(
                await self.supabase_client.fetch_bot(self.user_account.bot_id)
            )

    def _get_self_hosted_bots(self, bots):
        return [
            bot
            for bot in bots
            if self.user_account.is_self_hosted(bot) and not self.user_account.is_archived(bot)
        ]

    async def on_new_bot_select(self):
        await self._update_deployment_activity()

    async def logout(self):
        """
        logout and remove saved auth details
        Warning: also call stop_feeds if feeds have to be stopped (not done here to keep method sync)
        """
        await self.supabase_client.sign_out({"scope": "local"})
        self._reset_tokens()
        self.remove_login_detail()

    def is_logged_in(self):
        return bool(self.supabase_client.is_signed_in() and self.user_account.has_user_data())

    async def has_login_info(self):
        return await self.supabase_client.has_login_info()

    def remove_login_detail(self):
        self.user_account.flush()
        self._reset_login_token()
        # force user to (re)select a bot
        self._save_bot_id("")
        # mqtt feed can't connect as long as the user is not authenticated: don't display unusable email address
        self.save_tradingview_email("")
        self.logger.debug("Removed community login data")

    def _clear_bot_scoped_config(self):
        """
        Clears all bot local data including mqtt id, which will trigger a new mqtt device creation.
        Warning: should only be called in rare cases, mostly to avoid multi connection on the same mqtt
        device
        """
        self.logger.info(
            "Clearing bot local scoped config data. Your TradingView alert email address "
            "and webhook url will be different on this bot."
        )
        self._save_bot_id("")
        self.save_tradingview_email("")
        # also reset mqtt id to force a new mqtt id creation
        self._save_mqtt_device_uuid("")
        # will force reconfiguring the next email
        self.save_tradingview_email_confirmed(False)

    def clear_local_data_if_necessary(self):
        if constants.IS_CLOUD_ENV:
            # disabled on cloud environments
            return
        previous_local_identifier = self._get_saved_bot_scoped_data_identifier()
        current_local_identifier = self._get_bot_scoped_data_identifier()
        if not previous_local_identifier:
            self._save_bot_scoped_data_identifier(current_local_identifier)
            # nothing to clear
            return
        if current_local_identifier != previous_local_identifier:
            self._clear_bot_scoped_config()
            self._save_bot_scoped_data_identifier(current_local_identifier)

    def _get_bot_scoped_data_identifier(self) -> str:
        # identifier is based on the path to the local bot to ensure the same data are not re-used
        # when copy/pasting a bot config to another bot
        return hashlib.sha256(os.getcwd().encode()).hexdigest()

    async def stop(self):
        self.logger.debug("Stopping ...")
        if self._fetch_account_task is not None and not self._fetch_account_task.done():
            self._fetch_account_task.cancel()
        await self.supabase_client.aclose()
        if self._community_feed:
            await self._community_feed.stop()
        self.logger.debug("Stopped")

    def _update_supports(self, resp_status, json_data):
        if resp_status == 200:
            self.user_account.supports = community_supports.CommunitySupports.from_community_dict(json_data)
            self.logger.debug(f"Fetched supports data.")
        else:
            self.logger.error(f"Error when fetching community support, "
                              f"error code: {resp_status}")

    @contextlib.contextmanager
    def _login_process(self):
        try:
            if self._login_completed is None:
                self._login_completed = asyncio.Event()
            self._login_completed.clear()
            yield
        finally:
            if not self._login_completed.is_set():
                self._login_completed.set()

    async def _initialize_account(self, minimal=False, fetch_private_data=True):
        try:
            await self.ensure_async_loop()
            self.initialized_event = asyncio.Event()
            if not (self.is_logged_in() or await self._restore_previous_session()):
                return
            self._login_completed.set()
            if not minimal:
                await self._init_community_data(fetch_private_data)
                if self._community_feed and self._community_feed.has_registered_feed():
                    await self._ensure_init_community_feed()
        except authentication.AuthenticationError as err:
            self.logger.info(f"Login aborted: no authenticated session: {err}")
            if await self.has_login_info():
                await self.logout()
        except authentication.UnavailableError as e:
            self.logger.exception(e, True, f"Error when fetching community data, "
                                           f"please check your internet connection.")
        except Exception as e:
            self.logger.exception(e, True, f"Error when fetching community supports: {e}({e.__class__.__name__})")
        finally:
            self.initialized_event.set()

    async def _init_community_data(self, fetch_private_data):
        coros = [
            self.update_supports(),
            self.init_public_data(),
        ]
        if constants.IS_CLOUD_ENV or fetch_private_data:
            coros.append(self.update_selected_bot())
        if fetch_private_data:
            coros.append(self.fetch_private_data())
        if not self.user_account.is_hosting_enabled():
            coros.append(self.update_is_hosting_enabled(True))
        await asyncio.gather(*coros)

    async def init_public_data(self, reset=False):
        if reset or not self.public_data.products.fetched:
            await self._refresh_products()

    async def _refresh_products(self):
        self.public_data.set_products(
            await self.supabase_client.fetch_products(
                self._get_compatible_strategy_categories(),
                [self.user_account.get_user_id()] if self.user_account.has_user_data() else None
            )
        )

    def _get_compatible_strategy_categories(self) -> list[str]:
        category_types = ["profile"]
        if self.has_open_source_package():
            category_types.append("index")
        return category_types

    async def fetch_bot_tentacles_data_based_config(
        self, bot_id: str, auth_key: typing.Optional[str]
    ) -> (commons_profiles.ProfileData, list[commons_profiles.ExchangeAuthData]):
        return await self.supabase_client.fetch_bot_tentacles_data_based_config(
            bot_id, self, auth_key
        )

    async def fetch_private_data(self, reset=False):
        try:
            if not self.is_logged_in():
                self.logger.info(f"Can't fetch private data: no authenticated user")
                return
            mqtt_uuid = None
            try:
                mqtt_uuid = self.get_saved_mqtt_device_uuid()
            except errors.NoBotDeviceError:
                pass
            if constants.DISABLE_COMMUNITY_EXTENSIONS_CHECK:
                self.logger.info("Community extension check is disabled")
            elif reset or (not self.user_account.community_package_urls or not mqtt_uuid):
                self.successfully_fetched_tentacles_package_urls = False
                packages, package_urls, fetched_mqtt_uuid, tradingview_email = (
                    await self._fetch_extensions_details(mqtt_uuid)
                )
                self.successfully_fetched_tentacles_package_urls = True
                self.user_account.owned_packages = packages
                self.logger.debug(f"Account extension packages: {', '.join(packages) if packages else packages}")
                self.save_installed_package_urls(package_urls)
                has_tentacles_to_install = \
                    await community_tentacles_packages.has_tentacles_to_install_and_uninstall_tentacles_if_necessary(
                        self
                    )
                if has_tentacles_to_install:
                    # tentacles are not installed, save the fact that some are pending
                    self.logger.info(f"New tentacles are available for installation")
                    self.user_account.has_pending_packages_to_install = True
                if fetched_mqtt_uuid and fetched_mqtt_uuid != mqtt_uuid:
                    self._save_mqtt_device_uuid(fetched_mqtt_uuid)
                if tradingview_email and tradingview_email != self.get_saved_tradingview_email():
                    self.save_tradingview_email(tradingview_email)
        except Exception as err:
            self.logger.exception(err, True, f"Unexpected error when fetching package urls: {err}")
        finally:
            if self._fetched_private_data is None:
                self._fetched_private_data = asyncio.Event()
            self._fetched_private_data.set()
        if self.has_open_source_package():
            # fetch indexes as well
            await self._refresh_products()

    async def _fetch_extensions_details(self, mqtt_uuid: typing.Optional[str]) -> (list[str], list[str], str, str):
        self.logger.debug(f"Fetching extension package details")
        extensions_details = await self.supabase_client.fetch_extensions(mqtt_uuid)
        self.logger.debug("Fetched extension package details")
        if not extensions_details:
            return None, None, None, None
        packages = [
            package
            for package in extensions_details["paid_package_slugs"]
            if package
        ]
        urls = [
            url
            for url in extensions_details["package_urls"]
            if url
        ]
        mqtt_id = extensions_details["mqtt_id"]
        tradingview_email = extensions_details["tradingview_email"]
        return packages, urls, mqtt_id, tradingview_email

    async def fetch_checkout_url(self, payment_method: str, redirect_url: str):
        try:
            if not self.is_logged_in():
                self.logger.info(f"Can't fetch checkout url: no authenticated user")
                return None
            self.logger.debug(f"Fetching {payment_method} checkout url")
            url_details = await self.supabase_client.fetch_checkout_url(payment_method, redirect_url)
            if not url_details:
                # valid error code but no content: user already has this product
                return None
            url = url_details["checkout_url"]
            self.logger.info(
                f"Here is your {constants.OCTOBOT_EXTENSION_PACKAGE_1_NAME} checkout url {url} "
                f"paste it into a web browser to proceed to payment if your browser did to automatically "
                f"redirected to it."
            )
            return url
        except Exception as err:
            self.logger.exception(err, True, f"Error when fetching checkout url: {err}")
            raise

    def was_connected_with_remote_packages(self):
        return self.configuration_storage.has_remote_packages()

    def _reset_login_token(self):
        if self.supabase_client is not None:
            self._save_value_in_config(self.supabase_client.auth._storage_key, "")

    def save_installed_package_urls(self, package_urls: list[str]):
        self._save_value_in_config(constants.CONFIG_COMMUNITY_PACKAGE_URLS, package_urls)

    def save_tradingview_email(self, tradingview_email: str):
        self._save_value_in_config(constants.CONFIG_COMMUNITY_TRADINGVIEW_EMAIL, tradingview_email)

    def save_tradingview_email_confirmed(self, confirmed: bool):
        self._save_value_in_config(constants.CONFIG_COMMUNITY_TRADINGVIEW_EMAIL_CONFIRMED, confirmed)

    def _save_mqtt_device_uuid(self, mqtt_uuid: str):
        self._save_value_in_config(constants.CONFIG_COMMUNITY_MQTT_UUID, mqtt_uuid)

    def _save_bot_scoped_data_identifier(self, identifier: str):
        self._save_value_in_config(constants.CONFIG_COMMUNITY_LOCAL_DATA_IDENTIFIER, identifier)

    def get_saved_package_urls(self) -> list[str]:
        return self._get_value_in_config(constants.CONFIG_COMMUNITY_PACKAGE_URLS) or []

    def get_saved_mqtt_device_uuid(self) -> str:
        if mqtt_uuid := self._get_value_in_config(constants.CONFIG_COMMUNITY_MQTT_UUID):
            return mqtt_uuid
        raise errors.NoBotDeviceError("No MQTT device ID has been set")

    def _get_saved_bot_scoped_data_identifier(self) -> str:
        return self._get_value_in_config(constants.CONFIG_COMMUNITY_LOCAL_DATA_IDENTIFIER)

    def get_saved_tradingview_email(self) -> str:
        return self._get_value_in_config(constants.CONFIG_COMMUNITY_TRADINGVIEW_EMAIL)

    def is_tradingview_email_confirmed(self) -> bool:
        return self._get_value_in_config(constants.CONFIG_COMMUNITY_TRADINGVIEW_EMAIL_CONFIRMED) is True

    def _save_bot_id(self, bot_id):
        self._save_value_in_config(constants.CONFIG_COMMUNITY_BOT_ID, bot_id)

    def _get_saved_bot_id(self) -> str:
        return constants.COMMUNITY_BOT_ID or self._get_value_in_config(constants.CONFIG_COMMUNITY_BOT_ID)

    def _save_value_in_config(self, key, value):
        self.configuration_storage.sync_storage.set_item(key, value)

    def _get_value_in_config(self, key):
        return self.configuration_storage.sync_storage.get_item(key)

    async def _restore_previous_session(self):
        with self._login_process():
            async with self._auth_handler():
                # will raise on failure
                await self.supabase_client.restore_session()
                await self._on_account_updated()
                if not self.silent_auth:
                    self.logger.info(f"Signed in as {self.get_logged_in_email()}")
        return self.is_logged_in()

    @contextlib.asynccontextmanager
    async def _auth_handler(self):
        should_warn = await self.has_login_info()
        try:
            yield
        except authentication.FailedAuthentication as e:
            if should_warn:
                self.logger.warning(f"Invalid authentication details, please re-authenticate. {e}")
            if await self.has_login_info():
                await self.logout()
        except authentication.UnavailableError:
            raise
        except Exception as e:
            self.logger.exception(e, True, f"Error when trying to refresh community login: {e}")

    def _ensure_email(self, email):
        if constants.USER_ACCOUNT_EMAIL and email != constants.USER_ACCOUNT_EMAIL:
            raise authentication.AuthenticationError("The given email doesn't match the expected user email.")

    def _ensure_community_url(self):
        if not self.can_authenticate():
            raise authentication.UnavailableError("Community url required")

    async def _on_account_updated(self):
        self.user_account.set_profile_raw_data(await self.supabase_client.get_user())

    def _reset_tokens(self):
        self.user_account.flush()

    @_bot_data_update
    @supabase_backend.retried_failed_supabase_request
    async def update_trades(self, trades: list, exchange_name: str, reset: bool):
        """
        Updates authenticated account trades
        """
        if reset:
            await self.supabase_client.reset_trades(self.user_account.bot_id)
        trades_to_upload = trades if len(trades) <= self.MAX_UPLOADED_TRADES_COUNT else (
            sorted(
                trades,
                key=lambda x: x[trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value],
                reverse=True
            )[:self.MAX_UPLOADED_TRADES_COUNT]
        )
        if formatted_trades := formatters.format_trades(trades_to_upload, exchange_name, self.user_account.bot_id):
            await self.supabase_client.upsert_trades(formatted_trades)

    @_bot_data_update
    @supabase_backend.retried_failed_supabase_request
    async def update_orders(self, orders_by_exchange: dict[str, list]):
        """
        Updates authenticated account orders
        """
        formatted_orders = []
        for exchange_name, orders in orders_by_exchange.items():
            formatted_orders += formatters.format_orders(orders, exchange_name)
        await self.supabase_client.update_bot_orders(self.user_account.bot_id, formatted_orders)
        self.logger.info(f"Bot orders updated: using {len(formatted_orders)} orders")

    @_bot_data_update
    @supabase_backend.retried_failed_supabase_request
    async def update_positions(self, positions_by_exchange: dict[str, list]):
        """
        Updates authenticated account positions
        """
        formatted_positions = []
        for exchange_name, positions in positions_by_exchange.items():
            formatted_positions += formatters.format_positions(positions, exchange_name)
        await self.supabase_client.update_bot_positions(self.user_account.bot_id, formatted_positions)
        self.logger.info(f"Bot positions updated: using {len(formatted_positions)} positions")

    @_bot_data_update
    @supabase_backend.retried_failed_supabase_request
    async def update_portfolio(
        self, current_value: dict, initial_value: dict, profitability: float,
        unit: str, content: dict[str, dict[str, float]], history: dict,
        price_by_asset: dict[str, typing.Union[float, decimal.Decimal]],
        reset: bool, is_sub_portfolio: bool = False, 
        bot_locked_assets: typing.Optional[dict[str, dict[str, decimal.Decimal]]] = None
    ):
        """
        Updates authenticated account portfolio
        """
        try:
            formatted_portfolio = formatters.format_portfolio(
                current_value, initial_value, profitability, unit, content, price_by_asset, self.user_account.bot_id,
                is_sub_portfolio, bot_locked_assets
            )
            if reset or self.user_account.get_selected_bot_current_portfolio_id() is None:
                self.logger.info(f"Switching bot portfolio")
                await self.supabase_client.switch_portfolio(formatted_portfolio)
                await self.refresh_selected_bot()
            portfolio_id = self.user_account.get_selected_bot_current_portfolio_id()
            formatted_portfolio[backend_enums.PortfolioKeys.ID.value] = portfolio_id
            await self.supabase_client.update_portfolio(formatted_portfolio)
            self.logger.info(
                f"Bot portfolio [{formatted_portfolio[backend_enums.PortfolioKeys.ID.value]}] "
                f"updated with content: {formatted_portfolio[backend_enums.PortfolioKeys.CONTENT.value]}"
            )
            await self.upsert_portfolio_history(portfolio_id, history, unit)
        except KeyError as err:
            self.logger.debug(f"Error when updating community portfolio {err} (missing reference market value)")

    async def upsert_portfolio_history(self, portfolio_id: str, history: dict, unit: str):
        if formatted_histories := formatters.format_portfolio_history(history, unit, portfolio_id):
            await self.supabase_client.upsert_portfolio_history(formatted_histories)
            self.logger.info(f"Bot portfolio [{portfolio_id}] history updated")

    @_bot_data_update
    async def update_bot_config_and_stats(self, profitability):
        formatted_portfolio = formatters.format_portfolio_with_profitability(profitability)
        if self.user_account.get_selected_bot_current_portfolio_id() is None:
            await self.refresh_selected_bot()
        if self.user_account.get_selected_bot_current_portfolio_id() is None:
            self.logger.debug(
                f"Skipping portfolio update: current bot {self.user_account.bot_id} has no current portfolio_id"
            )
        else:
            formatted_portfolio[backend_enums.PortfolioKeys.ID.value] = \
                self.user_account.get_selected_bot_current_portfolio_id()
            await self.supabase_client.update_portfolio(formatted_portfolio)
        await self._update_deployment_activity()

    @_bot_data_update
    async def _update_deployment_activity(self):
        try:
            deployment_id = self.user_account.get_selected_bot_deployment_id()
            if not deployment_id:
                self.logger.debug(f"Missing deployment id to update last deployment activity time.")
                return
            current_time = time.time()
            await self.supabase_client.update_deployment(
                deployment_id,
                self.supabase_client.get_deployment_activity_update(
                    current_time,
                    current_time + commons_constants.TIMER_BETWEEN_METRICS_UPTIME_UPDATE,
                )
            )
        except KeyError:
            self.logger.debug(
                f"Skipping activity update: current bot {self.user_account.bot_id} has no deployment"
            )

