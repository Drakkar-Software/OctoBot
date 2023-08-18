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
import contextlib
import os
import dotenv
import mock
import pytest_asyncio
import pytest

import octobot.community as community
import octobot.community.supabase_backend.enums as supabase_backend_enums
import octobot_commons.configuration as commons_configuration


LOADED_BACKEND_CREDS_ENV_VARIABLES = False
VERBOSE = False


@pytest_asyncio.fixture
async def authenticated_client_1():
    async with _authenticated_client(*get_backend_client_creds(1)) as client:
        yield client


@pytest_asyncio.fixture
async def authenticated_client_1_with_temp_bot():
    async with _authenticated_client(*get_backend_client_creds(1)) as client:
        bot_id = None
        try:
            bot = await client.create_bot(supabase_backend_enums.DeploymentTypes.SELF_HOSTED)
            bot_id = bot[supabase_backend_enums.BotKeys.ID.value]
            _print(f"created bot {bot[supabase_backend_enums.BotKeys.NAME.value]} (id: {bot_id})")
            yield client, bot_id
        finally:
            if bot_id is not None:
                await delete_bot(client, bot_id)


@pytest_asyncio.fixture
async def authenticated_client_2():
    async with _authenticated_client(*get_backend_client_creds(2)) as client:
        yield client


@pytest_asyncio.fixture
async def authenticated_client_3():
    async with _authenticated_client(*get_backend_client_creds(3)) as client:
        yield client


@pytest_asyncio.fixture
async def admin_client():
    async with _authenticated_client(None, None, _get_backend_service_key()) as client:
        yield client


@pytest.fixture
def skip_if_no_service_key(request):
    if _get_backend_service_key() is None:
        pytest.skip(reason=f"Disabled {request.node.name} [SUPABASE_BACKEND_SERVICE_KEY is not set]")


async def delete_bot(client, bot_id):

    async def _delete_portfolio_histories(portfolio_id):
        await client.table("bot_portfolio_histories").delete().eq(
            supabase_backend_enums.PortfolioHistoryKeys.PORTFOLIO_ID.value, portfolio_id
        ).execute()

    async def _delete_portfolio(portfolio_id):
        await client.table("bot_portfolios").delete().eq(
            supabase_backend_enums.PortfolioKeys.ID.value, portfolio_id
        ).execute()

    async def _delete_config(config_id):
        await client.table("bot_configs").delete().eq(
            supabase_backend_enums.BotConfigKeys.ID.value, config_id
        ).execute()

    async def _delete_deployment(deployment_id):
        await client.table("bot_deployments").delete().eq(
            supabase_backend_enums.BotDeploymentKeys.ID.value, deployment_id
        ).execute()
    bot = await client.fetch_bot(bot_id)
    if deployment_id := bot[supabase_backend_enums.BotKeys.CURRENT_DEPLOYMENT_ID.value]:
        # cleanup deployments
        # remove deployment foreign key
        await client.update_bot(
            bot_id,
            {supabase_backend_enums.BotKeys.CURRENT_DEPLOYMENT_ID.value: None}
        )
        await _delete_deployment(deployment_id)
    # cleanup trades
    await client.reset_trades(bot_id)
    portfolios = await client.fetch_portfolios(bot_id)
    if portfolios:
        # cleanup portfolios
        # remove portfolio foreign key
        await client.update_bot(
            bot_id,
            {supabase_backend_enums.BotKeys.CURRENT_PORTFOLIO_ID.value: None}
        )
        for portfolio in portfolios:
            to_del_portfolio_id = portfolio[supabase_backend_enums.PortfolioKeys.ID.value]
            await _delete_portfolio_histories(to_del_portfolio_id)
            await _delete_portfolio(to_del_portfolio_id)
    configs = await client.fetch_configs(bot_id)
    if configs:
        # cleanup configs
        # remove configs foreign key
        await client.update_bot(
            bot_id,
            {supabase_backend_enums.BotKeys.CURRENT_CONFIG_ID.value: None}
        )
        for config in configs:
            to_del_config_id = config[supabase_backend_enums.BotConfigKeys.ID.value]
            await _delete_config(to_del_config_id)
    # delete bot
    deleted_bot = (await client.delete_bot(bot_id))[0]
    _print(f"deleted bot (id: {bot_id})")
    assert deleted_bot[supabase_backend_enums.BotKeys.ID.value] == bot_id
    return deleted_bot


@contextlib.asynccontextmanager
async def _authenticated_client(email, password, admin_key=None):
    config = commons_configuration.Configuration("", "")
    config.config = {}
    backend_url, backend_key = get_backend_api_creds()
    supabase_client = None
    try:
        supabase_client = community.CommunitySupabaseClient(
            backend_url,
            admin_key or backend_key,
            community.SyncConfigurationStorage(config)
        )
        if admin_key is None:
            await supabase_client.sign_in(email, password)
        yield supabase_client
    finally:
        if supabase_client:
            await supabase_client.close()


@pytest_asyncio.fixture
async def sandboxed_insert():
    to_delete = {}
    async with _authenticated_client(None, None, _get_backend_service_key()) as admin_client:
        async def _sandboxed_insert(_table, _content):
            if _table not in to_delete:
                to_delete[_table] = []
            inserted = (await admin_client.table(_table).insert(_content).execute()).data[0]
            to_delete[_table].append(inserted)
            return inserted
        try:
            yield mock.AsyncMock(insert=_sandboxed_insert)
        finally:
            for table, rows in to_delete.items():
                await admin_client.table(table).delete().in_(
                    "id", [row["id"] for row in rows]
                ).execute()



def _load_backend_creds_env_variables_if_necessary():
    global LOADED_BACKEND_CREDS_ENV_VARIABLES
    if not LOADED_BACKEND_CREDS_ENV_VARIABLES:
        # load environment variables from .env file if exists
        dotenv_path = os.getenv("SUPABASE_BACKEND_TESTS_DOTENV_PATH", os.path.dirname(os.path.abspath(__file__)))
        dotenv.load_dotenv(os.path.join(dotenv_path, ".env"), verbose=False)
        LOADED_BACKEND_CREDS_ENV_VARIABLES = True


def get_backend_api_creds():
    return os.getenv("SUPABASE_BACKEND_URL"), os.getenv("SUPABASE_BACKEND_KEY")


def get_backend_client_creds(identifier):
    return os.getenv(f"SUPABASE_BACKEND_CLIENT_{identifier}_EMAIL"), \
        os.getenv(f"SUPABASE_BACKEND_CLIENT_{identifier}_PASSWORD")


def _get_backend_service_key():
    return os.getenv(f"SUPABASE_BACKEND_SERVICE_KEY")


def _print(message):
    if VERBOSE:
        print(message)


_load_backend_creds_env_variables_if_necessary()
