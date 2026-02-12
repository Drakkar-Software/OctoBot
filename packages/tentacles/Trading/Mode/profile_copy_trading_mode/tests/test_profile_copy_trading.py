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
import os.path
import datetime
import pytest
import pytest_asyncio
import decimal
import mock

import async_channel.util as channel_util

import octobot_commons.tests.test_config as test_config
import octobot_commons.constants as commons_constants

import octobot_backtesting.api as backtesting_api

import octobot_tentacles_manager.api as tentacles_manager_api

import octobot_trading.api as trading_api
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.exchanges as exchanges
import octobot_trading.enums as trading_enums

import tentacles.Trading.Mode as Mode
import tentacles.Trading.Mode.profile_copy_trading_mode.profile_copy_trading as profile_copy_trading
import tentacles.Trading.Mode.profile_copy_trading_mode.profile_distribution as profile_distribution
import tentacles.Trading.Mode.index_trading_mode.index_distribution as index_distribution
import tentacles.Trading.Mode.index_trading_mode.index_trading as index_trading

import tests.test_utils.config as test_utils_config
import tests.test_utils.test_exchanges as test_exchanges

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

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

    mode = Mode.ProfileCopyTradingMode(config, exchange_manager)
    mode.symbol = None if mode.get_is_symbol_wildcard() else symbol
    # trading mode is not initialized: to be initialized with the required config in tests

    # add mode to exchange manager so that it can be stopped and freed from memory
    exchange_manager.trading_modes.append(mode)

    # set BTC/USDT price at 1000 USDT
    trading_api.force_set_mark_price(exchange_manager, symbol, 1000)

    return mode, trader


async def test_validate_portfolio_allocation_feasibility_valid_cases(tools):
    mode, trader = tools
    
    # Single profile at 100%
    mode.per_exchange_profile_portfolio_ratio = decimal.Decimal("1.0")
    mode.exchange_profile_ids = ["profile1"]
    mode._validate_portfolio_allocation_feasibility()
    
    # Multiple profiles totaling 100%
    mode.per_exchange_profile_portfolio_ratio = decimal.Decimal("0.5")
    mode.exchange_profile_ids = ["profile1", "profile2"]
    mode._validate_portfolio_allocation_feasibility()
    
    # Multiple profiles totaling less than 100%
    mode.per_exchange_profile_portfolio_ratio = decimal.Decimal("0.3")
    mode.exchange_profile_ids = ["profile1", "profile2", "profile3"]
    mode._validate_portfolio_allocation_feasibility()
    
    # Under allocation
    mode.per_exchange_profile_portfolio_ratio = decimal.Decimal("0.1")
    mode.exchange_profile_ids = ["profile1"]
    mode._validate_portfolio_allocation_feasibility()

    # update_global_distribution should convert reserved reference market ratio to tradable ratio
    mode.per_exchange_profile_portfolio_ratio = decimal.Decimal("0.45")
    mode.exchange_profile_ids = ["profile1", "profile2"]
    mode.distribution_per_exchange_profile = {
        "profile1": {
            profile_distribution.DISTRIBUTION_KEY: [
                {
                    index_distribution.DISTRIBUTION_NAME: "BTC/USDT",
                    index_distribution.DISTRIBUTION_VALUE: 100.0,
                }
            ],
            profile_distribution.TRADABLE_RATIO: decimal.Decimal("1"),
        },
        "profile2": {
            profile_distribution.DISTRIBUTION_KEY: [
                {
                    index_distribution.DISTRIBUTION_NAME: "ETH/USDT",
                    index_distribution.DISTRIBUTION_VALUE: 100.0,
                }
            ],
            profile_distribution.TRADABLE_RATIO: decimal.Decimal("1"),
        },
    }
    mode.update_global_distribution()
    assert mode.reference_market_ratio == decimal.Decimal("0.9")


async def test_validate_portfolio_allocation_feasibility_invalid_cases(tools):
    mode, trader = tools
    
    # Single profile over 100%
    mode.per_exchange_profile_portfolio_ratio = decimal.Decimal("1.1")
    mode.exchange_profile_ids = ["profile1"]
    with pytest.raises(ValueError) as exc_info:
        mode._validate_portfolio_allocation_feasibility()
    assert "Total portfolio allocation exceeds 100%" in str(exc_info.value)
    assert "110.00%" in str(exc_info.value)
    
    # Multiple profiles totaling over 100% (2 profiles at 60% each = 120%)
    mode.per_exchange_profile_portfolio_ratio = decimal.Decimal("0.6")
    mode.exchange_profile_ids = ["profile1", "profile2"]
    with pytest.raises(ValueError) as exc_info:
        mode._validate_portfolio_allocation_feasibility()
    assert "Total portfolio allocation exceeds 100%" in str(exc_info.value)
    assert "120.00%" in str(exc_info.value)
    assert "2 profiles" in str(exc_info.value)
    
    # Many profiles totaling over 100% (5 profiles at 25% each = 125%)
    mode.per_exchange_profile_portfolio_ratio = decimal.Decimal("0.25")
    mode.exchange_profile_ids = ["profile1", "profile2", "profile3", "profile4", "profile5"]
    with pytest.raises(ValueError) as exc_info:
        mode._validate_portfolio_allocation_feasibility()
    assert "Total portfolio allocation exceeds 100%" in str(exc_info.value)
    assert "125.00%" in str(exc_info.value)
    assert "5 profiles" in str(exc_info.value)


async def test_validate_portfolio_allocation_feasibility_edge_cases(tools):
    mode, trader = tools
    
    mode.per_exchange_profile_portfolio_ratio = decimal.Decimal("0.25")
    mode.exchange_profile_ids = ["profile1", "profile2", "profile3", "profile4"]
    mode._validate_portfolio_allocation_feasibility()
    
    # Empty profiles list (0% total allocation)
    mode.per_exchange_profile_portfolio_ratio = decimal.Decimal("1.0")
    mode.exchange_profile_ids = []
    mode._validate_portfolio_allocation_feasibility()


async def test_init_user_inputs_validates_portfolio_allocation_invalid(tools):
    mode, producer, consumer, trader = await _init_mode(tools, _get_config(tools, {}))
    
    # Set invalid values in trading_config and call init_user_inputs explicitly
    mode.trading_config[profile_copy_trading.ProfileCopyTradingModeProducer.EXCHANGE_PROFILE_IDS] = ["profile1", "profile2"]
    mode.trading_config[profile_copy_trading.ProfileCopyTradingModeProducer.PER_PROFILE_PORTFOLIO_RATIO] = 60.0  # 60% per profile * 2 = 120% total (invalid)
    
    with pytest.raises(ValueError) as exc_info:
        mode.init_user_inputs({})
    
    assert "Total portfolio allocation exceeds 100%" in str(exc_info.value)
    assert "120.00%" in str(exc_info.value)


async def test_init_user_inputs_validates_portfolio_allocation_valid(tools):
    mode, producer, consumer, trader = await _init_mode(tools, _get_config(tools, {
        profile_copy_trading.ProfileCopyTradingModeProducer.EXCHANGE_PROFILE_IDS: ["profile1", "profile2"],
        profile_copy_trading.ProfileCopyTradingModeProducer.PER_PROFILE_PORTFOLIO_RATIO: 50.0,  # 50% per profile * 2 = 100% total (valid)
    }))
    
    # init_user_inputs is called during _init_mode, values should be set correctly
    assert mode.exchange_profile_ids == ["profile1", "profile2"]
    assert mode.per_exchange_profile_portfolio_ratio == decimal.Decimal("0.5")
    
    # Can also call init_user_inputs again to refresh
    mode.init_user_inputs({})
    assert mode.exchange_profile_ids == ["profile1", "profile2"]
    assert mode.per_exchange_profile_portfolio_ratio == decimal.Decimal("0.5")


def _get_config(tools, update):
    mode, trader = tools
    config = tentacles_manager_api.get_tentacle_config(trader.exchange_manager.tentacles_setup_config, mode.__class__)
    return {**config, **update}


async def _init_mode(tools, config):
    mode, trader = tools
    await mode.initialize(trading_config=config)
    return mode, mode.producers[0], mode.get_trading_mode_consumers()[0], trader


async def _stop(exchange_manager):
    for importer in backtesting_api.get_importers(exchange_manager.exchange.backtesting):
        await backtesting_api.stop_importer(importer)
    await exchange_manager.exchange.backtesting.stop()
    await exchange_manager.stop()


async def test_init_sets_defaults_for_new_position_only_and_started_at(tools):
    mode, trader = tools
    
    assert mode.new_position_only is False
    assert isinstance(mode.started_at, datetime.datetime)
    # started_at should be set to current time (approximately)
    assert (datetime.datetime.now() - mode.started_at).total_seconds() < 5

async def test_rebalance_with_pending_open_orders(tools):
    mode, producer, _, _ = await _init_mode(tools, _get_config(tools, {}))
    mode.indexed_coins = ["BTC"]
    mode.ratio_per_asset = {
        "BTC": {
            index_distribution.DISTRIBUTION_NAME: "BTC",
            index_distribution.DISTRIBUTION_VALUE: decimal.Decimal("100"),
        }
    }
    mode.total_ratio_per_asset = decimal.Decimal("100")
    mode.reference_market_ratio = decimal.Decimal("1")
    mode.quote_asset_rebalance_ratio_threshold = decimal.Decimal("0.1")
    mode.rebalance_trigger_min_ratio = decimal.Decimal("0.05")

    def _fake_get_holdings_ratio(currency, traded_symbols_only=False, include_assets_in_open_orders=False, coins_whitelist=None):
        if currency == "BTC":
            return decimal.Decimal("1")
        if currency == "USDT":
            return decimal.Decimal("0") if include_assets_in_open_orders else decimal.Decimal("0.2")
        return decimal.Decimal("0")

    with mock.patch.object(producer, "get_holdings_ratio", mock.Mock(side_effect=_fake_get_holdings_ratio)):
        should_rebalance, details = producer._get_rebalance_details()
    # Without open orders we should have rebalanced
    # As we have open orders using USDT, the rebalance should not be triggered as the current ratio is 0.2 which is above the threshold of 0.1
    assert should_rebalance is False
    assert details[index_trading.RebalanceDetails.FORCED_REBALANCE.value] is False
