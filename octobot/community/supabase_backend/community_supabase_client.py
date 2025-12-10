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
import datetime
import time
import typing
import logging
import uuid
import json
import contextlib
import aiohttp
import httpx

import supabase_auth.errors
import supabase_auth.types
import postgrest
import postgrest.types
import postgrest.utils
import supabase

import octobot_commons.authentication as authentication
import octobot_commons.logging as commons_logging
import octobot_commons.profiles as commons_profiles
import octobot_commons.profiles.profile_data as commons_profile_data
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.dict_util as dict_util
import octobot_trading.api as trading_api
import octobot.constants as constants
import octobot.community.errors as errors
import octobot.community.models.formatters as formatters
import octobot.community.models.community_user_account as community_user_account
import octobot.community.models.strategy_data as strategy_data
import octobot.community.models.executed_product_details as executed_product_details_import
import octobot.community.supabase_backend.error_translator as error_translator
import octobot.community.supabase_backend.enums as enums
import octobot.community.supabase_backend.supabase_client as supabase_client
import octobot.community.supabase_backend.configuration_storage as configuration_storage
import octobot.community.identifiers_provider as identifiers_provider

# Experimental to prevent httpx.PoolTimeout
_INTERNAL_LOGGERS = [
    # "httpx", "httpx._client",
    # "httpcore.http11", "httpcore.http2", "httpcore.proxy", "httpcore.socks", "httpcore.connection"
]
# disable httpx info logs as it logs every request
commons_logging.set_logging_level(_INTERNAL_LOGGERS, logging.WARNING)
HTTP_RETRY_COUNT = 5


@contextlib.contextmanager
def error_describer():
    try:
        yield
    except postgrest.APIError as err:
        if _is_jwt_expired_error(err):
            raise errors.SessionTokenExpiredError(err) from err
        raise


def retried_failed_supabase_request(func):
    async def retried_failed_supabase_request_wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(1, constants.FAILED_DB_REQUEST_MAX_ATTEMPTS + 1):
            try:
                if attempt > 1:
                    await asyncio.sleep(constants.RETRY_DB_REQUEST_DELAY)
                    commons_logging.get_logger("retried_failed_supabase_request").warning(
                        f"{func.__name__} attempt {attempt}/{constants.FAILED_DB_REQUEST_MAX_ATTEMPTS} "
                        f"{last_error=} ({last_error.__class__.__name__})"
                    )
                return await func(*args, **kwargs)
            except postgrest.APIError as err:
                if str(err.code) in ("502", "500", "409"):
                    # cloudflare errors, to be retried
                    # 502: bad gateway, 500: internal server error, 409: Could not find host => can happen: retry
                    # all message are expected to be 'message': 'JSON could not be generated'
                    if err.message != "JSON could not be generated":
                        commons_logging.get_logger("retried_failed_supabase_request").error(
                            f"{func.__name__} attempt {attempt}/{constants.FAILED_DB_REQUEST_MAX_ATTEMPTS} "
                            f"unexpected error.message: '{err.message}'. Expected: 'JSON could not be generated'. "
                            f"Retrying anyway"
                        )
                    last_error = err
                    continue
                else:
                    raise
            except AttributeError as err:
                if "'str' object has no attribute 'get'" in str(err):
                    # error when parsing postgrest.APIError: retry
                    last_error = err
                    continue
                else:
                    raise
            except (httpx.NetworkError, httpx.RemoteProtocolError) as err:
                # network error (WriteError, etc), to be retried
                last_error = err
                continue
            except Exception as err:
                # unexpected error: don't retry
                raise
        if last_error:
            commons_logging.get_logger("retried_failed_supabase_request").error(
                f"{func.__name__} failed after {attempt} attempts: "
                f" {last_error=} ({last_error.__class__.__name__})"
            )
            raise last_error
        # last_error should always be set, handle it just in case
        raise Exception(f"{func.__name__} failed after {attempt} attempts")
    return retried_failed_supabase_request_wrapper


class CommunitySupabaseClient(supabase_client.AuthenticatedAsyncSupabaseClient):
    """
    Octobot Community layer added to supabase_client.AuthenticatedSupabaseClient
    """
    MAX_PAGINATED_REQUESTS_COUNT = 100
    MAX_UUID_PER_COMMUNITY_REQUEST_FILTERS = 150
    REQUEST_TIMEOUT = 30

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        storage: configuration_storage.ASyncConfigurationStorage,
        options: supabase.AClientOptions = None,
    ):
        # the timeout param logs a deprecation warning however default value still sets it
        # wait for a fix in supabase. maybe set timeout in a AsyncClient instead
        options = options or supabase.AClientOptions(
            storage=storage,
            postgrest_client_timeout=self.REQUEST_TIMEOUT
        )
        self.event_loop = None
        super().__init__(supabase_url, supabase_key, options=options)
        self.is_admin = False
        self.production_anon_client = None
        self._authenticated = False

    async def sign_in(self, email: str, password: str) -> None:
        try:
            self.event_loop = asyncio.get_event_loop()
            await self.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
        except supabase_auth.errors.AuthApiError as err:
            translated_error = error_translator.translate_error_code(err.code)
            if err.code == error_translator.EMAIL_NOT_CONFIRMED_ERROR:
                raise errors.EmailValidationRequiredError(translated_error) from err
            raise authentication.FailedAuthentication(translated_error) from err

    async def sign_up(self, email: str, password: str) -> None:
        try:
            self.event_loop = asyncio.get_event_loop()
            resp = await self.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "redirect_to": f"{identifiers_provider.IdentifiersProvider.COMMUNITY_URL}/login",
                    "data": {
                        "hasRegisteredFromSelfHosted": True,
                        community_user_account.CommunityUserAccount.HOSTING_ENABLED: True,
                    }
                }
            })
            if self._is_email_already_in_use(resp.user):
                raise authentication.AuthenticationError(error_translator.translate_error_code("email_exists"))
            if self._requires_email_validation(resp.user):
                raise errors.EmailValidationRequiredError()
        except supabase_auth.errors.AuthError as err:
            raise authentication.AuthenticationError(error_translator.translate_error_code(err.code)) from err

    async def sign_out(self, options: supabase_auth.types.SignOutOptions) -> None:
        try:
            await self.auth.sign_out(options)
        except (postgrest.exceptions.APIError, supabase_auth.errors.AuthApiError):
            pass

    def _requires_email_validation(self, user: supabase_auth.types.User) -> bool:
        return user.app_metadata.get("provider") == "email" and user.confirmed_at is None

    def _is_email_already_in_use(self, user: supabase_auth.types.User) -> bool:
        # // Check if the user got created based on https://github.com/orgs/supabase/discussions/1282
        if user.identities and len(user.identities) > 0:
            return False
        return True

    async def restore_session(self):
        self.event_loop = asyncio.get_event_loop()
        await self.auth.initialize_from_storage()
        if not self.is_signed_in():
            raise authentication.FailedAuthentication(f"Community auth error: restoring session failed")

    async def refresh_session(self, refresh_token: typing.Union[str, None] = None):
        try:
            with jwt_expired_auth_raiser():
                await self.auth.refresh_session(refresh_token=refresh_token)
        except supabase_auth.errors.AuthError as err:
            raise authentication.AuthenticationError(error_translator.translate_error_code(err.code)) from err
        except postgrest.exceptions.APIError as err:
            raise authentication.AuthenticationError(f"Community auth error: {err}") from err

    async def sign_in_with_otp_token(self, token):
        self.event_loop = asyncio.get_event_loop()
        # restore saved session in case otp token fails
        saved_session = await self.auth._storage.get_item(self.auth._storage_key)
        try:
            url = f"{self.auth_url}/verify?token={token}&type=magiclink"
            async with aiohttp.ClientSession() as client:
                resp = await client.get(url, allow_redirects=False)
                await self.auth.initialize_from_url(
                    resp.headers["Location"]
                    .replace("#access_token", "?access_token")
                    .replace("#error", "?error")
                )
        except supabase_auth.errors.AuthImplicitGrantRedirectError as err:
            if saved_session:
                await self.auth._storage.set_item(self.auth._storage_key, saved_session)
            raise authentication.AuthenticationError(error_translator.translate_error_code(err.code)) from err

    def is_signed_in(self) -> bool:
        # is signed in when a user auth key is set
        return self._get_auth_key() != self.supabase_key

    def get_in_saved_session(self) -> typing.Union[supabase_auth.types.Session, None]:
        return self.auth._get_valid_session(
            self.auth._storage.sync_storage.get_item(self.auth._storage_key)
        )

    async def has_login_info(self) -> bool:
        return bool(await self.auth._storage.get_item(self.auth._storage_key))

    async def update_metadata(self, metadata_update) -> dict:
        return (
            await self.auth.update_user({
                "data": metadata_update
            })
        ).user.model_dump()

    async def get_user(self) -> dict:
        try:
            user = await self._get_user()
            return user.model_dump()
        except supabase_auth.errors.AuthApiError as err:
            translated_error = error_translator.translate_error_code(err.code)
            if err.code == error_translator.EMAIL_NOT_CONFIRMED_ERROR:
                raise errors.EmailValidationRequiredError(translated_error) from err
            raise authentication.AuthenticationError(
                f"Please re-login to your OctoBot account: {translated_error}"
            ) from err

    async def get_otp_with_auth_key(self, user_email: str, auth_key: str) -> str:
        try:
            resp = await self.functions.invoke(
                "create-auth-token",
                {
                    "headers": {
                        "User-Auth-Token": auth_key
                    },
                    "body": {
                        "user_email": user_email
                    },
                }
            )
            return json.loads(resp)["token"]
        except Exception:
            raise authentication.AuthenticationError(f"Community auth error: invalid auth key authentication details")

    async def fetch_extensions(self, mqtt_uuid: typing.Optional[str]) -> dict:
        resp = await self.functions.invoke(
            "os-paid-package-api",
            {
                "body": {
                    "action": "get_extension_details",
                    "mqtt_id": mqtt_uuid
                },
            }
        )
        return json.loads(json.loads(resp)["message"])

    async def fetch_checkout_url(self, payment_method: str, redirect_url: str) -> dict:
        resp = await self.functions.invoke(
            "os-paid-package-api",
            {
                "body": {
                    "action": "get_checkout_url",
                    "payment_method": payment_method,
                    "success_url": redirect_url,
                },
            }
        )
        return json.loads(json.loads(resp)["message"])

    async def fetch_bot(self, bot_id) -> dict:
        with jwt_expired_auth_raiser():
            try:
                # https://postgrest.org/en/stable/references/api/resource_embedding.html#hint-disambiguation
                return (await self.table("bots").select("*,bot_deployment:bot_deployments!bots_current_deployment_id_fkey(*)").eq(
                    enums.BotKeys.ID.value, bot_id
                ).execute()).data[0]
            except IndexError:
                raise errors.BotNotFoundError(f"Can't find bot with id: {bot_id}")

    async def fetch_bots(self) -> list:
        with jwt_expired_auth_raiser():
            return (
                await self.table("bots").select(
                    "*,bot_deployment:bot_deployments!bots_current_deployment_id_fkey!inner(*)"
                ).execute()).data

    async def create_bot(self, deployment_type: enums.DeploymentTypes) -> dict:
        created_bot = (await self.table("bots").insert({
            enums.BotKeys.USER_ID.value: (await self._get_user()).id
        }).execute()).data[0]
        bot_id = created_bot[enums.BotKeys.ID.value]
        created_deployment = await self._create_deployment(
            deployment_type, bot_id, constants.VERSION
        )
        await self.table("bots").update({
            enums.BotKeys.CURRENT_DEPLOYMENT_ID.value: created_deployment[enums.BotDeploymentKeys.ID.value],
        }).eq(
            enums.BotDeploymentKeys.ID.value, bot_id
        ).execute()
        # fetch bot to fetch embed elements (like deployments)
        return await self.fetch_bot(bot_id)

    async def _create_deployment(self, deployment_type, bot_id, version):
        current_time = time.time()
        return (await self.table("bot_deployments").insert({
            enums.BotDeploymentKeys.TYPE.value: deployment_type.value,
            enums.BotDeploymentKeys.VERSION.value: version,
            enums.BotDeploymentKeys.BOT_ID.value: bot_id,
            enums.BotDeploymentKeys.ACTIVITIES.value: self._get_activities_content(
                current_time,
                current_time + commons_constants.TIMER_BETWEEN_METRICS_UPTIME_UPDATE
            )
        }).execute()).data[0]

    async def update_bot(self, bot_id, bot_update) -> dict:
        await self.table("bots").update(bot_update).eq(enums.BotKeys.ID.value, bot_id).execute()
        # fetch bot to fetch embed elements (like deployments)
        return await self.fetch_bot(bot_id)

    async def update_deployment(self, deployment_id, deployment_update: dict) -> dict:
        return (await self.table("bot_deployments").update(deployment_update).eq(
            enums.BotDeploymentKeys.ID.value, deployment_id
        ).execute()).data[0]

    def get_deployment_activity_update(self, last_activity: float, next_activity: float) -> dict:
        return {
            enums.BotDeploymentKeys.ACTIVITIES.value: self._get_activities_content(last_activity, next_activity)
        }

    def _get_activities_content(self, last_activity: float, next_activity: float):
        return {
            enums.BotDeploymentActivitiesKeys.LAST_ACTIVITY.value: self.get_formatted_time(last_activity),
            enums.BotDeploymentActivitiesKeys.NEXT_ACTIVITY.value: self.get_formatted_time(next_activity)
        }

    async def delete_bot(self, bot_id) -> list:
        return (await self.table("bots").delete().eq(enums.BotKeys.ID.value, bot_id).execute()).data

    async def fetch_deployment_url(self, deployment_url_id) -> dict:
        try:
            return (await self.table("bot_deployment_urls").select("*").eq(
                enums.BotDeploymentURLKeys.ID.value, deployment_url_id
            ).execute()).data[0]
        except IndexError:
            raise errors.BotDeploymentURLNotFoundError(deployment_url_id)

    async def fetch_startup_info(self, bot_id) -> dict:
        resp = await self.rpc("get_startup_info", {"bot_id": bot_id}).execute()
        return resp.data[0]

    async def fetch_products(self, category_types: list[str], author_ids: typing.Optional[list[str]]) -> list:
        try:
            sanitized_authors = ",".join(map(
                postgrest.utils.sanitize_param,
                [author_id for author_id in author_ids if author_id]
            )) if author_ids else None
            query = self.table("products").select(
                "*,"
                "category:product_categories!inner(slug, name_translations, type, metadata),"
                "results:product_results!products_current_result_id_fkey("
                "  profitability,"
                "  reference_market_profitability"
                ")"
            ).in_(
                "category.type", category_types
            )
            if sanitized_authors:
                query = query.or_(
                    # https://supabase.com/docs/reference/python/or
                    # either a public product with NULL author id
                    f"and({enums.ProductKeys.VISIBILITY.value}.{postgrest.types.Filters.EQ}.public"
                    f", {enums.ProductKeys.AUTHOR_ID.value}.{postgrest.types.Filters.IS}.NULL), "
                    # or a product whose author is in sanitized_authors
                    f"{enums.ProductKeys.AUTHOR_ID.value}.{postgrest.types.Filters.IN}.({sanitized_authors})"
                ).not_.eq(
                    # skip deleted strategies
                    enums.ProductKeys.VISIBILITY.value, "deleted"
                )
            else:
                query = query.eq(
                    enums.ProductKeys.VISIBILITY.value, "public"
                ).is_(
                    enums.ProductKeys.AUTHOR_ID.value, "NULL"
                )
            return (
                await query.execute()
            ).data
        except postgrest.exceptions.APIError as err:
            commons_logging.get_logger(__name__).error(f"Error when fetching products: {err}")
            return []

    async def fetch_subscribed_products_urls(self) -> list:
        resp = await self.rpc("get_subscribed_products_urls").execute()
        return resp.data or []

    async def fetch_bot_products_subscription(self, bot_deployment_id: str) -> dict:
        return (await self.table("bot_deployments").select(
            "products_subscription:products_subscriptions!product_subscription_id(id, status, desired_status)"
        ).eq(
            enums.BotDeploymentKeys.ID.value, bot_deployment_id
        ).execute()).data[0]["products_subscription"]

    async def fetch_trades(self, bot_id) -> list:
        # should be paginated to fetch all trades, will fetch the 1000 first ones only
        return (await self.table("bot_trades").select("*").eq(
            enums.TradeKeys.BOT_ID.value, bot_id
        ).execute()).data

    async def reset_trades(self, bot_id):
        return (await self.table("bot_trades").delete().eq(
            enums.TradeKeys.BOT_ID.value, bot_id
        ).execute()).data

    async def upsert_trades(self, formatted_trades) -> list:
        return (await self.table("bot_trades").upsert(
            formatted_trades, on_conflict=f"{enums.TradeKeys.TRADE_ID.value},{enums.TradeKeys.TIME.value}"
        ).execute()).data

    async def update_bot_orders(self, bot_id, formatted_orders) -> dict:
        bot_update = {
            enums.BotKeys.ORDERS.value: formatted_orders
        }
        return await self.update_bot(
            bot_id, bot_update
        )

    async def update_bot_positions(self, bot_id, formatted_positions) -> dict:
        bot_update = {
            enums.BotKeys.POSITIONS.value: formatted_positions
        }
        return await self.update_bot(
            bot_id, bot_update
        )

    async def fetch_bot_tentacles_data_based_config(
        self, bot_id: str, authenticator, auth_key: typing.Optional[str]
    ) -> (commons_profiles.ProfileData, list[commons_profiles.ExchangeAuthData]):
        if not bot_id:
            raise errors.BotNotFoundError(f"bot_id is '{bot_id}'")
        commons_logging.get_logger(__name__).debug(f"Fetching {bot_id} bot config")
        try:
            bot_config = (await self.table("bots").select(
                "id,"
                "name, "
                "bot_config:bot_configs!current_config_id!inner("
                    "id, "
                    "options, "
                    "exchanges, "
                    "is_simulated"
                ")"
            ).eq(enums.BotKeys.ID.value, bot_id).execute()).data[0]
        except IndexError:
            raise errors.MissingBotConfigError(f"No bot config for bot with bot_id: '{bot_id}'")
        commons_logging.get_logger(__name__).info(f"Fetched bot config: {bot_config['bot_config']}")
        bot_name = bot_config["name"]
        # generic options
        profile_data = commons_profiles.ProfileData(
            commons_profile_data.ProfileDetailsData(
                name=f"{bot_name}_fetched_config",
                id=str(uuid.uuid4()),
                bot_id=bot_id,
            ),
            [],
            commons_profile_data.TradingData(commons_constants.USD_LIKE_COINS[0])
        )
        auth_data = []
        # apply specific options
        await self._apply_options_based_authenticated_tentacles_config(
            profile_data, auth_data, bot_config["bot_config"], authenticator, auth_key
        )
        return profile_data, auth_data

    async def _apply_options_based_authenticated_tentacles_config(
        self, profile_data: commons_profiles.ProfileData,
        auth_data: list[commons_profiles.ExchangeAuthData], bot_config: dict,
        authenticator, auth_key: typing.Optional[str]
    ):
        # updates tentacles config using authenticated requests
        if tentacles_data := self.get_tentacles_data_options(bot_config):
            await commons_profiles.TentaclesProfileDataTranslator(profile_data, auth_data).translate(
                tentacles_data, bot_config, authenticator, auth_key
            )

    def _apply_options_based_tentacles_config(self, profile_data: commons_profiles.ProfileData, bot_config: dict):
        # updates tentacles config only from options, makes no request
        tentacle_data_overrides = self.get_tentacles_data_options(bot_config)
        if not tentacle_data_overrides:
            return
        self._include_tentacles_config(profile_data, tentacle_data_overrides)

    def _include_tentacles_config(
        self, profile_data: commons_profiles.ProfileData,
        tentacle_data_overrides: list[commons_profile_data.TentaclesData]
    ):
        tentacle_config_by_tentacle = {
            tentacle_config.name: tentacle_config.config
            for tentacle_config in profile_data.tentacles
        }
        for tentacle_data_override in tentacle_data_overrides:
            if tentacle_data_override.name in tentacle_config_by_tentacle:
                # tentacle data exists: patch values
                tentacle_config_by_tentacle[tentacle_data_override.name] = dict_util.nested_update_dict(
                    tentacle_config_by_tentacle[tentacle_data_override.name],
                    tentacle_data_override.config,
                    ignore_lists=True
                )
            else:
                # tentacle data doesn't exist: add it
                profile_data.tentacles.append(tentacle_data_override)

    def get_tentacles_data_options(self, bot_config: dict) -> list[commons_profile_data.TentaclesData]:
        return [
            commons_profile_data.TentaclesData.from_dict(td)
            for td in bot_config[enums.BotConfigKeys.OPTIONS.value].get(enums.BotConfigOptionsKeys.TENTACLES.value, [])
        ]

    async def fetch_bot_nested_config_profile_data_if_any(
        self,
        master_profile_config: typing.Optional[dict] = None,
        bot_config_options: typing.Optional[dict] = None,
        nested_config_id: typing.Optional[str] = None,
    ) -> typing.Optional[dict]:
        # one of master_profile_config, bot_config_options or nested_config_slug must be provided
        # if there is a nested config to be found
        to_fetch_nested_config = {}
        if bot_config_options:
            # use bot local config options as a priority when provided
            to_fetch_nested_config = bot_config_options.get(enums.NestedProductConfigKeys.NESTED_CONFIG_ROOT.value, {})
        if master_profile_config and not to_fetch_nested_config:
            # no nested config in bot local config options, try master product config
            to_fetch_nested_config = master_profile_config.get(enums.NestedProductConfigKeys.NESTED_CONFIG_ROOT.value, {})
        try:
            if to_fetch_nested_config:
                if nested_config_slug := to_fetch_nested_config.get(enums.NestedProductConfigKeys.SLUG.value):
                    nested_product_details = (await self.table("products").select(
                        "id, slug, attributes, current_config_id,"
                        "product_config:product_configs!current_config_id!inner("
                        "   id, "
                        "   config, "
                        "   version"
                        ")"
                    ).eq(enums.ProductKeys.SLUG.value, nested_config_slug).execute()).data[0]
                    # format as in fetch_bot_profile_data
                    nested_product_config = nested_product_details["product_config"]
                    nested_product_config["product"] = {
                        enums.ProductKeys.ID.value: nested_product_details[enums.ProductKeys.ID.value],
                        enums.ProductKeys.SLUG.value: nested_product_details[enums.ProductKeys.SLUG.value],
                        enums.ProductKeys.ATTRIBUTES.value: nested_product_details[enums.ProductKeys.ATTRIBUTES.value],
                    }
                    return nested_product_config
                # slug should be available if to_fetch_nested_config has been set
                key = (
                    f"bot_config.options.{enums.NestedProductConfigKeys.NESTED_CONFIG_ROOT.value}" if bot_config_options
                    else f"master product_config.config.{enums.NestedProductConfigKeys.NESTED_CONFIG_ROOT.value}"
                )
                raise TypeError(f"Invalid product nested config: {key} is '{to_fetch_nested_config}'")
            if nested_config_id:
                nested_product_config = (await self.table("product_configs").select(
                    "id, "
                    "config, "
                    "version, "
                    "product:products!product_id("
                    "   id, "
                    "   slug, "
                    "   attributes, "
                    "   current_config_id"  # current_config_id is required to identify product current config in updates
                    ")"
                ).eq(enums.ProfileConfigKeys.ID.value, nested_config_id).execute()).data[0]
                return nested_product_config
        except IndexError as err:
            raise errors.InvalidBotConfigError(
                f"Invalid nested product config: Nested product not found {err} ({err.__class__.__name__}). "
                f"{to_fetch_nested_config=} {nested_config_id=}"
            ) from err
        # no nested config or config id
        return None

    async def fetch_bot_profile_data(
        self, bot_config_id: str, usd_like_per_exchange: dict
    ) -> (commons_profiles.ProfileData, executed_product_details_import.ExecutedProductDetails):
        if not bot_config_id:
            raise errors.MissingBotConfigError(f"bot_config_id is '{bot_config_id}'")
        bot_config = (await self.table("bot_configs").select(
            "bot_id, "
            "options, "
            "exchanges, "
            "exchange_account_id, "
            "created_at, "
            "is_simulated, "
            "bot:bots!bot_id!inner(user_id, created_at), "
            "product_config:product_configs("
            "   config, "
            "   version, "
            "   product:products!product_id(slug, attributes, id)"
            ")"
        ).eq(enums.BotConfigKeys.ID.value, bot_config_id).execute()).data[0]
        nested_strategy_slug = nested_strategy_config_id = None
        bot_config_options = bot_config.get(enums.BotConfigKeys.OPTIONS.value) or {}
        try:
            bot_details = bot_config["bot"]
            master_product_config = bot_config["product_config"]
            master_profile_config = master_product_config[enums.ProfileConfigKeys.CONFIG.value]
            master_product_details = master_product_config.get("product", {})
            if not master_profile_config:
                raise TypeError(f"master product_config.config is '{master_profile_config}'")
            if nested_product_config := await self.fetch_bot_nested_config_profile_data_if_any(
                master_profile_config=master_profile_config, bot_config_options=bot_config_options
            ):
                # nested strategy: use nested strategy product config and details
                nested_product_details = nested_product_config.get("product", {})
                nested_strategy_slug = nested_product_details.get(enums.ProductKeys.SLUG.value, "")
                nested_strategy_config_id = nested_product_config.get(enums.ProfileConfigKeys.ID.value, "")
                # the nested strategy profile config will be executed
                executed_product_config = nested_product_config
                executed_profile_config = nested_product_config[enums.ProfileConfigKeys.CONFIG.value]
                # for nested strategy, use bot_config created_at: this is the time this product was selected
                executed_config_created_at = self.get_parsed_time(bot_config[enums.BotConfigKeys.CREATED_AT.value])
                executed_product_details = nested_product_details
            else:
                # non-nested strategy: use master product config
                executed_product_config = master_product_config
                executed_profile_config = master_profile_config
                # not a nested strategy: use actual bot creation time
                executed_config_created_at = self.get_parsed_time(bot_details[enums.BotKeys.CREATED_AT.value])
                executed_product_details = master_product_details
            # always build profile_data using the strategy the bot will actually execute, which might be a nested one
            profile_data = commons_profiles.ProfileData.from_dict(executed_profile_config)
        except (TypeError, KeyError) as err:
            raise errors.InvalidBotConfigError(f"Missing bot product config: {err} ({err.__class__.__name__})") from err
        profile_data.profile_details.name = formatters.create_profile_name(
            master_product_details.get(enums.ProductKeys.SLUG.value, "")
                or profile_data.profile_details.name,
            nested_strategy_slug
        )
        executed_product_details = executed_product_details_import.ExecutedProductDetails(
            executed_product_details.get(enums.ProductKeys.ID.value, ""), executed_config_created_at.timestamp()
        )
        profile_data.profile_details.nested_strategy_config_id = nested_strategy_config_id
        profile_data.profile_details.user_id = bot_details[enums.BotKeys.USER_ID.value]
        profile_data.profile_details.version = executed_product_config[enums.ProfileConfigKeys.VERSION.value]
        profile_data.profile_details.id = bot_config_id
        profile_data.trading.minimal_funds = [
            commons_profiles.MinimalFund.from_dict(minimal_fund)
            for minimal_fund in executed_product_config["product"][
                enums.ProductKeys.ATTRIBUTES.value
            ].get("minimal_funds", [])
        ]
        profile_data.trader_simulator.enabled = bot_config.get(enums.BotConfigKeys.IS_SIMULATED.value, False)
        profile_data.trading.sellable_assets = bot_config_options.get("sellable_assets")
        # only use exchanges from master product config to avoid exchange changes from swapped nested strategies
        master_product_exchanges_configs = master_product_config[enums.ProfileConfigKeys.CONFIG.value].get(
            "exchanges"
        )
        profile_data.exchanges, exchange_tentacles_data = await self._fetch_full_exchange_configs(
            bot_config, master_product_exchanges_configs, profile_data
        )
        if exchange_tentacles_data:
            self._include_tentacles_config(profile_data, exchange_tentacles_data)
        if bot_config_options:
            profile_data.options = commons_profiles.OptionsData.from_dict(bot_config_options)
            self._apply_options_based_tentacles_config(profile_data, bot_config)
        portfolio = bot_config_options.get("portfolio")
        if portfolio:
            exchange = profile_data.exchanges[0].internal_name if profile_data.exchanges else None
            if trading_api.is_usd_like_coin(profile_data.trading.reference_market):
                usd_like_asset = profile_data.trading.reference_market
            elif profile_data.trading.reference_market == formatters.USD_LIKE:
                # use proper reference market for exchange, defaulting to first USD_LIKE_COINS coin
                profile_data.trading.reference_market = usd_like_per_exchange.get(
                    exchange, commons_constants.USD_LIKE_COINS[0]
                )
                usd_like_asset = profile_data.trading.reference_market
            else:
                usd_like_asset = usd_like_per_exchange.get(exchange, commons_constants.USD_LIKE_COINS[0])
            try:
                formatted_portfolio = formatters.get_adapted_portfolio(
                    usd_like_asset, portfolio
                )
            except KeyError as err:
                raise errors.InvalidBotConfigError(
                    f"Invalid configured portfolio: {err} ({err.__class__.__name__})"
                ) from err
            profile_data.trader_simulator.starting_portfolio = formatted_portfolio
            profile_data.trading.sub_portfolio = formatted_portfolio
        elif profile_data.trader_simulator.enabled:
            # portfolio is required on trading simulator
            raise errors.InvalidBotConfigError("Missing portfolio in bot config")
        return profile_data, executed_product_details

    async def _fetch_full_exchange_configs(
        self, bot_config: dict, product_exchanges_configs, profile_data: commons_profiles.ProfileData
    ) -> (list[commons_profiles.ExchangeData], list[commons_profile_data.TentaclesData]):

        # ensure all required exchange info are available
        exchanges_configs = []
        exchange_account_id = None
        if exchange_account_id := bot_config.get(enums.BotConfigKeys.EXCHANGE_ACCOUNT_ID.value):
            # check 1: latest real bot config: use exchange_account_id when set in bot_config
            # if exchange_account_id is set, this config only runs on one exchange and should use this account current credentials
            exchange_id, credentials_id, exchange_details = await self.fetch_exchange_and_credential_ids_from_account_id(exchange_account_id)
            exchange_config = {
                # EXCHANGE_CREDENTIAL_ID is not set in latest real bot config
                enums.ExchangeKeys.EXCHANGE_ID.value: exchange_id,
                enums.ExchangeKeys.INTERNAL_NAME.value: exchange_details[enums.ExchangeKeys.INTERNAL_NAME.value],
                enums.ExchangeKeys.AVAILABILITY.value: exchange_details[enums.ExchangeKeys.AVAILABILITY.value],
                enums.ExchangeKeys.URL.value: exchange_details[enums.ExchangeKeys.URL.value],
            }
            exchanges_configs = [exchange_config]
        else:
            # check 2: latest simulated bot config: update exchange using exchange_id when set in bot_config
            incomplete_exchange_config_by_id = {
                config[enums.ExchangeKeys.EXCHANGE_ID.value]: config
                for config in (bot_config.get(enums.BotConfigKeys.EXCHANGES.value) or [])
                if (
                    config.get(enums.ExchangeKeys.EXCHANGE_ID.value, None)
                    and not (
                        config.get(enums.ExchangeKeys.INTERNAL_NAME.value, None)
                        and config.get(enums.ExchangeKeys.AVAILABILITY.value, None)
                    )
                )
            }
            if incomplete_exchange_config_by_id:
                fetched_exchanges = await self.fetch_exchanges(list(incomplete_exchange_config_by_id))
                exchanges_configs += [
                    {
                        **incomplete_exchange_config_by_id[exchange[enums.ExchangeKeys.ID.value]],
                        **{
                            enums.ExchangeKeys.INTERNAL_NAME.value: exchange[enums.ExchangeKeys.INTERNAL_NAME.value],
                            enums.ExchangeKeys.AVAILABILITY.value: exchange[enums.ExchangeKeys.AVAILABILITY.value],
                            enums.ExchangeKeys.URL.value: exchange[enums.ExchangeKeys.URL.value],
                        }
                    }
                    for exchange in fetched_exchanges
                ]
            # check 3: legacy real bot config: set exchange using credentials_id when set in bot_config
            incomplete_exchange_config_by_credentials_id = {
                config[enums.ExchangeKeys.EXCHANGE_CREDENTIAL_ID.value]: config
                for config in (bot_config.get(enums.BotConfigKeys.EXCHANGES.value) or [])
                if (
                    config.get(enums.ExchangeKeys.EXCHANGE_CREDENTIAL_ID.value, None)
                    and not config.get(enums.ExchangeKeys.EXCHANGE_ID.value, None)
                )
            }
            if incomplete_exchange_config_by_credentials_id:
                exchanges_by_credential_ids = await self.fetch_exchanges_by_credential_ids(
                    list(incomplete_exchange_config_by_credentials_id)
                )
                if len(incomplete_exchange_config_by_credentials_id) != len(exchanges_by_credential_ids):
                    missing = [
                        cred for cred in incomplete_exchange_config_by_credentials_id
                        if cred not in exchanges_by_credential_ids
                    ]
                    commons_logging.get_logger(self.__class__.__name__).error(
                        f"{len(missing)} exchange credentials id not found in db: {', '.join(missing)}"
                    )
                exchanges_configs += [
                    {
                        **incomplete_exchange_config_by_credentials_id[credentials_id],
                        **{
                            enums.ExchangeKeys.EXCHANGE_ID.value: exchange[enums.ExchangeKeys.ID.value],
                            enums.ExchangeKeys.INTERNAL_NAME.value: exchange[enums.ExchangeKeys.INTERNAL_NAME.value],
                            enums.ExchangeKeys.AVAILABILITY.value: exchange[enums.ExchangeKeys.AVAILABILITY.value],
                            enums.ExchangeKeys.URL.value: exchange[enums.ExchangeKeys.URL.value],
                        }
                    }
                    for credentials_id, exchange in exchanges_by_credential_ids.items()
                ]
            if not exchanges_configs:
                if profile_data.trader_simulator.enabled:
                    # last attempt (simulator only): use exchange details from product config
                    internal_names = [
                        exchanges_config[enums.ExchangeKeys.INTERNAL_NAME.value]
                        for exchanges_config in product_exchanges_configs
                    ]
                    fetched_exchanges = await self.fetch_exchanges([], internal_names=internal_names)
                    exchanges_configs += [
                        {
                            enums.ExchangeKeys.EXCHANGE_ID.value: exchange[enums.ExchangeKeys.ID.value],
                            enums.ExchangeKeys.INTERNAL_NAME.value: exchange[enums.ExchangeKeys.INTERNAL_NAME.value],
                            enums.ExchangeKeys.AVAILABILITY.value: exchange[enums.ExchangeKeys.AVAILABILITY.value],
                            enums.ExchangeKeys.URL.value: exchange[enums.ExchangeKeys.URL.value],
                        }
                        for exchange in fetched_exchanges
                        # no way to differentiate futures and spot exchanges using internal_names only:
                        # use spot exchange here by default
                        if (
                            formatters.get_exchange_type_from_availability(
                                exchange.get(enums.ExchangeKeys.AVAILABILITY.value)
                            )
                            == commons_constants.CONFIG_EXCHANGE_SPOT
                        )
                    ]
                else:
                    commons_logging.get_logger(self.__class__.__name__).error(
                        f"Impossible to fetch exchange details for profile with bot id: {profile_data.profile_details.id}"
                    )
        # Register exchange_type from exchange availability
        exchange_type = commons_constants.CONFIG_EXCHANGE_SPOT
        if exchanges_configs:
            # Multi exchange type configurations are not yet supported
            exchange_type = formatters.get_exchange_type_from_availability(
                exchanges_configs[0].get(
                    enums.ExchangeKeys.AVAILABILITY.value
                )
            )
        exchange_tentacles_data = []
        for exchange_data in exchanges_configs:
            exchange_data[enums.ExchangeKeys.EXCHANGE_TYPE.value] = exchange_type
            exchange_data[enums.ExchangeKeys.INTERNAL_NAME.value] = formatters.to_bot_exchange_internal_name(
                exchange_data[enums.ExchangeKeys.INTERNAL_NAME.value]
            )
            if (
                (exchanges_credentials_id := exchange_data.get(enums.ExchangeKeys.EXCHANGE_CREDENTIAL_ID.value))
                and exchange_account_id is None
            ):
                # legacy bot_config compatibility: ensure exchange_account_id is set if missing
                exchange_account_id = await self.fetch_exchange_accounts_id_from_credential_id(exchanges_credentials_id)
            # always bind exchange_account_id when available
            exchange_data[enums.BotConfigKeys.EXCHANGE_ACCOUNT_ID.value] = exchange_account_id
            if url := exchange_data.get(enums.ExchangeKeys.URL.value):
                exchange_tentacles_data.append(
                    formatters.get_tentacles_data_exchange_config(
                        exchange_data[enums.ExchangeKeys.INTERNAL_NAME.value], url
                    )
                )
        return [
            commons_profiles.ExchangeData.from_dict(exchange_data)
            for exchange_data in exchanges_configs
        ], exchange_tentacles_data

    async def fetch_exchanges(
        self, 
        exchange_ids: typing.Optional[list] = None,
        internal_names: typing.Optional[list] = None, 
        availabilities: typing.Optional[list[enums.ExchangeAvailabilities]] = None
    ) -> list:
        # WARNING: setting internal_names can result in duplicate (futures and spot) exchanges
        select = self.table("exchanges").select(
            f"{enums.ExchangeKeys.ID.value}, "
            f"{enums.ExchangeKeys.INTERNAL_NAME.value}, "
            f"{enums.ExchangeKeys.URL.value}, "
            f"{enums.ExchangeKeys.AVAILABILITY.value}, "
            f"{enums.ExchangeKeys.TRUSTED_IPS.value}"
        )
        if internal_names:
            select = select.in_(enums.ExchangeKeys.INTERNAL_NAME.value, internal_names)
        if exchange_ids:
            select = select.in_(enums.ExchangeKeys.ID.value, exchange_ids)
        exchanges = (await select.execute()).data
        if availabilities:
            exchanges = [
                exchange for exchange in exchanges
                if self.is_compatible_availability(
                    exchange[enums.ExchangeKeys.AVAILABILITY.value], availabilities
                )
            ]
        return exchanges

    async def fetch_exchange_and_credential_ids_from_account_id(
        self, exchange_account_id: str
    ) -> (str, str, dict):
        select = self.table("exchange_accounts").select(
            f"exchange_id, current_exchange_credentials_id,"
            f"exchange:exchanges!exchange_id!inner("
            f"  {enums.ExchangeKeys.ID.value}, "
            f"  {enums.ExchangeKeys.INTERNAL_NAME.value}, "
            f"  {enums.ExchangeKeys.URL.value}, "
            f"  {enums.ExchangeKeys.AVAILABILITY.value}"           
            f")" 
        ).eq(
            "id", exchange_account_id
        )
        exchange_accounts = (await select.execute()).data
        if len(exchange_accounts) != 1:
            raise errors.InvalidBotConfigError(f"Exchange account with id: {exchange_account_id} and associated exchange not found")
        return (
            exchange_accounts[0]["exchange_id"], 
            exchange_accounts[0]["current_exchange_credentials_id"],
            exchange_accounts[0]["exchange"]
        )

    @staticmethod
    def is_compatible_availability(
        exchange_availability: typing.Optional[dict[str, str]], availabilities: list[enums.ExchangeAvailabilities]
    ) -> bool:
        return bool(
            exchange_availability and any(
                exchange_availability.get(availability.value) == enums.ExchangeSupportValues.SUPPORTED.value
                for availability in availabilities
            )
        )

    async def fetch_exchanges_by_credential_ids(self, exchange_credential_ids: list) -> dict:
        exchanges = (await self.table("exchange_credentials").select(
            "id,"
            f"exchange:exchanges("
            f"  {enums.ExchangeKeys.ID.value}, "
            f"  {enums.ExchangeKeys.INTERNAL_NAME.value}, "
            f"  {enums.ExchangeKeys.URL.value}, "
            f"  {enums.ExchangeKeys.AVAILABILITY.value}"
            f")"
        ).in_("id", exchange_credential_ids).execute()).data
        return {
            exchange["id"]: exchange["exchange"]
            for exchange in exchanges
        }

    async def fetch_exchange_accounts_id_from_credential_id(self, exchange_credential_id: str) -> typing.Optional[str]:
        rows = (await self.table("exchange_credentials").select(
            "exchange_accounts_id"
        ).eq("id", exchange_credential_id).execute()).data
        if len(rows) != 1:
            raise errors.InvalidBotConfigError(f"Exchange credential with id: {exchange_credential_id} not found")
        return rows[0]["exchange_accounts_id"]

    async def fetch_product_config(self, product_id: str, product_slug: str = None) -> commons_profiles.ProfileData:
        if not product_id and not product_slug:
            raise errors.MissingProductConfigError(f"product_id is '{product_id}'")
        try:
            query = self.table("products").select(
                "slug, "
                "product_config:product_configs!current_config_id(config, version), "
                "category:product_categories!inner(slug)"
            )
            query = query.eq(enums.ProductKeys.SLUG.value, product_slug) if product_slug \
                else query.eq(enums.ProductKeys.ID.value, product_id)
            product = (await query.execute()).data[0]
        except IndexError:
            raise errors.MissingProductConfigError(f"Missing product with id '{product_id}'")
        profile_data = commons_profiles.ProfileData.from_dict(
            product["product_config"][enums.ProfileConfigKeys.CONFIG.value]
        )
        name = product["slug"]
        if strategy_data.is_custom_category(product["category"]):
            name = strategy_data.get_custom_strategy_name(name)
        profile_data.profile_details.name = name
        profile_data.profile_details.version = product["product_config"][enums.ProfileConfigKeys.VERSION.value]
        return profile_data

    async def fetch_configs(self, bot_id: str) -> list:
        # use a new current portfolio for the given bot
        return (await self.table("bot_configs").select("*").eq(
            enums.BotConfigKeys.BOT_ID.value, bot_id
        ).execute()).data

    async def fetch_portfolios(self, bot_id: str) -> list:
        return (await self.table("bot_portfolios").select("*").eq(
            enums.PortfolioKeys.BOT_ID.value, bot_id
        ).execute()).data

    async def fetch_portfolio_from_id(self, portfolio_id: str) -> list:
        return (await self.table("bot_portfolios").select("*").eq(
            enums.PortfolioKeys.ID.value, portfolio_id
        ).execute()).data

    async def update_portfolio(self, portfolio_update: dict) -> list:
        # use a new current portfolio for the given bot
        return (await self.table("bot_portfolios").update(portfolio_update).eq(
            enums.PortfolioKeys.ID.value, portfolio_update[enums.PortfolioKeys.ID.value]
        ).execute()).data

    async def switch_portfolio(self, new_portfolio) -> dict:
        # use a new current portfolio for the given bot
        bot_id = new_portfolio[enums.PortfolioKeys.BOT_ID.value]
        inserted_portfolio = (await self.table("bot_portfolios").insert(new_portfolio).execute()).data[0]
        await self.update_bot(
            bot_id,
            {enums.BotKeys.CURRENT_PORTFOLIO_ID.value: inserted_portfolio[enums.PortfolioKeys.ID.value]}
        )
        return inserted_portfolio

    async def fetch_portfolio_history(self, portfolio_id) -> list:
        return (await self.table("bot_portfolio_histories").select("*").eq(
            enums.PortfolioHistoryKeys.PORTFOLIO_ID.value, portfolio_id
        ).execute()).data

    async def upsert_portfolio_history(self, portfolio_histories) -> list:
        return (await self.table("bot_portfolio_histories").upsert(
            portfolio_histories,
            on_conflict=f"{enums.PortfolioHistoryKeys.TIME.value},{enums.PortfolioHistoryKeys.PORTFOLIO_ID.value}"
        ).execute()).data

    async def fetch_gpt_signal(
        self, exchange: str, symbol: str, time_frame: commons_enums.TimeFrames, timestamp: float, version: str
    ) -> str:
        signals = (await (await self.get_production_anon_client()).table("temp_chatgpt_signals").select("signal").match(
            {
                "timestamp": self.get_formatted_time(timestamp),
                # "exchange_internal_name": exchange,
                "symbol": symbol,
                "time_frame": time_frame.value,
                "metadata->>version": version,
            },
        ).execute()).data
        if signals:
            return signals[0]["signal"]["content"]
        return ""

    async def fetch_gpt_signals_history(
        self, exchange: typing.Union[str, None], symbol: str, time_frame: commons_enums.TimeFrames,
        first_open_time: float, last_open_time: float, version: str
    ) -> dict:
        matcher = {
            "symbol": symbol,
            "time_frame": time_frame.value,
            "metadata->>version": version,
        }
        if exchange:
            matcher["exchange_internal_name"] = exchange
        historical_signals = await self._paginated_fetch_historical_data(
            await self.get_production_anon_client(),
            "temp_chatgpt_signals",
            "timestamp, signal",
            matcher,
            first_open_time,
            last_open_time
        )
        return self._format_gpt_signals(historical_signals)

    async def get_production_anon_client(self):
        if self.production_anon_client is None:
            self.production_anon_client = await self.init_other_postgrest_client(
                supabase_url=constants.COMMUNITY_PRODUCTION_BACKEND_URL,
                supabase_key=constants.COMMUNITY_PRODUCTION_BACKEND_KEY,
            )
        return self.production_anon_client

    # def _get_production_anon_auth_headers(self):
    #     return self._get_anon_auth_headers(constants.COMMUNITY_PRODUCTION_BACKEND_KEY)

    async def production_anon_rpc(self):
        return (await self.get_production_anon_client()).rpc

    async def _paginated_fetch_historical_data(
        self, client, table_name: str, select: str, matcher: dict,
        first_open_time: float, last_open_time: float
    ) -> list:
        def request_factory(table: postgrest.AsyncRequestBuilder, select_count, last_fetched_row):
            request = table.select(select, count=select_count)
            if last_fetched_row is None:
                request = request.match(matcher).gte(
                    "timestamp", self.get_formatted_time(first_open_time)
                )
            else:
                request = request.match(matcher).gt(
                    "timestamp", last_fetched_row["timestamp"]
                )
            return (
                request.lte(
                    "timestamp", self.get_formatted_time(last_open_time)
                ).order(
                    "timestamp", desc=False
                )
            )

        return await self.cursor_paginated_fetch(
            client, table_name, request_factory
        )

    async def paginated_fetch(
        self,
        client,
        table_name: str,
        request_factory: typing.Callable[
            [postgrest.AsyncRequestBuilder, postgrest.types.CountMethod], postgrest.AsyncSelectRequestBuilder
        ],
    ) -> list:
        offset = 0
        max_size_per_fetch = 0
        total_elements = []
        request_count = 0
        total_elements_count = 0
        while request_count < self.MAX_PAGINATED_REQUESTS_COUNT:
            request = request_factory(
                client.table(table_name),
                None if total_elements_count else postgrest.types.CountMethod.exact
            )
            if offset:
                request = request.range(offset, offset+max_size_per_fetch)
            result = await request.execute()
            fetched_elements = result.data
            total_elements_count = total_elements_count or result.count   # don't change total count within iteration
            total_elements += fetched_elements
            if(
                len(fetched_elements) == 0 or   # nothing to fetch
                len(fetched_elements) < max_size_per_fetch or   # fetched the last elements
                len(fetched_elements) == total_elements_count   # finished fetching
            ):
                # fetched everything
                break
            offset += len(fetched_elements)
            if max_size_per_fetch == 0:
                max_size_per_fetch = offset
            request_count += 1

        if request_count == self.MAX_PAGINATED_REQUESTS_COUNT:
            commons_logging.get_logger(self.__class__.__name__).info(
                f"Paginated fetch error on {table_name} with request_factory: {request_factory.__name__}: "
                f"too many requests ({request_count}), fetched: {len(total_elements)} elements"
            )
        return total_elements

    async def cursor_paginated_fetch(
        self,
        client,
        table_name: str,
        request_factory: typing.Callable[
            [postgrest.AsyncRequestBuilder, postgrest.types.CountMethod, typing.Optional[dict]],
            postgrest.AsyncSelectRequestBuilder
        ],
    ) -> list:
        max_size_per_fetch = 0
        total_elements = []
        request_count = 0
        total_elements_count = 0
        while request_count < self.MAX_PAGINATED_REQUESTS_COUNT:
            request = request_factory(
                client.table(table_name),
                None if total_elements_count else postgrest.types.CountMethod.exact,
                total_elements[-1] if total_elements else None
            )
            result = await request.execute()
            fetched_elements = result.data
            total_elements_count = total_elements_count or result.count   # don't change total count within iteration
            total_elements += fetched_elements
            if(
                len(fetched_elements) == 0 or   # nothing to fetch
                len(fetched_elements) < max_size_per_fetch or   # fetched the last elements
                len(fetched_elements) == total_elements_count   # finished fetching
            ):
                # fetched everything
                break
            if max_size_per_fetch == 0:
                max_size_per_fetch = len(fetched_elements)
            request_count += 1

        if request_count == self.MAX_PAGINATED_REQUESTS_COUNT:
            commons_logging.get_logger(self.__class__.__name__).info(
                f"Paginated fetch error on {table_name} with request_factory: {request_factory.__name__}: "
                f"too many requests ({request_count}), fetched: {len(total_elements)} elements"
            )
        return total_elements

    def _format_gpt_signals(self, signals: list):
        return {
            self.get_parsed_time(signal["timestamp"]).timestamp(): signal["signal"]["content"]
            for signal in signals
        }

    async def upload_asset(self, bucket_name: str, asset_name: str, content: typing.Union[str, bytes],) -> str:
        """
        Not implemented for authenticated users
        """
        result = await self.storage.from_(bucket_name).upload(asset_name, content)
        return result.path

    async def list_assets(self, bucket_name: str) -> list[dict[str, str]]:
        """
        Not implemented for authenticated users
        """
        return await self.storage.from_(bucket_name).list()

    async def remove_asset(self, bucket_name: str, asset_path: str) -> None:
        """
        Not implemented for authenticated users
        """
        await self.storage.from_(bucket_name).remove([asset_path])

    async def send_signal(self, table, product_id: str, signal: str):
        return (await self.table(table).insert({
            enums.SignalKeys.TIME.value: self.get_formatted_time(time.time()),
            enums.SignalKeys.PRODUCT_ID.value: product_id,
            enums.SignalKeys.SIGNAL.value: signal,
        }).execute()).data[0]

    def get_subscribed_channel_tables(self) -> set:
        return set(
            channel.table_name
            for channel in self.realtime.channels
        )

    def is_realtime_connected(self) -> bool:
        return self.realtime.is_connected

    def _get_auth_key(self):
        if session := self.get_in_saved_session():
            return session.access_token
        return self.supabase_key

    @staticmethod
    def get_formatted_time(timestamp: float) -> str:
        # don't include timezone offset (+00:00) as this is always a UTC time
        return datetime.datetime.fromtimestamp(
            timestamp, datetime.timezone.utc
        ).isoformat(sep='T').replace("+00:00", "")

    @staticmethod
    def get_parsed_time(str_time: str) -> datetime.datetime:
        try:
            # no fractional seconds, no timezone
            return datetime.datetime.strptime(str_time, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            try:
                # fractional seconds, no timezone
                return datetime.datetime.strptime(str_time, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=datetime.timezone.utc)
            except ValueError:
                # last chance, try using iso format (ex: 2011-11-04T00:05:23.283+04:00)
                try:
                    # potential fractional seconds & timezone
                    return datetime.datetime.fromisoformat(str_time)
                except ValueError:
                    # removed fractional seconds & timezone
                    # sometimes fractional seconds are not supported, ex:
                    # '2023-09-04T00:01:31.06381+00:00'
                    if "." in str_time and "+" in str_time:
                        without_ms_time = str_time[0:str_time.rindex(".")] + str_time[str_time.rindex("+"):]
                        # convert to '2023-09-04T00:01:31+00:00'
                        return datetime.datetime.fromisoformat(without_ms_time)
                    raise

    async def _get_user(self) -> supabase_auth.User:
        if user := await self.auth.get_user():
            return user.user
        raise authentication.AuthenticationError("Please login to your OctoBot account")

    async def aclose(self):
        await super().aclose()
        if self.production_anon_client is not None:
            try:
                await self.production_anon_client.aclose()
            except RuntimeError:
                # happens when the event loop is closed already
                pass
            self.production_anon_client = None


def _is_jwt_expired_error(err: Exception) -> bool:
    return "jwt expired" in str(err).lower()


@contextlib.contextmanager
def jwt_expired_auth_raiser():
    try:
        yield
    except postgrest.exceptions.APIError as err:
        if _is_jwt_expired_error(err):
            raise errors.JWTExpiredError(f"Please re-login to your OctoBot account: {err}") from err
        raise
