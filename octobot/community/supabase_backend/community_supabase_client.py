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
import gotrue.errors
import datetime
import supabase.lib.client_options
import octobot_commons.authentication as authentication
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
        super().__init__(supabase_url, supabase_key, options=options)

    def sign_in(self, email: str, password: str) -> None:
        try:
            self.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
        except gotrue.errors.AuthApiError as err:
            raise authentication.FailedAuthentication(err) from err

    def sign_up(self, email: str, password: str) -> None:
        self.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "hasRegisteredFromSelfHosted": True
                }
            }
        })

    def sign_out(self) -> None:
        self.auth.sign_out()

    def restore_session(self):
        self.auth.initialize_from_storage()
        if not self.is_signed_in():
            raise authentication.FailedAuthentication()

    def is_signed_in(self) -> bool:
        return self.auth.get_session() is not None

    def has_login_info(self) -> bool:
        return self.auth._storage.get_item(self.auth._storage_key) is not None

    def update_metadata(self, metadata_update):
        self.auth.update_user({
            "data": metadata_update
        })

    def get_user(self) -> dict:
        return self._get_user().dict()

    async def fetch_bot(self, bot_id) -> dict:
        try:
            return (await self.table("bots").select("*").eq(
                enums.BotKeys.ID.value, bot_id
            ).execute()).data[0]
        except IndexError:
            raise errors.BotNotFoundError(bot_id)

    async def fetch_bots(self) -> list:
        return (await self.table("bots").select("*").execute()).data

    async def create_bot(self) -> dict:
        return (await self.table("bots").insert(
            {enums.BotKeys.USER_ID.value: self._get_user().id}
        ).execute()).data[0]

    async def update_bot(self, bot_id, bot_update) -> list:
        return (await self.table("bots").update(bot_update).eq(enums.BotKeys.ID.value, bot_id).execute()).data

    async def delete_bot(self, bot_id) -> list:
        return (await self.table("bots").delete().eq(enums.BotKeys.ID.value, bot_id).execute()).data

    async def fetch_startup_info(self, bot_id) -> dict:
        return await self.postgres_functions().invoke("get_startup_info", {"body": {"bot_id": bot_id}})["data"]

    async def fetch_subscribed_products_urls(self) -> dict:
        return await self.postgres_functions().invoke("get_subscribed_products_urls", {})["data"]

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
            trades, on_conflict=
            f"{enums.TradeKeys.TRADE_ID.value},{enums.TradeKeys.TIME.value}"
        ).execute()).data

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

    @staticmethod
    def get_formatted_time(timestamp):
        # remove trailing 0 to be consistent with database
        str_time = f"{datetime.datetime.utcfromtimestamp(timestamp).isoformat('T')}".rstrip("0")
        if str_time.endswith("."):
            str_time = f"{str_time}0"
        return str_time

    def _get_user(self) -> gotrue.User:
        return self.auth.get_user().user
