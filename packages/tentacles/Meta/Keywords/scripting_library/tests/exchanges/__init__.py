import os
import pathlib

import pytest
import pytest_asyncio

import octobot_commons.constants as commons_constants
import octobot_backtesting.backtesting as backtesting
import octobot_backtesting.constants as backtesting_constants
import octobot_backtesting.time as backtesting_time
import octobot_trading.exchanges as exchanges

from octobot_commons.tests.test_config import load_test_config

pytestmark = pytest.mark.asyncio


DEFAULT_EXCHANGE_NAME = "binance"
TEST_CONFIG_FOLDER = pathlib.Path(os.path.abspath(__file__)).parent.parent


@pytest_asyncio.fixture
async def backtesting_config(request):
    config = load_test_config(test_folder=TEST_CONFIG_FOLDER)
    config[backtesting_constants.CONFIG_BACKTESTING] = {}
    config[backtesting_constants.CONFIG_BACKTESTING][commons_constants.CONFIG_ENABLED_OPTION] = True
    if hasattr(request, "param"):
        ref_market = request.param
        config[commons_constants.CONFIG_TRADING][commons_constants.CONFIG_TRADER_REFERENCE_MARKET] = ref_market
    return config


@pytest_asyncio.fixture
async def fake_backtesting(backtesting_config):
    return backtesting.Backtesting(
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
        config, exchange_name, is_spot, is_margin, is_future = request.param

    if config is None:
        config = backtesting_config
    exchange_manager_instance = exchanges.ExchangeManager(config, exchange_name)
    exchange_manager_instance.is_backtesting = True
    exchange_manager_instance.is_spot_only = is_spot
    exchange_manager_instance.is_margin = is_margin
    exchange_manager_instance.is_future = is_future
    exchange_manager_instance.is_option = is_option
    exchange_manager_instance.use_cached_markets = False
    exchange_manager_instance.backtesting = fake_backtesting
    exchange_manager_instance.backtesting.time_manager = backtesting_time.TimeManager(config)
    await exchange_manager_instance.initialize(exchange_config_by_exchange=None)
    yield exchange_manager_instance
    await exchange_manager_instance.stop()


@pytest_asyncio.fixture
async def backtesting_trader(backtesting_config, backtesting_exchange_manager):
    trader_instance = exchanges.TraderSimulator(backtesting_config, backtesting_exchange_manager)
    await trader_instance.initialize()
    return backtesting_config, backtesting_exchange_manager, trader_instance
