#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or
#  (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with
#  OctoBot. If not, see <https://www.gnu.org/licenses/>.
#  Local pytest fixtures for octobot_copy tests (copied from packages/trading/tests).
import time

import mock
import pytest
import pytest_asyncio

import octobot_commons.constants as commons_constants
import octobot_backtesting.backtesting as backtesting_module
import octobot_backtesting.constants as backtesting_constants
import octobot_backtesting.time as backtesting_time
import octobot_commons.tests.test_config as test_config_module
import octobot_trading.exchanges

pytestmark = pytest.mark.asyncio

DEFAULT_EXCHANGE_NAME = "binanceus"
DEFAULT_FUTURE_EXCHANGE_NAME = "bybit"


@pytest_asyncio.fixture
async def backtesting_config(request):
    config = test_config_module.load_test_config()
    config[backtesting_constants.CONFIG_BACKTESTING] = {}
    config[backtesting_constants.CONFIG_BACKTESTING][commons_constants.CONFIG_ENABLED_OPTION] = True
    if hasattr(request, "param"):
        ref_market = request.param
        config[commons_constants.CONFIG_TRADING][commons_constants.CONFIG_TRADER_REFERENCE_MARKET] = ref_market
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
async def backtesting_exchange_manager(request, backtesting_config, fake_backtesting):
    config = None
    exchange_name = DEFAULT_EXCHANGE_NAME
    is_spot = True
    is_margin = False
    is_future = False
    is_option = False
    if hasattr(request, "param"):
        if isinstance(request.param, str):
            mode = request.param
            if mode == "spot":
                is_spot = True
                is_margin = False
                is_future = False
                is_option = False
            elif mode == "margin":
                is_spot = False
                is_margin = True
                is_future = False
                is_option = False
            elif mode == "futures":
                is_spot = False
                is_margin = False
                is_future = True
                is_option = False
                exchange_name = DEFAULT_FUTURE_EXCHANGE_NAME
            elif mode == "options":
                is_spot = False
                is_margin = False
                is_future = False
                is_option = True
        elif isinstance(request.param, tuple) and len(request.param) == 5:
            config, exchange_name, is_spot, is_margin, is_future = request.param

    if config is None:
        config = backtesting_config
    exchange_manager_instance = octobot_trading.exchanges.ExchangeManager(config, exchange_name)
    exchange_manager_instance.is_backtesting = True
    exchange_manager_instance.use_cached_markets = False
    exchange_manager_instance.is_spot_only = is_spot
    exchange_manager_instance.is_margin = is_margin
    exchange_manager_instance.is_future = is_future
    exchange_manager_instance.is_option = is_option
    exchange_manager_instance.backtesting = fake_backtesting
    exchange_manager_instance.backtesting.time_manager = backtesting_time.TimeManager(config)
    await exchange_manager_instance.initialize(exchange_config_by_exchange=None)
    with mock.patch.object(
        exchange_manager_instance.exchange.connector,
        "get_exchange_current_time",
        side_effect=lambda: time.time(),
    ):
        yield exchange_manager_instance
    await exchange_manager_instance.stop()


@pytest_asyncio.fixture
async def backtesting_trader(backtesting_config, backtesting_exchange_manager):
    trader_instance = octobot_trading.exchanges.TraderSimulator(
        backtesting_config,
        backtesting_exchange_manager,
    )
    await trader_instance.initialize()
    return backtesting_config, backtesting_exchange_manager, trader_instance
