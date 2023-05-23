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
import decimal
import time
import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot.community as community
import octobot.community.errors as errors
import octobot.community.models as models
import octobot.community.supabase_backend.enums as supabase_backend_enums
import octobot_trading.enums
from additional_tests.supabase_backend_tests import authenticated_client_1, authenticated_client_2, \
    authenticated_client_1_with_temp_bot


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_create_update_and_fetch_bot(authenticated_client_1, authenticated_client_2):
    existing_bots = await authenticated_client_1.fetch_bots()
    other_client_bots = await authenticated_client_2.fetch_bots()

    bot = await authenticated_client_1.create_bot(supabase_backend_enums.DeploymentTypes.SELF_HOSTED)
    assert all(
        attribute.value in bot
        for attribute in supabase_backend_enums.BotKeys
    )
    created_bot_id = bot[supabase_backend_enums.BotKeys.ID.value]

    fetched_bot = await authenticated_client_1.fetch_bot(created_bot_id)
    assert fetched_bot == bot
    with pytest.raises(errors.BotNotFoundError):
        assert await authenticated_client_2.fetch_bot(created_bot_id) is None

    bot_update = {
        "name": "super plop"
    }
    bot.update(bot_update)
    updated_bot = (await authenticated_client_1.update_bot(created_bot_id, bot_update))
    assert updated_bot == bot

    fetched_bots = await authenticated_client_1.fetch_bots()
    assert created_bot_id in [b[supabase_backend_enums.BotKeys.ID.value] for b in fetched_bots]
    assert len(fetched_bots) == len(existing_bots) + 1

    client_2_fetched_bots = await authenticated_client_2.fetch_bots()
    assert created_bot_id not in [b[supabase_backend_enums.BotKeys.ID.value] for b in client_2_fetched_bots]
    assert len(client_2_fetched_bots) == len(other_client_bots)

    assert (await authenticated_client_1.delete_bot(created_bot_id))[0][supabase_backend_enums.BotKeys.ID.value] \
           == created_bot_id
    bots = await authenticated_client_1.fetch_bots()
    assert len(bots) == len(existing_bots)


async def test_fetch_deployment_and_deployment_data(authenticated_client_1, authenticated_client_2):
    bot = await authenticated_client_1.create_bot(supabase_backend_enums.DeploymentTypes.SELF_HOSTED)
    deployment = bot[community.CommunityUserAccount.BOT_DEPLOYMENT]
    assert all(
        attribute.value in deployment
        for attribute in supabase_backend_enums.BotDeploymentKeys
    )
    deployment_id = deployment[supabase_backend_enums.BotDeploymentKeys.ID.value]

    async def _create_deployment_url(client):
        deployment_url_data = {
            supabase_backend_enums.BotDeploymentURLKeys.URL.value: "plop.fr",
            supabase_backend_enums.BotDeploymentURLKeys.DEPLOYMENT_ID.value: deployment_id
        }
        created_deployment_url = (
            await client.table("bot_deployment_urls").insert(deployment_url_data).execute()
        ).data[0]
        await client.update_deployment(deployment_id, {
            supabase_backend_enums.BotDeploymentKeys.CURRENT_URL_ID.value:
                created_deployment_url[supabase_backend_enums.BotDeploymentURLKeys.ID.value]
        })
        return created_deployment_url

    deployment_url_id = (await _create_deployment_url(authenticated_client_1))[
        supabase_backend_enums.BotDeploymentURLKeys.ID.value
    ]
    try:
        deployment_url = await authenticated_client_1.fetch_deployment_url(deployment_url_id)
        assert all(
            attribute.value in deployment_url
            for attribute in supabase_backend_enums.BotDeploymentURLKeys
        )

        # ensure authenticated_client_2 can't access deployments
        with pytest.raises(errors.BotDeploymentURLNotFoundError):
            await authenticated_client_2.fetch_deployment_url(deployment_url_id)

        async def _fetch_deployment(client, to_fetch_deployment_id):
            return (await client.table("bot_deployments").select("*").eq(
                supabase_backend_enums.BotDeploymentKeys.ID.value, to_fetch_deployment_id
            ).execute()).data[0]

        assert (await _fetch_deployment(authenticated_client_1, deployment_id))[
            supabase_backend_enums.BotDeploymentKeys.CURRENT_URL_ID.value
        ] == deployment_url_id
        with pytest.raises(IndexError):
            await _fetch_deployment(authenticated_client_2, deployment_id)
    finally:
        async def _delete_deployment_url(client):
            await client.update_deployment(deployment_id, {
                supabase_backend_enums.BotDeploymentKeys.CURRENT_URL_ID.value: None
            })
            await client.table("bot_deployment_urls").delete().eq(
                supabase_backend_enums.BotDeploymentURLKeys.ID.value, deployment_url_id
            ).execute()
        await _delete_deployment_url(authenticated_client_1)


async def test_fetch_startup_info(authenticated_client_1_with_temp_bot):
    authenticated_client_1, bot_id = authenticated_client_1_with_temp_bot
    startup_info = await authenticated_client_1.fetch_startup_info(bot_id)
    parsed_info = community.StartupInfo.from_dict(startup_info)
    assert parsed_info.forced_profile_url is None
    assert parsed_info.subscribed_products_urls == []


async def test_upsert_and_reset_trades(authenticated_client_1_with_temp_bot, authenticated_client_2):
    authenticated_client_1, bot_id = authenticated_client_1_with_temp_bot
    # bot just created, no trade yet
    existing_trades = await authenticated_client_1.fetch_trades(bot_id)
    assert existing_trades == []
    other_existing_trades = await authenticated_client_2.fetch_trades(bot_id)
    assert other_existing_trades == []

    seed = time.time()
    trades = trades_mock(seed, bot_id)
    res = await authenticated_client_1.upsert_trades(trades)
    assert_are_same_elements(trades, res)
    # all got inserted
    inserted_trades = await authenticated_client_1.fetch_trades(bot_id)
    assert_are_same_elements(trades, inserted_trades)

    seed_2 = time.time() + 2
    updated_trades = trades + trades_mock(seed_2, bot_id)
    res = await authenticated_client_1.upsert_trades(updated_trades)
    assert_are_same_elements(updated_trades, res)
    # all got inserted, no duplicate
    upserted_trades = await authenticated_client_1.fetch_trades(bot_id)
    assert_are_same_elements(updated_trades, upserted_trades)

    assert len(
        set([trade[supabase_backend_enums.TradeKeys.TRADE_ID.value] for trade in upserted_trades])
    ) == len(updated_trades)
    assert all(
        attribute.value in trade
        for trade in upserted_trades
        for attribute in supabase_backend_enums.TradeKeys
    )

    # try with other client
    other_existing_trades = await authenticated_client_2.fetch_trades(bot_id)
    assert other_existing_trades == []
    res = await authenticated_client_2.reset_trades(bot_id)
    assert res == []

    # reset dit not work (wrong client)
    assert len(await authenticated_client_1.fetch_trades(bot_id)) == len(updated_trades)
    res = await authenticated_client_1.reset_trades(bot_id)
    # ensure delete all
    assert_are_same_elements(updated_trades, res)
    assert await authenticated_client_1.fetch_trades(bot_id) == []


async def test_switch_and_update_portfolio(authenticated_client_1_with_temp_bot, authenticated_client_2):
    authenticated_client_1, bot_id = authenticated_client_1_with_temp_bot
    # bot just created, no portfolio yet
    existing_portfolios = await authenticated_client_1.fetch_portfolios(bot_id)
    assert existing_portfolios == []
    other_existing_portfolios = await authenticated_client_2.fetch_portfolios(bot_id)
    assert other_existing_portfolios == []

    seed = time.time()
    portfolio = portfolio_mock(seed, bot_id)
    created_portfolio = await authenticated_client_1.switch_portfolio(portfolio)
    updated_bot = await authenticated_client_1.fetch_bot(bot_id)
    assert updated_bot[supabase_backend_enums.BotKeys.CURRENT_PORTFOLIO_ID.value] == \
           created_portfolio[supabase_backend_enums.PortfolioKeys.ID.value]
    assert updated_bot == await authenticated_client_1.fetch_bot(bot_id)
    assert_are_same_elements([portfolio], [created_portfolio])
    assert all(
        attribute.value in created_portfolio
        for attribute in supabase_backend_enums.PortfolioKeys
    )

    created_portfolios = await authenticated_client_1.fetch_portfolios(bot_id)
    assert len(created_portfolios) == 1
    assert_are_same_elements([portfolio], created_portfolios)

    seed_2 = time.time() + 1
    portfolio_2 = portfolio_mock(seed_2, bot_id)
    created_portfolio = await authenticated_client_1.switch_portfolio(portfolio_2)
    updated_bot = await authenticated_client_1.fetch_bot(bot_id)
    assert updated_bot[supabase_backend_enums.BotKeys.CURRENT_PORTFOLIO_ID.value] == \
           created_portfolio[supabase_backend_enums.PortfolioKeys.ID.value]

    created_portfolios = await authenticated_client_1.fetch_portfolios(bot_id)
    assert len(created_portfolios) == 2
    assert_are_same_elements([portfolio], created_portfolios[0:1])
    assert_are_same_elements([portfolio_2], created_portfolios[1:])

    portfolio_2[supabase_backend_enums.PortfolioKeys.CURRENT_VALUE.value] = 1
    portfolio_2[supabase_backend_enums.PortfolioKeys.CONTENT.value] = []
    portfolio_2[supabase_backend_enums.PortfolioKeys.ID.value] = \
        created_portfolios[1][supabase_backend_enums.PortfolioKeys.ID.value]
    updated_portfolio = (await authenticated_client_1.update_portfolio(portfolio_2))
    assert_are_same_elements([portfolio_2], updated_portfolio)

    fetched_portfolios = await authenticated_client_1.fetch_portfolios(bot_id)
    assert_are_same_elements([portfolio_2], fetched_portfolios[1:])

    # other client
    assert await authenticated_client_2.fetch_portfolios(bot_id) == []


async def test_upsert_portfolio_history(authenticated_client_1_with_temp_bot, authenticated_client_2):
    authenticated_client_1, bot_id = authenticated_client_1_with_temp_bot
    seed = round(time.time())
    portfolio = portfolio_mock(seed, bot_id)
    created_portfolio = await authenticated_client_1.switch_portfolio(portfolio)
    portfolio_id = created_portfolio[supabase_backend_enums.PortfolioKeys.ID.value]

    history = portfolio_histories_mock(seed, portfolio_id)
    created_history = await authenticated_client_1.upsert_portfolio_history(history)
    assert_are_same_elements(history, created_history)
    assert all(
        attribute.value in history
        for history in created_history
        for attribute in supabase_backend_enums.PortfolioHistoryKeys
    )

    seed = round(time.time()) + 10
    full_history = history + portfolio_histories_mock(seed, portfolio_id)
    upserted_history = await authenticated_client_1.upsert_portfolio_history(full_history)
    assert_are_same_elements(full_history, upserted_history)

    assert upserted_history == await authenticated_client_1.fetch_portfolio_history(portfolio_id)
    assert await authenticated_client_2.fetch_portfolio_history(portfolio_id) == []


async def test_switch_and_update_config(authenticated_client_1_with_temp_bot, authenticated_client_2):
    authenticated_client_1, bot_id = authenticated_client_1_with_temp_bot
    # bot just created, no config yet
    existing_configs = await authenticated_client_1.fetch_configs(bot_id)
    assert existing_configs == []
    other_existing_configs = await authenticated_client_2.fetch_configs(bot_id)
    assert other_existing_configs == []

    seed = time.time()
    config = config_mock(seed, bot_id)
    created_config = await authenticated_client_1.switch_config(config)
    updated_bot = await authenticated_client_1.fetch_bot(bot_id)
    assert updated_bot[supabase_backend_enums.BotKeys.CURRENT_CONFIG_ID.value] == \
           created_config[supabase_backend_enums.ConfigKeys.ID.value]
    assert updated_bot == await authenticated_client_1.fetch_bot(bot_id)
    assert_are_same_elements([config], [created_config])
    assert all(
        attribute.value in created_config
        for attribute in supabase_backend_enums.ConfigKeys
    )

    created_configs = await authenticated_client_1.fetch_configs(bot_id)
    assert len(created_configs) == 1
    assert_are_same_elements([config], created_configs)

    seed_2 = time.time() + 1
    config_2 = config_mock(seed_2, bot_id)
    created_config = await authenticated_client_1.switch_config(config_2)
    updated_bot = await authenticated_client_1.fetch_bot(bot_id)
    assert updated_bot[supabase_backend_enums.BotKeys.CURRENT_CONFIG_ID.value] == \
           created_config[supabase_backend_enums.ConfigKeys.ID.value]

    created_configs = await authenticated_client_1.fetch_configs(bot_id)
    assert len(created_configs) == 2
    assert_are_same_elements([config], created_configs[0:1])
    assert_are_same_elements([config_2], created_configs[1:])

    config_2[supabase_backend_enums.ConfigKeys.CURRENT.value][
        supabase_backend_enums.CurrentConfigKeys.PROFITABILITY.value] = 1
    config_2[supabase_backend_enums.ConfigKeys.ID.value] = \
        created_configs[1][supabase_backend_enums.ConfigKeys.ID.value]
    updated_config = (await authenticated_client_1.update_config(config_2))
    assert_are_same_elements([config_2], updated_config)

    fetched_configs = await authenticated_client_1.fetch_configs(bot_id)
    assert_are_same_elements([config_2], fetched_configs[1:])

    # other client
    assert await authenticated_client_2.fetch_configs(bot_id) == []


def assert_are_same_elements(local, fetched):
    assert len(local) == len(fetched)
    differences = [
        {
            key: (element[key], fetched[i][key])
        }
        for i, element in enumerate(local)
        for key in element
        if not _equal(element, fetched[i], key)
    ]
    assert differences == []


def _equal(d_1, d_2, key):
    if isinstance(d_1[key], dict):
        return all(
            _equal(d_1[key], d_2[key], sub_key)
            for sub_key in d_1[key]
        )
    if isinstance(d_1[key], list):
        return all(
            _equal(d_1[key], d_2[key], sub_key)
            for sub_key in range(len(d_1[key]))
        )
    if key == "time":
        return community.CommunitySupabaseClient.get_parsed_time(d_1[key]) == \
            community.CommunitySupabaseClient.get_parsed_time(d_2[key])
    return d_1[key] == d_2[key]


def config_mock(seed, bot_id):
    return models.format_bot_config_and_stats(
        str(seed) + "profile", seed, bot_id
    )


def trades_mock(seed, bot_id):
    trades = [
        mock.Mock(
            trade_id=str(round((seed + i) % 10) * 101),
            executed_time=seed + i,
            exchange_manager=mock.Mock(exchange_name="binance"),
            executed_price=round((seed + i) % 10) * 100,
            executed_quantity=round((seed + i) % 3) * 100,
            symbol="BTC/USDT",
            trade_type=octobot_trading.enums.TraderOrderType.SELL_LIMIT if int(seed + i) % 2 == 0
            else octobot_trading.enums.TraderOrderType.BUY_MARKET,
        )
        for i in range(2)
    ]
    return models.format_trades(trades, bot_id)


def portfolio_histories_mock(seed, portfolio_id):
    return models.format_portfolio_history(
        {seed + i: {"USDT": round((seed + i) % 10) * 101} for i in range(2)},
        "USDT",
        portfolio_id
    )


def portfolio_mock(seed, bot_id):
    return models.format_portfolio(
        {"USDT": round(seed % 10) * 100},
        {"USDT": round(seed % 10) * 45},
        "USDT",
        {"plop": {commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("12.2")},
         "BTC": {commons_constants.PORTFOLIO_TOTAL: decimal.Decimal("0.32")}},
        {"plop": 1, "BTC": 12},
        bot_id
    )
