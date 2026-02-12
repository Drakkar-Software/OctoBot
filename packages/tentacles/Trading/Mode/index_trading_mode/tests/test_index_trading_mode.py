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
import time
import typing
import pytest
import pytest_asyncio
import os.path
import mock
import decimal

import async_channel.util as channel_util

import octobot_commons.enums as commons_enum
import octobot_commons.tests.test_config as test_config
import octobot_commons.constants as commons_constants
import octobot_commons.symbols as commons_symbols
import octobot_commons.configuration as commons_configuration
import octobot_commons.signals as commons_signals

import octobot_backtesting.api as backtesting_api

import octobot_tentacles_manager.api as tentacles_manager_api

import octobot_trading.api as trading_api
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.exchanges as exchanges
import octobot_trading.exchange_data as trading_exchange_data
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.modes
import octobot_trading.errors as trading_errors
import octobot_trading.signals as trading_signals

import tentacles.Trading.Mode as Mode
import tentacles.Trading.Mode.index_trading_mode.index_trading as index_trading
import tentacles.Trading.Mode.index_trading_mode.index_distribution as index_distribution
import tentacles.Trading.Mode.index_trading_mode.rebalancer as rebalancer

import tests.test_utils.memory_check_util as memory_check_util
import tests.test_utils.config as test_utils_config
import tests.test_utils.test_exchanges as test_exchanges

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

TRADED_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"]


def _create_position_mock(
    symbol,
    trader,
    is_futures,
    is_idle=False,
    size=decimal.Decimal(0),
    side=None,
    position_value=None,
    initial_margin=decimal.Decimal(0),
    margin=decimal.Decimal(0),
):

    position_mock = mock.Mock()
    position_mock.symbol = symbol
    
    if is_idle:
        position_mock.is_idle.return_value = True
        position_mock.size = decimal.Decimal(0)
        position_mock.side = trading_enums.PositionSide.UNKNOWN
        position_mock.is_long.return_value = False
        position_mock.is_short.return_value = False
        position_mock.is_open.return_value = False
    else:
        position_mock.is_idle.return_value = False
        position_mock.size = size
        position_mock.side = side or trading_enums.PositionSide.LONG
        position_mock.is_long.return_value = (side == trading_enums.PositionSide.LONG)
        position_mock.is_short.return_value = (side == trading_enums.PositionSide.SHORT)
        position_mock.is_open.return_value = True
    
    if position_value is not None:
        position_mock.get_value.return_value = position_value
    
    position_mock.initial_margin = initial_margin
    position_mock.margin = margin
    position_mock.symbol_contract = trader.exchange_manager.exchange.get_pair_contract(symbol) if is_futures else None
    
    return position_mock


@pytest_asyncio.fixture
async def tools():
    trader = None
    try:
        tentacles_manager_api.reload_tentacle_info()
        mode, trader = await _get_tools()
        yield mode, trader
    finally:
        if trader:
            await _stop(trader.exchange_manager)


@pytest_asyncio.fixture
async def futures_tools():
    trader = None
    try:
        tentacles_manager_api.reload_tentacle_info()
        mode, trader = await _get_futures_tools()
        yield mode, trader
    finally:
        if trader:
            await _stop(trader.exchange_manager)


@pytest_asyncio.fixture
async def trading_tools(request):
    trader = None
    try:
        tentacles_manager_api.reload_tentacle_info()
        fixture_type = getattr(request, 'param', 'spot')
        if fixture_type == "futures":
            mode, trader = await _get_futures_tools()
        else:
            mode, trader = await _get_tools()
        yield mode, trader
    finally:
        if trader:
            await _stop(trader.exchange_manager)


async def test_run_independent_backtestings_with_memory_check():
    """
    Should always be called first here to avoid other tests' related memory check issues
    """
    tentacles_setup_config = tentacles_manager_api.create_tentacles_setup_config_with_tentacles(
        Mode.IndexTradingMode,
    )
    config = test_config.load_test_config()
    config[commons_constants.CONFIG_TIME_FRAME] = [commons_enum.TimeFrames.FOUR_HOURS]

    _CONFIG = {
        Mode.IndexTradingMode.get_name(): {
            "required_strategies": [],
            "refresh_interval": 7,
            "rebalance_trigger_min_percent": 5,
            "index_content": []
        },
    }

    def config_proxy(tentacles_setup_config, klass):
        try:
            return _CONFIG[klass if isinstance(klass, str) else klass.get_name()]
        except KeyError:
            return {}

    with tentacles_manager_api.local_tentacle_config_proxy(config_proxy):
        with mock.patch.object(octobot_trading.modes.AbstractTradingMode, "get_historical_config", mock.Mock()) \
            as get_historical_config:
            await memory_check_util.run_independent_backtestings_with_memory_check(
                config, tentacles_setup_config, use_multiple_asset_data_file=True
            )
            # should not be called when no historical config is available (or it will log errors)
            get_historical_config.assert_not_called()


def _get_config(tools, update):
    mode, trader = tools
    config = tentacles_manager_api.get_tentacle_config(trader.exchange_manager.tentacles_setup_config, mode.__class__)
    return {**config, **update}

@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_init_default_values(trading_tools):
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, {}))
    assert mode.refresh_interval_days == 1
    assert mode.rebalance_trigger_min_ratio == decimal.Decimal(str(index_trading.DEFAULT_REBALANCE_TRIGGER_MIN_RATIO))
    assert mode.quote_asset_rebalance_ratio_threshold == decimal.Decimal(str(index_trading.DEFAULT_QUOTE_ASSET_REBALANCE_TRIGGER_MIN_RATIO))
    assert mode.min_order_size_margin == decimal.Decimal("2")
    assert mode.ratio_per_asset == {'BTC': {'name': 'BTC', 'value': 100.0, 'price': None}}
    assert mode.total_ratio_per_asset == decimal.Decimal(100)
    assert mode.synchronization_policy == index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE
    assert mode.requires_initializing_appropriate_coins_distribution is False
    assert mode.indexed_coins == ["BTC"]
    assert mode.selected_rebalance_trigger_profile is None
    assert mode.rebalance_trigger_profiles is None
    assert mode.allow_skip_asset is False


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_init_config_values(trading_tools):
    update = {
        index_trading.IndexTradingModeProducer.REFRESH_INTERVAL: 72,
        index_trading.IndexTradingModeProducer.SYNCHRONIZATION_POLICY: index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE.value,
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT: 10.2,
        index_trading.IndexTradingModeProducer.MIN_ORDER_SIZE_MARGIN: 3.5,
        index_trading.IndexTradingModeProducer.ALLOW_SKIP_ASSET: True,
        index_trading.IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE: None,
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES: [
            {
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile-1",
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 5.2,
            },
            {
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile-2",
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 20.2,
            },
        ],
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_distribution.DISTRIBUTION_NAME: "ETH",
                index_distribution.DISTRIBUTION_VALUE: 53,
            },
            {
                index_distribution.DISTRIBUTION_NAME: "BTC",
                index_distribution.DISTRIBUTION_VALUE: 1,
            },
            {
                index_distribution.DISTRIBUTION_NAME: "SOL",
                index_distribution.DISTRIBUTION_VALUE: 1,
            },
        ]
    }
    # no selected rebalance trigger profile
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    assert mode.refresh_interval_days == 72
    assert mode.rebalance_trigger_min_ratio == decimal.Decimal("0.102")
    assert mode.min_order_size_margin == decimal.Decimal("3.5")
    assert mode.allow_skip_asset is True
    assert mode.selected_rebalance_trigger_profile is None
    assert mode.rebalance_trigger_profiles ==  [
        {
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile-1",
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 5.2,
        },
        {
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile-2",
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 20.2,
        },
    ]
    assert mode.synchronization_policy == index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE
    assert mode.requires_initializing_appropriate_coins_distribution is True
    assert mode.ratio_per_asset == {
        "BTC": {
            index_distribution.DISTRIBUTION_NAME: "BTC",
            index_distribution.DISTRIBUTION_VALUE: 1,
        },
    }
    assert mode.total_ratio_per_asset == decimal.Decimal("1")
    assert mode.indexed_coins == ["BTC"]

    # now with ETH as traded assets
    trader.exchange_manager.exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in ["ETH/USDT", "ADA/USDT", "BTC/USDT"]
    ]
    mode.trading_config[index_trading.IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE] = "profile-1"
    mode.init_user_inputs({})
    assert mode.refresh_interval_days == 72
    assert mode.rebalance_trigger_profiles ==  [
        {
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile-1",
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 5.2,
        },
        {
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile-2",
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 20.2,
        },
    ]
    assert mode.selected_rebalance_trigger_profile == {
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile-1",
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 5.2,
    }   # applied profile
    assert mode.rebalance_trigger_min_ratio == decimal.Decimal("0.052")
    assert mode.ratio_per_asset == {
        "ETH": {
            index_distribution.DISTRIBUTION_NAME: "ETH",
            index_distribution.DISTRIBUTION_VALUE: 53,
        },
        "BTC": {
            index_distribution.DISTRIBUTION_NAME: "BTC",
            index_distribution.DISTRIBUTION_VALUE: 1,
        }
        # SOL is not added
    }
    assert mode.total_ratio_per_asset == decimal.Decimal("54")
    assert mode.indexed_coins == ["BTC", "ETH"]  # sorted list

    # refresh user inputs
    trader.exchange_manager.exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in ["ETH/USDT", "ADA/USDT", "BTC/USDT", "SOL/USDT"]
    ]
    mode.init_user_inputs({})
    assert mode.refresh_interval_days == 72
    assert mode.rebalance_trigger_min_ratio == decimal.Decimal("0.052")
    assert mode.ratio_per_asset == {
        "ETH": {
            index_distribution.DISTRIBUTION_NAME: "ETH",
            index_distribution.DISTRIBUTION_VALUE: 53,
        },
        "BTC": {
            index_distribution.DISTRIBUTION_NAME: "BTC",
            index_distribution.DISTRIBUTION_VALUE: 1,
        },
        "SOL": {
            index_distribution.DISTRIBUTION_NAME: "SOL",
            index_distribution.DISTRIBUTION_VALUE: 1,
        },
    }
    assert mode.total_ratio_per_asset == decimal.Decimal("55")
    assert mode.indexed_coins == ["BTC", "ETH", "SOL"]  # sorted list

    # add ref market in coin rations
    mode.trading_config["index_content"] = [
        {
            index_distribution.DISTRIBUTION_NAME: "USDT",
            index_distribution.DISTRIBUTION_VALUE: 75,
        },
        {
            index_distribution.DISTRIBUTION_NAME: "BTC",
            index_distribution.DISTRIBUTION_VALUE: 25,
        },
    ]
    # select profile 2
    mode.trading_config[index_trading.IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE] = "profile-2"
    mode.init_user_inputs({})
    assert mode.refresh_interval_days == 72
    assert mode.selected_rebalance_trigger_profile == {
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile-2",
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 20.2,
    }   # applied profile
    assert mode.rebalance_trigger_min_ratio == decimal.Decimal("0.202")
    assert mode.ratio_per_asset == {
        "BTC": {
            index_distribution.DISTRIBUTION_NAME: "BTC",
            index_distribution.DISTRIBUTION_VALUE: 25,
        },
        "USDT": {
            index_distribution.DISTRIBUTION_NAME: "USDT",
            index_distribution.DISTRIBUTION_VALUE: 75,
        },
    }
    assert mode.total_ratio_per_asset == decimal.Decimal("100")
    assert mode.indexed_coins == ["BTC", "USDT"]  # sorted list

    # unknown profile
    mode.trading_config[index_trading.IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE] = "unknown"
    mode.init_user_inputs({})
    # back to non-profile config values bu profiles are loaded
    assert mode.rebalance_trigger_profiles ==  [
        {
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile-1",
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 5.2,
        },
        {
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile-2",
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 20.2,
        },
    ]
    assert mode.selected_rebalance_trigger_profile is None
    assert mode.rebalance_trigger_min_ratio == decimal.Decimal(str(10.2 / 100))

    # invalid synchronization policy
    mode.trading_config[index_trading.IndexTradingModeProducer.SYNCHRONIZATION_POLICY] = "invalid_policy"
    mode.init_user_inputs({})   # does no raise error
    # use current or default value
    assert mode.synchronization_policy == index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_single_exchange_process_optimize_initial_portfolio(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))

    with mock.patch.object(
            octobot_trading.modes, "convert_assets_to_target_asset", mock.AsyncMock(return_value=["order_1"])
    ) as convert_assets_to_target_asset_mock, mock.patch.object(
        mode, "cancel_order", mock.AsyncMock()
    ) as cancel_order_mock:
        # no open order
        orders = await mode.single_exchange_process_optimize_initial_portfolio(["BTC", "ETH"], "USDT", {})
        convert_assets_to_target_asset_mock.assert_called_once_with(mode, ["BTC", "ETH"], "USDT", {})
        cancel_order_mock.assert_not_called()
        assert orders == ["order_1"]
        convert_assets_to_target_asset_mock.reset_mock()

        # open orders of the given symbol are cancelled
        open_order_1 = trading_personal_data.SellLimitOrder(trader)
        open_order_2 = trading_personal_data.BuyLimitOrder(trader)
        open_order_3 = trading_personal_data.BuyLimitOrder(trader)
        open_order_1.update(order_type=trading_enums.TraderOrderType.SELL_LIMIT,
                            order_id="open_order_1_id",
                            symbol="BTC/USDT",
                            current_price=decimal.Decimal("70"),
                            quantity=decimal.Decimal("10"),
                            price=decimal.Decimal("70"))
        open_order_2.update(order_type=trading_enums.TraderOrderType.BUY_LIMIT,
                            order_id="open_order_2_id",
                            symbol="ETH/USDT",
                            current_price=decimal.Decimal("70"),
                            quantity=decimal.Decimal("10"),
                            price=decimal.Decimal("70"),
                            reduce_only=True)
        open_order_3.update(order_type=trading_enums.TraderOrderType.BUY_LIMIT,
                            order_id="open_order_2_id",
                            symbol="ADA/USDT",
                            current_price=decimal.Decimal("70"),
                            quantity=decimal.Decimal("10"),
                            price=decimal.Decimal("70"),
                            reduce_only=True)
        await mode.exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(open_order_1)
        await mode.exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(open_order_2)
        await mode.exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(open_order_3)
        mode.exchange_manager.exchange_config.traded_symbol_pairs = ["BTC/USDT", "ETH/USDT"]

        orders = await mode.single_exchange_process_optimize_initial_portfolio(["BTC", "ETH"], "USDT", {})
        convert_assets_to_target_asset_mock.assert_called_once_with(mode, ["BTC", "ETH"], "USDT", {})
        cancel_order_mock.assert_not_called()
        assert orders == ["order_1"]
        convert_assets_to_target_asset_mock.reset_mock()


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_get_target_ratio_with_config(trading_tools):
    update = {
        "refresh_interval": 72,
        "rebalance_trigger_min_percent": 10.2,
        "index_content": [
            {
                index_distribution.DISTRIBUTION_NAME: "BTC",
                index_distribution.DISTRIBUTION_VALUE: 1,
            },
            {
                index_distribution.DISTRIBUTION_NAME: "ETH",
                index_distribution.DISTRIBUTION_VALUE: 53,
            },
        ]
    }
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    assert mode.get_target_ratio("ETH") == decimal.Decimal('0')
    assert mode.get_target_ratio("BTC") == decimal.Decimal("1")  # use 100% BTC as others are not in traded pairs
    assert mode.get_target_ratio("SOL") == decimal.Decimal("0")

    trader.exchange_manager.exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in ["ETH/USDT", "ADA/USDT", "BTC/USDT", "SOL/USDT"]
    ]
    mode.init_user_inputs({})
    assert mode.get_target_ratio("ETH") == decimal.Decimal('0.9814814814814814814814814815')
    assert mode.get_target_ratio("BTC") == decimal.Decimal("0.01851851851851851851851851852")
    assert mode.get_target_ratio("SOL") == decimal.Decimal("0")


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_get_target_ratio_without_config(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    assert mode.get_target_ratio("ETH") == decimal.Decimal('0')
    assert mode.get_target_ratio("BTC") == decimal.Decimal("1")
    assert mode.get_target_ratio("SOL") == decimal.Decimal("0")
    trader.exchange_manager.exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in ["ETH/USDT", "SOL/USDT", "BTC/USDT"]
    ]
    mode.ensure_updated_coins_distribution()
    assert mode.get_target_ratio("ETH") == decimal.Decimal('0.3333333333333333617834929233')
    assert mode.get_target_ratio("BTC") == decimal.Decimal("0.3333333333333333617834929233")
    assert mode.get_target_ratio("SOL") == decimal.Decimal("0.3333333333333333617834929233")
    assert mode.get_target_ratio("ADA") == decimal.Decimal("0")

    trader.exchange_manager.exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in ["ETH/USDT", "BTC/USDT"]
    ]
    mode.ensure_updated_coins_distribution()
    assert mode.get_target_ratio("ETH") == decimal.Decimal('0.5')
    assert mode.get_target_ratio("BTC") == decimal.Decimal("0.5")
    assert mode.get_target_ratio("SOL") == decimal.Decimal("0")

    trader.exchange_manager.exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in ["ETH/USDT", "BTC/USDT", "ADA/USDT", "SOL/USDT"]
    ]
    mode.ensure_updated_coins_distribution()
    assert mode.get_target_ratio("ETH") == decimal.Decimal('0.25')
    assert mode.get_target_ratio("BTC") == decimal.Decimal("0.25")
    assert mode.get_target_ratio("SOL") == decimal.Decimal("0.25")


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_ohlcv_callback(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    current_time = time.time()
    with mock.patch.object(producer, "ensure_index", mock.AsyncMock()) as ensure_index_mock, \
        mock.patch.object(producer, "_notify_if_missing_too_many_coins", mock.Mock()) \
            as _notify_if_missing_too_many_coins_mock:
        with mock.patch.object(
                trader.exchange_manager.exchange, "get_exchange_current_time", mock.Mock(return_value=current_time)
        ) as get_exchange_current_time_mock:
            # not enough indexed coins
            mode.indexed_coins = []
            assert producer._last_trigger_time == 0
            await producer.ohlcv_callback("binance", "123", "BTC", "BTC/USDT", None, None)
            ensure_index_mock.assert_not_called()
            _notify_if_missing_too_many_coins_mock.assert_not_called()
            assert get_exchange_current_time_mock.call_count == 1   # only called once as no historical config exists
            get_exchange_current_time_mock.reset_mock()
            assert producer._last_trigger_time == current_time

            # enough coins
            mode.indexed_coins = [1, 2, 3]
            # already called on this time
            await producer.ohlcv_callback("binance", "123", "BTC", "BTC/USDT", None, None)
            ensure_index_mock.assert_not_called()
            _notify_if_missing_too_many_coins_mock.assert_not_called()
            assert get_exchange_current_time_mock.call_count == 1

            assert producer._last_trigger_time == current_time
        with mock.patch.object(
                trader.exchange_manager.exchange, "get_exchange_current_time", mock.Mock(return_value=current_time * 2)
        ) as get_exchange_current_time_mock:
            mode.indexed_coins = [1, 2, 3]
            await producer.ohlcv_callback("binance", "123", "BTC", "BTC/USDT", None, None)
            ensure_index_mock.assert_called_once()
            _notify_if_missing_too_many_coins_mock.assert_called_once()
            assert get_exchange_current_time_mock.call_count == 1
            assert producer._last_trigger_time == current_time * 2


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_notify_if_missing_too_many_coins(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    with mock.patch.object(producer.logger, "error", mock.Mock()) as error_mock:
        mode.trading_config[producer.INDEX_CONTENT] = [1, 2, 3, 4, 5]
        mode.indexed_coins = [1, 2, 3, 4, 5]
        producer._notify_if_missing_too_many_coins()
        error_mock.assert_not_called()

        mode.indexed_coins = [1, 2, 3]
        producer._notify_if_missing_too_many_coins()
        error_mock.assert_not_called()

        # error
        mode.indexed_coins = [1, 2]
        producer._notify_if_missing_too_many_coins()
        error_mock.assert_called_once()
        error_mock.reset_mock()

        # error
        mode.indexed_coins = []
        producer._notify_if_missing_too_many_coins()
        error_mock.assert_called_once()
        error_mock.reset_mock()


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_ensure_index(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    dependencies = trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])
    with mock.patch.object(
            producer, "_wait_for_symbol_prices_and_profitability_init", mock.AsyncMock()
    ) as _wait_for_symbol_prices_and_profitability_init_mock, \
        mock.patch.object(producer, "cancel_traded_pairs_open_orders_if_any", mock.AsyncMock(return_value=dependencies)) \
            as _cancel_traded_pairs_open_orders_if_any:
        with mock.patch.object(producer, "_trigger_rebalance", mock.AsyncMock()) as _trigger_rebalance_mock:
            with mock.patch.object(
                    producer, "_get_rebalance_details", mock.Mock(return_value=(False, {}))
            ) as _get_rebalance_details_mock:
                await producer.ensure_index()
                assert producer.last_activity == octobot_trading.modes.TradingModeActivity(
                    index_trading.IndexActivity.REBALANCING_SKIPPED
                )
                _cancel_traded_pairs_open_orders_if_any.assert_called_once()
                _cancel_traded_pairs_open_orders_if_any.reset_mock()
                _wait_for_symbol_prices_and_profitability_init_mock.assert_called_once()
                _wait_for_symbol_prices_and_profitability_init_mock.reset_mock()
                _get_rebalance_details_mock.assert_called_once()
                _trigger_rebalance_mock.assert_not_called()
            with mock.patch.object(
                    producer, "_get_rebalance_details", mock.Mock(return_value=(True, {"plop": 1}))
            ) as _get_rebalance_details_mock:
                await producer.ensure_index()
                assert producer.last_activity == octobot_trading.modes.TradingModeActivity(
                    index_trading.IndexActivity.REBALANCING_DONE, {"plop": 1}
                )
                _cancel_traded_pairs_open_orders_if_any.assert_called_once()
                _cancel_traded_pairs_open_orders_if_any.reset_mock()
                _wait_for_symbol_prices_and_profitability_init_mock.assert_called_once()
                _wait_for_symbol_prices_and_profitability_init_mock.reset_mock()
                _get_rebalance_details_mock.assert_called_once()
                _trigger_rebalance_mock.assert_called_once_with({"plop": 1}, dependencies)
                _trigger_rebalance_mock.reset_mock()
            with mock.patch.object(
                    producer, "_get_rebalance_details", mock.Mock(return_value=(True, {"plop": 1}))
            ) as _get_rebalance_details_mock:
                producer.trading_mode.cancel_open_orders = False
                await producer.ensure_index()
                assert producer.last_activity == octobot_trading.modes.TradingModeActivity(
                    index_trading.IndexActivity.REBALANCING_DONE, {"plop": 1}
                )
                _wait_for_symbol_prices_and_profitability_init_mock.assert_called_once()
                _wait_for_symbol_prices_and_profitability_init_mock.reset_mock()
                _get_rebalance_details_mock.assert_called_once()
                _cancel_traded_pairs_open_orders_if_any.assert_not_called()
                _trigger_rebalance_mock.assert_called_once_with({"plop": 1}, None)

        # Test with requires_initializing_appropriate_coins_distribution = True
        with mock.patch.object(producer, "_trigger_rebalance", mock.AsyncMock()) as _trigger_rebalance_mock:
            with mock.patch.object(
                    producer, "_get_rebalance_details", mock.Mock(return_value=(False, {}))
            ) as _get_rebalance_details_mock:
                with mock.patch.object(
                        mode, "ensure_updated_coins_distribution", mock.Mock()
                ) as ensure_updated_coins_distribution_mock:
                    # Set the flag to True
                    mode.requires_initializing_appropriate_coins_distribution = True
                    producer.trading_mode.cancel_open_orders = True
                    await producer.ensure_index()
                    # Verify ensure_updated_coins_distribution was called with adapt_to_holdings=True
                    ensure_updated_coins_distribution_mock.assert_called_once_with(adapt_to_holdings=True)
                    # Verify the flag was set to False
                    assert mode.requires_initializing_appropriate_coins_distribution is False
                    assert producer.last_activity == octobot_trading.modes.TradingModeActivity(
                        index_trading.IndexActivity.REBALANCING_SKIPPED
                    )
                    _cancel_traded_pairs_open_orders_if_any.assert_called_once()
                    _wait_for_symbol_prices_and_profitability_init_mock.assert_called_once()
                    _get_rebalance_details_mock.assert_called_once()
                    _trigger_rebalance_mock.assert_not_called()
                    ensure_updated_coins_distribution_mock.reset_mock()
                    _cancel_traded_pairs_open_orders_if_any.reset_mock()
                    _wait_for_symbol_prices_and_profitability_init_mock.reset_mock()
                    _get_rebalance_details_mock.reset_mock()

            with mock.patch.object(
                    producer, "_get_rebalance_details", mock.Mock(return_value=(True, {"plop": 1}))
            ) as _get_rebalance_details_mock:
                with mock.patch.object(
                        mode, "ensure_updated_coins_distribution", mock.Mock()
                ) as ensure_updated_coins_distribution_mock:
                    # Set the flag to True and disable cancel_open_orders
                    mode.requires_initializing_appropriate_coins_distribution = True
                    producer.trading_mode.cancel_open_orders = False
                    await producer.ensure_index()
                    # Verify ensure_updated_coins_distribution was called with adapt_to_holdings=True
                    ensure_updated_coins_distribution_mock.assert_called_once_with(adapt_to_holdings=True)
                    # Verify the flag was set to False
                    assert mode.requires_initializing_appropriate_coins_distribution is False
                    assert producer.last_activity == octobot_trading.modes.TradingModeActivity(
                        index_trading.IndexActivity.REBALANCING_DONE, {"plop": 1}
                    )
                    _wait_for_symbol_prices_and_profitability_init_mock.assert_called_once()
                    _get_rebalance_details_mock.assert_called_once()
                    _cancel_traded_pairs_open_orders_if_any.assert_not_called()
                    _trigger_rebalance_mock.assert_called_once_with({"plop": 1}, None)
                    ensure_updated_coins_distribution_mock.reset_mock()
                    _wait_for_symbol_prices_and_profitability_init_mock.reset_mock()
                    _get_rebalance_details_mock.reset_mock()
                    _trigger_rebalance_mock.reset_mock()

        # Test with requires_initializing_appropriate_coins_distribution = False (default)
        with mock.patch.object(producer, "_trigger_rebalance", mock.AsyncMock()) as _trigger_rebalance_mock:
            with mock.patch.object(
                    producer, "_get_rebalance_details", mock.Mock(return_value=(False, {}))
            ) as _get_rebalance_details_mock:
                with mock.patch.object(
                        mode, "ensure_updated_coins_distribution", mock.Mock()
                ) as ensure_updated_coins_distribution_mock:
                    # Ensure the flag is False (default state)
                    mode.requires_initializing_appropriate_coins_distribution = False
                    producer.trading_mode.cancel_open_orders = True
                    await producer.ensure_index()
                    # Verify ensure_updated_coins_distribution was NOT called
                    ensure_updated_coins_distribution_mock.assert_not_called()
                    # Verify the flag remains False
                    assert mode.requires_initializing_appropriate_coins_distribution is False
                    assert producer.last_activity == octobot_trading.modes.TradingModeActivity(
                        index_trading.IndexActivity.REBALANCING_SKIPPED
                    )
                    _cancel_traded_pairs_open_orders_if_any.assert_called_once()
                    _wait_for_symbol_prices_and_profitability_init_mock.assert_called_once()
                    _get_rebalance_details_mock.assert_called_once()
                    _trigger_rebalance_mock.assert_not_called()


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_cancel_traded_pairs_open_orders_if_any(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    orders = [
        mock.Mock(symbol="BTC/USDT"),
        mock.Mock(symbol="BTC/USDT"),
        mock.Mock(symbol="ETH/USDT"),
        mock.Mock(symbol="DOGE/USDT"),
    ]
    with mock.patch.object(
        trader.exchange_manager.exchange_personal_data.orders_manager, "get_open_orders", mock.Mock(return_value=orders)
    ) as get_open_orders_mock, \
        mock.patch.object(mode, "cancel_order", mock.AsyncMock(return_value=(True, trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])))) \
            as cancel_order_mock:
        assert await producer.cancel_traded_pairs_open_orders_if_any() == trading_signals.get_orders_dependencies([mock.Mock(order_id="123"), mock.Mock(order_id="123")])
        get_open_orders_mock.assert_called_once()
        assert cancel_order_mock.call_count == 2
        assert cancel_order_mock.mock_calls[0].args[0] is orders[0]
        assert cancel_order_mock.mock_calls[1].args[0] is orders[1]


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_trigger_rebalance(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    with mock.patch.object(
            producer, "submit_trading_evaluation", mock.AsyncMock()
    ) as _wait_for_symbol_prices_and_profitability_init_mock:
        details = {"hi": "ho"}
        await producer._trigger_rebalance(details, trading_signals.get_orders_dependencies([mock.Mock(order_id="123")]))
        _wait_for_symbol_prices_and_profitability_init_mock.assert_called_once_with(
            cryptocurrency=None,
            symbol=None,
            time_frame=None,
            final_note=None,
            state=trading_enums.EvaluatorStates.NEUTRAL,
            data=details,
            dependencies=trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])
        )


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_get_rebalance_details(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    trader.exchange_manager.exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in ["ETH/USDT", "BTC/USDT", "SOL/USDT"]
    ]
    mode.ensure_updated_coins_distribution()
    mode.rebalance_trigger_min_ratio = decimal.Decimal("0.1")
    is_futures = trader.exchange_manager.is_future
    portfolio_value_holder = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder
    positions_manager = trader.exchange_manager.exchange_personal_data.positions_manager

    with mock.patch.object(producer, "_resolve_swaps", mock.Mock()) as _resolve_swaps_mock:
        def _get_holdings_ratio(coin, **kwargs):
            if coin == "USDT":
                return decimal.Decimal("0")
            return decimal.Decimal("0.3")
        
        # For futures, positions need to be non-idle with proper values to get ratio 0.3
        # If total_portfolio_value = 1000, then position_value should be 1000 * 0.3 = 300
        total_portfolio_value = decimal.Decimal("1000")
        position_value = total_portfolio_value * decimal.Decimal("0.3")  # 300
        
        def _get_symbol_position(symbol, side=None):
            position_mock = mock.Mock()
            position_mock.symbol = symbol
            position_mock.side = side or trading_enums.PositionSide.LONG
            position_mock.get_value.return_value = position_value
            position_mock.size = decimal.Decimal("0.3")  # Size for BTC/USDT at ~1000 price
            position_mock.is_open.return_value = True
            position_mock.is_idle.return_value = False
            return position_mock
        
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ) as get_symbol_position_mock, \
        mock.patch.object(
            portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio)
        ) as get_holdings_ratio_mock, \
        mock.patch.object(
            portfolio_value_holder, "get_traded_assets_holdings_value", mock.Mock(return_value=total_portfolio_value)
        ) as get_traded_assets_holdings_value_mock:
            with mock.patch.object(
                mode, "get_removed_coins_from_config", mock.Mock(return_value=[])
            ) as get_removed_coins_from_config_mock:
                should_rebalance, details = producer._get_rebalance_details()
                assert should_rebalance is False
                assert details == {
                    index_trading.RebalanceDetails.SELL_SOME.value: {},
                    index_trading.RebalanceDetails.BUY_MORE.value: {},
                    index_trading.RebalanceDetails.REMOVE.value: {},
                    index_trading.RebalanceDetails.ADD.value: {},
                    index_trading.RebalanceDetails.SWAP.value: {},
                index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
                }
                assert get_holdings_ratio_mock.call_count == len(mode.indexed_coins) + 1  # +1 for USDT
                get_removed_coins_from_config_mock.assert_called_once()
                _resolve_swaps_mock.assert_called_once_with(details)
                _resolve_swaps_mock.reset_mock()
                get_holdings_ratio_mock.reset_mock()
                get_symbol_position_mock.reset_mock()
                get_traded_assets_holdings_value_mock.reset_mock()
            with mock.patch.object(
                    mode, "get_removed_coins_from_config", mock.Mock(return_value=["SOL", "ADA"])
            ) as get_removed_coins_from_config_mock:
                should_rebalance, details = producer._get_rebalance_details()
                assert should_rebalance is True
                assert details == {
                    index_trading.RebalanceDetails.SELL_SOME.value: {},
                    index_trading.RebalanceDetails.BUY_MORE.value: {},
                    index_trading.RebalanceDetails.REMOVE.value: {
                        "SOL": decimal.Decimal("0.3"),
                        # "ADA": decimal.Decimal("0.3")  # ADA is not in traded pairs, it's not removed
                    },
                    index_trading.RebalanceDetails.ADD.value: {},
                    index_trading.RebalanceDetails.SWAP.value: {},
                index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
                }
                assert get_holdings_ratio_mock.call_count == \
                           len(mode.indexed_coins) + len(details[index_trading.RebalanceDetails.REMOVE.value]) + 1  # +1 for USDT
                get_removed_coins_from_config_mock.assert_called_once()
                _resolve_swaps_mock.assert_called_once_with(details)
                _resolve_swaps_mock.reset_mock()
                get_holdings_ratio_mock.reset_mock()
                get_symbol_position_mock.reset_mock()
                get_traded_assets_holdings_value_mock.reset_mock()
        def _get_holdings_ratio(coin, **kwargs):
            if coin == "USDT":
                return decimal.Decimal("0")
            return decimal.Decimal("0.2")
        
        # For futures, positions need to be non-idle with proper values to get ratio 0.2 (below target, so triggers BUY_MORE)
        # If total_portfolio_value = 1000, then position_value should be 1000 * 0.2 = 200
        total_portfolio_value_2 = decimal.Decimal("1000")
        position_value_2 = total_portfolio_value_2 * decimal.Decimal("0.2")  # 200
        
        def _get_symbol_position(symbol, side=None):
            position_mock = mock.Mock()
            position_mock.symbol = symbol
            position_mock.side = side or trading_enums.PositionSide.LONG
            position_mock.get_value.return_value = position_value_2
            position_mock.size = decimal.Decimal("0.2")  # Size for BTC/USDT at ~1000 price
            position_mock.is_open.return_value = True
            position_mock.is_idle.return_value = False
            return position_mock
        
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ) as get_symbol_position_mock, \
        mock.patch.object(
                portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio)
        ) as get_holdings_ratio_mock, \
        mock.patch.object(
            portfolio_value_holder, "get_traded_assets_holdings_value", mock.Mock(return_value=total_portfolio_value_2)
        ) as get_traded_assets_holdings_value_mock_2:
            with mock.patch.object(
                    mode, "get_removed_coins_from_config", mock.Mock(return_value=[])
            ) as get_removed_coins_from_config_mock:
                should_rebalance, details = producer._get_rebalance_details()
                assert should_rebalance is True
                assert details == {
                    index_trading.RebalanceDetails.SELL_SOME.value: {},
                    index_trading.RebalanceDetails.BUY_MORE.value: {
                        'BTC': decimal.Decimal('0.3333333333333333617834929233'),
                        'ETH': decimal.Decimal('0.3333333333333333617834929233'),
                        'SOL': decimal.Decimal('0.3333333333333333617834929233')
                    },
                    index_trading.RebalanceDetails.REMOVE.value: {},
                    index_trading.RebalanceDetails.ADD.value: {},
                    index_trading.RebalanceDetails.SWAP.value: {},
                index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
                }
                assert get_holdings_ratio_mock.call_count == len(mode.indexed_coins) + 1  # +1 for USDT
                get_removed_coins_from_config_mock.assert_called_once()
                _resolve_swaps_mock.assert_called_once_with(details)
                _resolve_swaps_mock.reset_mock()
                get_holdings_ratio_mock.reset_mock()
                get_symbol_position_mock.reset_mock()
                get_traded_assets_holdings_value_mock_2.reset_mock()
            with mock.patch.object(
                    mode, "get_removed_coins_from_config", mock.Mock(return_value=["SOL", "ADA"])
            ) as get_removed_coins_from_config_mock:
                should_rebalance, details = producer._get_rebalance_details()
                assert should_rebalance is True
                assert details == {
                    index_trading.RebalanceDetails.SELL_SOME.value: {},
                    index_trading.RebalanceDetails.BUY_MORE.value: {
                        'BTC': decimal.Decimal('0.3333333333333333617834929233'),
                        'ETH': decimal.Decimal('0.3333333333333333617834929233'),
                        'SOL': decimal.Decimal('0.3333333333333333617834929233')
                    },
                    index_trading.RebalanceDetails.REMOVE.value: {
                        "SOL": decimal.Decimal("0.2"),
                        # "ADA": decimal.Decimal("0.2")  # not in traded pairs
                    },
                    index_trading.RebalanceDetails.ADD.value: {},
                    index_trading.RebalanceDetails.SWAP.value: {},
                index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
                }
                assert get_holdings_ratio_mock.call_count == \
                           len(mode.indexed_coins) + len(details[index_trading.RebalanceDetails.REMOVE.value]) + 1  # +1 for USDT
                get_removed_coins_from_config_mock.assert_called_once()
                _resolve_swaps_mock.assert_called_once_with(details)
                _resolve_swaps_mock.reset_mock()
                get_holdings_ratio_mock.reset_mock()
                get_symbol_position_mock.reset_mock()

        # rebalance cap larger than ratio
        def _get_holdings_ratio(coin, **kwargs):
            if coin == "USDT":
                return decimal.Decimal("0")
            return decimal.Decimal("0.3")
        
        # For futures, positions need to have proper values to get ratio 0.3 (within acceptable range)
        # If total_portfolio_value = 1000, then position_value should be 1000 * 0.3 = 300
        total_portfolio_value_rebalance_cap = decimal.Decimal("1000")
        position_value_rebalance_cap = total_portfolio_value_rebalance_cap * decimal.Decimal("0.3")  # 300
        
        def _get_symbol_position(symbol, side=None):
            position_mock = mock.Mock()
            position_mock.symbol = symbol
            position_mock.side = side or trading_enums.PositionSide.LONG
            position_mock.get_value.return_value = position_value_rebalance_cap
            position_mock.size = decimal.Decimal("0.3")  # Size for BTC/USDT at ~1000 price
            position_mock.is_open.return_value = True
            position_mock.is_idle.return_value = False
            return position_mock
        
        mode.rebalance_trigger_min_ratio = decimal.Decimal("0.5")
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ) as get_symbol_position_mock, \
        mock.patch.object(
                portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio)
        ) as get_holdings_ratio_mock, \
        mock.patch.object(
            portfolio_value_holder, "get_traded_assets_holdings_value", mock.Mock(return_value=total_portfolio_value_rebalance_cap)
        ) as get_traded_assets_holdings_value_mock:
            should_rebalance, details = producer._get_rebalance_details()
            assert should_rebalance is False
            assert details == {
                index_trading.RebalanceDetails.SELL_SOME.value: {},
                index_trading.RebalanceDetails.BUY_MORE.value: {},
                index_trading.RebalanceDetails.REMOVE.value: {},
                index_trading.RebalanceDetails.ADD.value: {},
                index_trading.RebalanceDetails.SWAP.value: {},
                index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
            }
            assert get_holdings_ratio_mock.call_count == len(mode.indexed_coins) + 1  # +1 for USDT
            get_holdings_ratio_mock.reset_mock()
            get_symbol_position_mock.reset_mock()
            get_traded_assets_holdings_value_mock.reset_mock()
            _resolve_swaps_mock.assert_called_once_with(details)
            _resolve_swaps_mock.reset_mock()
        def _get_holdings_ratio(coin, **kwargs):
            if coin == "USDT":
                return decimal.Decimal("0")
            return decimal.Decimal("0.00000001")
        
        # For futures, positions need to have proper values to get ratio 0.00000001 (within acceptable range)
        # If total_portfolio_value = 1000, then position_value should be 1000 * 0.00000001 = 0.00001
        total_portfolio_value_small = decimal.Decimal("1000")
        position_value_small = total_portfolio_value_small * decimal.Decimal("0.00000001")  # 0.00001
        
        def _get_symbol_position_small(symbol, side=None):
            position_mock = mock.Mock()
            position_mock.symbol = symbol
            position_mock.side = side or trading_enums.PositionSide.LONG
            position_mock.get_value.return_value = position_value_small
            position_mock.size = decimal.Decimal("0.00000001")  # Very small size
            position_mock.is_open.return_value = True
            position_mock.is_idle.return_value = False
            return position_mock
        
        with mock.patch.object(
                positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position_small)
        ) as get_symbol_position_mock, \
        mock.patch.object(
                portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio)
        ) as get_holdings_ratio_mock, \
        mock.patch.object(
            portfolio_value_holder, "get_traded_assets_holdings_value", mock.Mock(return_value=total_portfolio_value_small)
        ) as get_traded_assets_holdings_value_mock:
            should_rebalance, details = producer._get_rebalance_details()
            assert should_rebalance is False
            assert details == {
                index_trading.RebalanceDetails.SELL_SOME.value: {},
                index_trading.RebalanceDetails.BUY_MORE.value: {},
                index_trading.RebalanceDetails.REMOVE.value: {},
                index_trading.RebalanceDetails.ADD.value: {},
                index_trading.RebalanceDetails.SWAP.value: {},
                index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
            }
            assert get_holdings_ratio_mock.call_count == len(mode.indexed_coins) + 1  # +1 for USDT
            get_holdings_ratio_mock.reset_mock()
            get_symbol_position_mock.reset_mock()
            get_traded_assets_holdings_value_mock.reset_mock()
            _resolve_swaps_mock.assert_called_once_with(details)
            _resolve_swaps_mock.reset_mock()
        def _get_holdings_ratio(coin, **kwargs):
            if coin == "USDT":
                return decimal.Decimal("0")
            return decimal.Decimal("0.9")
        
        # For futures, positions need to have proper values to get ratio 0.9 (above target, so triggers SELL_SOME)
        # If total_portfolio_value = 1000, then position_value should be 1000 * 0.9 = 900
        total_portfolio_value_high = decimal.Decimal("1000")
        position_value_high = total_portfolio_value_high * decimal.Decimal("0.9")  # 900
        
        def _get_symbol_position(symbol, side=None):
            position_mock = mock.Mock()
            position_mock.symbol = symbol
            position_mock.side = side or trading_enums.PositionSide.LONG
            position_mock.get_value.return_value = position_value_high
            position_mock.size = decimal.Decimal("0.9")  # Size for BTC/USDT at ~1000 price
            position_mock.is_open.return_value = True
            position_mock.is_idle.return_value = False
            return position_mock
        
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ) as get_symbol_position_mock, \
        mock.patch.object(
                portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio)
        ) as get_holdings_ratio_mock, \
        mock.patch.object(
            portfolio_value_holder, "get_traded_assets_holdings_value", mock.Mock(return_value=total_portfolio_value_high)
        ) as get_traded_assets_holdings_value_mock:
            should_rebalance, details = producer._get_rebalance_details()
            assert should_rebalance is True
            assert details == {
                index_trading.RebalanceDetails.SELL_SOME.value: {
                    'BTC': decimal.Decimal('0.3333333333333333617834929233'),
                    'ETH': decimal.Decimal('0.3333333333333333617834929233'),
                    'SOL': decimal.Decimal('0.3333333333333333617834929233')
                },
                index_trading.RebalanceDetails.BUY_MORE.value: {},
                index_trading.RebalanceDetails.REMOVE.value: {},
                index_trading.RebalanceDetails.ADD.value: {},
                index_trading.RebalanceDetails.SWAP.value: {},
                index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
            }
            assert get_holdings_ratio_mock.call_count == len(details[index_trading.RebalanceDetails.SELL_SOME.value]) + 1  # +1 for USDT
            get_holdings_ratio_mock.reset_mock()
            get_symbol_position_mock.reset_mock()
            get_traded_assets_holdings_value_mock.reset_mock()
            _resolve_swaps_mock.assert_called_once_with(details)
            _resolve_swaps_mock.reset_mock()
        def _get_holdings_ratio(coin, **kwargs):
            return decimal.Decimal("0")
        
        def _get_symbol_position(symbol, side=None):
            position_mock = mock.Mock()
            position_mock.symbol = symbol
            position_mock.side = side or trading_enums.PositionSide.LONG
            position_mock.get_value.return_value = decimal.Decimal("0")
            position_mock.size = decimal.Decimal("0")
            position_mock.is_open.return_value = False
            position_mock.is_idle.return_value = True
            return position_mock
        
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ) as get_symbol_position_mock, \
        mock.patch.object(
                portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio)
        ) as get_holdings_ratio_mock:
            should_rebalance, details = producer._get_rebalance_details()
            assert should_rebalance is True
            assert details == {
                index_trading.RebalanceDetails.SELL_SOME.value: {},
                index_trading.RebalanceDetails.BUY_MORE.value: {},
                index_trading.RebalanceDetails.REMOVE.value: {},
                index_trading.RebalanceDetails.ADD.value: {
                    'BTC': decimal.Decimal('0.3333333333333333617834929233'),
                    'ETH': decimal.Decimal('0.3333333333333333617834929233'),
                    'SOL': decimal.Decimal('0.3333333333333333617834929233')
                },
                index_trading.RebalanceDetails.SWAP.value: {},
                index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
            }
            assert get_holdings_ratio_mock.call_count == len(details[index_trading.RebalanceDetails.ADD.value]) + 1  # +1 for USDT
            get_traded_assets_holdings_value_mock.reset_mock()
            get_holdings_ratio_mock.reset_mock()
            get_symbol_position_mock.reset_mock()
            _resolve_swaps_mock.assert_called_once_with(details)
            _resolve_swaps_mock.reset_mock()

        # will only add ETH
        def _get_holdings_ratio(coin, **kwargs):
            if coin == "ETH":
                return decimal.Decimal("0")
            return decimal.Decimal("0.33")
        
        # For futures, positions need to have proper values: ETH should be idle (0), BTC and SOL should have ratio 0.33
        # If total_portfolio_value = 1000, then position_value for BTC/SOL should be 1000 * 0.33 = 330
        total_portfolio_value_eth_only = decimal.Decimal("1000")
        position_value_eth_only = total_portfolio_value_eth_only * decimal.Decimal("0.33")  # 330
        
        def _get_symbol_position(symbol, side=None):
            position_mock = mock.Mock()
            position_mock.symbol = symbol
            position_mock.side = side or trading_enums.PositionSide.LONG
            # ETH should be idle (ratio 0), BTC and SOL should have proper values (ratio 0.33)
            if "ETH" in symbol:
                position_mock.get_value.return_value = decimal.Decimal("0")
                position_mock.size = decimal.Decimal("0")
                position_mock.is_open.return_value = False
                position_mock.is_idle.return_value = True
            else:
                # BTC and SOL have proper positions
                position_mock.get_value.return_value = position_value_eth_only
                position_mock.size = decimal.Decimal("0.33")  # Size for BTC/USDT or SOL/USDT at ~1000 price
                position_mock.is_open.return_value = True
                position_mock.is_idle.return_value = False
            return position_mock
        
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ) as get_symbol_position_mock, \
        mock.patch.object(
            portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio)
        ) as get_holdings_ratio_mock, \
        mock.patch.object(
            portfolio_value_holder, "get_traded_assets_holdings_value", mock.Mock(return_value=total_portfolio_value_eth_only)
        ) as get_traded_assets_holdings_value_mock:
            should_rebalance, details = producer._get_rebalance_details()
            assert should_rebalance is True
            assert details == {
                index_trading.RebalanceDetails.SELL_SOME.value: {},
                index_trading.RebalanceDetails.BUY_MORE.value: {},
                index_trading.RebalanceDetails.REMOVE.value: {},
                index_trading.RebalanceDetails.ADD.value: {
                    'ETH': decimal.Decimal('0.3333333333333333617834929233'),
                },
                index_trading.RebalanceDetails.SWAP.value: {},
                index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
            }
            assert get_holdings_ratio_mock.call_count == 3 + 1  # called for each coin + 1 for USDT
            get_holdings_ratio_mock.reset_mock()
            get_symbol_position_mock.reset_mock()
            get_traded_assets_holdings_value_mock.reset_mock()
            _resolve_swaps_mock.assert_called_once_with(details)
            _resolve_swaps_mock.reset_mock()
        
@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_get_rebalance_details_with_usdt_without_coin_distribution_update(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    trader.exchange_manager.exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in ["ETH/USDT", "BTC/USDT", "SOL/USDT"]
    ]
    mode.ensure_updated_coins_distribution()
    mode.rebalance_trigger_min_ratio = decimal.Decimal("0.1")
    mode.synchronization_policy = index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE
    is_futures = trader.exchange_manager.is_future
    portfolio_value_holder = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder

    with mock.patch.object(producer, "_resolve_swaps", mock.Mock()) as _resolve_swaps_mock, \
        mock.patch.object(mode, "ensure_updated_coins_distribution", mock.Mock()) as ensure_updated_coins_distribution_mock:
        def _get_holdings_ratio(coin, **kwargs):
            # USDT is 1/3 of the portfolio
            if coin == "USDT":
                return decimal.Decimal("0.33")
            # other coins are 2/3 of the portfolio
            return decimal.Decimal("0.33") * decimal.Decimal("2") / decimal.Decimal("3")

        # Mock positions for futures - create positions for BTC, ETH, SOL
        # For futures rebalancer: ratio = position_value / total_portfolio_value
        # We want ratio = 0.22 (which is 0.33 * 2 / 3) to trigger BUY_MORE
        # If total_portfolio_value = 2000, then position_value should be 2000 * 0.22 = 440
        total_portfolio_value = decimal.Decimal("2000")
        target_coin_ratio = decimal.Decimal("0.33") * decimal.Decimal("2") / decimal.Decimal("3")  # 0.22
        position_value = total_portfolio_value * target_coin_ratio  # 440
        
        def _get_symbol_position(symbol, side=None):
            position_mock = mock.Mock()
            position_mock.symbol = symbol
            position_mock.side = side or trading_enums.PositionSide.LONG
            # Set position value to give ratio of 0.22 (below target of 0.333, so triggers BUY_MORE)
            position_mock.get_value.return_value = position_value
            position_mock.size = decimal.Decimal("1.33")  # Size for BTC/USDT at ~1000 price
            position_mock.is_open.return_value = True
            position_mock.is_idle.return_value = False
            return position_mock

        expected_details = {
            index_trading.RebalanceDetails.SELL_SOME.value: {},
            index_trading.RebalanceDetails.BUY_MORE.value: {
                'BTC': decimal.Decimal('0.3333333333333333617834929233'),
                'ETH': decimal.Decimal('0.3333333333333333617834929233'),
                'SOL': decimal.Decimal('0.3333333333333333617834929233')
            },
            index_trading.RebalanceDetails.REMOVE.value: {},
            index_trading.RebalanceDetails.ADD.value: {},
            index_trading.RebalanceDetails.SWAP.value: {},
            index_trading.RebalanceDetails.FORCED_REBALANCE.value: True,
        }
        
        positions_manager = trader.exchange_manager.exchange_personal_data.positions_manager
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ) as get_symbol_position_mock, \
        mock.patch.object(
            portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio)
        ) as get_holdings_ratio_mock, \
        mock.patch.object(
            portfolio_value_holder, "get_traded_assets_holdings_value", mock.Mock(return_value=total_portfolio_value)
        ) as get_traded_assets_holdings_value_mock:
            should_rebalance, details = producer._get_rebalance_details()
            assert should_rebalance is True
            assert details == expected_details
            assert get_holdings_ratio_mock.call_count == len(mode.indexed_coins) + 1  # called for each coin + 1 for USDT
            ensure_updated_coins_distribution_mock.assert_not_called()
            get_holdings_ratio_mock.reset_mock()
            get_symbol_position_mock.reset_mock()
            get_traded_assets_holdings_value_mock.reset_mock()
            _resolve_swaps_mock.assert_not_called()
            _resolve_swaps_mock.reset_mock()
    
        
@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_get_rebalance_details_with_usdt_and_coin_distribution_update(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    trader.exchange_manager.exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in ["ETH/USDT", "BTC/USDT", "SOL/USDT"]
    ]
    mode.ensure_updated_coins_distribution()
    mode.rebalance_trigger_min_ratio = decimal.Decimal("0.1")
    is_futures = trader.exchange_manager.is_future
    portfolio_value_holder = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder
    positions_manager = trader.exchange_manager.exchange_personal_data.positions_manager
    mode.synchronization_policy = index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE
    with mock.patch.object(producer, "_resolve_swaps", mock.Mock()) as _resolve_swaps_mock, \
        mock.patch.object(mode, "ensure_updated_coins_distribution", mock.Mock()) as ensure_updated_coins_distribution_mock:
        def _get_holdings_ratio(coin, **kwargs):
            # USDT is 1/3 of the portfolio
            if coin == "USDT":
                return decimal.Decimal("0.33")
            # other coins are 2/3 of the portfolio
            return decimal.Decimal("0.33") * decimal.Decimal("2") / decimal.Decimal("3")

        # Mock positions for futures - create positions for BTC, ETH, SOL
        # For futures rebalancer: ratio = position_value / total_portfolio_value
        # We want ratio = 0.22 (which is 0.33 * 2 / 3) to trigger BUY_MORE
        # If total_portfolio_value = 2000, then position_value should be 2000 * 0.22 = 440
        total_portfolio_value = decimal.Decimal("2000")
        target_coin_ratio = decimal.Decimal("0.33") * decimal.Decimal("2") / decimal.Decimal("3")  # 0.22
        position_value = total_portfolio_value * target_coin_ratio  # 440

        def _get_symbol_position(symbol, side=None):
            position_mock = mock.Mock()
            position_mock.symbol = symbol
            position_mock.side = side or trading_enums.PositionSide.LONG
            # Set position value to give ratio of 0.22 (below target of 0.333, so triggers BUY_MORE)
            position_mock.get_value.return_value = position_value
            position_mock.size = decimal.Decimal("1.33")  # Size for BTC/USDT at ~1000 price
            position_mock.is_open.return_value = True
            position_mock.is_idle.return_value = False
            return position_mock

        # with added USDT to the portfolio
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ) as get_symbol_position_mock, \
        mock.patch.object(
            portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio)
        ) as get_holdings_ratio_mock, \
        mock.patch.object(
            portfolio_value_holder, "get_traded_assets_holdings_value", mock.Mock(return_value=total_portfolio_value)
        ) as get_traded_assets_holdings_value_mock:
            should_rebalance, details = producer._get_rebalance_details()
            assert should_rebalance is True
            assert details == {
                index_trading.RebalanceDetails.SELL_SOME.value: {},
                index_trading.RebalanceDetails.BUY_MORE.value: {
                    'BTC': decimal.Decimal('0.3333333333333333617834929233'),
                    'ETH': decimal.Decimal('0.3333333333333333617834929233'),
                    'SOL': decimal.Decimal('0.3333333333333333617834929233')
                },
                index_trading.RebalanceDetails.REMOVE.value: {},
                index_trading.RebalanceDetails.ADD.value: {},
                index_trading.RebalanceDetails.SWAP.value: {},
                index_trading.RebalanceDetails.FORCED_REBALANCE.value: True,
            }
            assert get_holdings_ratio_mock.call_count == 2 * (len(mode.indexed_coins) + 1)  
            ensure_updated_coins_distribution_mock.assert_called_once()
            get_holdings_ratio_mock.reset_mock()
            get_symbol_position_mock.reset_mock()
            get_traded_assets_holdings_value_mock.reset_mock()
            _resolve_swaps_mock.assert_not_called()
            _resolve_swaps_mock.reset_mock()


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_should_rebalance_due_to_non_indexed_quote_assets_ratio(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    assert mode.quote_asset_rebalance_ratio_threshold == decimal.Decimal("0.1")
    rebalance_details = {
        index_trading.RebalanceDetails.SELL_SOME.value: {},
        index_trading.RebalanceDetails.BUY_MORE.value: {},
        index_trading.RebalanceDetails.REMOVE.value: {},
        index_trading.RebalanceDetails.ADD.value: {},
        index_trading.RebalanceDetails.SWAP.value: {},
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
    }
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.23"), rebalance_details) is True
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.1"), rebalance_details) is True
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.09"), rebalance_details) is False
    # lower threshold
    mode.quote_asset_rebalance_ratio_threshold = decimal.Decimal("0.05")
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.09"), rebalance_details) is True
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.04"), rebalance_details) is False

    # test added coins
    rebalance_details[index_trading.RebalanceDetails.ADD.value] = {
        "BTC": decimal.Decimal("0.1")
    }
    rebalance_details[index_trading.RebalanceDetails.BUY_MORE.value] = {
        "ETH": decimal.Decimal("0.1")
    }
    # can't swap quote for BTC & ETH
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.1"), rebalance_details) is True
    # can swap quote for BTC & ETH: don't rebalance
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.2"), rebalance_details) is False
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.21"), rebalance_details) is False
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.18"), rebalance_details) is False
    # beyond QUOTE_ASSET_TO_INDEXED_SWAP_RATIO_THRESHOLD threshold
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.17"), rebalance_details) is True

    # with removed coins: can't "just swap quote for added coins", perform regular quote ratio check
    rebalance_details[index_trading.RebalanceDetails.REMOVE.value] = {
        "BTC": decimal.Decimal("0.1")
    }
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.2"), rebalance_details) is True  # is False when no coins are to remove
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.03"), rebalance_details) is False  # bellow threshold: still false

    # with sell some coins and removed coins: can't "just swap quote for added coins", perform regular quote ratio check
    rebalance_details[index_trading.RebalanceDetails.SELL_SOME.value] = {
        "BTC": decimal.Decimal("0.1")
    }
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.2"), rebalance_details) is True  # is False when no coins are to remove
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.03"), rebalance_details) is False  # bellow threshold: still false
    # with only sell some coin
    rebalance_details[index_trading.RebalanceDetails.REMOVE.value] = {}
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.2"), rebalance_details) is True  # is False when no coins are to remove
    assert producer._should_rebalance_due_to_non_indexed_quote_assets_ratio(decimal.Decimal("0.03"), rebalance_details) is False  # bellow threshold: still false


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_get_non_indexed_quote_assets_ratio_with_reference_market_ratio(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    ref_market = trader.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
    portfolio_value_holder = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder

    def _get_holdings_ratio_usdt_15(coin, **kwargs):
        return decimal.Decimal("0.15") if coin == ref_market else decimal.Decimal("0")

    def _get_holdings_ratio_usdt_08(coin, **kwargs):
        return decimal.Decimal("0.08") if coin == ref_market else decimal.Decimal("0")

    def _get_holdings_ratio_usdt_95(coin, **kwargs):
        return decimal.Decimal("0.95") if coin == ref_market else decimal.Decimal("0")

    def _get_holdings_ratio_usdt_92(coin, **kwargs):
        return decimal.Decimal("0.92") if coin == ref_market else decimal.Decimal("0")

    with mock.patch.object(portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio_usdt_15)):
        mode.reference_market_ratio = trading_constants.ZERO
        assert producer._get_non_indexed_quote_assets_ratio() == decimal.Decimal("0.15")

    with mock.patch.object(portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio_usdt_15)):
        mode.reference_market_ratio = decimal.Decimal("0.1")
        # reference_market_ratio=10% means 90% should be kept, so excess = 15% - 90% = -75% = 0
        assert producer._get_non_indexed_quote_assets_ratio() == decimal.Decimal("0")

    with mock.patch.object(portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio_usdt_08)):
        mode.reference_market_ratio = decimal.Decimal("0.1")
        # reference_market_ratio=10% means 90% should be kept, so excess = 8% - 90% = -82% = 0
        assert producer._get_non_indexed_quote_assets_ratio() == decimal.Decimal("0")

    with mock.patch.object(portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio_usdt_95)):
        mode.reference_market_ratio = decimal.Decimal("0.1")
        # reference_market_ratio=10% means 90% should be kept, so excess = 95% - 90% = 5%
        assert producer._get_non_indexed_quote_assets_ratio() == decimal.Decimal("0.05")

    with mock.patch.object(portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio_usdt_92)):
        mode.reference_market_ratio = decimal.Decimal("0.1")
        # reference_market_ratio=10% means 90% should be kept, so excess = 92% - 90% = 2%
        assert producer._get_non_indexed_quote_assets_ratio() == decimal.Decimal("0.02")

    rebalance_details = {
        index_trading.RebalanceDetails.SELL_SOME.value: {},
        index_trading.RebalanceDetails.BUY_MORE.value: {},
        index_trading.RebalanceDetails.REMOVE.value: {},
        index_trading.RebalanceDetails.ADD.value: {},
        index_trading.RebalanceDetails.SWAP.value: {},
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
    }

    # USDT=15%, threshold 10%: without reference_market_ratio -> 15% >= 10% -> forces rebalance
    with mock.patch.object(portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio_usdt_15)):
        mode.reference_market_ratio = trading_constants.ZERO
        mode.quote_asset_rebalance_ratio_threshold = decimal.Decimal("0.1")
        details = {k: ({}.copy() if isinstance(v, dict) else v) for k, v in rebalance_details.items()}
        assert producer._register_quote_asset_rebalance(details) is True
        assert details[index_trading.RebalanceDetails.FORCED_REBALANCE.value] is True

    # reference_market_ratio=10% means 90% should be kept, USDT=15% -> excess = 15% - 90% = -75% = 0; threshold 10% -> no forced rebalance
    with mock.patch.object(portfolio_value_holder, "get_holdings_ratio", mock.Mock(side_effect=_get_holdings_ratio_usdt_15)):
        mode.reference_market_ratio = decimal.Decimal("0.1")
        mode.quote_asset_rebalance_ratio_threshold = decimal.Decimal("0.1")
        details = {k: ({}.copy() if isinstance(v, dict) else v) for k, v in rebalance_details.items()}
        assert producer._register_quote_asset_rebalance(details) is False
        assert details[index_trading.RebalanceDetails.FORCED_REBALANCE.value] is False


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_get_removed_coins_from_config_sell_removed_coins_asap(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    mode.synchronization_policy = index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE
    mode.sell_unindexed_traded_coins = False
    assert mode.get_removed_coins_from_config([]) == []
    mode.trading_config = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "AA"
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BB"
            }
        ]
    }
    assert mode.get_removed_coins_from_config([]) == []
    mode.previous_trading_config = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "AA"
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BB"
            }
        ]
    }
    mode.trading_config = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "AA"
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "CC"
            }
        ]
    }
    assert mode.get_removed_coins_from_config([]) == ["BB"]
    # with sell_unindexed_traded_coins=True
    mode.sell_unindexed_traded_coins = True
    mode.indexed_coins = ["BTC"]
    mode.previous_trading_config = None
    assert mode.get_removed_coins_from_config(["BTC", "ETH"]) == ["ETH"]
    mode.previous_trading_config = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "AA"
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BB"
            }
        ]
    }
    assert sorted(mode.get_removed_coins_from_config(["BTC", "ETH"])) == sorted(["ETH", "BB"])


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_get_removed_coins_from_config_sell_removed_on_ratio_rebalance(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    mode.synchronization_policy = index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE
    mode.sell_unindexed_traded_coins = False
    assert mode.get_removed_coins_from_config([]) == []
    # without historical config
    mode.trading_config = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC"
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "SOL"
            }
        ]
    }
    assert mode.get_removed_coins_from_config([]) == []
    # with sell_unindexed_traded_coins=True
    mode.sell_unindexed_traded_coins = True
    mode.indexed_coins = ["BTC"]
    assert mode.get_removed_coins_from_config(["BTC", "ETH"]) == ["ETH"]

    # with historical config
    historical_config_1 = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC"
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "ADA"
            }
        ]
    }
    historical_config_2 = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC"
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "DOT"
            }
        ]
    }
    commons_configuration.add_historical_tentacle_config(mode.trading_config, 1, historical_config_1)
    commons_configuration.add_historical_tentacle_config(mode.trading_config, 2, historical_config_2)
    mode.historical_master_config = mode.trading_config
    with mock.patch.object(mode.exchange_manager.exchange, "get_exchange_current_time", mock.Mock(return_value=0)):
        assert mode.get_removed_coins_from_config(["BTC", "ETH", "SOL"]) == ["ETH", "SOL"]
    with mock.patch.object(mode.exchange_manager.exchange, "get_exchange_current_time", mock.Mock(return_value=2)):
        assert sorted(mode.get_removed_coins_from_config(["BTC", "ETH", "SOL"])) == sorted(
            ["ETH", "SOL", "ADA", "DOT"]
        )
        assert sorted(mode.get_removed_coins_from_config(["BTC", "ETH"])) == sorted(['ADA', 'DOT', 'ETH'])

    # with sell_unindexed_traded_coins=False
    mode.sell_unindexed_traded_coins = False
    with mock.patch.object(mode.exchange_manager.exchange, "get_exchange_current_time", mock.Mock(return_value=0)):
        assert mode.get_removed_coins_from_config(["BTC", "ETH", "SOL"]) == []
    with mock.patch.object(mode.exchange_manager.exchange, "get_exchange_current_time", mock.Mock(return_value=2)):
        assert sorted(mode.get_removed_coins_from_config(["BTC", "ETH", "SOL"])) == sorted(
            ["ADA", "DOT"]
        )
        assert sorted(mode.get_removed_coins_from_config(["BTC", "ETH"])) == sorted(['ADA', 'DOT'])


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_create_new_orders(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    with mock.patch.object(
            consumer, "_rebalance_portfolio", mock.AsyncMock(return_value="plop")
    ) as _rebalance_portfolio_mock:
        assert mode.is_processing_rebalance is False
        with pytest.raises(KeyError):
            # missing "data"
            await consumer.create_new_orders(None, None, None)
        assert await consumer.create_new_orders(None, None, None, data="hello", dependencies=trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])) == []
        assert mode.is_processing_rebalance is False
        _rebalance_portfolio_mock.assert_not_called()
        assert await consumer.create_new_orders(
            None, None, trading_enums.EvaluatorStates.NEUTRAL.value, data="hello", dependencies=trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])
        ) == "plop"
        _rebalance_portfolio_mock.assert_called_once_with("hello", trading_signals.get_orders_dependencies([mock.Mock(order_id="123")]))
        assert mode.is_processing_rebalance is False


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_rebalance_portfolio(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    sell_order = mock.Mock(order_id="456")
    with mock.patch.object(
            consumer, "_ensure_enough_funds_to_buy_after_selling", mock.AsyncMock()
    ) as _ensure_enough_funds_to_buy_after_selling_mock, mock.patch.object(
        consumer.trading_mode.rebalancer, "sell_indexed_coins_for_reference_market", mock.AsyncMock(return_value=[sell_order])
    ) as _sell_indexed_coins_for_reference_market_mock, mock.patch.object(
        consumer, "_split_reference_market_into_indexed_coins", mock.AsyncMock(return_value=["buy"])
    ) as _split_reference_market_into_indexed_coins_mock:
        with mock.patch.object(
            consumer, "_can_simply_buy_coins_without_selling", mock.Mock(return_value=False)
        ) as _can_simply_buy_coins_without_selling_mock:
            assert await consumer._rebalance_portfolio("details", trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])) == [sell_order, "buy"]
            _ensure_enough_funds_to_buy_after_selling_mock.assert_called_once()
            _sell_indexed_coins_for_reference_market_mock.assert_called_once_with("details", trading_signals.get_orders_dependencies([mock.Mock(order_id="123")]))
            _split_reference_market_into_indexed_coins_mock.assert_called_once_with("details", False, trading_signals.get_orders_dependencies([mock.Mock(order_id="456")]))
            _can_simply_buy_coins_without_selling_mock.assert_called_once_with("details")
            _ensure_enough_funds_to_buy_after_selling_mock.reset_mock()
            _sell_indexed_coins_for_reference_market_mock.reset_mock()
            _split_reference_market_into_indexed_coins_mock.reset_mock()
        with mock.patch.object(
            consumer, "_can_simply_buy_coins_without_selling", mock.Mock(return_value=True)
        ) as _can_simply_buy_coins_without_selling_mock:
            assert await consumer._rebalance_portfolio("details", trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])) == ["buy"]
            _ensure_enough_funds_to_buy_after_selling_mock.assert_called_once()
            _sell_indexed_coins_for_reference_market_mock.assert_not_called()
            _split_reference_market_into_indexed_coins_mock.assert_called_once_with("details", True, trading_signals.get_orders_dependencies([mock.Mock(order_id="123")]))
            _can_simply_buy_coins_without_selling_mock.assert_called_once_with("details")

    with mock.patch.object(
            consumer, "_update_producer_last_activity", mock.Mock()
    ) as _update_producer_last_activity_mock:
        with mock.patch.object(
                consumer, "_ensure_enough_funds_to_buy_after_selling", mock.AsyncMock()
        ) as _ensure_enough_funds_to_buy_after_selling_mock, mock.patch.object(
            consumer.trading_mode.rebalancer, "sell_indexed_coins_for_reference_market", mock.AsyncMock(
                side_effect=trading_errors.MissingMinimalExchangeTradeVolume
            )
        ) as _sell_indexed_coins_for_reference_market_mock, mock.patch.object(
            consumer, "_split_reference_market_into_indexed_coins", mock.AsyncMock(return_value=["buy"])
        ) as _split_reference_market_into_indexed_coins_mock, mock.patch.object(
            consumer, "_can_simply_buy_coins_without_selling", mock.Mock(return_value=False)
        ) as _can_simply_buy_coins_without_selling_mock:
            assert await consumer._rebalance_portfolio("details", trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])) == []
            _ensure_enough_funds_to_buy_after_selling_mock.assert_called_once()
            _sell_indexed_coins_for_reference_market_mock.assert_called_once_with("details", trading_signals.get_orders_dependencies([mock.Mock(order_id="123")]))
            _split_reference_market_into_indexed_coins_mock.assert_not_called()
            _can_simply_buy_coins_without_selling_mock.assert_called_once_with("details")
            _update_producer_last_activity_mock.assert_called_once_with(
                index_trading.IndexActivity.REBALANCING_SKIPPED,
                index_trading.RebalanceSkipDetails.NOT_ENOUGH_AVAILABLE_FOUNDS.value
            )
            _update_producer_last_activity_mock.reset_mock()

        with mock.patch.object(
            consumer, "_ensure_enough_funds_to_buy_after_selling", mock.AsyncMock(
                side_effect=trading_errors.MissingMinimalExchangeTradeVolume
            )
        ) as _ensure_enough_funds_to_buy_after_selling_mock, \
            mock.patch.object(
                consumer.trading_mode.rebalancer, "sell_indexed_coins_for_reference_market", mock.AsyncMock(return_value=[sell_order])
        ) as _sell_indexed_coins_for_reference_market_mock, mock.patch.object(
            consumer, "_split_reference_market_into_indexed_coins", mock.AsyncMock(return_value=["buy"])
        ) as _split_reference_market_into_indexed_coins_mock, mock.patch.object(
            consumer, "_can_simply_buy_coins_without_selling", mock.Mock(return_value=False)
        ) as _can_simply_buy_coins_without_selling_mock:
            assert await consumer._rebalance_portfolio("details", trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])) == []
            _ensure_enough_funds_to_buy_after_selling_mock.assert_called_once()
            _sell_indexed_coins_for_reference_market_mock.assert_not_called()
            _split_reference_market_into_indexed_coins_mock.assert_not_called()
            _can_simply_buy_coins_without_selling_mock.assert_not_called()
            _update_producer_last_activity_mock.assert_called_once_with(
                index_trading.IndexActivity.REBALANCING_SKIPPED,
                index_trading.RebalanceSkipDetails.NOT_ENOUGH_AVAILABLE_FOUNDS.value
            )
            _update_producer_last_activity_mock.reset_mock()

        with mock.patch.object(
            consumer, "_ensure_enough_funds_to_buy_after_selling", mock.AsyncMock()
        ) as _ensure_enough_funds_to_buy_after_selling_mock, \
        mock.patch.object(
            consumer.trading_mode.rebalancer, "sell_indexed_coins_for_reference_market", mock.AsyncMock(return_value=[sell_order])
        ) as _sell_indexed_coins_for_reference_market_mock, mock.patch.object(
            consumer, "_split_reference_market_into_indexed_coins", mock.AsyncMock(
                side_effect=trading_errors.MissingMinimalExchangeTradeVolume
            )
        ) as _split_reference_market_into_indexed_coins_mock:
            with mock.patch.object(
                consumer, "_can_simply_buy_coins_without_selling", mock.Mock(return_value=False)
            ) as _can_simply_buy_coins_without_selling_mock:
                assert await consumer._rebalance_portfolio("details", trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])) == [sell_order]
                _ensure_enough_funds_to_buy_after_selling_mock.assert_called_once()
                _sell_indexed_coins_for_reference_market_mock.assert_called_once_with("details", trading_signals.get_orders_dependencies([mock.Mock(order_id="123")]))
                _split_reference_market_into_indexed_coins_mock.assert_called_once_with("details", False, trading_signals.get_orders_dependencies([mock.Mock(order_id="456")]))
                _update_producer_last_activity_mock.assert_called_once_with(
                    index_trading.IndexActivity.REBALANCING_SKIPPED,
                    index_trading.RebalanceSkipDetails.NOT_ENOUGH_AVAILABLE_FOUNDS.value
                )
                _ensure_enough_funds_to_buy_after_selling_mock.reset_mock()
                _sell_indexed_coins_for_reference_market_mock.reset_mock()
                _split_reference_market_into_indexed_coins_mock.reset_mock()
                _update_producer_last_activity_mock.reset_mock()
            with mock.patch.object(
                consumer, "_can_simply_buy_coins_without_selling", mock.Mock(return_value=True)
            ) as _can_simply_buy_coins_without_selling_mock:
                assert await consumer._rebalance_portfolio("details", trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])) == []
                _ensure_enough_funds_to_buy_after_selling_mock.assert_called_once()
                _sell_indexed_coins_for_reference_market_mock.assert_not_called()
                _split_reference_market_into_indexed_coins_mock.assert_called_once_with("details", True, trading_signals.get_orders_dependencies([mock.Mock(order_id="123")]))
                _update_producer_last_activity_mock.assert_called_once_with(
                    index_trading.IndexActivity.REBALANCING_SKIPPED,
                    index_trading.RebalanceSkipDetails.NOT_ENOUGH_AVAILABLE_FOUNDS.value
                )
                _ensure_enough_funds_to_buy_after_selling_mock.reset_mock()
                _sell_indexed_coins_for_reference_market_mock.reset_mock()
                _split_reference_market_into_indexed_coins_mock.reset_mock()
                _update_producer_last_activity_mock.reset_mock()

        with mock.patch.object(
            consumer, "_ensure_enough_funds_to_buy_after_selling", mock.AsyncMock()
        ) as _ensure_enough_funds_to_buy_after_selling_mock, \
        mock.patch.object(
            consumer.trading_mode.rebalancer, "sell_indexed_coins_for_reference_market", mock.AsyncMock(return_value=[sell_order])
        ) as _sell_indexed_coins_for_reference_market_mock, mock.patch.object(
            consumer, "_split_reference_market_into_indexed_coins", mock.AsyncMock(
                side_effect=rebalancer.RebalanceAborted
            )
        ) as _split_reference_market_into_indexed_coins_mock:
            with mock.patch.object(
                consumer, "_can_simply_buy_coins_without_selling", mock.Mock(return_value=False)
            ) as _can_simply_buy_coins_without_selling_mock:
                assert await consumer._rebalance_portfolio("details", trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])) == [sell_order]
                _ensure_enough_funds_to_buy_after_selling_mock.assert_called_once()
                _sell_indexed_coins_for_reference_market_mock.assert_called_once_with("details", trading_signals.get_orders_dependencies([mock.Mock(order_id="123")]))
                _split_reference_market_into_indexed_coins_mock.assert_called_once_with("details", False, trading_signals.get_orders_dependencies([mock.Mock(order_id="456")]))
                _update_producer_last_activity_mock.assert_called_once_with(
                    index_trading.IndexActivity.REBALANCING_SKIPPED,
                    index_trading.RebalanceSkipDetails.NOT_ENOUGH_AVAILABLE_FOUNDS.value
                )
                _ensure_enough_funds_to_buy_after_selling_mock.reset_mock()
                _sell_indexed_coins_for_reference_market_mock.reset_mock()
                _split_reference_market_into_indexed_coins_mock.reset_mock()
                _update_producer_last_activity_mock.reset_mock()
            with mock.patch.object(
                consumer, "_can_simply_buy_coins_without_selling", mock.Mock(return_value=True)
            ) as _can_simply_buy_coins_without_selling_mock:
                assert await consumer._rebalance_portfolio("details", trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])) == []
                _ensure_enough_funds_to_buy_after_selling_mock.assert_called_once()
                _sell_indexed_coins_for_reference_market_mock.assert_not_called()
                _split_reference_market_into_indexed_coins_mock.assert_called_once_with("details", True, trading_signals.get_orders_dependencies([mock.Mock(order_id="123")]))
                _update_producer_last_activity_mock.assert_called_once_with(
                    index_trading.IndexActivity.REBALANCING_SKIPPED,
                    index_trading.RebalanceSkipDetails.NOT_ENOUGH_AVAILABLE_FOUNDS.value
                )
                _ensure_enough_funds_to_buy_after_selling_mock.reset_mock()
                _sell_indexed_coins_for_reference_market_mock.reset_mock()
                _split_reference_market_into_indexed_coins_mock.reset_mock()
                _update_producer_last_activity_mock.reset_mock()


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_ensure_enough_funds_to_buy_after_selling(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    with mock.patch.object(
            trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder,
            "get_traded_assets_holdings_value", mock.Mock(return_value=decimal.Decimal("2000"))
    ) as get_traded_assets_holdings_value_mock, mock.patch.object(
        consumer, "_get_symbols_and_amounts", mock.AsyncMock()
    ) as _get_symbols_and_amounts_mock:
        await consumer._ensure_enough_funds_to_buy_after_selling()
        get_traded_assets_holdings_value_mock.assert_called_once_with("USDT", None)
        _get_symbols_and_amounts_mock.assert_called_once_with(["BTC"], mode.indexed_coins_prices, decimal.Decimal("2000"))


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_can_simply_buy_coins_without_selling(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    details = "details"
    with mock.patch.object(
        trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder,
        "get_traded_assets_holdings_value", mock.Mock(return_value=decimal.Decimal("2000"))
    ) as get_traded_assets_holdings_value_mock:

        # no coins to simply buy
        with mock.patch.object(
            consumer, "_get_simple_buy_coins", return_value=[]
        ) as _get_simple_buy_coins_mock, mock.patch.object(
            trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
            "get_currency_portfolio", mock.Mock(return_value=mock.Mock(available=decimal.Decimal("160")))
        ) as get_currency_portfolio_mock:
            assert consumer._can_simply_buy_coins_without_selling(details) is False
            _get_simple_buy_coins_mock.assert_called_once_with(details)
            get_traded_assets_holdings_value_mock.assert_not_called()
            get_currency_portfolio_mock.assert_not_called()

        # there are coins to simply buy
        with mock.patch.object(
            mode, "get_target_ratio", return_value=decimal.Decimal("0.25")
        ) as get_target_ratio_mock, mock.patch.object(
            consumer, "_get_simple_buy_coins", return_value=["BTC"]
        ) as _get_simple_buy_coins_mock:

            # not enough free funds in portfolio to buy for 25% of 2000
            with mock.patch.object(
                trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
                "get_currency_portfolio", mock.Mock(return_value=mock.Mock(available=decimal.Decimal("160")))
            ) as get_currency_portfolio_mock:
                assert consumer._can_simply_buy_coins_without_selling(details) is False
                _get_simple_buy_coins_mock.assert_called_once_with(details)
                get_traded_assets_holdings_value_mock.assert_called_once_with("USDT", None)
                get_currency_portfolio_mock.assert_called_once_with("USDT")
                get_target_ratio_mock.assert_called_once_with("BTC")
                _get_simple_buy_coins_mock.reset_mock()
                get_traded_assets_holdings_value_mock.reset_mock()
                get_target_ratio_mock.reset_mock()

            # enough free funds in portfolio to buy for 25% of 2000 (using tolerance)
            with mock.patch.object(
                trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
                "get_currency_portfolio", mock.Mock(return_value=mock.Mock(available=decimal.Decimal("450")))
            ) as get_currency_portfolio_mock:
                assert consumer._can_simply_buy_coins_without_selling(details) is True
                _get_simple_buy_coins_mock.assert_called_once_with(details)
                get_traded_assets_holdings_value_mock.assert_called_once_with("USDT", None)
                get_currency_portfolio_mock.assert_called_once_with("USDT")
                get_target_ratio_mock.assert_called_once_with("BTC")
                _get_simple_buy_coins_mock.reset_mock()
                get_traded_assets_holdings_value_mock.reset_mock()
                get_target_ratio_mock.reset_mock()

            # more than enough free funds in portfolio to buy for 25% of 2000
            with mock.patch.object(
                trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
                "get_currency_portfolio", mock.Mock(return_value=mock.Mock(available=decimal.Decimal("600.811")))
            ) as get_currency_portfolio_mock:
                assert consumer._can_simply_buy_coins_without_selling(details) is True
                _get_simple_buy_coins_mock.assert_called_once_with(details)
                get_traded_assets_holdings_value_mock.assert_called_once_with("USDT", None)
                get_currency_portfolio_mock.assert_called_once_with("USDT")
                get_target_ratio_mock.assert_called_once_with("BTC")
                _get_simple_buy_coins_mock.reset_mock()
                get_traded_assets_holdings_value_mock.reset_mock()
                get_target_ratio_mock.reset_mock()

            # now having multiple coins to buy
            with  mock.patch.object(
                consumer, "_get_simple_buy_coins", return_value=["BTC", "ETH"]
            ) as _get_simple_buy_coins_mock:
                # enough funds for 1 but not 2 coins at 25%
                with mock.patch.object(
                    trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
                    "get_currency_portfolio",
                    mock.Mock(return_value=mock.Mock(available=decimal.Decimal("600.811")))
                ) as get_currency_portfolio_mock:
                    assert consumer._can_simply_buy_coins_without_selling(details) is False
                    _get_simple_buy_coins_mock.assert_called_once_with(details)
                    get_traded_assets_holdings_value_mock.assert_called_once_with("USDT", None)
                    get_currency_portfolio_mock.assert_called_once_with("USDT")
                    assert get_target_ratio_mock.call_count == 2
                    assert get_target_ratio_mock.mock_calls[0].args[0] == "BTC"
                    assert get_target_ratio_mock.mock_calls[1].args[0] == "ETH"
                    _get_simple_buy_coins_mock.reset_mock()
                    get_traded_assets_holdings_value_mock.reset_mock()
                    get_target_ratio_mock.reset_mock()

                # enough funds for 2 coins at 25%
                with mock.patch.object(
                    trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
                    "get_currency_portfolio",
                    mock.Mock(return_value=mock.Mock(available=decimal.Decimal("1000.811")))
                ) as get_currency_portfolio_mock:
                    assert consumer._can_simply_buy_coins_without_selling(details) is True
                    _get_simple_buy_coins_mock.assert_called_once_with(details)
                    get_traded_assets_holdings_value_mock.assert_called_once_with("USDT", None)
                    get_currency_portfolio_mock.assert_called_once_with("USDT")
                    assert get_target_ratio_mock.call_count == 2
                    assert get_target_ratio_mock.mock_calls[0].args[0] == "BTC"
                    assert get_target_ratio_mock.mock_calls[1].args[0] == "ETH"
                    _get_simple_buy_coins_mock.reset_mock()
                    get_traded_assets_holdings_value_mock.reset_mock()
                    get_target_ratio_mock.reset_mock()


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_get_simple_buy_coins(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    mode.indexed_coins = ["BTC", "ETH", "SOL"]
    assert consumer._get_simple_buy_coins({
        index_trading.RebalanceDetails.SELL_SOME.value: {},
        index_trading.RebalanceDetails.BUY_MORE.value: {},
        index_trading.RebalanceDetails.REMOVE.value: {},
        index_trading.RebalanceDetails.ADD.value: {},
        index_trading.RebalanceDetails.SWAP.value: {},
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
    }) == []
    assert consumer._get_simple_buy_coins({
        index_trading.RebalanceDetails.SELL_SOME.value: {},
        index_trading.RebalanceDetails.BUY_MORE.value: {},
        index_trading.RebalanceDetails.REMOVE.value: {},
        index_trading.RebalanceDetails.ADD.value: {"BTC": decimal.Decimal("0.2"), "ETH": decimal.Decimal("0.2")},
        index_trading.RebalanceDetails.SWAP.value: {},
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
    }) == ["BTC", "ETH"]
    # keep index coins order
    assert consumer._get_simple_buy_coins({
        index_trading.RebalanceDetails.SELL_SOME.value: {},
        index_trading.RebalanceDetails.BUY_MORE.value: {"SOL": decimal.Decimal("0.2")},
        index_trading.RebalanceDetails.REMOVE.value: {},
        index_trading.RebalanceDetails.ADD.value: {"ETH": decimal.Decimal("0.2"), "BTC": decimal.Decimal("0.2")},
        index_trading.RebalanceDetails.SWAP.value: {},
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
    }) == ["BTC", "ETH", "SOL"]
    # TRX not in indexed coins: added at the end
    assert consumer._get_simple_buy_coins({
        index_trading.RebalanceDetails.SELL_SOME.value: {},
        index_trading.RebalanceDetails.BUY_MORE.value: {"SOL": decimal.Decimal("0.1"), "TRX": decimal.Decimal("0.2")},
        index_trading.RebalanceDetails.REMOVE.value: {},
        index_trading.RebalanceDetails.ADD.value: {"ETH": decimal.Decimal("0.2"), "BTC": decimal.Decimal("0.5")},
        index_trading.RebalanceDetails.SWAP.value: {},
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
    }) == ["BTC", "ETH", "SOL", "TRX"]

    # don't return anything when other values are set
    assert consumer._get_simple_buy_coins({
        index_trading.RebalanceDetails.SELL_SOME.value: {"BTC": decimal.Decimal("0.2")},
        index_trading.RebalanceDetails.BUY_MORE.value: {},
        index_trading.RebalanceDetails.REMOVE.value: {},
        index_trading.RebalanceDetails.ADD.value: {"ETH": decimal.Decimal("0.2")},
        index_trading.RebalanceDetails.SWAP.value: {},
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
    }) == []
    assert consumer._get_simple_buy_coins({
        index_trading.RebalanceDetails.SELL_SOME.value: {},
        index_trading.RebalanceDetails.BUY_MORE.value: {},
        index_trading.RebalanceDetails.REMOVE.value: {"BTC": decimal.Decimal("0.2")},
        index_trading.RebalanceDetails.ADD.value: {"ETH": decimal.Decimal("0.2")},
        index_trading.RebalanceDetails.SWAP.value: {},
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
    }) == []
    assert consumer._get_simple_buy_coins({
        index_trading.RebalanceDetails.SELL_SOME.value: {},
        index_trading.RebalanceDetails.BUY_MORE.value: {},
        index_trading.RebalanceDetails.REMOVE.value: {},
        index_trading.RebalanceDetails.ADD.value: {"ETH": decimal.Decimal("0.2")},
        index_trading.RebalanceDetails.SWAP.value: {"BTC": decimal.Decimal("0.2")},
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
    }) == []
    # whatever is in other values, return [] when forced rebalance
    assert consumer._get_simple_buy_coins({
        index_trading.RebalanceDetails.SELL_SOME.value: {},
        index_trading.RebalanceDetails.BUY_MORE.value: {},
        index_trading.RebalanceDetails.REMOVE.value: {},
        index_trading.RebalanceDetails.ADD.value: {"ETH": decimal.Decimal("0.2")},
        index_trading.RebalanceDetails.SWAP.value: {"BTC": decimal.Decimal("0.2")},
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: True,
    }) == []
    # should return [BTC, ETH] but doesn't because of forced rebalance
    assert consumer._get_simple_buy_coins({
        index_trading.RebalanceDetails.SELL_SOME.value: {},
        index_trading.RebalanceDetails.BUY_MORE.value: {},
        index_trading.RebalanceDetails.REMOVE.value: {},
        index_trading.RebalanceDetails.ADD.value: {"BTC": decimal.Decimal("0.2"), "ETH": decimal.Decimal("0.2")},
        index_trading.RebalanceDetails.SWAP.value: {},
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: True,
    }) == []


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_sell_indexed_coins_for_reference_market(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    is_futures = trader.exchange_manager.is_future
    dependencies = trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])
    if is_futures:
        mode.indexed_coins = ["BTC/USDT"]
        positions_manager = trader.exchange_manager.exchange_personal_data.positions_manager
        symbol_market = trader.exchange_manager.exchange.get_market_status("BTC/USDT", with_fixer=False)
        position_mock = _create_position_mock(
            "BTC/USDT", trader, True, is_idle=False,
            size=decimal.Decimal("2"),
            side=trading_enums.PositionSide.LONG
        )
        with mock.patch.object(
            octobot_trading.modes, "convert_assets_to_target_asset", mock.AsyncMock(return_value=[])
        ) as convert_assets_to_target_asset_mock, mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(return_value=position_mock)
        ) as get_symbol_position_mock, mock.patch.object(
            trading_personal_data, "get_pre_order_data", mock.AsyncMock(return_value=(
                decimal.Decimal("0"), decimal.Decimal("0"), decimal.Decimal("0"), decimal.Decimal("1000"), symbol_market
            ))
        ) as get_pre_order_data_mock, mock.patch.object(
            mode, "create_order", mock.AsyncMock(side_effect=lambda order, **kwargs: order)
        ) as create_order_mock, mock.patch.object(
            trading_api, "get_open_orders", mock.Mock(return_value=[])
        ) as get_open_orders_mock, mock.patch.object(
            consumer.trading_mode.rebalancer, "cancel_symbol_open_orders", mock.AsyncMock()
        ) as cancel_symbol_open_orders_mock, mock.patch.object(
            trading_personal_data, "wait_for_order_fill", mock.AsyncMock()
        ) as wait_for_order_fill_mock:
            details = {
                index_trading.RebalanceDetails.REMOVE.value: {},
                index_trading.RebalanceDetails.SWAP.value: {},
            }
            orders = await consumer.trading_mode.rebalancer.sell_indexed_coins_for_reference_market(details, dependencies)

        assert len(orders) == 1
        assert isinstance(orders[0], trading_personal_data.SellMarketOrder)
        convert_assets_to_target_asset_mock.assert_not_called()
        get_symbol_position_mock.assert_called_once_with("BTC/USDT", trading_enums.PositionSide.BOTH)
        get_pre_order_data_mock.assert_called_once()
        get_open_orders_mock.assert_called_once_with(mode.exchange_manager, symbol="BTC/USDT")
        cancel_symbol_open_orders_mock.assert_not_called()
        create_order_mock.assert_called_once_with(orders[0], dependencies=dependencies)
        wait_for_order_fill_mock.assert_called_once()
    else:
        orders = [
            mock.Mock(
                symbol="BTC/USDT",
                side=trading_enums.TradeOrderSide.SELL
            ),
            mock.Mock(
                symbol="ETH/USDT",
                side=trading_enums.TradeOrderSide.SELL
            )
        ]
        with mock.patch.object(
                octobot_trading.modes, "convert_assets_to_target_asset", mock.AsyncMock(return_value=orders)
        ) as convert_assets_to_target_asset_mock, mock.patch.object(
            trading_personal_data, "wait_for_order_fill", mock.AsyncMock()
        ) as wait_for_order_fill_mock, mock.patch.object(
            consumer.trading_mode.rebalancer, "get_coins_to_sell", mock.Mock(return_value=["BTC", "ETH", "SOL"])
        ) as _get_coins_to_sell_mock, mock.patch.object(
            consumer.trading_mode.rebalancer, "cancel_symbol_open_orders", mock.AsyncMock()
        ) as cancel_symbol_open_orders_mock:
            details = {
                index_trading.RebalanceDetails.REMOVE.value: {}
            }
            assert await consumer.trading_mode.rebalancer.sell_indexed_coins_for_reference_market(details, dependencies) == orders
            convert_assets_to_target_asset_mock.assert_called_once_with(
                mode, ["BTC", "ETH", "SOL"],
                consumer.exchange_manager.exchange_personal_data.portfolio_manager.reference_market, {},
                dependencies=dependencies
            )
            assert wait_for_order_fill_mock.call_count == 2
            _get_coins_to_sell_mock.assert_called_once_with(details)
            convert_assets_to_target_asset_mock.reset_mock()
            wait_for_order_fill_mock.reset_mock()
            _get_coins_to_sell_mock.reset_mock()

            # with valid remove coins
            details = {
                index_trading.RebalanceDetails.REMOVE.value: {"BTC": 0.01},
                index_trading.RebalanceDetails.BUY_MORE.value: {},
                index_trading.RebalanceDetails.ADD.value: {},
                index_trading.RebalanceDetails.SWAP.value: {},
                index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
            }
            assert await consumer.trading_mode.rebalancer.sell_indexed_coins_for_reference_market(details, dependencies) == orders + orders
            assert convert_assets_to_target_asset_mock.call_count == 2
            assert wait_for_order_fill_mock.call_count == 4
            _get_coins_to_sell_mock.assert_called_once_with(details)
            convert_assets_to_target_asset_mock.reset_mock()
            wait_for_order_fill_mock.reset_mock()
            _get_coins_to_sell_mock.reset_mock()

            with mock.patch.object(
                    octobot_trading.modes, "convert_assets_to_target_asset", mock.AsyncMock(return_value=[])
            ) as convert_assets_to_target_asset_mock_2:
                # with remove coins that can't be sold
                details = {
                    index_trading.RebalanceDetails.REMOVE.value: {"BTC": 0.01},
                    index_trading.RebalanceDetails.BUY_MORE.value: {},
                    index_trading.RebalanceDetails.ADD.value: {},
                    index_trading.RebalanceDetails.SWAP.value: {},
                    index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
                }
                with pytest.raises(trading_errors.MissingMinimalExchangeTradeVolume):
                    assert await consumer.trading_mode.rebalancer.sell_indexed_coins_for_reference_market(details, dependencies) == orders + orders
                convert_assets_to_target_asset_mock_2.assert_called_once_with(
                    mode, ["BTC"],
                    consumer.exchange_manager.exchange_personal_data.portfolio_manager.reference_market, {},
                    dependencies=dependencies
                )
                wait_for_order_fill_mock.assert_not_called()
                _get_coins_to_sell_mock.assert_not_called()

@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_sell_some_reduces_or_closes_position(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    dependencies = trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])
    if trader.exchange_manager.is_future:
        mode.indexed_coins = ["BTC/USDT"]
        positions_manager = trader.exchange_manager.exchange_personal_data.positions_manager
        symbol_market = trader.exchange_manager.exchange.get_market_status("BTC/USDT", with_fixer=False)
        portfolio_value_holder = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder
        position_mock = _create_position_mock(
            "BTC/USDT", trader, True, is_idle=False,
            size=decimal.Decimal("2"),
            side=trading_enums.PositionSide.LONG
        )

        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(return_value=position_mock)
        ), mock.patch.object(
            trading_personal_data, "get_pre_order_data", mock.AsyncMock(return_value=(
                decimal.Decimal("0"), decimal.Decimal("0"), decimal.Decimal("0"), decimal.Decimal("1000"), symbol_market
            ))
        ), mock.patch.object(
            portfolio_value_holder, "get_traded_assets_holdings_value", mock.Mock(return_value=decimal.Decimal("1000"))
        ), mock.patch.object(
            mode, "create_order", mock.AsyncMock(side_effect=lambda order, **kwargs: order)
        ) as create_order_mock, mock.patch.object(
            trading_api, "get_open_orders", mock.Mock(return_value=[])
        ), mock.patch.object(
            trading_personal_data, "wait_for_order_fill", mock.AsyncMock()
        ):
            # target_size = 0.1*1000/1000 = 0.1 => close 1.9 out of 2
            details = {
                index_trading.RebalanceDetails.SELL_SOME.value: {"BTC/USDT": decimal.Decimal("0.1")},
                index_trading.RebalanceDetails.REMOVE.value: {},
                index_trading.RebalanceDetails.SWAP.value: {},
            }
            orders = await consumer.trading_mode.rebalancer.sell_indexed_coins_for_reference_market(details, dependencies)
            assert len(orders) == 1
            assert isinstance(orders[0], trading_personal_data.SellMarketOrder)
            assert orders[0].origin_quantity == decimal.Decimal("1.9")

            create_order_mock.reset_mock()
            # target_size = 0 => close full position
            details = {
                index_trading.RebalanceDetails.SELL_SOME.value: {"BTC/USDT": decimal.Decimal("0")},
                index_trading.RebalanceDetails.REMOVE.value: {},
                index_trading.RebalanceDetails.SWAP.value: {},
            }
            orders = await consumer.trading_mode.rebalancer.sell_indexed_coins_for_reference_market(details, dependencies)
            assert len(orders) == 1
            assert isinstance(orders[0], trading_personal_data.SellMarketOrder)
            assert orders[0].origin_quantity == decimal.Decimal("2")
    else:
        mode.indexed_coins = ["BTC"]
        converted_orders = [mock.Mock(symbol="BTC/USDT", side=trading_enums.TradeOrderSide.SELL)]
        with mock.patch.object(
            octobot_trading.modes, "convert_assets_to_target_asset", mock.AsyncMock(return_value=converted_orders)
        ) as convert_assets_to_target_asset_mock, mock.patch.object(
            trading_personal_data, "wait_for_order_fill", mock.AsyncMock()
        ):
            details = {
                index_trading.RebalanceDetails.SELL_SOME.value: {"BTC": decimal.Decimal("0.1")},
                index_trading.RebalanceDetails.REMOVE.value: {},
                index_trading.RebalanceDetails.SWAP.value: {},
            }
            orders = await consumer.trading_mode.rebalancer.sell_indexed_coins_for_reference_market(details, dependencies)
            assert orders == converted_orders
            convert_assets_to_target_asset_mock.assert_called_once_with(
                mode, ["BTC"],
                consumer.exchange_manager.exchange_personal_data.portfolio_manager.reference_market, {},
                dependencies=dependencies
            )

        # When pending sells already exceed holdings, no new sell is created
        portfolio = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio
        portfolio["BTC"].total = decimal.Decimal("1")
        stale_sell_order = mock.Mock(
            symbol="BTC/USDT",
            side=trading_enums.TradeOrderSide.SELL,
            origin_quantity=decimal.Decimal("2"),
            filled_quantity=decimal.Decimal("0"),
        )
        stale_buy_order = mock.Mock(
            symbol="BTC/USDT",
            side=trading_enums.TradeOrderSide.BUY,
            origin_quantity=decimal.Decimal("1"),
            filled_quantity=decimal.Decimal("0"),
        )
        with mock.patch.object(
            octobot_trading.modes, "convert_assets_to_target_asset", mock.AsyncMock(return_value=[])
        ), mock.patch.object(
            trading_api, "get_open_orders", mock.Mock(return_value=[stale_sell_order, stale_buy_order])
        ), mock.patch.object(
            mode, "cancel_order", mock.AsyncMock(return_value=(True, commons_signals.SignalDependencies()))
        ) as cancel_order_mock, mock.patch.object(
            trading_personal_data, "wait_for_order_fill", mock.AsyncMock()
        ):
            details = {
                index_trading.RebalanceDetails.SELL_SOME.value: {"BTC": decimal.Decimal("0.1")},
                index_trading.RebalanceDetails.REMOVE.value: {},
                index_trading.RebalanceDetails.SWAP.value: {},
            }
            orders = await consumer.trading_mode.rebalancer.sell_indexed_coins_for_reference_market(details, dependencies)
            assert orders == []


def _cleanup_rebalance_details(
    *,
    remove: typing.Optional[dict] = None,
    sell_some: typing.Optional[dict] = None,
    buy_more: typing.Optional[dict] = None,
    add: typing.Optional[dict] = None,
    swap: typing.Optional[dict] = None,
    forced_rebalance: bool = False,
) -> dict:
    return {
        index_trading.RebalanceDetails.SELL_SOME.value: sell_some or {},
        index_trading.RebalanceDetails.BUY_MORE.value: buy_more or {},
        index_trading.RebalanceDetails.REMOVE.value: remove or {},
        index_trading.RebalanceDetails.ADD.value: add or {},
        index_trading.RebalanceDetails.SWAP.value: swap or {},
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: forced_rebalance,
    }


def _mock_open_orders(
    sides: list[trading_enums.TradeOrderSide],
    symbol: str = "BTC/USDT",
) -> list[mock.Mock]:
    return [
        mock.Mock(
            symbol=symbol,
            side=side,
            origin_quantity=decimal.Decimal("1"),
            filled_quantity=decimal.Decimal("0"),
        )
        for side in sides
    ]


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
@pytest.mark.parametrize(
    "details,expected_symbols",
    [
        pytest.param(
            _cleanup_rebalance_details(
                buy_more={"ETH/USDT": decimal.Decimal("0.2")},
                add={"BTC": decimal.Decimal("0.2")},
            ),
            {"BTC/USDT", "ETH/USDT"},
            id="add_and_buy_more_cleanup",
        ),
        pytest.param(
            _cleanup_rebalance_details(
                buy_more={"BTC/USDT": decimal.Decimal("0.2")},
                add={"BTC": decimal.Decimal("0.2")},
            ),
            {"BTC/USDT"},
            id="dedup_same_symbol_from_add_and_buy_more",
        ),
        pytest.param(
            _cleanup_rebalance_details(),
            set(),
            id="no_add_no_buy_more",
        ),
    ],
)
async def test_buy_cleanup_on_rebalance_actions(trading_tools, details, expected_symbols):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    dependencies = trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])
    mode.allow_skip_asset = True
    with mock.patch.object(
        consumer.trading_mode.rebalancer, "cancel_symbol_open_orders", mock.AsyncMock()
    ) as cancel_symbol_open_orders_mock, mock.patch.object(
        consumer, "_get_symbols_and_amounts", mock.AsyncMock(return_value={})
    ) as get_symbols_and_amounts_mock, mock.patch.object(
        consumer.trading_mode.rebalancer, "buy_coin", mock.AsyncMock()
    ) as buy_coin_mock:
        orders = await consumer._split_reference_market_into_indexed_coins(details, True, dependencies)

    assert orders == []
    cancelled_symbols = {call.args[0] for call in cancel_symbol_open_orders_mock.call_args_list}
    assert cancelled_symbols == expected_symbols
    for call in cancel_symbol_open_orders_mock.call_args_list:
        assert call.kwargs["dependencies"] == dependencies
        assert call.kwargs["allowed_sides"] == {trading_enums.TradeOrderSide.SELL}
    get_symbols_and_amounts_mock.assert_called_once()
    buy_coin_mock.assert_not_called()


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
@pytest.mark.parametrize(
    "details,open_order_sides,expected_cancelled_sides,portfolio_total,exact_cancelled_sides",
    [
        pytest.param(
            _cleanup_rebalance_details(remove={"BTC": decimal.Decimal("0.1")}),
            [trading_enums.TradeOrderSide.BUY, trading_enums.TradeOrderSide.SELL],
            {trading_enums.TradeOrderSide.BUY},
            decimal.Decimal("0"),
            True,
            id="remove_without_holdings_buy_and_sell_orders",
        ),
        pytest.param(
            _cleanup_rebalance_details(remove={"BTC": decimal.Decimal("0.1")}),
            [trading_enums.TradeOrderSide.BUY],
            {trading_enums.TradeOrderSide.BUY},
            decimal.Decimal("0"),
            True,
            id="remove_without_holdings_only_buy_order",
        ),
        pytest.param(
            _cleanup_rebalance_details(remove={"BTC": decimal.Decimal("0.1")}),
            [trading_enums.TradeOrderSide.BUY, trading_enums.TradeOrderSide.SELL],
            {trading_enums.TradeOrderSide.BUY},
            decimal.Decimal("1"),
            True,
            id="remove_with_holdings_no_post_cleanup",
        ),
        pytest.param(
            _cleanup_rebalance_details(
                remove={"BTC": decimal.Decimal("0.1")},
                sell_some={"BTC/USDT": decimal.Decimal("0.2")},
            ),
            [trading_enums.TradeOrderSide.BUY],
            {trading_enums.TradeOrderSide.BUY},
            decimal.Decimal("1"),
            True,
            id="dedup_same_symbol_from_remove_and_sell_some",
        ),
    ],
)
async def test_sell_cleanup_on_rebalance_actions(
    trading_tools, details, open_order_sides, expected_cancelled_sides, portfolio_total, exact_cancelled_sides
):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    dependencies = trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])
    portfolio = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio
    portfolio["BTC"].total = portfolio_total
    portfolio["BTC"].available = portfolio_total
    open_orders = _mock_open_orders(open_order_sides)
    with mock.patch.object(
        octobot_trading.modes, "convert_assets_to_target_asset", mock.AsyncMock(return_value=[])
    ), mock.patch.object(
        trading_api, "get_open_orders", mock.Mock(return_value=open_orders)
    ), mock.patch.object(
        mode, "cancel_order", mock.AsyncMock(return_value=(True, commons_signals.SignalDependencies()))
    ) as cancel_order_mock, mock.patch.object(
        trading_personal_data, "wait_for_order_fill", mock.AsyncMock()
    ):
        with pytest.raises(trading_errors.MissingMinimalExchangeTradeVolume):
            await consumer.trading_mode.rebalancer.sell_indexed_coins_for_reference_market(details, dependencies)

    cancelled_sides = {call.args[0].side for call in cancel_order_mock.call_args_list}
    if exact_cancelled_sides:
        assert cancelled_sides == expected_cancelled_sides
    else:
        assert expected_cancelled_sides.issubset(cancelled_sides)


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_get_coins_to_sell(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    mode.indexed_coins = ["BTC", "ETH", "DOGE", "SHIB"]
    assert consumer.trading_mode.rebalancer.get_coins_to_sell({
        index_trading.RebalanceDetails.SELL_SOME.value: {},
        index_trading.RebalanceDetails.BUY_MORE.value: {},
        index_trading.RebalanceDetails.REMOVE.value: {},
        index_trading.RebalanceDetails.ADD.value: {},
        index_trading.RebalanceDetails.SWAP.value: {},
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
    }) == ["BTC", "ETH", "DOGE", "SHIB"]
    assert consumer.trading_mode.rebalancer.get_coins_to_sell({
        index_trading.RebalanceDetails.SELL_SOME.value: {},
        index_trading.RebalanceDetails.BUY_MORE.value: {},
        index_trading.RebalanceDetails.REMOVE.value: {},
        index_trading.RebalanceDetails.ADD.value: {},
        index_trading.RebalanceDetails.SWAP.value: {
            "BTC": "ETH"
        },
    }) == ["BTC"]
    assert consumer.trading_mode.rebalancer.get_coins_to_sell({
        index_trading.RebalanceDetails.SELL_SOME.value: {},
        index_trading.RebalanceDetails.BUY_MORE.value: {},
        index_trading.RebalanceDetails.REMOVE.value: {
            "XRP": trading_constants.ONE_HUNDRED
        },
        index_trading.RebalanceDetails.ADD.value: {},
        index_trading.RebalanceDetails.SWAP.value: {
            "BTC": "ETH",
            "SOL": "ADA",
        },
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
    }) == ["BTC", "SOL"]
    assert consumer.trading_mode.rebalancer.get_coins_to_sell({
        index_trading.RebalanceDetails.SELL_SOME.value: {},
        index_trading.RebalanceDetails.BUY_MORE.value: {},
        index_trading.RebalanceDetails.REMOVE.value: {},
        index_trading.RebalanceDetails.ADD.value: {},
        index_trading.RebalanceDetails.SWAP.value: {},
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
    }) == ["BTC", "ETH", "DOGE", "SHIB"]
    assert consumer.trading_mode.rebalancer.get_coins_to_sell({
        index_trading.RebalanceDetails.SELL_SOME.value: {},
        index_trading.RebalanceDetails.BUY_MORE.value: {},
        index_trading.RebalanceDetails.REMOVE.value: {
            "XRP": trading_constants.ONE_HUNDRED
        },
        index_trading.RebalanceDetails.ADD.value: {},
        index_trading.RebalanceDetails.SWAP.value: {},
        index_trading.RebalanceDetails.FORCED_REBALANCE.value: False,
    }) == ["BTC", "ETH", "DOGE", "SHIB"]


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_resolve_swaps(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    mode.rebalance_trigger_min_ratio = decimal.Decimal("0.05")  # %5
    is_futures = trader.exchange_manager.is_future
    positions_manager = trader.exchange_manager.exchange_personal_data.positions_manager
    
    def _get_symbol_position(symbol, side=None):
        return _create_position_mock(
            symbol, trader, is_futures,
            is_idle=False,
            size=decimal.Decimal(2),
            side=trading_enums.PositionSide.LONG,
            initial_margin=decimal.Decimal(0),
            margin=decimal.Decimal(0),
        )
    
    with mock.patch.object(
        positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
    ), \
    mock.patch.object(
        order_util, "get_futures_max_order_size", mock.Mock(return_value=(decimal.Decimal(10), True))
    ), \
    mock.patch.object(
        trader.exchange_manager.exchange, "get_pair_contract",
        return_value=mock.Mock() if is_futures else None
    ):
        rebalance_details = {
            index_trading.RebalanceDetails.SELL_SOME.value: {},
            index_trading.RebalanceDetails.BUY_MORE.value: {},
            index_trading.RebalanceDetails.REMOVE.value: {},
            index_trading.RebalanceDetails.ADD.value: {},
            index_trading.RebalanceDetails.SWAP.value: {},
        }
        # regular full rebalance
        producer._resolve_swaps(rebalance_details)
        assert rebalance_details[index_trading.RebalanceDetails.SWAP.value] == {}

        # regular full rebalance with removed coins to sell
        rebalance_details[index_trading.RebalanceDetails.REMOVE.value] = {"SOL": decimal.Decimal("0.3")}
        producer._resolve_swaps(rebalance_details)
        assert rebalance_details[index_trading.RebalanceDetails.SWAP.value] == {}

        # rebalances with a coin swap only from ADD coin
        rebalance_details[index_trading.RebalanceDetails.ADD.value] = {"ADA": decimal.Decimal("0.3")}
        producer._resolve_swaps(rebalance_details)
        assert rebalance_details[index_trading.RebalanceDetails.SWAP.value] == {"SOL": "ADA"}

        # rebalances with a coin swap only from BUY_MORE coin
        rebalance_details[index_trading.RebalanceDetails.ADD.value] = {}
        rebalance_details[index_trading.RebalanceDetails.BUY_MORE.value] = {"ADA": decimal.Decimal("0.3")}
        producer._resolve_swaps(rebalance_details)
        assert rebalance_details[index_trading.RebalanceDetails.SWAP.value] == {"SOL": "ADA"}
        rebalance_details[index_trading.RebalanceDetails.BUY_MORE.value] = {}

        # rebalances with an incompatible coin swap (ratio too different)
        rebalance_details[index_trading.RebalanceDetails.BUY_MORE.value] = {"ADA": decimal.Decimal("0.1")}
        producer._resolve_swaps(rebalance_details)
        assert rebalance_details[index_trading.RebalanceDetails.SWAP.value] == {}
        rebalance_details[index_trading.RebalanceDetails.BUY_MORE.value] = {}

        # rebalances with an incompatible coin swap (ratio too different)
        rebalance_details[index_trading.RebalanceDetails.ADD.value] = {"ADA": decimal.Decimal("0.5")}
        producer._resolve_swaps(rebalance_details)
        assert rebalance_details[index_trading.RebalanceDetails.SWAP.value] == {}

        # rebalances with 2 removed coins: sell everything
        rebalance_details[index_trading.RebalanceDetails.REMOVE.value] = {
            "SOL": decimal.Decimal("0.3"),
            "XRP": decimal.Decimal("0.3"),
        }
        producer._resolve_swaps(rebalance_details)
        assert rebalance_details[index_trading.RebalanceDetails.SWAP.value] == {}

        # rebalances with 2 coin swaps: sell everything
        rebalance_details[index_trading.RebalanceDetails.ADD.value] = {
            "ADA": decimal.Decimal("0.3"),
            "ADA2": decimal.Decimal("0.3"),
        }
        producer._resolve_swaps(rebalance_details)
        assert rebalance_details[index_trading.RebalanceDetails.SWAP.value] == {}

        # rebalance with regular buy / sell more
        rebalance_details[index_trading.RebalanceDetails.BUY_MORE.value] = {"LTC": decimal.Decimal(1)}
        producer._resolve_swaps(rebalance_details)
        assert rebalance_details[index_trading.RebalanceDetails.SWAP.value] == {}

        # rebalance with regular buy / sell more
        rebalance_details[index_trading.RebalanceDetails.SELL_SOME.value] = {"BTC": decimal.Decimal(1)}
        producer._resolve_swaps(rebalance_details)
        assert rebalance_details[index_trading.RebalanceDetails.SWAP.value] == {}


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_split_reference_market_into_indexed_coins(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    # no indexed coin
    mode.indexed_coins = []
    details = {index_trading.RebalanceDetails.SWAP.value: {}}
    is_simple_buy_without_selling = False
    dependencies = trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])
    with mock.patch.object(
        consumer, "_get_symbols_and_amounts", mock.AsyncMock(
            side_effect=lambda coins, coins_prices, reference_market_to_split: {
                f"{coin}/USDT": {
                    consumer.IDEAL_AMOUNT: decimal.Decimal(i + 1),
                    consumer.IDEAL_PRICE: None
                }
                for i, coin in enumerate(coins)
            }
        )
    ) as _get_symbols_and_amounts_mock:
        with mock.patch.object(
            consumer, "_get_simple_buy_coins", mock.Mock()
        ) as _get_simple_buy_coins_mock:
            with mock.patch.object(
                    trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
                    "get_currency_portfolio", mock.Mock(return_value=mock.Mock(available=decimal.Decimal("2")))
            ) as get_currency_portfolio_mock, mock.patch.object(
                consumer.trading_mode.rebalancer, "buy_coin", mock.AsyncMock(return_value=["order"])
            ) as _buy_coin_mock:
                with pytest.raises(trading_errors.MissingMinimalExchangeTradeVolume):
                    await consumer._split_reference_market_into_indexed_coins(details, is_simple_buy_without_selling, dependencies)
                get_currency_portfolio_mock.assert_called_once_with("USDT")
                _buy_coin_mock.assert_not_called()
                _get_symbols_and_amounts_mock.assert_called_once()
                _get_symbols_and_amounts_mock.reset_mock()
                _get_simple_buy_coins_mock.assert_not_called()

            # coins to swap
            mode.indexed_coins = []
            details = {index_trading.RebalanceDetails.SWAP.value: {"BTC": "ETH", "ADA": "SOL"}}
            with mock.patch.object(
                    trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
                    "get_currency_portfolio", mock.Mock(return_value=mock.Mock(available=decimal.Decimal("2")))
            ) as get_currency_portfolio_mock, mock.patch.object(
                trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder,
                "get_traded_assets_holdings_value", mock.Mock(return_value=decimal.Decimal("2000"))
            ) as get_traded_assets_holdings_value_mock, mock.patch.object(
                consumer.trading_mode.rebalancer, "buy_coin", mock.AsyncMock(return_value=["order"])
            ) as _buy_coin_mock:
                # Test with default reference_market_ratio = 0 (no reservation)
                mode.reference_market_ratio = trading_constants.ZERO
                reference_market_to_split = decimal.Decimal("2000")
                reference_market_reserved = reference_market_to_split * mode.reference_market_ratio
                reference_market_to_distribute = reference_market_to_split - reference_market_reserved
                
                assert await consumer._split_reference_market_into_indexed_coins(
                    details, is_simple_buy_without_selling, dependencies
                ) == ["order", "order"]
                _get_symbols_and_amounts_mock.assert_called_once()
                # Verify _get_symbols_and_amounts was called with correct reference_market_to_distribute
                assert _get_symbols_and_amounts_mock.call_args[0][2] == reference_market_to_distribute
                assert reference_market_reserved == trading_constants.ZERO
                assert reference_market_to_distribute == reference_market_to_split
                _get_symbols_and_amounts_mock.reset_mock()
                get_traded_assets_holdings_value_mock.assert_called_once_with("USDT", None)
                get_currency_portfolio_mock.assert_not_called()
                _get_simple_buy_coins_mock.assert_not_called()
                assert _buy_coin_mock.call_count == 2
                assert _buy_coin_mock.mock_calls[0].args == ("ETH/USDT", decimal.Decimal("1"), None, dependencies)
                assert _buy_coin_mock.mock_calls[1].args == ("SOL/USDT", decimal.Decimal("2"), None, dependencies)
                
                # Test with reference_market_ratio > 0 (with reservation)
                get_traded_assets_holdings_value_mock.reset_mock()
                _buy_coin_mock.reset_mock()
                mode.reference_market_ratio = decimal.Decimal("0.1")  # 10% to trade
                reference_market_to_split = decimal.Decimal("2000")
                reference_market_to_distribute = reference_market_to_split * mode.reference_market_ratio
                reference_market_reserved = reference_market_to_split - reference_market_to_distribute
                
                assert await consumer._split_reference_market_into_indexed_coins(
                    details, is_simple_buy_without_selling, dependencies
                ) == ["order", "order"]
                _get_symbols_and_amounts_mock.assert_called_once()
                # Verify _get_symbols_and_amounts was called with correct reference_market_to_distribute
                assert _get_symbols_and_amounts_mock.call_args[0][2] == reference_market_to_distribute
                assert reference_market_to_distribute == decimal.Decimal("200")
                assert reference_market_reserved == decimal.Decimal("1800")
                _get_symbols_and_amounts_mock.reset_mock()
                get_traded_assets_holdings_value_mock.assert_called_once_with("USDT", None)
                _buy_coin_mock.reset_mock()

            # no bought coin
            details = {index_trading.RebalanceDetails.SWAP.value: {}}
            mode.indexed_coins = ["ETH", "BTC"]
            with mock.patch.object(
                    trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
                    "get_currency_portfolio", mock.Mock(return_value=mock.Mock(available=decimal.Decimal("2")))
            ) as get_currency_portfolio_mock, mock.patch.object(
                consumer.trading_mode.rebalancer, "buy_coin", mock.AsyncMock(return_value=[])
            ) as _buy_coin_mock:
                with pytest.raises(trading_errors.MissingMinimalExchangeTradeVolume):
                    await consumer._split_reference_market_into_indexed_coins(details, is_simple_buy_without_selling, dependencies)
                _get_symbols_and_amounts_mock.assert_called_once()
                _get_symbols_and_amounts_mock.reset_mock()
                get_currency_portfolio_mock.assert_called_once_with("USDT")
                _get_simple_buy_coins_mock.assert_not_called()
                assert _buy_coin_mock.call_count == 2

            # bought coins
            mode.indexed_coins = ["ETH", "BTC"]
            with mock.patch.object(
                    trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
                    "get_currency_portfolio", mock.Mock(return_value=mock.Mock(available=decimal.Decimal("2")))
            ) as get_currency_portfolio_mock, mock.patch.object(
                consumer.trading_mode.rebalancer, "buy_coin", mock.AsyncMock(return_value=["order"])
            ) as _buy_coin_mock:
                # Test with default reference_market_ratio = 0 (no reservation)
                mode.reference_market_ratio = trading_constants.ZERO
                reference_market_to_split = decimal.Decimal("2")
                reference_market_reserved = reference_market_to_split * mode.reference_market_ratio
                reference_market_to_distribute = reference_market_to_split - reference_market_reserved
                
                assert await consumer._split_reference_market_into_indexed_coins(
                    details, is_simple_buy_without_selling, dependencies
                ) == ["order", "order"]
                _get_symbols_and_amounts_mock.assert_called_once()
                # Verify _get_symbols_and_amounts was called with correct reference_market_to_distribute
                assert _get_symbols_and_amounts_mock.call_args[0][2] == reference_market_to_distribute
                assert reference_market_reserved == trading_constants.ZERO
                assert reference_market_to_distribute == reference_market_to_split
                _get_symbols_and_amounts_mock.reset_mock()
                get_currency_portfolio_mock.assert_called_once_with("USDT")
                _get_simple_buy_coins_mock.assert_not_called()
                assert _buy_coin_mock.call_count == 2
                assert _buy_coin_mock.mock_calls[0].args[0] == "ETH/USDT"
                assert _buy_coin_mock.mock_calls[0].args[3] == dependencies
                assert _buy_coin_mock.mock_calls[1].args[0] == "BTC/USDT"
                assert _buy_coin_mock.mock_calls[1].args[3] == dependencies
                
                # Test with reference_market_ratio > 0 (with reservation)
                get_currency_portfolio_mock.reset_mock()
                _buy_coin_mock.reset_mock()
                mode.reference_market_ratio = decimal.Decimal("0.15")  # 15% to trade
                reference_market_to_split = decimal.Decimal("2")
                reference_market_to_distribute = reference_market_to_split * mode.reference_market_ratio
                reference_market_reserved = reference_market_to_split - reference_market_to_distribute
                
                assert await consumer._split_reference_market_into_indexed_coins(
                    details, is_simple_buy_without_selling, dependencies
                ) == ["order", "order"]
                _get_symbols_and_amounts_mock.assert_called_once()
                # Verify _get_symbols_and_amounts was called with correct reference_market_to_distribute
                assert _get_symbols_and_amounts_mock.call_args[0][2] == reference_market_to_distribute
                assert reference_market_to_distribute == decimal.Decimal("0.3")
                assert reference_market_reserved == decimal.Decimal("1.7")
                _get_symbols_and_amounts_mock.reset_mock()
                get_currency_portfolio_mock.assert_called_once_with("USDT")
                _buy_coin_mock.reset_mock()

        with mock.patch.object(
            consumer, "_get_simple_buy_coins", mock.Mock(return_value=["ETH"])
        ) as _get_simple_buy_coins_mock:
            # simple buy without selling => buying only ETH
            is_simple_buy_without_selling = True
            mode.indexed_coins = ["ETH", "BTC"]
            with mock.patch.object(
                    trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
                    "get_currency_portfolio", mock.Mock(return_value=mock.Mock(available=decimal.Decimal("2")))
            ) as get_currency_portfolio_mock, mock.patch.object(
                consumer.trading_mode.rebalancer, "buy_coin", mock.AsyncMock(return_value=["order"])
            ) as _buy_coin_mock, mock.patch.object(
                trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder,
                "get_traded_assets_holdings_value", mock.Mock(return_value=decimal.Decimal("2000"))
            ) as get_traded_assets_holdings_value_mock:
                # Test with default reference_market_ratio = 0 (no reservation)
                mode.reference_market_ratio = trading_constants.ZERO
                reference_market_to_split = decimal.Decimal("2000")
                reference_market_reserved = reference_market_to_split * mode.reference_market_ratio
                reference_market_to_distribute = reference_market_to_split - reference_market_reserved
                
                assert await consumer._split_reference_market_into_indexed_coins(
                    details, is_simple_buy_without_selling, dependencies
                ) == ["order"]
                _get_symbols_and_amounts_mock.assert_called_once()
                # Verify _get_symbols_and_amounts was called with correct reference_market_to_distribute
                assert _get_symbols_and_amounts_mock.call_args[0][2] == reference_market_to_distribute
                assert reference_market_reserved == trading_constants.ZERO
                assert reference_market_to_distribute == reference_market_to_split
                _get_symbols_and_amounts_mock.reset_mock()
                get_currency_portfolio_mock.assert_not_called()
                get_traded_assets_holdings_value_mock.assert_called_once_with("USDT", None)
                _get_simple_buy_coins_mock.assert_called_once_with(details)
                assert _buy_coin_mock.call_count == 1
                assert _buy_coin_mock.mock_calls[0].args[0] == "ETH/USDT"
                assert _buy_coin_mock.mock_calls[0].args[3] == dependencies
                
                # Test with reference_market_ratio > 0 (with reservation)
                get_traded_assets_holdings_value_mock.reset_mock()
                _buy_coin_mock.reset_mock()
                _get_simple_buy_coins_mock.reset_mock()
                mode.reference_market_ratio = decimal.Decimal("0.2")  # 20% to trade
                reference_market_to_split = decimal.Decimal("2000")
                reference_market_to_distribute = reference_market_to_split * mode.reference_market_ratio
                reference_market_reserved = reference_market_to_split - reference_market_to_distribute
                
                assert await consumer._split_reference_market_into_indexed_coins(
                    details, is_simple_buy_without_selling, dependencies
                ) == ["order"]
                _get_symbols_and_amounts_mock.assert_called_once()
                # Verify _get_symbols_and_amounts was called with correct reference_market_to_distribute
                assert _get_symbols_and_amounts_mock.call_args[0][2] == reference_market_to_distribute
                assert reference_market_to_distribute == decimal.Decimal("400")
                assert reference_market_reserved == decimal.Decimal("1600")
                _get_symbols_and_amounts_mock.reset_mock()
                get_traded_assets_holdings_value_mock.assert_called_once_with("USDT", None)
                _get_simple_buy_coins_mock.assert_called_once_with(details)
                _buy_coin_mock.reset_mock()

@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_get_symbols_and_amounts(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    trader.exchange_manager.exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in ["BTC/USDT"]
    ]
    mode.ensure_updated_coins_distribution()
    with mock.patch.object(
            trading_personal_data, "get_up_to_date_price", mock.AsyncMock(return_value=decimal.Decimal(1000))
    ) as get_up_to_date_price_mock:
        assert await consumer._get_symbols_and_amounts(["BTC"], {}, decimal.Decimal(3000)) == {
            "BTC/USDT": {
                consumer.IDEAL_AMOUNT: decimal.Decimal(3),
                consumer.IDEAL_PRICE: decimal.Decimal(1000)
            }
        }
        assert get_up_to_date_price_mock.call_count == 1
        get_up_to_date_price_mock.reset_mock()
        assert await consumer._get_symbols_and_amounts(["BTC", "ETH"], {}, decimal.Decimal(3000)) == {
            "BTC/USDT": {
                consumer.IDEAL_AMOUNT: decimal.Decimal(3),
                consumer.IDEAL_PRICE: decimal.Decimal(1000)
            }
        }
        assert get_up_to_date_price_mock.call_count == 2
        get_up_to_date_price_mock.reset_mock()
        trader.exchange_manager.exchange_config.traded_symbols = [
            commons_symbols.parse_symbol(symbol)
            for symbol in ["BTC/USDT", "ETH/USDT"]
        ]
        mode.ensure_updated_coins_distribution()
        assert await consumer._get_symbols_and_amounts(["BTC", "ETH"], {}, decimal.Decimal(3000)) == {
            "BTC/USDT": {
                consumer.IDEAL_AMOUNT: decimal.Decimal("1.5"),
                consumer.IDEAL_PRICE: decimal.Decimal(1000)
            },
            "ETH/USDT": {
                consumer.IDEAL_AMOUNT: decimal.Decimal("1.5"),
                consumer.IDEAL_PRICE: decimal.Decimal(1000)
            }
        }
        assert get_up_to_date_price_mock.call_count == 2

    # enough funds
    trader.exchange_manager.exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in ["BTC/USDT"]
    ]
    mode.ensure_updated_coins_distribution()
    mode.min_order_size_margin = decimal.Decimal("2")
    with mock.patch.object(
            trading_personal_data, "get_up_to_date_price", mock.AsyncMock(return_value=decimal.Decimal(1000))
    ), mock.patch.object(
            trading_personal_data,
            "decimal_check_and_adapt_order_details_if_necessary",
            mock.Mock(return_value=decimal.Decimal("1"))
    ) as decimal_check_mock:
        await consumer._get_symbols_and_amounts(["BTC"], {}, decimal.Decimal(3000))
        assert decimal_check_mock.call_args[0][0] == decimal.Decimal("1.5")

    # not enough funds due to too much margin
    mode.min_order_size_margin = decimal.Decimal("10")
    with mock.patch.object(
            trading_personal_data, "get_up_to_date_price", mock.AsyncMock(return_value=decimal.Decimal(1000))
    ), mock.patch.object(
            trading_personal_data,
            "decimal_check_and_adapt_order_details_if_necessary",
            mock.Mock(return_value=None)
    ) as decimal_check_mock:
        with pytest.raises(trading_errors.MissingMinimalExchangeTradeVolume):
            await consumer._get_symbols_and_amounts(["BTC"], {}, decimal.Decimal(3000))
        assert decimal_check_mock.call_args[0][0] == decimal.Decimal("0.3")

    # not enough funds
    with pytest.raises(trading_errors.MissingMinimalExchangeTradeVolume):
        await consumer._get_symbols_and_amounts(["BTC"], {}, decimal.Decimal(0.0003))

    # not enough funds but skipping allowed so it doesn't raise
    mode.allow_skip_asset = True
    assert await consumer._get_symbols_and_amounts(["BTC"], {}, decimal.Decimal(0.0003)) == {}
    mode.allow_skip_asset = False

    with mock.patch.object(
            trading_personal_data, "get_up_to_date_price", mock.AsyncMock(return_value=decimal.Decimal(0.000000001))
    ) as get_up_to_date_price_mock:
        with pytest.raises(trading_errors.MissingMinimalExchangeTradeVolume):
            await consumer._get_symbols_and_amounts(["BTC", "ETH"], {}, decimal.Decimal(0.01))
        assert get_up_to_date_price_mock.call_count == 1

    # with ref market in coins config
    mode.trading_config = {
        "index_content": [
            {
                "name": "BTC",
                "value": 70
            },
            {
                "name": "USDT",
                "value": 30
            }
        ],
        "refresh_interval": 1,
        "required_strategies": [],
        "rebalance_trigger_min_percent": 5
    }
    mode.ensure_updated_coins_distribution()
    with mock.patch.object(
            trading_personal_data, "get_up_to_date_price", mock.AsyncMock(return_value=decimal.Decimal(1000))
    ) as get_up_to_date_price_mock:
        # USDT is not counted in orders to create (nothing to buy as USDT is the reference market everything is sold to)
        assert await consumer._get_symbols_and_amounts(["BTC", "USDT"], {}, decimal.Decimal(3000)) == {
            "BTC/USDT": {
                consumer.IDEAL_AMOUNT: decimal.Decimal("2.1"),
                consumer.IDEAL_PRICE: decimal.Decimal(1000)
            }
        }
        assert get_up_to_date_price_mock.call_count == 1


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_buy_coin(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    portfolio = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio
    dependencies = trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])
    is_futures = trader.exchange_manager.is_future
    positions_manager = trader.exchange_manager.exchange_personal_data.positions_manager
    with mock.patch.object(mode, "create_order", mock.AsyncMock(side_effect=lambda x, **kwargs: x)) as create_order_mock:
        # coin already held
        portfolio["BTC"].available = decimal.Decimal(20)
        # For futures, mock position to have size >= ideal_amount so it returns empty
        def _get_symbol_position(symbol, side=None):
            return _create_position_mock(
                symbol, trader, is_futures,
                is_idle=False,
                size=decimal.Decimal(2),  # Already at target
                side=trading_enums.PositionSide.LONG,
            )
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ), \
        mock.patch.object(
            order_util, "get_futures_max_order_size", mock.Mock(return_value=(decimal.Decimal(10), True))
        ):
            assert await consumer.trading_mode.rebalancer.buy_coin("BTC/USDT", decimal.Decimal(2), None, dependencies) == []
        create_order_mock.assert_not_called()

        # coin already partially held
        portfolio["BTC"].available = decimal.Decimal(0.5)
        # For futures, mock position to have size 0.5 so we need to buy 1.5 more (2 - 0.5 = 1.5)
        def _get_symbol_position(symbol, side=None):
            return _create_position_mock(
                symbol, trader, is_futures,
                is_idle=False,
                size=decimal.Decimal(0.5),  # Already have 0.5, need 1.5 more to reach 2
                side=trading_enums.PositionSide.LONG,
            )
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ), \
        mock.patch.object(
            order_util, "get_futures_max_order_size", mock.Mock(return_value=(decimal.Decimal(10), True))
        ):
            orders = await consumer.trading_mode.rebalancer.buy_coin("BTC/USDT", decimal.Decimal(2), None, dependencies)
        assert len(orders) == 1
        create_order_mock.assert_called_once_with(orders[0], dependencies=dependencies)
        assert isinstance(orders[0], trading_personal_data.BuyMarketOrder)
        assert orders[0].symbol == "BTC/USDT"
        assert orders[0].origin_price == decimal.Decimal(1000)
        assert orders[0].origin_quantity == decimal.Decimal("1.5")
        assert orders[0].total_cost == decimal.Decimal("1500")
        create_order_mock.reset_mock()

        # coin not already held
        portfolio["BTC"].available = decimal.Decimal(0)
        # For futures, mock position to be idle (no position)
        def _get_symbol_position(symbol, side=None):
            return _create_position_mock(
                symbol, trader, is_futures,
                is_idle=True,
            )
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ), \
        mock.patch.object(
            order_util, "get_futures_max_order_size", mock.Mock(return_value=(decimal.Decimal(10), True))
        ):
            orders = await consumer.trading_mode.rebalancer.buy_coin("BTC/USDT", decimal.Decimal(2), None, dependencies)
        assert len(orders) == 1
        create_order_mock.assert_called_once_with(orders[0], dependencies=dependencies)
        assert isinstance(orders[0], trading_personal_data.BuyMarketOrder)
        assert orders[0].symbol == "BTC/USDT"
        assert orders[0].origin_price == decimal.Decimal(1000)
        assert orders[0].origin_quantity == decimal.Decimal(2)
        assert orders[0].total_cost == decimal.Decimal("2000")
        create_order_mock.reset_mock()

        # given ideal_amount is lower
        def _get_symbol_position(symbol, side=None):
            return _create_position_mock(
                symbol, trader, is_futures,
                is_idle=True,
            )
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ), \
        mock.patch.object(
            order_util, "get_futures_max_order_size", mock.Mock(return_value=(decimal.Decimal(1), True))
        ):
            orders = await consumer.trading_mode.rebalancer.buy_coin("BTC/USDT", decimal.Decimal("0.025"), None, dependencies)
        assert len(orders) == 1
        create_order_mock.assert_called_once_with(orders[0], dependencies=dependencies)
        assert isinstance(orders[0], trading_personal_data.BuyMarketOrder)
        assert orders[0].symbol == "BTC/USDT"
        assert orders[0].origin_price == decimal.Decimal(1000)
        assert orders[0].origin_quantity == decimal.Decimal("0.025")  # use 100 instead of all 2000 USDT in pf
        assert orders[0].total_cost == decimal.Decimal("25")
        create_order_mock.reset_mock()

        # adapt for fees
        fee_usdt_cost = decimal.Decimal(10)
        with mock.patch.object(
                consumer.exchange_manager.exchange, "get_trade_fee", mock.Mock(return_value={
                    trading_enums.FeePropertyColumns.COST.value: str(fee_usdt_cost),
                    trading_enums.FeePropertyColumns.CURRENCY.value: "USDT",
                })
        ) as get_trade_fee_mock:
            def _get_symbol_position(symbol, side=None):
                return _create_position_mock(
                    symbol, trader, is_futures,
                    is_idle=True,
                )
            with mock.patch.object(
                positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
            ), \
            mock.patch.object(
                order_util, "get_futures_max_order_size", mock.Mock(return_value=(decimal.Decimal(10), True))
            ):
                orders = await consumer.trading_mode.rebalancer.buy_coin("BTC/USDT", decimal.Decimal("0.5"), None, dependencies)
            if is_futures:
                # For futures, get_trade_fee is not called in decimal_adapt_order_quantity_because_fees
                assert get_trade_fee_mock.call_count == 0
            else:
                assert get_trade_fee_mock.call_count == 2
            assert len(orders) == 1
            create_order_mock.assert_called_once_with(orders[0], dependencies=dependencies)
            assert isinstance(orders[0], trading_personal_data.BuyMarketOrder)
            assert orders[0].symbol == "BTC/USDT"
            assert orders[0].origin_price == decimal.Decimal(1000)
            # no adaptation needed as not all funds are used (1/4 ratio)
            assert orders[0].origin_quantity == decimal.Decimal("0.5")
            assert orders[0].total_cost == decimal.Decimal("500")
            create_order_mock.reset_mock()
            get_trade_fee_mock.reset_mock()

            def _get_symbol_position(symbol, side=None):
                return _create_position_mock(
                    symbol, trader, is_futures,
                    is_idle=True,
                )
            
            with mock.patch.object(
                positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
            ), \
            mock.patch.object(
                order_util, "get_futures_max_order_size", mock.Mock(return_value=(decimal.Decimal(10), True))
            ):
                orders = await consumer.trading_mode.rebalancer.buy_coin("BTC/USDT", decimal.Decimal(2), None, dependencies)
            if is_futures:
                # For futures, get_trade_fee is not called in decimal_adapt_order_quantity_because_fees
                assert get_trade_fee_mock.call_count == 0
            else:
                assert get_trade_fee_mock.call_count == 2
            assert len(orders) == 1
            create_order_mock.assert_called_once_with(orders[0], dependencies=dependencies)
            assert isinstance(orders[0], trading_personal_data.BuyMarketOrder)
            assert orders[0].symbol == "BTC/USDT"
            assert orders[0].origin_price == decimal.Decimal(1000)
            if is_futures:
                # For futures, fees are not deducted in decimal_adapt_order_quantity_because_fees
                assert orders[0].origin_quantity == decimal.Decimal("2")
                assert orders[0].total_cost == decimal.Decimal("2000")
            else:
                btc_fees = fee_usdt_cost / orders[0].origin_price
                # 2 - fees denominated in BTC
                assert orders[0].origin_quantity == decimal.Decimal("2") - btc_fees * trading_constants.FEES_SAFETY_MARGIN
                assert orders[0].total_cost == decimal.Decimal('1987.5000')
            create_order_mock.reset_mock()


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_buy_coin_does_not_duplicate_with_pending_open_orders(trading_tools):
    update = {}
    mode, _, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    dependencies = trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])
    is_futures = trader.exchange_manager.is_future
    positions_manager = trader.exchange_manager.exchange_personal_data.positions_manager
    orders_manager = trader.exchange_manager.exchange_personal_data.orders_manager
    portfolio = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio

    pending_buy_order = mock.Mock(
        symbol="BTC/USDT",
        origin_quantity=decimal.Decimal("2"),
        filled_quantity=decimal.Decimal("0"),
        side=trading_enums.TradeOrderSide.BUY,
    )
    portfolio["BTC"].available = decimal.Decimal("0")
    with mock.patch.object(mode, "create_order", mock.AsyncMock(side_effect=lambda x, **kwargs: x)) as create_order_mock, \
        mock.patch.object(
            orders_manager, "get_open_orders", mock.Mock(return_value=[pending_buy_order])
        ), \
        mock.patch.object(
            order_util, "get_futures_max_order_size", mock.Mock(return_value=(decimal.Decimal("10"), True))
        ):
        def _get_symbol_position(symbol, side=None):
            return _create_position_mock(
                symbol, trader, is_futures,
                is_idle=True,
            )
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ):
            orders = await consumer.trading_mode.rebalancer.buy_coin("BTC/USDT", decimal.Decimal("2"), None, dependencies)

    assert orders == [] # order already exists, we should not create a new one
    create_order_mock.assert_not_called()


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_buy_coin_using_limit_order(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    portfolio = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio
    dependencies = trading_signals.get_orders_dependencies([mock.Mock(order_id="123")])
    is_futures = trader.exchange_manager.is_future
    positions_manager = trader.exchange_manager.exchange_personal_data.positions_manager
    with mock.patch.object(
            mode,
            "create_order", mock.AsyncMock(side_effect=lambda x, **kwargs: x)
    ) as create_order_mock, mock.patch.object(
            mode.exchange_manager.exchange,
            "is_market_open_for_order_type", mock.Mock(return_value=False)
    ) as is_market_open_for_order_type_mock:
        # coin already held
        portfolio["BTC"].available = decimal.Decimal(20)
        # For futures, mock position to have size >= ideal_amount so it returns empty
        def _get_symbol_position(symbol, side=None):
            return _create_position_mock(
                symbol, trader, is_futures,
                is_idle=False,
                size=decimal.Decimal(2),  # Already at target
                side=trading_enums.PositionSide.LONG,
            )
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ), \
        mock.patch.object(
            order_util, "get_futures_max_order_size", mock.Mock(return_value=(decimal.Decimal(10), True))
        ):
            assert await consumer.trading_mode.rebalancer.buy_coin("BTC/USDT", decimal.Decimal(2), None, dependencies) == []
        create_order_mock.assert_not_called()
        is_market_open_for_order_type_mock.assert_not_called()

        # coin already partially held: buy more using limit order
        portfolio["BTC"].available = decimal.Decimal(0.5)
        # For futures, mock position to have size 0.5 so we need to buy 1.5 more (2 - 0.5 = 1.5)
        def _get_symbol_position(symbol, side=None):
            return _create_position_mock(
                symbol, trader, is_futures,
                is_idle=False,
                size=decimal.Decimal(0.5),  # Already have 0.5, need 1.5 more to reach 2
                side=trading_enums.PositionSide.LONG,
            )
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ), \
        mock.patch.object(
            order_util, "get_futures_max_order_size", mock.Mock(return_value=(decimal.Decimal(10), True))
        ):
            orders = await consumer.trading_mode.rebalancer.buy_coin("BTC/USDT", decimal.Decimal(2), None, dependencies)
        assert len(orders) == 1
        is_market_open_for_order_type_mock.assert_called_once_with("BTC/USDT", trading_enums.TraderOrderType.BUY_MARKET)
        create_order_mock.assert_called_once_with(orders[0], dependencies=dependencies)
        assert isinstance(orders[0], trading_personal_data.BuyLimitOrder)
        assert orders[0].symbol == "BTC/USDT"
        assert orders[0].origin_price == decimal.Decimal(1005)  # a bit above market price to instant fill
        assert orders[0].origin_quantity == decimal.Decimal('1.49253731')  # reduced a bit to compensate price increase
        assert decimal.Decimal("1499.99999") < orders[0].total_cost < decimal.Decimal("1500")
        create_order_mock.reset_mock()
        is_market_open_for_order_type_mock.reset_mock()

        # coin not already held
        portfolio["BTC"].available = decimal.Decimal(0)
        # For futures, mock position to be idle (no position)
        def _get_symbol_position(symbol, side=None):
            return _create_position_mock(
                symbol, trader, is_futures,
                is_idle=True,
            )
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ), \
        mock.patch.object(
            order_util, "get_futures_max_order_size", mock.Mock(return_value=(decimal.Decimal(10), True))
        ):
            orders = await consumer.trading_mode.rebalancer.buy_coin("BTC/USDT", decimal.Decimal(2), None, dependencies)
        assert len(orders) == 1
        is_market_open_for_order_type_mock.assert_called_once_with("BTC/USDT", trading_enums.TraderOrderType.BUY_MARKET)
        create_order_mock.assert_called_once_with(orders[0], dependencies=dependencies)
        assert isinstance(orders[0], trading_personal_data.BuyLimitOrder)
        assert orders[0].symbol == "BTC/USDT"
        assert orders[0].origin_price == decimal.Decimal('1005.000')
        assert orders[0].origin_quantity == decimal.Decimal('1.99004975')
        assert decimal.Decimal("1999.99999") < orders[0].total_cost < decimal.Decimal("2000")
        create_order_mock.reset_mock()
        is_market_open_for_order_type_mock.reset_mock()

        # given ideal_amount is lower
        def _get_symbol_position(symbol, side=None):
            return _create_position_mock(
                symbol, trader, is_futures,
                is_idle=True,
            )
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ), \
        mock.patch.object(
            order_util, "get_futures_max_order_size", mock.Mock(return_value=(decimal.Decimal(1), True))
        ):
            orders = await consumer.trading_mode.rebalancer.buy_coin("BTC/USDT", decimal.Decimal("0.025"), None, dependencies)
        assert len(orders) == 1
        is_market_open_for_order_type_mock.assert_called_once_with("BTC/USDT", trading_enums.TraderOrderType.BUY_MARKET)
        create_order_mock.assert_called_once_with(orders[0], dependencies=dependencies)
        assert isinstance(orders[0], trading_personal_data.BuyLimitOrder)
        assert orders[0].symbol == "BTC/USDT"
        assert orders[0].origin_price == decimal.Decimal(1005)
        assert orders[0].origin_quantity == decimal.Decimal('0.02487562')  # use 100 instead of all 2000 USDT in pf, adjusted for limit price
        assert decimal.Decimal('24.999') < orders[0].total_cost < decimal.Decimal("25")
        create_order_mock.reset_mock()
        is_market_open_for_order_type_mock.reset_mock()

        # adapt for fees
        fee_usdt_cost = decimal.Decimal(10)
        with mock.patch.object(
                consumer.exchange_manager.exchange, "get_trade_fee", mock.Mock(return_value={
                    trading_enums.FeePropertyColumns.COST.value: str(fee_usdt_cost),
                    trading_enums.FeePropertyColumns.CURRENCY.value: "USDT",
                })
        ) as get_trade_fee_mock:
            def _get_symbol_position(symbol, side=None):
                return _create_position_mock(
                    symbol, trader, is_futures,
                    is_idle=True,
                )
            with mock.patch.object(
                positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
            ), \
            mock.patch.object(
                order_util, "get_futures_max_order_size", mock.Mock(return_value=(decimal.Decimal(10), True))
            ):
                orders = await consumer.trading_mode.rebalancer.buy_coin("BTC/USDT", decimal.Decimal("0.5"), None, dependencies)
            if is_futures:
                # For futures, get_trade_fee is not called in decimal_adapt_order_quantity_because_fees
                assert get_trade_fee_mock.call_count == 0
            else:
                assert get_trade_fee_mock.call_count == 2
            assert len(orders) == 1
            is_market_open_for_order_type_mock.assert_called_once_with("BTC/USDT", trading_enums.TraderOrderType.BUY_MARKET)
            create_order_mock.assert_called_once_with(orders[0], dependencies=dependencies)
            assert isinstance(orders[0], trading_personal_data.BuyLimitOrder)
            assert orders[0].symbol == "BTC/USDT"
            assert orders[0].origin_price == decimal.Decimal(1005)
            # no adaptation needed as not all funds are used (1/4 ratio)
            assert orders[0].origin_quantity == decimal.Decimal('0.49751243')
            assert decimal.Decimal('499.999') < orders[0].total_cost < decimal.Decimal("500")
            create_order_mock.reset_mock()
            get_trade_fee_mock.reset_mock()
            is_market_open_for_order_type_mock.reset_mock()

            def _get_symbol_position(symbol, side=None):
                return _create_position_mock(
                    symbol, trader, is_futures,
                    is_idle=True,
                )
            with mock.patch.object(
                positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
            ), \
            mock.patch.object(
                order_util, "get_futures_max_order_size", mock.Mock(return_value=(decimal.Decimal(10), True))
            ):
                orders = await consumer.trading_mode.rebalancer.buy_coin("BTC/USDT", decimal.Decimal(2), None, dependencies)
            if is_futures:
                # For futures, get_trade_fee is not called in decimal_adapt_order_quantity_because_fees
                assert get_trade_fee_mock.call_count == 0
            else:
                assert get_trade_fee_mock.call_count == 2
            assert len(orders) == 1
            is_market_open_for_order_type_mock.assert_called_once_with("BTC/USDT", trading_enums.TraderOrderType.BUY_MARKET)
            create_order_mock.assert_called_once_with(orders[0], dependencies=dependencies)
            assert isinstance(orders[0], trading_personal_data.BuyLimitOrder)
            assert orders[0].symbol == "BTC/USDT"
            assert orders[0].origin_price == decimal.Decimal(1005)
            if not is_futures:
                # 2 - fees denominated in BTC
                symbol_market = trader.exchange_manager.exchange.get_market_status(orders[0].symbol, with_fixer=False)
                assert orders[0].origin_quantity == trading_personal_data.decimal_adapt_quantity(
                    symbol_market,
                    (
                        decimal.Decimal("2000") - fee_usdt_cost * trading_constants.FEES_SAFETY_MARGIN
                    ) / orders[0].origin_price
                )
            assert decimal.Decimal('1985') < orders[0].total_cost < decimal.Decimal('2000')
            create_order_mock.reset_mock()
            is_market_open_for_order_type_mock.reset_mock()

        # test price threshold to use market order
        # Current price is 1000, threshold is PRICE_THRESHOLD_TO_USE_MARKET_ORDER (0.01 = 1%)
        # Threshold price = 1000 * (1 - 0.01) = 990
        # If ideal_price >= 990, should try market order
        # If ideal_price < 990, should use limit order
        current_price = decimal.Decimal(1000)
        price_threshold = mode.rebalancer.PRICE_THRESHOLD_TO_USE_MARKET_ORDER
        threshold_price = current_price * (decimal.Decimal(1) - price_threshold)
    
        # ideal_price just below threshold (should use limit order)
        price_below_threshold = threshold_price - decimal.Decimal("0.01")
        def _get_symbol_position(symbol, side=None):
            return _create_position_mock(
                symbol, trader, is_futures,
                is_idle=True,
            )
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ), \
        mock.patch.object(
            order_util, "get_futures_max_order_size", mock.Mock(return_value=(decimal.Decimal(10), True))
        ):
            orders = await consumer.trading_mode.rebalancer.buy_coin("BTC/USDT", decimal.Decimal(2), price_below_threshold, dependencies)
        assert len(orders) == 1
        # Should use limit order since price is below threshold
        is_market_open_for_order_type_mock.assert_called_once_with("BTC/USDT", trading_enums.TraderOrderType.BUY_LIMIT)
        create_order_mock.reset_mock()
        is_market_open_for_order_type_mock.reset_mock()

    


async def _get_tools(symbol="BTC/USDT"):
    config = test_config.load_test_config()
    config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["USDT"] = 2000
    exchange_manager = test_exchanges.get_test_exchange_manager(config, "binance")
    exchange_manager.tentacles_setup_config = test_utils_config.get_tentacles_setup_config()

    # use backtesting not to spam exchanges apis
    exchange_manager.is_simulated = True
    exchange_manager.is_backtesting = True
    exchange_manager.use_cached_markets = False
    backtesting = await backtesting_api.initialize_backtesting(
        config,
        exchange_ids=[exchange_manager.id],
        matrix_id=None,
        data_files=[os.path.join(test_config.TEST_CONFIG_FOLDER,
                                 "AbstractExchangeHistoryCollector_1586017993.616272.data")])
    exchange_manager.exchange = exchanges.ExchangeSimulator(
        exchange_manager.config, exchange_manager, backtesting
    )
    await exchange_manager.exchange.initialize()
    exchange_manager.exchange_config.set_config_traded_pairs()
    for exchange_channel_class_type in [exchanges_channel.ExchangeChannel, exchanges_channel.TimeFrameExchangeChannel]:
        await channel_util.create_all_subclasses_channel(exchange_channel_class_type, exchanges_channel.set_chan,
                                                         exchange_manager=exchange_manager)

    trader = exchanges.TraderSimulator(config, exchange_manager)
    await trader.initialize()
    exchange_manager.exchange_personal_data.portfolio_manager.reference_market = "USDT"

    mode = Mode.IndexTradingMode(config, exchange_manager)
    mode.symbol = None if mode.get_is_symbol_wildcard() else symbol
    # trading mode is not initialized: to be initialized with the required config in tests

    # add mode to exchange manager so that it can be stopped and freed from memory
    exchange_manager.trading_modes.append(mode)

    # set BTC/USDT price at 1000 USDT
    trading_api.force_set_mark_price(exchange_manager, symbol, 1000)

    return mode, trader

def _support_contract(exchange_manager, symbol, contract: trading_exchange_data.Contract):
    contract = contract(
        pair=symbol,
        margin_type=trading_enums.MarginType.ISOLATED,
        contract_type=trading_enums.FutureContractType.LINEAR_PERPETUAL,
        current_leverage=trading_constants.ONE,
        maximum_leverage=trading_constants.ONE_HUNDRED
    )
    exchange_manager.exchange.set_pair_contract(symbol, contract)

async def _get_futures_tools(symbol="BTC/USDT"):
    config = test_config.load_test_config()
    config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["USDT"] = 2000
    exchange_manager = test_exchanges.get_test_exchange_manager(config, "binance")
    exchange_manager.tentacles_setup_config = test_utils_config.get_tentacles_setup_config()

    # use backtesting not to spam exchanges apis
    exchange_manager.is_spot_only = False
    exchange_manager.is_future = True
    exchange_manager.is_simulated = True
    exchange_manager.is_backtesting = True
    exchange_manager.use_cached_markets = False
    backtesting = await backtesting_api.initialize_backtesting(
        config,
        exchange_ids=[exchange_manager.id],
        matrix_id=None,
        data_files=[os.path.join(test_config.TEST_CONFIG_FOLDER,
                                 "AbstractExchangeHistoryCollector_1586017993.616272.data")])
    exchange_manager.exchange = exchanges.ExchangeSimulator(
        exchange_manager.config, exchange_manager, backtesting
    )
    await exchange_manager.exchange.initialize()
    exchange_manager.exchange_config.set_config_traded_pairs()
    # Ensure the futures symbol is in traded_symbols for index trading mode to work correctly
    parsed_symbol = commons_symbols.parse_symbol(symbol)
    if parsed_symbol not in exchange_manager.exchange_config.traded_symbols:
        exchange_manager.exchange_config.traded_symbols.append(parsed_symbol)
        exchange_manager.exchange_config.traded_symbol_pairs.append(symbol)
    for exchange_channel_class_type in [exchanges_channel.ExchangeChannel, exchanges_channel.TimeFrameExchangeChannel]:
        await channel_util.create_all_subclasses_channel(exchange_channel_class_type, exchanges_channel.set_chan,
                                                         exchange_manager=exchange_manager)
    
    # Create contracts for all traded symbols
    for contract_symbol in TRADED_SYMBOLS:
        _support_contract(exchange_manager, contract_symbol, trading_exchange_data.FutureContract)

    trader = exchanges.TraderSimulator(config, exchange_manager)
    await trader.initialize()
    exchange_manager.exchange_personal_data.portfolio_manager.reference_market = "USDT"

    mode = Mode.IndexTradingMode(config, exchange_manager)
    mode.symbol = None if mode.get_is_symbol_wildcard() else symbol
    # trading mode is not initialized: to be initialized with the required config in tests

    # add mode to exchange manager so that it can be stopped and freed from memory
    exchange_manager.trading_modes.append(mode)

    # Initialize mark prices for all traded symbols
    for traded_symbol in TRADED_SYMBOLS:
        if traded_symbol == symbol:
            # set symbol price at 1000 USDT
            trading_api.force_set_mark_price(exchange_manager, symbol, 1000)
        else:
            trading_api.force_set_mark_price(trader.exchange_manager, traded_symbol, 1)

    return mode, trader


async def _init_mode(tools, config):
    mode, trader = tools
    await mode.initialize(trading_config=config)
    return mode, mode.producers[0], mode.get_trading_mode_consumers()[0], trader


async def _stop(exchange_manager):
    for importer in backtesting_api.get_importers(exchange_manager.exchange.backtesting):
        await backtesting_api.stop_importer(importer)
    await exchange_manager.exchange.backtesting.stop()
    await exchange_manager.stop()


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_automatically_update_historical_config_on_set_intervals(trading_tools):
    update = {}
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, update))
    
    # Test with SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE policy
    mode.synchronization_policy = index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE
    with mock.patch.object(mode, "supports_historical_config", mock.Mock(return_value=True)) as supports_historical_config_mock:
        assert mode.automatically_update_historical_config_on_set_intervals() is True
        supports_historical_config_mock.assert_called_once()
        supports_historical_config_mock.reset_mock()
    
    with mock.patch.object(mode, "supports_historical_config", mock.Mock(return_value=False)) as supports_historical_config_mock:
        assert mode.automatically_update_historical_config_on_set_intervals() is False
        supports_historical_config_mock.assert_called_once()
        supports_historical_config_mock.reset_mock()
    
    # Test with SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE policy
    mode.synchronization_policy = index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE
    with mock.patch.object(mode, "supports_historical_config", mock.Mock(return_value=True)) as supports_historical_config_mock:
        assert mode.automatically_update_historical_config_on_set_intervals() is False
        supports_historical_config_mock.assert_called_once()
        supports_historical_config_mock.reset_mock()
    
    with mock.patch.object(mode, "supports_historical_config", mock.Mock(return_value=False)) as supports_historical_config_mock:
        assert mode.automatically_update_historical_config_on_set_intervals() is False
        supports_historical_config_mock.assert_called_once()
        supports_historical_config_mock.reset_mock()

@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_ensure_updated_coins_distribution(trading_tools):
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, {}))
    trader.exchange_manager.exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in ["ETH/USDT", "SOL/USDT", "BTC/USDT"]
    ]
    distribution = [
        {
            index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
            index_trading.index_distribution.DISTRIBUTION_VALUE: 50
        },
        {
            index_trading.index_distribution.DISTRIBUTION_NAME: "ETH",
            index_trading.index_distribution.DISTRIBUTION_VALUE: 30
        },
        {
            index_trading.index_distribution.DISTRIBUTION_NAME: "SOL",
            index_trading.index_distribution.DISTRIBUTION_VALUE: 20
        },
    ]
    with mock.patch.object(mode, "_get_supported_distribution", mock.Mock(return_value=distribution)) as _get_supported_distribution_mock:
        mode.ensure_updated_coins_distribution()
        _get_supported_distribution_mock.assert_called_once()
        _get_supported_distribution_mock.reset_mock()
        assert mode.ratio_per_asset == {
            "BTC": {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 50
            },
            "ETH": {
                index_trading.index_distribution.DISTRIBUTION_NAME: "ETH",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 30
            },
            "SOL": {
                index_trading.index_distribution.DISTRIBUTION_NAME: "SOL",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 20
            }
        }
        assert mode.total_ratio_per_asset == 100
        assert mode.indexed_coins == ["BTC", "ETH", "SOL"]
    
    # include ref market in distribution
    distribution = [
        {
            index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
            index_trading.index_distribution.DISTRIBUTION_VALUE: 50
        },
        {
            index_trading.index_distribution.DISTRIBUTION_NAME: "ETH",
            index_trading.index_distribution.DISTRIBUTION_VALUE: 30
        },
        {
            index_trading.index_distribution.DISTRIBUTION_NAME: "USDT",
            index_trading.index_distribution.DISTRIBUTION_VALUE: 20
        },
    ]
    with mock.patch.object(mode, "_get_supported_distribution", mock.Mock(return_value=distribution)) as _get_supported_distribution_mock:
        mode.ensure_updated_coins_distribution()
        _get_supported_distribution_mock.assert_called_once()
        _get_supported_distribution_mock.reset_mock()
        assert mode.ratio_per_asset == {
            "BTC": {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 50
            },
            "ETH": {
                index_trading.index_distribution.DISTRIBUTION_NAME: "ETH",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 30
            },
            "USDT": {
                index_trading.index_distribution.DISTRIBUTION_NAME: "USDT",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 20
            }
        }
        assert mode.total_ratio_per_asset == 100
        assert mode.indexed_coins == ["BTC", "ETH", "USDT"]


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_get_supported_distribution(trading_tools):
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, {}))
    trader.exchange_manager.exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"]
    ]
    mode.trading_config = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT:  [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 25
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "ETH",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 25
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "SOL",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 25
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "ADA",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 25
            },
        ]
    }
    with mock.patch.object(mode, "get_ideal_distribution", mock.Mock(wraps=mode.get_ideal_distribution)) as get_ideal_distribution_mock:
        # no ideal distribution: return uniform distribution over traded assets
        assert mode._get_supported_distribution(False, False) == mode.trading_config[
            index_trading.IndexTradingModeProducer.INDEX_CONTENT
        ]
        get_ideal_distribution_mock.assert_called_once()

    mode.trading_config = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT:  [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 50
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "ETH",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 30
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "USDT",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 20
            },
        ]
    }
    with mock.patch.object(mode, "get_ideal_distribution", mock.Mock(wraps=mode.get_ideal_distribution)) as get_ideal_distribution_mock:
        assert mode._get_supported_distribution(False, False) == mode.trading_config[
            index_trading.IndexTradingModeProducer.INDEX_CONTENT
        ]
        get_ideal_distribution_mock.assert_called_once()

    mode.trading_config = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT:  [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 50
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "ETH",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 30
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "USDT",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 20
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "PLOP", # not traded
                index_trading.index_distribution.DISTRIBUTION_VALUE: 20
            },
        ]
    }
    with mock.patch.object(mode, "get_ideal_distribution", mock.Mock(wraps=mode.get_ideal_distribution)) as get_ideal_distribution_mock:
        assert mode._get_supported_distribution(False, False) == [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 50
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "ETH",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 30
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "USDT",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 20
            },
            # {
            #     index_trading.index_distribution.DISTRIBUTION_NAME: "PLOP", # not traded
            #     index_trading.index_distribution.DISTRIBUTION_VALUE: 20
            # },
        ]
        get_ideal_distribution_mock.assert_called_once()

    mode.trading_config = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT:  [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 50
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "ETH",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 30
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "USDT",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 20
            },
        ]
    }

    # synchronization policy is not SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE
    mode.synchronization_policy = index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE
    with mock.patch.object(mode, "get_ideal_distribution", mock.Mock(wraps=mode.get_ideal_distribution)) as get_ideal_distribution_mock:
        with mock.patch.object(mode, "_get_currently_applied_historical_config_according_to_holdings", mock.Mock()) as _get_currently_applied_historical_config_according_to_holdings_mock, \
            mock.patch.object(mode, "get_historical_configs", mock.Mock()) as get_historical_configs_mock:
            assert mode._get_supported_distribution(True, False) == mode.trading_config[
                index_trading.IndexTradingModeProducer.INDEX_CONTENT
            ]
            get_ideal_distribution_mock.assert_called_once()
            _get_currently_applied_historical_config_according_to_holdings_mock.assert_not_called()
            get_historical_configs_mock.assert_not_called()
            _get_currently_applied_historical_config_according_to_holdings_mock.reset_mock()
            get_historical_configs_mock.reset_mock()
            get_ideal_distribution_mock.reset_mock()
            assert mode._get_supported_distribution(False, True) == mode.trading_config[
                index_trading.IndexTradingModeProducer.INDEX_CONTENT
            ]
            get_ideal_distribution_mock.assert_called_once()
            _get_currently_applied_historical_config_according_to_holdings_mock.assert_not_called()
            get_historical_configs_mock.assert_not_called()
    
    # synchronization policy is SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE
    mode.synchronization_policy = index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE
    holding_adapted_config = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 50
            },
        ]
    }
    with mock.patch.object(mode, "get_ideal_distribution", mock.Mock(wraps=mode.get_ideal_distribution)) as get_ideal_distribution_mock:
        with mock.patch.object(mode, "_get_currently_applied_historical_config_according_to_holdings", mock.Mock(return_value=holding_adapted_config)) as _get_currently_applied_historical_config_according_to_holdings_mock, \
            mock.patch.object(mode, "get_historical_configs", mock.Mock()) as get_historical_configs_mock:
            assert mode._get_supported_distribution(True, False) == holding_adapted_config[
                index_trading.IndexTradingModeProducer.INDEX_CONTENT
            ]
            assert get_ideal_distribution_mock.call_count == 2
            _get_currently_applied_historical_config_according_to_holdings_mock.assert_called_once_with(
                mode.trading_config, {'ADA', 'BTC', 'SOL', 'USDT', 'ETH'}
            )
            get_historical_configs_mock.assert_not_called()
            get_ideal_distribution_mock.reset_mock()
        
        # with historical configs
        latest_config = {
            index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
                {
                    index_trading.index_distribution.DISTRIBUTION_NAME: "ETH",
                    index_trading.index_distribution.DISTRIBUTION_VALUE: 50
                },
            ]
        }
        historical_configs = [
            latest_config,
            holding_adapted_config,

        ]
        with mock.patch.object(mode, "_get_currently_applied_historical_config_according_to_holdings", mock.Mock()) as _get_currently_applied_historical_config_according_to_holdings_mock, \
            mock.patch.object(mode, "get_historical_configs", mock.Mock(return_value=historical_configs)) as get_historical_configs_mock:
            assert mode._get_supported_distribution(False, True) == latest_config[
                index_trading.IndexTradingModeProducer.INDEX_CONTENT
            ]
            assert get_ideal_distribution_mock.call_count == 3
            _get_currently_applied_historical_config_according_to_holdings_mock.assert_not_called()
            get_historical_configs_mock.assert_called_once_with(
                0, mode.exchange_manager.exchange.get_exchange_current_time()
            )
            get_ideal_distribution_mock.reset_mock()

        # without historical configs
        with mock.patch.object(mode, "_get_currently_applied_historical_config_according_to_holdings", mock.Mock()) as _get_currently_applied_historical_config_according_to_holdings_mock, \
            mock.patch.object(mode, "get_historical_configs", mock.Mock(return_value=[])) as get_historical_configs_mock:
            # use current config
            assert mode._get_supported_distribution(False, True) == mode.trading_config[
                index_trading.IndexTradingModeProducer.INDEX_CONTENT
            ]
            assert get_ideal_distribution_mock.call_count == 2
            _get_currently_applied_historical_config_according_to_holdings_mock.assert_not_called()
            get_historical_configs_mock.assert_called_once_with(
                0, mode.exchange_manager.exchange.get_exchange_current_time()
            )
            get_ideal_distribution_mock.reset_mock()


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_get_currently_applied_historical_config_according_to_holdings(trading_tools):
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, {}))
    trader.exchange_manager.exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"]
    ]
    traded_bases = set(
        symbol.base
        for symbol in trader.exchange_manager.exchange_config.traded_symbols
    )
    # 1. using latest config
    with mock.patch.object(mode, "_is_index_config_applied", mock.Mock(return_value=True)) as _is_index_config_applied_mock:
        assert mode._get_currently_applied_historical_config_according_to_holdings(
            mode.trading_config, traded_bases
        ) == mode.trading_config
        _is_index_config_applied_mock.assert_called_once_with(mode.trading_config, traded_bases)

    # 2. using historical configs
    with mock.patch.object(mode, "_is_index_config_applied", mock.Mock(return_value=False)) as _is_index_config_applied_mock, mock.patch.object(mode.exchange_manager.exchange, "get_exchange_current_time", mock.Mock(return_value=2)) as get_exchange_current_time_mock:
        # 2.1. no historical configs
        assert mode._get_currently_applied_historical_config_according_to_holdings(
            mode.trading_config, traded_bases
        ) == mode.trading_config
        _is_index_config_applied_mock.assert_called_once_with(mode.trading_config, traded_bases)
        _is_index_config_applied_mock.reset_mock()
        get_exchange_current_time_mock.assert_called_once()
        get_exchange_current_time_mock.reset_mock()

        # 2.2. with historical configs but as _is_index_config_applied always return False, fallback to current config
        hist_config_1 = {
            index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
                {
                    index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
                    index_trading.index_distribution.DISTRIBUTION_VALUE: 50
                },
                {
                    index_trading.index_distribution.DISTRIBUTION_NAME: "ETH",
                    index_trading.index_distribution.DISTRIBUTION_VALUE: 30
                },
            ]
        }
        hist_config_2 = {
            index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
                {
                    index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
                    index_trading.index_distribution.DISTRIBUTION_VALUE: 50
                },
            ]
        }
        commons_configuration.add_historical_tentacle_config(mode.trading_config, 1, hist_config_1)
        commons_configuration.add_historical_tentacle_config(mode.trading_config, 2, hist_config_2)
        mode.historical_master_config = mode.trading_config
        assert mode._get_currently_applied_historical_config_according_to_holdings(
            mode.trading_config, traded_bases
        ) == mode.trading_config
        assert _is_index_config_applied_mock.call_count == 3
        assert _is_index_config_applied_mock.mock_calls[0].args[0] == mode.trading_config
        assert _is_index_config_applied_mock.mock_calls[1].args[0] == hist_config_2
        assert _is_index_config_applied_mock.mock_calls[2].args[0] == hist_config_1
        _is_index_config_applied_mock.reset_mock()
        get_exchange_current_time_mock.assert_called_once()
        get_exchange_current_time_mock.reset_mock()

        __is_index_config_applied_calls = []
        accepted_config_index = 1
        def __is_index_config_applied(*args):
            __is_index_config_applied_calls.append(1)
            if len(__is_index_config_applied_calls) - 1 >= accepted_config_index:
                return True
            return False

        # 2.3. with historical configs using historical config
        with mock.patch.object(mode, "_is_index_config_applied", mock.Mock(side_effect=__is_index_config_applied)) as _is_index_config_applied_mock:
            # 1. use most up to date config
            assert mode._get_currently_applied_historical_config_according_to_holdings(
                mode.trading_config, traded_bases
            ) == hist_config_2
            assert _is_index_config_applied_mock.call_count == 2
            assert _is_index_config_applied_mock.mock_calls[0].args[0] == mode.trading_config
            assert _is_index_config_applied_mock.mock_calls[1].args[0] == hist_config_2
            _is_index_config_applied_mock.reset_mock()
            get_exchange_current_time_mock.assert_called_once()
            get_exchange_current_time_mock.reset_mock()

        __is_index_config_applied_calls.clear()
        accepted_config_index = 2
        with mock.patch.object(mode, "_is_index_config_applied", mock.Mock(side_effect=__is_index_config_applied)) as _is_index_config_applied_mock:
            # 2. use oldest config
            assert mode._get_currently_applied_historical_config_according_to_holdings(
                mode.trading_config, traded_bases
            ) == hist_config_1
            assert _is_index_config_applied_mock.call_count == 3
            assert _is_index_config_applied_mock.mock_calls[0].args[0] == mode.trading_config
            assert _is_index_config_applied_mock.mock_calls[1].args[0] == hist_config_2
            assert _is_index_config_applied_mock.mock_calls[2].args[0] == hist_config_1
            _is_index_config_applied_mock.reset_mock()


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_is_index_config_applied(trading_tools):
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, {}))
    trader.exchange_manager.exchange_config.traded_symbols = [
        commons_symbols.parse_symbol(symbol)
        for symbol in ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"]
    ]
    traded_bases = set(
        symbol.base
        for symbol in trader.exchange_manager.exchange_config.traded_symbols
    )
    is_futures = trader.exchange_manager.is_future
    positions_manager = trader.exchange_manager.exchange_personal_data.positions_manager
    portfolio_value_holder = trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder
    
    # Test 1: No ideal distribution - should return False
    config_without_distribution = {}
    assert mode._is_index_config_applied(config_without_distribution, traded_bases) is False
    
    # Test 2: Empty ideal distribution - should return False
    config_with_empty_distribution = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: []
    }
    assert mode._is_index_config_applied(config_with_empty_distribution, traded_bases) is False
    
    # Test 3: Distribution with only non-traded assets - should return False
    config_with_non_traded_assets = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "NON_TRADED_COIN",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 100
            }
        ]
    }
    assert mode._is_index_config_applied(config_with_non_traded_assets, traded_bases) is False
    
    # Test 4: Distribution with zero total ratio - should return False
    config_with_zero_total = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 0
            }
        ]
    }
    assert mode._is_index_config_applied(config_with_zero_total, traded_bases) is False
    
    # Test 5: Valid distribution with holdings matching target ratios
    config_with_valid_distribution = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 60
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "ETH",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 40
            }
        ]
    }
    
    # Mock holdings ratios to match target ratios exactly
    # For futures, also need to mock positions and get_traded_assets_holdings_value
    total_portfolio_value = decimal.Decimal("1000")
    btc_position_value = total_portfolio_value * decimal.Decimal("0.6")  # 600
    eth_position_value = total_portfolio_value * decimal.Decimal("0.4")  # 400
    
    def _get_symbol_position(symbol, side=None):
        position_mock = mock.Mock()
        position_mock.symbol = symbol
        position_mock.side = side or trading_enums.PositionSide.LONG
        if is_futures:
            # Match symbol by checking if it contains the coin name (handles both "BTC/USDT" and "BTC/USDT:USDT")
            symbol_str = str(symbol) if not isinstance(symbol, str) else symbol
            if "BTC" in symbol_str and "USDT" in symbol_str:
                position_mock.margin = btc_position_value
                position_mock.size = decimal.Decimal("0.6")  # Position size for BTC
            elif "ETH" in symbol_str and "USDT" in symbol_str:
                position_mock.margin = eth_position_value
                position_mock.size = decimal.Decimal("0.4")  # Position size for ETH
            else:
                position_mock.margin = decimal.Decimal("0")
                position_mock.size = decimal.Decimal("0")
            position_mock.is_idle.return_value = False
            position_mock.is_open.return_value = True  # Position is open
        else:
            position_mock.get_value.return_value = decimal.Decimal("0")
            position_mock.size = decimal.Decimal("0")
            position_mock.is_idle.return_value = True
            position_mock.is_open.return_value = False
        return position_mock
    
    if is_futures:
        with mock.patch.object(
            positions_manager, "get_symbol_position", mock.Mock(side_effect=_get_symbol_position)
        ) as get_symbol_position_mock, \
        mock.patch.object(
            portfolio_value_holder, "get_traded_assets_holdings_value", mock.Mock(return_value=total_portfolio_value)
        ) as get_traded_assets_holdings_value_mock:
            assert mode._is_index_config_applied(config_with_valid_distribution, traded_bases) is True
            assert get_symbol_position_mock.call_count == 2
            assert "BTC" in str(get_symbol_position_mock.mock_calls[0].args[0])
            assert "ETH" in str(get_symbol_position_mock.mock_calls[1].args[0])
            get_symbol_position_mock.reset_mock()
            assert get_traded_assets_holdings_value_mock.call_count == 2  # called for each coin
            get_traded_assets_holdings_value_mock.reset_mock()
    else:
        with mock.patch.object(
            portfolio_value_holder,
            "get_holdings_ratio", mock.Mock(side_effect=lambda coin, **kwargs: {
                "BTC": decimal.Decimal("0.6"),  # 60% target
                "ETH": decimal.Decimal("0.4"),  # 40% target
            }.get(coin, decimal.Decimal("0")))
        ) as get_holdings_ratio_mock:
            assert mode._is_index_config_applied(config_with_valid_distribution, traded_bases) is True
            assert get_holdings_ratio_mock.call_count == 2
            assert get_holdings_ratio_mock.mock_calls[0].args[0] == "BTC"
            assert get_holdings_ratio_mock.mock_calls[1].args[0] == "ETH"
            get_holdings_ratio_mock.reset_mock()
    
    # Test 6: Valid distribution with holdings within tolerance range
    with mock.patch.object(
        trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder,
        "get_holdings_ratio", mock.Mock(side_effect=lambda coin, **kwargs: {
            "BTC": decimal.Decimal("0.62"),  # 60% target + 2% (within 5% tolerance)
            "ETH": decimal.Decimal("0.38"),  # 40% target - 2% (within 5% tolerance)
        }.get(coin, decimal.Decimal("0")))
    ) as get_holdings_ratio_mock:
        assert mode._is_index_config_applied(config_with_valid_distribution, traded_bases) is True
        assert get_holdings_ratio_mock.call_count == 2
        get_holdings_ratio_mock.reset_mock()
    
    # Test 7: Holdings outside tolerance range - should return False
    with mock.patch.object(
        trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder,
        "get_holdings_ratio", mock.Mock(side_effect=lambda coin, **kwargs: {
            "BTC": decimal.Decimal("0.68"),  # 60% target + 8% (outside 5% tolerance)
            "ETH": decimal.Decimal("0.32"),  # 40% target - 8% (outside 5% tolerance)
        }.get(coin, decimal.Decimal("0")))
    ) as get_holdings_ratio_mock:
        assert mode._is_index_config_applied(config_with_valid_distribution, traded_bases) is False
        assert get_holdings_ratio_mock.call_count == 1  # only BTC is considered
        get_holdings_ratio_mock.assert_called_once_with("BTC", traded_symbols_only=True)
        get_holdings_ratio_mock.reset_mock()
    
    # Test 8: Missing coin in portfolio - should return False
    with mock.patch.object(
        trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder,
        "get_holdings_ratio", mock.Mock(side_effect=lambda coin, **kwargs: {
            "BTC": decimal.Decimal("0.6"),  # 60% target
            "ETH": decimal.Decimal("0"),     # Missing ETH
        }.get(coin, decimal.Decimal("0")))
    ) as get_holdings_ratio_mock:
        assert mode._is_index_config_applied(config_with_valid_distribution, traded_bases) is False
        assert get_holdings_ratio_mock.call_count == 2
        get_holdings_ratio_mock.reset_mock()
    
    # Test 9: Too much of a coin in portfolio - should return False
    with mock.patch.object(
        trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder,
        "get_holdings_ratio", mock.Mock(side_effect=lambda coin, **kwargs: {
            "BTC": decimal.Decimal("0.6"),  # 60% target: OK
            "ETH": decimal.Decimal("0.3"),  # 40% target - 10% (too little)
        }.get(coin, decimal.Decimal("0")))
    ) as get_holdings_ratio_mock:
        assert mode._is_index_config_applied(config_with_valid_distribution, traded_bases) is False
        assert get_holdings_ratio_mock.call_count == 2  # BTC and ETH considered
        assert get_holdings_ratio_mock.mock_calls[0].args[0] == "BTC"
        assert get_holdings_ratio_mock.mock_calls[1].args[0] == "ETH"
        get_holdings_ratio_mock.reset_mock()
    
    # Test 10a: Custom rebalance trigger ratio in config from REBALANCE_TRIGGER_MIN_PERCENT
    config_with_custom_trigger = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 50
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "ETH",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 50
            }
        ],
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT: 10.0  # 10% tolerance
    }
    
    # Holdings within 10% tolerance
    with mock.patch.object(
        trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder,
        "get_holdings_ratio", mock.Mock(side_effect=lambda coin, **kwargs: {
            "BTC": decimal.Decimal("0.57"),  # 50% target + 7% (within 10% tolerance)
            "ETH": decimal.Decimal("0.43"),  # 50% target - 7% (within 10% tolerance)
        }.get(coin, decimal.Decimal("0")))
    ) as get_holdings_ratio_mock:
        assert mode._is_index_config_applied(config_with_custom_trigger, traded_bases) is True
        assert get_holdings_ratio_mock.call_count == 2
        get_holdings_ratio_mock.reset_mock()
    
    # Holdings outside 10% tolerance
    with mock.patch.object(
        trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder,
        "get_holdings_ratio", mock.Mock(side_effect=lambda coin, **kwargs: {
            "BTC": decimal.Decimal("0.65"),  # 50% target + 15% (outside 10% tolerance)
            "ETH": decimal.Decimal("0.35"),  # 50% target - 15% (outside 10% tolerance)
        }.get(coin, decimal.Decimal("0")))
    ) as get_holdings_ratio_mock:
        assert mode._is_index_config_applied(config_with_custom_trigger, traded_bases) is False
        assert get_holdings_ratio_mock.call_count == 1  # only BTC is considered
        get_holdings_ratio_mock.assert_called_once_with("BTC", traded_symbols_only=True)
        get_holdings_ratio_mock.reset_mock()
    
    # Test 10b: Custom rebalance trigger ratio in config from REBALANCE_TRIGGER_MIN_PERCENT
    config_with_custom_trigger = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 50
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "ETH",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 50
            }
        ],
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES: [
            {
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile-1",
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 10.0  # 10% tolerance
            }
        ],
        index_trading.IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE: "profile-1",
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT: 99.0  # 99% tolerance
    }
    
    # Holdings within 10% tolerance (profile 1)
    with mock.patch.object(
        trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder,
        "get_holdings_ratio", mock.Mock(side_effect=lambda coin, **kwargs: {
            "BTC": decimal.Decimal("0.57"),  # 50% target + 7% (within 10% tolerance)
            "ETH": decimal.Decimal("0.43"),  # 50% target - 7% (within 10% tolerance)
        }.get(coin, decimal.Decimal("0")))
    ) as get_holdings_ratio_mock:
        assert mode._is_index_config_applied(config_with_custom_trigger, traded_bases) is True
        assert get_holdings_ratio_mock.call_count == 2
        get_holdings_ratio_mock.reset_mock()
    
    # Holdings outside 10% tolerance (profile 1)
    with mock.patch.object(
        trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder,
        "get_holdings_ratio", mock.Mock(side_effect=lambda coin, **kwargs: {
            "BTC": decimal.Decimal("0.65"),  # 50% target + 15% (outside 10% tolerance)
            "ETH": decimal.Decimal("0.35"),  # 50% target - 15% (outside 10% tolerance)
        }.get(coin, decimal.Decimal("0")))
    ) as get_holdings_ratio_mock:
        assert mode._is_index_config_applied(config_with_custom_trigger, traded_bases) is False
        assert get_holdings_ratio_mock.call_count == 1  # only BTC is considered
        get_holdings_ratio_mock.assert_called_once_with("BTC", traded_symbols_only=True)
        get_holdings_ratio_mock.reset_mock()
    
    # Test 11: Mixed traded and non-traded assets
    config_with_mixed_assets = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "BTC",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 60
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "ETH",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 30
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "NON_TRADED_COIN",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 10
            }
        ]
    }
    
    # Should only consider traded assets (BTC and ETH)
    with mock.patch.object(
        trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder,
        "get_holdings_ratio", mock.Mock(side_effect=lambda coin, **kwargs: {
            "BTC": decimal.Decimal("0.6666666666666666666666666667"),  # 60/90 = 66.67%
            "ETH": decimal.Decimal("0.3333333333333333333333333333"),  # 30/90 = 33.33%
        }.get(coin, decimal.Decimal("0")))
    ) as get_holdings_ratio_mock:
        assert mode._is_index_config_applied(config_with_mixed_assets, traded_bases) is False
        get_holdings_ratio_mock.assert_not_called()
    
    # Test 12: All assets non-traded
    config_all_non_traded = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: [
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "NON_TRADED_1",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 50
            },
            {
                index_trading.index_distribution.DISTRIBUTION_NAME: "NON_TRADED_2",
                index_trading.index_distribution.DISTRIBUTION_VALUE: 50
            }
        ]
    }
    assert mode._is_index_config_applied(config_all_non_traded, traded_bases) is False
    
    # Test 13: Zero holdings for all coins
    with mock.patch.object(
        trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder,
        "get_holdings_ratio", mock.Mock(return_value=decimal.Decimal("0"))
    ) as get_holdings_ratio_mock:
        assert mode._is_index_config_applied(config_with_valid_distribution, traded_bases) is False
        assert get_holdings_ratio_mock.call_count == 1  # only BTC considered
        get_holdings_ratio_mock.assert_called_once_with("BTC", traded_symbols_only=True)
        get_holdings_ratio_mock.reset_mock()


@pytest.mark.parametrize("trading_tools", ["spot", "futures"], indirect=True)
async def test_get_config_min_ratio(trading_tools):
    mode, producer, consumer, trader = await _init_mode(trading_tools, _get_config(trading_tools, {}))
    # 1. With selected profile
    config_with_profiles = {
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES: [
            {
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile-1",
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 7.5,
            },
            {
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile-2",
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 15.0,
            },
        ],
        index_trading.IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE: "profile-2",
    }
    # Should pick 15.0% from profile-2
    assert mode._get_config_min_ratio(config_with_profiles) == decimal.Decimal("0.15")

    # 2. With direct config value only
    config_with_direct = {
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT: 3.3
    }
    # Should pick 3.3% from direct config
    assert mode._get_config_min_ratio(config_with_direct) == decimal.Decimal("0.033")

    # 3. With neither, should fall back to mode.rebalance_trigger_min_ratio
    mode.rebalance_trigger_min_ratio = decimal.Decimal("0.123")
    config_empty = {}
    assert mode._get_config_min_ratio(config_empty) == decimal.Decimal("0.123")

    # 4. With profiles but no selected profile matches, should fall back to direct config
    config_profiles_no_match = {
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES: [
            {
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile-1",
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 7.5,
            }
        ],
        index_trading.IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE: "profile-x",
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT: 2.2
    }
    assert mode._get_config_min_ratio(config_profiles_no_match) == decimal.Decimal("0.022")
