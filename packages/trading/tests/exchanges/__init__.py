#  Drakkar-Software OctoBot-Trading
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
import contextlib
import copy
import os
import mock
import pytest
import pytest_asyncio

import octobot_commons.constants as commons_constants
from octobot_backtesting.backtesting import Backtesting
from octobot_backtesting.constants import CONFIG_BACKTESTING
import octobot_backtesting.time as backtesting_time
from octobot_commons.asyncio_tools import wait_asyncio_next_cycle
from octobot_commons.enums import TimeFrames
import octobot_trading.exchanges.connectors.ccxt.ccxt_clients_cache as ccxt_clients_cache

from octobot_commons.tests.test_config import load_test_config
from octobot_trading.api.exchange import create_exchange_builder, cancel_ccxt_throttle_task
from octobot_trading.exchanges.exchange_manager import ExchangeManager
from octobot_trading.exchanges.exchanges import Exchanges
from octobot_trading.exchanges.implementations.default_rest_exchange import DefaultRestExchange
from octobot_trading.exchanges.connectors.ccxt.ccxt_connector import CCXTConnector
from octobot_trading.exchanges.traders.trader_simulator import TraderSimulator
import octobot_trading.personal_data as personal_data
import octobot_trading.exchanges.connectors.ccxt.ccxt_client_util as ccxt_client_util
from octobot_trading.enums import FeePropertyColumns, ExchangeConstantsMarketPropertyColumns, \
    ExchangeConstantsMarketPropertyColumns

import tests.exchanges.connectors.ccxt.mock_exchanges_data as mock_exchanges_data

pytestmark = pytest.mark.asyncio

TESTS_FOLDER = "tests"
TESTS_STATIC_FOLDER = os.path.join(TESTS_FOLDER, "static")
DEFAULT_EXCHANGE_NAME = "binanceus"
DEFAULT_LIQUID_EXCHANGE_NAME = "bitget"
DEFAULT_FUTURE_EXCHANGE_NAME = "bybit"


def _load_liquid_exchange_test_config():
    default_config = load_test_config()
    default_config[commons_constants.CONFIG_EXCHANGES][DEFAULT_LIQUID_EXCHANGE_NAME] = \
        copy.deepcopy(default_config[commons_constants.CONFIG_EXCHANGES][DEFAULT_EXCHANGE_NAME])
    return default_config


class MockedCCXTConnector(CCXTConnector):
    @classmethod
    def get_name(cls):
        return DEFAULT_EXCHANGE_NAME

    async def load_symbol_markets(self, reload=False, market_filter=None):
        if mock_exchanges_data.MOCKED_EXCHANGE_SYMBOL_DETAILS.get(
            self.exchange_manager.exchange_name, None
        ):
            register_market_status_mocks(self.exchange_manager.exchange_name)
        await super().load_symbol_markets(
            reload=reload,
        )

    def _should_authenticate(self):
        return False

    def register_simulator_connector_fee_methods(self, *args, **kwargs):
        pass


class MockedRestExchange(DefaultRestExchange):
    DEFAULT_CONNECTOR_CLASS = MockedCCXTConnector
    FIX_MARKET_STATUS = True    # true as binanceus needs this and is mainly used

    @classmethod
    def get_exchange_connector_class(cls, exchange_manager):
        return cls.DEFAULT_CONNECTOR_CLASS

    @classmethod
    def is_default_exchange(cls) -> bool:
        return False


class MockedAutoFillRestExchange(MockedRestExchange):
    HAS_FETCHED_DETAILS = True
    _SUPPORTED_EXCHANGE_MOCK = []
    _EXCHANGE_DETAILS_MOCK = {}

    def _apply_fetched_details(self, config, exchange_manager):
        pass

    @classmethod
    async def fetch_exchange_config(
        cls, exchange_config_by_exchange, exchange_manager
    ):
        pass

    @classmethod
    def supported_autofill_exchanges(cls, tentacle_config):
        return MockedAutoFillRestExchange._SUPPORTED_EXCHANGE_MOCK

    @classmethod
    async def get_autofilled_exchange_details(cls, aiohttp_session, tentacle_config, exchange_name):
        return MockedAutoFillRestExchange._EXCHANGE_DETAILS_MOCK[exchange_name]

    @classmethod
    @contextlib.contextmanager
    def patched_supported_exchanges(cls, exchange_details_by_exchange_name):
        previous_exchanges = cls._SUPPORTED_EXCHANGE_MOCK
        previous_details = cls._EXCHANGE_DETAILS_MOCK
        try:
            cls._SUPPORTED_EXCHANGE_MOCK = list(exchange_details_by_exchange_name)
            cls._EXCHANGE_DETAILS_MOCK = exchange_details_by_exchange_name
            yield
        finally:
            cls._SUPPORTED_EXCHANGE_MOCK = previous_exchanges
            cls._EXCHANGE_DETAILS_MOCK = previous_details


@pytest_asyncio.fixture
async def exchange_manager():
    exchange_manager_instance = ExchangeManager(load_test_config(), DEFAULT_EXCHANGE_NAME)
    exchange_manager_instance.is_spot_only = True
    exchange_manager_instance.is_simulated = False
    await exchange_manager_instance.initialize(exchange_config_by_exchange=None)
    try:
        yield exchange_manager_instance
    finally:
        cancel_ccxt_throttle_task()
        await exchange_manager_instance.stop()
        # let updaters gracefully shutdown
        await wait_asyncio_next_cycle()


@pytest_asyncio.fixture
async def liquid_exchange_manager():
    exchange_manager_instance = ExchangeManager(_load_liquid_exchange_test_config(), DEFAULT_LIQUID_EXCHANGE_NAME)
    exchange_manager_instance.is_spot_only = True
    exchange_manager_instance.is_simulated = False
    await exchange_manager_instance.initialize(exchange_config_by_exchange=None)
    try:
        yield exchange_manager_instance
    finally:
        cancel_ccxt_throttle_task()
        await exchange_manager_instance.stop()
        # let updaters gracefully shutdown
        await wait_asyncio_next_cycle()


@pytest_asyncio.fixture
async def simulated_exchange_manager():
    exchange_manager_instance = ExchangeManager(load_test_config(), DEFAULT_EXCHANGE_NAME)
    exchange_manager_instance.is_spot_only = True
    exchange_manager_instance.is_simulated = True
    await exchange_manager_instance.initialize(exchange_config_by_exchange=None)
    try:
        yield exchange_manager_instance
    finally:
        cancel_ccxt_throttle_task()
        await exchange_manager_instance.stop()
        # let updaters gracefully shutdown
        await wait_asyncio_next_cycle()


@pytest_asyncio.fixture
async def margin_exchange_manager():
    exchange_manager_instance = ExchangeManager(load_test_config(), DEFAULT_EXCHANGE_NAME)
    exchange_manager_instance.is_spot_only = False
    exchange_manager_instance.is_margin = True
    await exchange_manager_instance.initialize(exchange_config_by_exchange=None)
    try:
        yield exchange_manager_instance
    finally:
        cancel_ccxt_throttle_task()
        await exchange_manager_instance.stop()
        # let updaters gracefully shutdown
        await wait_asyncio_next_cycle()


@pytest_asyncio.fixture
async def margin_simulated_exchange_manager():
    exchange_manager_instance = ExchangeManager(load_test_config(), DEFAULT_EXCHANGE_NAME)
    exchange_manager_instance.is_spot_only = False
    exchange_manager_instance.is_simulated = True
    exchange_manager_instance.is_margin = True
    await exchange_manager_instance.initialize(exchange_config_by_exchange=None)
    try:
        yield exchange_manager_instance
    finally:
        cancel_ccxt_throttle_task()
        await exchange_manager_instance.stop()
        # let updaters gracefully shutdown
        await wait_asyncio_next_cycle()


@pytest_asyncio.fixture
async def future_exchange_manager():
    exchange_manager_instance = ExchangeManager(load_test_config(), DEFAULT_FUTURE_EXCHANGE_NAME)
    exchange_manager_instance.is_spot_only = False
    exchange_manager_instance.is_future = True
    await exchange_manager_instance.initialize(exchange_config_by_exchange=None)
    try:
        yield exchange_manager_instance
    finally:
        cancel_ccxt_throttle_task()
        await exchange_manager_instance.stop()
        # let updaters gracefully shutdown
        await wait_asyncio_next_cycle()


@pytest_asyncio.fixture
async def future_simulated_exchange_manager():
    exchange_manager_instance = ExchangeManager(load_test_config(), DEFAULT_FUTURE_EXCHANGE_NAME)
    exchange_manager_instance.is_spot_only = False
    exchange_manager_instance.is_simulated = True
    exchange_manager_instance.is_future = True
    await exchange_manager_instance.initialize(exchange_config_by_exchange=None)
    try:
        yield exchange_manager_instance
    finally:
        cancel_ccxt_throttle_task()
        await exchange_manager_instance.stop()
        # let updaters gracefully shutdown
        await wait_asyncio_next_cycle()


@pytest_asyncio.fixture
async def exchange_builder(request):
    config = None
    exchange_name = DEFAULT_EXCHANGE_NAME
    if hasattr(request, "param"):
        config, exchange_name = request.param

    exchange_builder_instance = create_exchange_builder(config if config is not None else load_test_config(),
                                                        exchange_name).is_simulated().is_rest_only()
    try:
        yield exchange_builder_instance
    finally:
        await exchange_builder_instance.exchange_manager.stop()


# SIMULATED / BACKTESTING
DEFAULT_BACKTESTING_SYMBOL = "BTC/USDT"
DEFAULT_BACKTESTING_SPLIT_SYMBOL = "BTC", "USDT"
DEFAULT_BACKTESTING_CURRENCY = "BTC"
DEFAULT_BACKTESTING_MARKET = "USDT"
DEFAULT_BACKTESTING_TF = TimeFrames.ONE_HOUR


@pytest_asyncio.fixture
async def backtesting_config(request):
    config = load_test_config()
    config[CONFIG_BACKTESTING] = {}
    config[CONFIG_BACKTESTING][commons_constants.CONFIG_ENABLED_OPTION] = True
    if hasattr(request, "param"):
        ref_market = request.param
        config[commons_constants.CONFIG_TRADING][commons_constants.CONFIG_TRADER_REFERENCE_MARKET] = ref_market
    return config


@pytest_asyncio.fixture
async def fake_backtesting(backtesting_config):
    return Backtesting(config=backtesting_config,
                       exchange_ids=[],
                       matrix_id="",
                       backtesting_files=[])


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
    exchange_manager_instance = ExchangeManager(config, exchange_name)
    exchange_manager_instance.is_backtesting = True
    exchange_manager_instance.use_cached_markets = False
    exchange_manager_instance.is_spot_only = is_spot
    exchange_manager_instance.is_margin = is_margin
    exchange_manager_instance.is_future = is_future
    exchange_manager_instance.is_option = is_option
    exchange_manager_instance.backtesting = fake_backtesting
    exchange_manager_instance.backtesting.time_manager = backtesting_time.TimeManager(config)
    await exchange_manager_instance.initialize(exchange_config_by_exchange=None)
    yield exchange_manager_instance
    await exchange_manager_instance.stop()


@pytest_asyncio.fixture
async def simulated_trader(simulated_exchange_manager):
    config = load_test_config()
    trader_instance = TraderSimulator(config, simulated_exchange_manager)
    await trader_instance.initialize()
    return config, simulated_exchange_manager, trader_instance


@pytest_asyncio.fixture
async def backtesting_trader(backtesting_config, backtesting_exchange_manager):
    trader_instance = TraderSimulator(backtesting_config, backtesting_exchange_manager)
    await trader_instance.initialize()
    return backtesting_config, backtesting_exchange_manager, trader_instance


def storage_mock():
    return mock.Mock(
        portfolio_storage=mock.Mock(
            get_db=mock.Mock(
                return_value=mock.Mock(
                    all=mock.AsyncMock(return_value=[])
                )
            ),
            save_historical_portfolio_value=mock.AsyncMock(),
        ),
        stop=mock.AsyncMock(),
    )


def get_fees_mock(symbol, rate=0.1, cost=0.1):  # huge fees for tests
    return {
        FeePropertyColumns.RATE.value: rate,
        FeePropertyColumns.COST.value: cost,
        FeePropertyColumns.CURRENCY.value: symbol
    }


def set_future_exchange_fees(exchange, symbol, taker=0.0004, maker=0.0004):
    exchange.client.markets[symbol]['taker'] = taker
    exchange.client.markets[symbol]['maker'] = maker


@pytest_asyncio.fixture
async def backtesting_trader_with_historical_pf_value_manager(backtesting_trader):
    backtesting_config, backtesting_exchange_manager, trader_instance = backtesting_trader
    backtesting_exchange_manager.storage_manager = storage_mock()
    historical_portfolio_value_manager_inst = personal_data.HistoricalPortfolioValueManager(
        backtesting_exchange_manager.exchange_personal_data.portfolio_manager
    )
    backtesting_exchange_manager.exchange_personal_data.portfolio_manager.historical_portfolio_value_manager = \
        historical_portfolio_value_manager_inst
    await historical_portfolio_value_manager_inst.initialize()
    backtesting_exchange_manager.exchange_personal_data.portfolio_manager.handle_profitability_recalculation(True)
    return backtesting_config, backtesting_exchange_manager, trader_instance


@pytest_asyncio.fixture
async def margin_backtesting_trader(backtesting_config, backtesting_exchange_manager):
    trader_instance = TraderSimulator(backtesting_config, backtesting_exchange_manager)
    await trader_instance.initialize()
    return backtesting_config, backtesting_exchange_manager, trader_instance


@pytest_asyncio.fixture
async def future_backtesting_trader(backtesting_config, backtesting_exchange_manager):
    trader_instance = TraderSimulator(backtesting_config, backtesting_exchange_manager)
    await trader_instance.initialize()
    return backtesting_config, backtesting_exchange_manager, trader_instance


@contextlib.asynccontextmanager
async def cached_markets_exchange_manager(config, exchange_name, exchange_only=False):
    exchange_manager = None
    try:
        exchange_manager = ExchangeManager(config, exchange_name)
        register_market_status_mocks(exchange_name)
        exchange_manager.exchange_only = exchange_only
        await exchange_manager.initialize(exchange_config_by_exchange=None)
        Exchanges.instance().add_exchange(exchange_manager, "")
        yield exchange_manager
    finally:
        if exchange_manager is not None:
            await exchange_manager.stop()


def register_market_status_mocks(exchange_name):
    ccxt_clients_cache.set_exchange_parsed_markets(
        ccxt_clients_cache.get_client_key(
            ccxt_client_util.ccxt_exchange_class_factory(exchange_name)(), False
        ),
        mock_exchanges_data.MOCKED_EXCHANGE_SYMBOL_DETAILS[exchange_name]
    )
