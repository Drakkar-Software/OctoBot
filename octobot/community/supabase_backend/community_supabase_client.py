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

    async def fetch_bot(self, bot_id):
        return (await self.table("bots").select("*").eq("id", bot_id).execute()).data

    async def fetch_bots(self) -> list:
        return (await self.table("bots").select("*").execute()).data

    async def create_bot(self):
        return (await self.table("bots").insert({"user_id": self._get_user().id}).execute()).data

    async def fetch_startup_info(self, bot_id) -> dict:
        return await self.postgres_functions().invoke("get_startup_info", {"body": {"bot_id": bot_id}})["data"]

    async def fetch_subscribed_products_urls(self) -> dict:
        return await self.postgres_functions().invoke("get_subscribed_products_urls", {})["data"]

    async def reset_trades(self):
        await self.table("bot_trades").delete().execute()

    async def upsert_trades(self, trades):
        return await self.table("bot_trades").upsert(
            trades, on_conflict="trade_id,time"
        ).execute()

    async def update_config(self, config, config_id):
        # use a new current portfolio for the given bot
        await self.table("bot_configs").update(config).eq("id", config_id).execute()

    async def reset_config(self, new_config):
        # use a new current portfolio for the given bot
        bot_id = new_config["bot_id"]
        inserted_config = (await self.table("bot_configs").insert(new_config).execute()).data[0]
        await self.table("bots").update({"current_config_id": inserted_config["id"]}).eq("id", bot_id).execute()

    async def update_portfolio(self, portfolio):
        # use a new current portfolio for the given bot
        await self.table("bot_portfolios").update(portfolio).eq("id", portfolio["id"]).execute()

    async def reset_portfolio(self, new_portfolio):
        # use a new current portfolio for the given bot
        bot_id = new_portfolio["bot_id"]
        inserted_portfolio = (await self.table("bot_portfolios").insert(new_portfolio).execute()).data[0]
        await self.table("bots").update({"current_portfolio_id": inserted_portfolio["id"]}).eq("id", bot_id).execute()

    async def upsert_portfolio_history(self, portfolio_histories):
        return await self.table("bot_portfolio_histories").upsert(
            portfolio_histories, on_conflict="portfolio_id,time"
        ).execute()

    @staticmethod
    def get_formatted_time(timestamp):
        return f"{datetime.datetime.utcfromtimestamp(timestamp).isoformat('T')}Z"

    def _get_user(self) -> gotrue.User:
        return self.auth.get_user().user
