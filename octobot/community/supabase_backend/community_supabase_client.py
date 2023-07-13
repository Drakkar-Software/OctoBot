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

import aiohttp
import gotrue.errors
import supabase.lib.client_options

import octobot_commons.authentication as authentication
import octobot_commons.logging as logging
import octobot_commons.profiles as commons_profiles
import octobot.constants as constants
import octobot.community.errors as errors
import octobot.community.supabase_backend.enums as enums
import octobot.community.supabase_backend.supabase_client as supabase_client
import octobot.community.supabase_backend.configuration_storage as configuration_storage


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
            logging.get_logger(self.__class__.__name__).info(f"Authentication error: {err}")
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
            return (await self.table("bots").select("*,bot_deployment:bot_deployments(*)").eq(
                enums.BotKeys.ID.value, bot_id
            ).execute()).data[0]
        except IndexError:
            raise errors.BotNotFoundError(f"Can't find bot with id: {bot_id}")

    async def fetch_bots(self) -> list:
        return (await self.table("bots").select("*,bot_deployment:bot_deployments(*)").execute()).data

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
        return (await self.table("products").select("*").execute()).data

    async def fetch_subscribed_products_urls(self) -> list:
        return json.loads(
            (await self.postgres_functions().invoke("get_subscribed_products_urls", {}))["data"]
        ) or []

    async def fetch_trades(self, bot_id) -> list:
        return (await self.table("bot_trades").select("*").eq(
            enums.TradeKeys.BOT_ID.value, bot_id
        ).execute()).data

    async def reset_trades(self, bot_id):
        return (await self.table("bot_trades").delete().eq(
            enums.TradeKeys.BOT_ID.value, bot_id
        ).execute()).data

    async def upsert_trades(self, trades) -> list:
        return (await self.table("bot_trades").upsert(
            trades, on_conflict=f"{enums.TradeKeys.TRADE_ID.value},{enums.TradeKeys.TIME.value}"
        ).execute()).data

    # todo test
    async def fetch_orders(self, bot_id) -> list:
        return (await self.table("bot_orders").select("*").eq(
            enums.OrderKeys.BOT_ID.value, bot_id
        ).execute()).data

    # todo test
    async def reset_orders(self, bot_id):
        return (await self.table("bot_orders").delete().eq(
            enums.OrderKeys.BOT_ID.value, bot_id
        ).execute()).data

    # todo test
    async def upsert_orders(self, trades) -> list:
        return (await self.table("bot_orders").upsert(
            trades, on_conflict=f"{enums.OrderKeys.ORDER_ID.value},{enums.OrderKeys.TIME.value}"
        ).execute()).data

    # todo test
    async def fetch_profile_data(self, bot_id: str) -> commons_profiles.ProfileData:
        return commons_profiles.ProfileData.from_dict(
            (await self.table("bot_configs").select("profile_data").eq(
                enums.ConfigKeys.BOT_ID.value, bot_id
            ).execute()).data[0]
        )

    async def fetch_configs(self, bot_id) -> list:
        # use a new current portfolio for the given bot
        return (await self.table("bot_configs").select("*").eq(
            enums.ConfigKeys.BOT_ID.value, bot_id
        ).execute()).data

    async def update_config(self, config) -> list:
        # use a new current portfolio for the given bot
        return (await self.table("bot_configs").update(config).eq(
            enums.ConfigKeys.ID.value, config[enums.ConfigKeys.ID.value]
        ).execute()).data

    async def switch_config(self, new_config) -> dict:
        # use a new current portfolio for the given bot
        bot_id = new_config[enums.ConfigKeys.BOT_ID.value]
        inserted_config = (await self.table("bot_configs").insert(new_config).execute()).data[0]
        await self.table("bots").update(
            {enums.BotKeys.CURRENT_CONFIG_ID.value: inserted_config[enums.ConfigKeys.ID.value]}
        ).eq(enums.BotKeys.ID.value, bot_id).execute()
        return inserted_config

    async def fetch_portfolios(self, bot_id) -> list:
        return (await self.table("bot_portfolios").select("*").eq(
            enums.PortfolioKeys.BOT_ID.value, bot_id
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
            return datetime.datetime.strptime(str_time, "%Y-%m-%dT%H:%M:%S.%f")

    async def _get_user(self) -> gotrue.User:
        return self.auth.get_user().user
