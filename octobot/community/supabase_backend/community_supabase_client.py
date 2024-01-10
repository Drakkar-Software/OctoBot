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
import datetime
import json
import time
import typing
import logging

import aiohttp
import gotrue.errors
import supabase.lib.client_options

import octobot_commons.authentication as authentication
import octobot_commons.logging as commons_logging
import octobot_commons.profiles as commons_profiles
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_trading.api as trading_api
import octobot.constants as constants
import octobot.community.errors as errors
import octobot.community.models.formatters as formatters
import octobot.community.supabase_backend.enums as enums
import octobot.community.supabase_backend.supabase_client as supabase_client
import octobot.community.supabase_backend.configuration_storage as configuration_storage


# Experimental to prevent httpx.PoolTimeout
_INTERNAL_LOGGERS = [
    # "httpx", "httpx._client",
    # "httpcore.http11", "httpcore.http2", "httpcore.proxy", "httpcore.socks", "httpcore.connection"
]
# disable httpx info logs as it logs every request
commons_logging.set_logging_level(_INTERNAL_LOGGERS, logging.WARNING)


class CommunitySupabaseClient(supabase_client.AuthenticatedAsyncSupabaseClient):
    """
    Octobot Community layer added to supabase_client.AuthenticatedSupabaseClient
    """
    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        storage: configuration_storage.SyncConfigurationStorage,
        options: supabase.lib.client_options.ClientOptions = supabase.lib.client_options.ClientOptions(),
    ):
        options.storage = storage   # use configuration storage
        self.event_loop = None
        super().__init__(supabase_url, supabase_key, options=options)
        self.is_admin = False
        self.production_anon_client = None

    async def sign_in(self, email: str, password: str) -> None:
        try:
            self.event_loop = asyncio.get_event_loop()
            self.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
        except gotrue.errors.AuthApiError as err:
            if "email" in str(err).lower():
                raise errors.EmailValidationRequiredError(err) from err
            raise authentication.FailedAuthentication(err) from err

    async def sign_up(self, email: str, password: str) -> None:
        try:
            self.event_loop = asyncio.get_event_loop()
            self.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "hasRegisteredFromSelfHosted": True
                    }
                }
            })
        except gotrue.errors.AuthApiError as err:
            raise authentication.AuthenticationError(err) from err

    def sign_out(self) -> None:
        self.auth.sign_out()

    def restore_session(self):
        self.event_loop = asyncio.get_event_loop()
        self.auth.initialize_from_storage()
        if not self.is_signed_in():
            raise authentication.FailedAuthentication()

    async def sign_in_with_otp_token(self, token):
        self.event_loop = asyncio.get_event_loop()
        # restore saved session in case otp token fails
        saved_session = self.auth._storage.get_item(self.auth._storage_key)
        try:
            url = f"{self.auth_url}/verify?token={token}&type=magiclink"
            async with aiohttp.ClientSession() as client:
                resp = await client.get(url, allow_redirects=False)
                self.auth.initialize_from_url(
                    resp.headers["Location"].replace("#access_token", "?access_token").replace("#error", "?error")
                )
        except gotrue.errors.AuthImplicitGrantRedirectError as err:
            if saved_session:
                self.auth._storage.set_item(self.auth._storage_key, saved_session)
            raise authentication.AuthenticationError(err) from err

    def is_signed_in(self) -> bool:
        try:
            return self.auth.get_session() is not None
        except gotrue.errors.AuthApiError as err:
            commons_logging.get_logger(self.__class__.__name__).info(f"Authentication error: {err}")
            # remove invalid session from
            self.remove_session_details()
            return False

    def has_login_info(self) -> bool:
        return bool(self.auth._storage.get_item(self.auth._storage_key))

    async def update_metadata(self, metadata_update) -> dict:
        return self.auth.update_user({
            "data": metadata_update
        }).user.dict()

    async def get_user(self) -> dict:
        try:
            return (await self._get_user()).dict()
        except gotrue.errors.AuthApiError as err:
            if "missing" in str(err):
                raise errors.EmailValidationRequiredError(err) from err
            raise authentication.AuthenticationError(err) from err

    def sync_get_user(self) -> dict:
        return self.auth.get_user().user.dict()

    async def fetch_bot(self, bot_id) -> dict:
        try:
            # https://postgrest.org/en/stable/references/api/resource_embedding.html#hint-disambiguation
            return (await self.table("bots").select("*,bot_deployment:bot_deployments!bots_current_deployment_id_fkey(*)").eq(
                enums.BotKeys.ID.value, bot_id
            ).execute()).data[0]
        except IndexError:
            raise errors.BotNotFoundError(f"Can't find bot with id: {bot_id}")

    async def fetch_bots(self) -> list:
        return (await self.table("bots").select("*,bot_deployment:bot_deployments!bots_current_deployment_id_fkey!inner(*)").execute()).data

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
        return (await self.table("bot_deployments").insert({
            enums.BotDeploymentKeys.TYPE.value: deployment_type.value,
            enums.BotDeploymentKeys.VERSION.value: version,
            enums.BotDeploymentKeys.BOT_ID.value: bot_id,
        }).execute()).data[0]

    async def update_bot(self, bot_id, bot_update) -> dict:
        await self.table("bots").update(bot_update).eq(enums.BotKeys.ID.value, bot_id).execute()
        # fetch bot to fetch embed elements (like deployments)
        return await self.fetch_bot(bot_id)

    async def update_deployment(self, deployment_id, deployment_update) -> dict:
        return (await self.table("bot_deployments").update(deployment_update).eq(
            enums.BotDeploymentKeys.ID.value, deployment_id
        ).execute()).data[0]

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
        return json.loads(
            (await self.postgres_functions().invoke("get_startup_info", {"body": {"bot_id": bot_id}}))["data"]
        )[0]

    async def fetch_products(self) -> list:
        return (
            await self.table("products").select(
                "*,"
                "category:product_categories!inner(slug, name_translations, type, metadata),"
                "results:product_results!products_current_result_id_fkey("
                "  profitability,"
                "  reference_market_profitability"
                ")"
            ).eq(
                enums.ProductKeys.VISIBILITY.value, "public"
            )
            .execute()
        ).data

    async def fetch_subscribed_products_urls(self) -> list:
        return json.loads(
            (await self.postgres_functions().invoke("get_subscribed_products_urls", {}))["data"]
        ) or []

    async def fetch_bot_products_subscription(self, bot_deployment_id: str) -> dict:
        return (await self.table("bot_deployments").select(
            "products_subscription:products_subscriptions!product_subscription_id(id, status, desired_status)"
        ).eq(
            enums.BotDeploymentKeys.ID.value, bot_deployment_id
        ).execute()).data[0]["products_subscription"]

    async def fetch_trades(self, bot_id) -> list:
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

    async def fetch_bot_profile_data(self, bot_config_id: str) -> commons_profiles.ProfileData:
        if not bot_config_id:
            raise errors.MissingBotConfigError(f"bot_config_id is '{bot_config_id}'")
        bot_config = (await self.table("bot_configs").select(
            "bot_id, "
            "options, "
            "exchanges, "
            "is_simulated, "
            "product_config:product_configs("
            "   config, "
            "   version, "
            "   product:products!product_id(attributes)"
            ")"
        ).eq(enums.BotConfigKeys.ID.value, bot_config_id).execute()).data[0]
        profile_data = commons_profiles.ProfileData.from_dict(
            bot_config["product_config"][enums.ProfileConfigKeys.CONFIG.value]
        )
        profile_data.trading.minimal_funds = [
            commons_profiles.MinimalFund.from_dict(minimal_fund)
            for minimal_fund in bot_config["product_config"]["product"][
                enums.ProductKeys.ATTRIBUTES.value
            ].get("minimal_funds", [])
        ] if bot_config[enums.BotConfigKeys.EXCHANGES.value] else []
        profile_data.profile_details.version = bot_config["product_config"][enums.ProfileConfigKeys.VERSION.value]
        profile_data.trader_simulator.enabled = bot_config.get("is_simulated", False)
        if profile_data.trader_simulator.enabled:
            portfolio = (bot_config.get(
                enums.BotConfigKeys.OPTIONS.value
            ) or {}).get("portfolio")
            if trading_api.is_usd_like_coin(profile_data.trading.reference_market):
                usd_like_asset = profile_data.trading.reference_market
            else:
                usd_like_asset = "USDT"  # todo use dynamic value when exchange is not supporting USDT
            profile_data.trader_simulator.starting_portfolio = formatters.get_adapted_portfolio(
                usd_like_asset, portfolio
            )
        exchanges_config = (
            # use product config exchanges when no exchange is set in bot_config and when in simulator mode
            bot_config["product_config"][enums.ProfileConfigKeys.CONFIG.value]["exchanges"]
            if profile_data.trader_simulator.enabled
            # otherwise use botconfig exchange id
            else bot_config[enums.BotConfigKeys.EXCHANGES.value] if bot_config[enums.BotConfigKeys.EXCHANGES.value]
            else []
        )
        profile_data.exchanges = [
            commons_profiles.ExchangeData.from_dict(exchange_data)
            for exchange_data in exchanges_config
        ]
        if options := bot_config.get(enums.BotConfigKeys.OPTIONS.value):
            profile_data.options = commons_profiles.OptionsData.from_dict(options)
        profile_data.profile_details.id = bot_config_id
        return profile_data

    async def fetch_product_config(self, product_id: str) -> commons_profiles.ProfileData:
        if not product_id:
            raise errors.MissingProductConfigError(f"product_id is '{product_id}'")
        try:
            product = (await self.table("products").select(
                "product_config:product_configs!current_config_id(config, version)"
            ).eq(enums.ProductKeys.ID.value, product_id).execute()).data[0]
        except IndexError:
            raise errors.MissingProductConfigError(f"Missing product with id '{product_id}'")
        profile_data = commons_profiles.ProfileData.from_dict(
            product["product_config"][enums.ProfileConfigKeys.CONFIG.value]
        )
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

    async def update_portfolio(self, portfolio) -> list:
        # use a new current portfolio for the given bot
        return (await self.table("bot_portfolios").update(portfolio).eq(
            enums.PortfolioKeys.ID.value, portfolio[enums.PortfolioKeys.ID.value]
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

    async def fetch_candles_history_range(
        self, exchange: str, symbol: str, time_frame: commons_enums.TimeFrames
    ) -> (typing.Union[float, None], typing.Union[float, None]):
        min_max = json.loads(
            (await self.postgres_functions().invoke(
                "get_ohlcv_range",
                {"body": {
                    "exchange_internal_name": exchange,
                    "symbol": symbol,
                    "time_frame": time_frame.value,
                }}
            ))["data"]
        )[0]
        return (
            self.get_parsed_time(min_max["min_value"]).timestamp() if min_max["min_value"] else None,
            self.get_parsed_time(min_max["max_value"]).timestamp() if min_max["max_value"] else None,
        )

    async def fetch_candles_history(
        self, exchange: str, symbol: str, time_frame: commons_enums.TimeFrames,
        first_open_time: float, last_open_time: float
    ) -> list:
        historical_candles = await self._fetch_paginated_history(
            await self.get_production_anon_client(),
            "temp_ohlcv_history",
            "timestamp, open, high, low, close, volume",
            {
                "exchange_internal_name": exchange,
                "symbol": symbol,
                "time_frame": time_frame.value,
            },
            commons_enums.TimeFramesMinutes[time_frame] * commons_constants.MINUTE_TO_SECONDS,
            first_open_time,
            last_open_time
        )
        return self._format_ohlcvs(historical_candles)

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
        historical_signals = await self._fetch_paginated_history(
            await self.get_production_anon_client(),
            "temp_chatgpt_signals",
            "timestamp, signal",
            matcher,
            commons_enums.TimeFramesMinutes[time_frame] * commons_constants.MINUTE_TO_SECONDS,
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

    async def _fetch_paginated_history(
        self, client, table_name: str, select: str, matcher: dict,
        time_interval: float, first_open_time: float, last_open_time: float
    ) -> list:
        total_elements_count = (last_open_time - first_open_time) // time_interval
        offset = 0
        max_size = 0
        total_elements = []
        max_requests_count = 100
        request_count = 0
        while request_count < max_requests_count:
            request = (
                client.table(table_name).select(select)
                .match(matcher).gte(
                    "timestamp", self.get_formatted_time(first_open_time)
                ).lte(
                    "timestamp", self.get_formatted_time(last_open_time)
                ).order(
                    "timestamp", desc=False
                )
            )
            if offset:
                request = request.range(offset, offset+max_size)
            fetched_elements = (await request.execute()).data
            total_elements += fetched_elements
            if(
                len(fetched_elements) == 0 or
                len(fetched_elements) < max_size or
                (max_size == 0 and len(fetched_elements) == total_elements_count)
            ):
                # fetched everything
                break
            offset += len(fetched_elements)
            if max_size == 0:
                max_size = offset
            request_count += 1

        if request_count == max_requests_count:
            commons_logging.get_logger(self.__class__.__name__).info(
                f"paginated fetch error on {table_name} with matcher: {matcher}: "
                f"too many requests ({request_count}), fetched: {len(total_elements)} elements"
            )
        return total_elements

    def _format_gpt_signals(self, signals: list):
        return {
            self.get_parsed_time(signal["timestamp"]).timestamp(): signal["signal"]["content"]
            for signal in signals
        }

    def _format_ohlcvs(self, ohlcvs: list):
        # uses PriceIndexes order
        # IND_PRICE_TIME = 0
        # IND_PRICE_OPEN = 1
        # IND_PRICE_HIGH = 2
        # IND_PRICE_LOW = 3
        # IND_PRICE_CLOSE = 4
        # IND_PRICE_VOL = 5
        return [
            [
                int(self.get_parsed_time(ohlcv["timestamp"]).timestamp()),
                ohlcv["open"],
                ohlcv["high"],
                ohlcv["low"],
                ohlcv["close"],
                ohlcv["volume"],
            ]
            for ohlcv in ohlcvs
        ]

    async def get_asset_id(self, bucket_id: str, asset_name: str) -> str:
        """
        Not implemented for authenticated users
        """
        async with self.other_postgres_client("storage") as client:
            return (await client.from_("objects").select("*")
                .eq(
                    "bucket_id", bucket_id
                ).eq(
                    "name", asset_name
                ).execute()
            ).data[0]["id"]

    async def upload_asset(self, bucket_name: str, asset_name: str, content: typing.Union[str, bytes],) -> str:
        """
        Not implemented for authenticated users
        """
        result = await self.storage.from_(bucket_name).upload(asset_name, content)
        return asset_name

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
        return self.realtime.socket and self.realtime.socket.connected and not self.realtime.socket.closed

    @staticmethod
    def get_formatted_time(timestamp: float) -> str:
        return datetime.datetime.utcfromtimestamp(timestamp).isoformat('T')

    @staticmethod
    def get_parsed_time(str_time: str) -> datetime.datetime:
        try:
            return datetime.datetime.strptime(str_time, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            try:
                return datetime.datetime.strptime(str_time, "%Y-%m-%dT%H:%M:%S.%f")
            except ValueError:
                # last chance, try using iso format (ex: 2011-11-04T00:05:23.283+04:00)
                try:
                    return datetime.datetime.fromisoformat(str_time)
                except ValueError:
                    # sometimes fractional seconds are not supported, ex:
                    # '2023-09-04T00:01:31.06381+00:00'
                    if "." in str_time and "+" in str_time:
                        without_ms_time = str_time[0:str_time.rindex(".")] + str_time[str_time.rindex("+"):]
                        # convert to '2023-09-04T00:01:31+00:00'
                        return datetime.datetime.fromisoformat(without_ms_time)
                    raise

    async def _get_user(self) -> gotrue.User:
        return self.auth.get_user().user

    async def close(self):
        await super().close()
        if self.production_anon_client is not None:
            try:
                await self.production_anon_client.aclose()
            except RuntimeError:
                # happens when the event loop is closed already
                pass
            self.production_anon_client = None
