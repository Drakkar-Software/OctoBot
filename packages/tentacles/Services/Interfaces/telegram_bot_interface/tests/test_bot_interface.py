#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import pytest
import asyncio
import contextlib

import octobot_services.interfaces as interfaces
import octobot.octobot as octobot
import octobot.constants as octobot_constants
import octobot.producers as octobot_producers
import octobot.producers as trading_producers
import octobot.community as community
import octobot_commons.tests.test_config as test_config
import octobot_tentacles_manager.loaders as loaders
import octobot_evaluators.api as evaluator_api
import tests.test_utils.config as test_utils_config

# All test coroutines will be treated as marked.

pytestmark = pytest.mark.asyncio


async def create_minimalist_unconnected_octobot():
    # import here to prevent later web interface import issues
    community.IdentifiersProvider.use_production()
    octobot_instance = octobot.OctoBot(test_config.load_test_config(dict_only=False))
    octobot_instance.initialized = True
    tentacles_config = test_utils_config.load_test_tentacles_config()
    loaders.reload_tentacle_by_tentacle_class()
    octobot_instance.task_manager.async_loop = asyncio.get_event_loop()
    octobot_instance.task_manager.create_pool_executor()
    octobot_instance.tentacles_setup_config = tentacles_config
    octobot_instance.configuration_manager.add_element(octobot_constants.TENTACLES_SETUP_CONFIG_KEY, tentacles_config)
    octobot_instance.exchange_producer = trading_producers.ExchangeProducer(None, octobot_instance, None, False)
    octobot_instance.evaluator_producer = octobot_producers.EvaluatorProducer(None, octobot_instance)
    await evaluator_api.initialize_evaluators(octobot_instance.config, tentacles_config)
    octobot_instance.evaluator_producer.matrix_id = evaluator_api.create_matrix()
    return octobot_instance


# use context manager instead of fixture to prevent pytest threads issues
@contextlib.asynccontextmanager
async def get_bot_interface():
    bot = await create_minimalist_unconnected_octobot()
    bot_interface = interfaces.AbstractBotInterface({})
    interfaces.AbstractInterface.initialize_global_project_data(
        bot.bot_id,
        "octobot",
        "x.y.z-alpha42")
    yield bot_interface


async def test_all_commands():
    """
    Test basing commands interactions, for most of them a default message will be saying that the bot is not ready.
    :return: None
    """
    async with get_bot_interface() as bot_interface:
        assert len(bot_interface.get_command_configuration()) > 50
        assert len(bot_interface.get_command_market_status()) > 50
        assert len(bot_interface.get_command_trades_history()) > 50
        assert len(bot_interface.get_command_open_orders()) > 50
        assert len(bot_interface.get_command_fees()) > 50
        assert "Decimal" not in bot_interface.get_command_fees()
        assert "Nothing to sell" in await bot_interface.get_command_sell_all_currencies()
        assert "Nothing to sell for BTC" in await bot_interface.get_command_sell_all("BTC")
        with pytest.raises(RuntimeError):
            await bot_interface.set_command_portfolios_refresh()
        assert len(bot_interface.get_command_portfolio()) > 50
        assert "Decimal" not in bot_interface.get_command_portfolio()
        assert len(bot_interface.get_command_profitability()) > 50
        assert "Decimal" not in bot_interface.get_command_profitability()
        assert "I'm alive since" in bot_interface.get_command_ping()
        assert all(elem in bot_interface.get_command_version()
                   for elem in
                   [interfaces.AbstractInterface.project_name, interfaces.AbstractInterface.project_version])
        assert "Hello, I'm OctoBot" in bot_interface.get_command_start()
        assert await bot_interface.set_command_pause() is None
