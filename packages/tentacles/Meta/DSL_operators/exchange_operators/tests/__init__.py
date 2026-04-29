#  Drakkar-Software OctoBot-Commons
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
import pytest_asyncio

import octobot_commons.constants as commons_constants
import octobot_commons.tests.test_config as test_config
import octobot_backtesting.backtesting as backtesting_module
import octobot_backtesting.constants as backtesting_constants
import octobot_backtesting.time as backtesting_time
import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.exchange_manager as exchange_manager_module


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def backtesting_config():
    config = dict(test_config.load_test_config())
    config[backtesting_constants.CONFIG_BACKTESTING] = {}
    config[backtesting_constants.CONFIG_BACKTESTING][commons_constants.CONFIG_ENABLED_OPTION] = True
    return config


@pytest_asyncio.fixture
async def fake_backtesting(backtesting_config):
    return backtesting_module.Backtesting(
        config=backtesting_config,
        exchange_ids=[],
        matrix_id="",
        backtesting_files=[],
    )


@pytest_asyncio.fixture
async def backtesting_exchange_manager(backtesting_config, fake_backtesting):
    exchange_manager_instance = exchange_manager_module.ExchangeManager(
        backtesting_config, "binanceus"
    )
    exchange_manager_instance.is_backtesting = True
    exchange_manager_instance.use_cached_markets = False
    exchange_manager_instance.is_spot_only = True
    exchange_manager_instance.is_margin = False
    exchange_manager_instance.is_future = False
    exchange_manager_instance.backtesting = fake_backtesting
    exchange_manager_instance.backtesting.time_manager = backtesting_time.TimeManager(
        backtesting_config
    )
    await exchange_manager_instance.initialize(exchange_config_by_exchange=None)
    try:
        yield exchange_manager_instance
    finally:
        await exchange_manager_instance.stop()


@pytest_asyncio.fixture
async def backtesting_trader(backtesting_config, backtesting_exchange_manager):
    trader_instance = exchanges.TraderSimulator(
        backtesting_config, backtesting_exchange_manager
    )
    await trader_instance.initialize()
    return backtesting_config, backtesting_exchange_manager, trader_instance
