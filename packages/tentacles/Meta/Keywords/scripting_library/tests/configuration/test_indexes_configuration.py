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
import octobot_commons.profiles.profile_data as commons_profile_data
import octobot_commons.constants as commons_constants

import tentacles.Trading.Mode.index_trading_mode.index_trading as index_trading
import tentacles.Trading.Mode.index_trading_mode.index_distribution as index_distribution
import tentacles.Meta.Keywords.scripting_library.configuration.indexes_configuration as indexes_configuration


def test_create_index_config_from_tentacles_config():
    # Create test distribution
    distribution = [
        {
            index_distribution.DISTRIBUTION_NAME: "BTC",
            index_distribution.DISTRIBUTION_VALUE: 50.0,
        },
        {
            index_distribution.DISTRIBUTION_NAME: "ETH",
            index_distribution.DISTRIBUTION_VALUE: 30.0,
        },
        {
            index_distribution.DISTRIBUTION_NAME: "USD",  # Should be replaced by reference market
            index_distribution.DISTRIBUTION_VALUE: 20.0,
        },
    ]
    
    # Create test trading mode config
    trading_mode_config = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: distribution,
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT: 5.0,
        index_trading.IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE: "test_profile",
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES: [
            {
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "test_profile",
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 5.0,
            }
        ],
    }
    
    # Create tentacles config
    tentacles_config = [
        commons_profile_data.TentaclesData(
            name=index_trading.IndexTradingMode.get_name(),
            config=trading_mode_config
        )
    ]
    
    # Test parameters
    exchange = "binance"
    starting_funds = 10000.0
    backtesting_start_time_delta = 86400.0  # 1 day in seconds
    
    # Call the function
    result = indexes_configuration.create_index_config_from_tentacles_config(
        tentacles_config, exchange, starting_funds, backtesting_start_time_delta
    )
    
    # Assertions
    assert isinstance(result, commons_profile_data.ProfileData)
    assert result.profile_details.name == "serverless"
    assert result.trading.reference_market == "USDC"  # binance default
    assert result.trading.risk == 0.5
    assert len(result.exchanges) == 1
    assert result.exchanges[0].internal_name == exchange
    assert result.exchanges[0].exchange_type == commons_constants.CONFIG_EXCHANGE_SPOT
    
    # Check currencies (BTC and ETH, not USD which should be replaced by reference market)
    assert len(result.crypto_currencies) == 2
    trading_pairs = {curr.name: curr.trading_pairs for curr in result.crypto_currencies}
    assert ["BTC/USDC"] == trading_pairs["BTC"]
    assert ["ETH/USDC"] == trading_pairs["ETH"]
    
    # Check trader settings
    assert result.trader.enabled is True
    
    # Check tentacles config
    assert len(result.tentacles) == 1
    assert result.tentacles[0].name == index_trading.IndexTradingMode.get_name()
    assert index_trading.IndexTradingModeProducer.INDEX_CONTENT in result.tentacles[0].config
    
    # Check that USD was replaced by reference market in distribution
    distribution_names = [
        item[index_distribution.DISTRIBUTION_NAME] 
        for item in result.tentacles[0].config[index_trading.IndexTradingModeProducer.INDEX_CONTENT]
    ]
    assert "USD" not in distribution_names
    assert "USDC" in distribution_names  # binance's reference market
    
    # Check backtesting config
    assert result.backtesting_context is not None
    assert [exchange] == result.backtesting_context.exchanges
    assert result.backtesting_context.start_time_delta == backtesting_start_time_delta
    assert {"USDC": starting_funds} == result.backtesting_context.starting_portfolio


def test_generate_index_config():
    # Create test distribution
    distribution = [
        {
            index_distribution.DISTRIBUTION_NAME: "BTC",
            index_distribution.DISTRIBUTION_VALUE: 50.0,
        },
        {
            index_distribution.DISTRIBUTION_NAME: "ETH",
            index_distribution.DISTRIBUTION_VALUE: 30.0,
        },
        {
            index_distribution.DISTRIBUTION_NAME: "USDT",
            index_distribution.DISTRIBUTION_VALUE: 20.0,
        },
    ]
    
    # Test parameters
    rebalance_cap = 5.0
    selected_rebalance_trigger_profile = "profile1"
    rebalance_trigger_profiles = [
        {
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile1",
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 5.0,
        },
        {
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "profile2",
            index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 10.0,
        },
    ]
    reference_market = "USDT"
    exchange = "binance"
    min_funds = 1000.0
    coins_by_symbol = {
        "BTC": "BTC",
        "ETH": "ETH",
        "USDT": "USDT",
    }
    disabled_backtesting = False
    backtesting_start_time_delta = 172800.0  # 2 days in seconds
    
    # Call the function
    result = indexes_configuration.generate_index_config(
        distribution, rebalance_cap, selected_rebalance_trigger_profile, 
        rebalance_trigger_profiles, reference_market, exchange, min_funds, 
        coins_by_symbol, disabled_backtesting, backtesting_start_time_delta
    )
    
    # Assertions - check that result is a dict
    assert isinstance(result, dict)
    
    # Check profile details
    assert "profile_details" in result
    assert result["profile_details"]["name"] == "serverless"
    
    # Check trading config
    assert "trading" in result
    assert result["trading"]["reference_market"] == reference_market
    assert result["trading"]["risk"] == 0.5
    
    # Check exchanges
    assert "exchanges" in result
    assert len(result["exchanges"]) == 1
    assert result["exchanges"][0]["internal_name"] == exchange
    
    # Check crypto currencies (should not include reference market)
    assert "crypto_currencies" in result
    assert len(result["crypto_currencies"]) == 2  # BTC and ETH, not USDT (reference market)
    trading_pairs = {curr["name"]: curr["trading_pairs"] for curr in result["crypto_currencies"]}
    assert ["BTC/USDT"] == trading_pairs["BTC"]
    assert ["ETH/USDT"] == trading_pairs["ETH"]
    
    # Check trader
    assert "trader" in result
    assert result["trader"]["enabled"] is True
    
    # Check tentacles
    assert "tentacles" in result
    assert len(result["tentacles"]) == 1
    tentacle_config = result["tentacles"][0]
    assert tentacle_config["name"] == index_trading.IndexTradingMode.get_name()
    assert "config" in tentacle_config
    
    # Check index trading config
    config = tentacle_config["config"]
    assert config[index_trading.IndexTradingModeProducer.INDEX_CONTENT] == distribution
    assert config[index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT] == rebalance_cap
    assert config[index_trading.IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE] == selected_rebalance_trigger_profile
    assert config[index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES] == rebalance_trigger_profiles
    assert config[index_trading.IndexTradingModeProducer.SYNCHRONIZATION_POLICY] == index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE.value
    assert config[index_trading.IndexTradingModeProducer.SELL_UNINDEXED_TRADED_COINS] is True
    assert config[index_trading.IndexTradingModeProducer.REFRESH_INTERVAL] == 1
    
    # Check backtesting config
    assert "backtesting_context" in result
    backtesting = result["backtesting_context"]
    assert backtesting["exchanges"] == [exchange]
    assert backtesting["start_time_delta"] == backtesting_start_time_delta
    assert {"USDT": min_funds * 10} == backtesting["starting_portfolio"]
    
    # Test with disabled backtesting
    result_no_backtesting = indexes_configuration.generate_index_config(
        distribution, rebalance_cap, selected_rebalance_trigger_profile,
        rebalance_trigger_profiles, reference_market, exchange, min_funds,
        coins_by_symbol, True, backtesting_start_time_delta
    )
    assert "exchanges" not in result_no_backtesting["backtesting_context"]
