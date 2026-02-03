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
import tentacles.Trading.Mode.index_trading_mode.index_trading as index_trading

import octobot_commons.constants as commons_constants
import octobot_commons.profiles.profile_data as commons_profile_data
import tentacles.Meta.Keywords.scripting_library as scripting_library



def test_register_historical_configs_adds_traded_pairs():
    # Master has no traded pairs, historical has one
    master = scripting_library.minimal_profile_data()
    tentacle_name = "TestTentacle"
    master.tentacles = [commons_profile_data.TentaclesData(name=tentacle_name, config={})]
    # Historical profile with a traded pair
    historical = scripting_library.minimal_profile_data()
    historical.tentacles = [commons_profile_data.TentaclesData(name=tentacle_name, config={})]
    scripting_library.add_traded_symbols(historical, ["BTC/USDT"])
    historicals = {1000.0: historical}
    assert [] == scripting_library.get_traded_symbols(master)
    scripting_library.register_historical_configs(master, historicals, True, False)
    # Master should now have the traded pair
    assert ["BTC/USDT"] == scripting_library.get_traded_symbols(master)


def test_register_historical_configs_registers_historical_tentacle_config():
    # Master and historical have different tentacle config dicts
    master = scripting_library.minimal_profile_data()
    tentacle_name = "TestTentacle"
    master_config = {"foo": 1}
    master.tentacles = [commons_profile_data.TentaclesData(name=tentacle_name, config=master_config)]
    historical_1 = scripting_library.minimal_profile_data()
    hist_config_1 = {"foo": 2}
    historical_1.tentacles = [commons_profile_data.TentaclesData(name=tentacle_name, config=hist_config_1)]
    historical_2 = scripting_library.minimal_profile_data()
    hist_config_2 = {"foo": 3}
    historical_2.tentacles = [commons_profile_data.TentaclesData(name=tentacle_name, config=hist_config_2)]
    historicals = {1000.0: historical_1, 2000.0: historical_2}
    scripting_library.register_historical_configs(master, historicals, False, False)
    # Master config should now have a historical config registered
    assert commons_constants.CONFIG_HISTORICAL_CONFIGURATION in master_config
    assert len(master_config[commons_constants.CONFIG_HISTORICAL_CONFIGURATION]) == 2
    assert master_config[commons_constants.CONFIG_HISTORICAL_CONFIGURATION][0][0] == 2000.0
    assert master_config[commons_constants.CONFIG_HISTORICAL_CONFIGURATION][0][1] == hist_config_2
    assert master_config[commons_constants.CONFIG_HISTORICAL_CONFIGURATION][1][0] == 1000.0
    assert master_config[commons_constants.CONFIG_HISTORICAL_CONFIGURATION][1][1] == hist_config_1


def test_register_historical_configs_applies_master_edits():
    # Master has a config with a special field, historical does not
    master = scripting_library.minimal_profile_data()
    tentacle_name = "TestTentacle"
    special_key = "special"
    master_config = {
        special_key: 42, 
        index_trading.IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE: "plop1", 
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES: [
            {
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "plop1",
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 4
            },
            {
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "plop2",
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 20
            }
        ], 
        index_trading.IndexTradingModeProducer.SYNCHRONIZATION_POLICY: index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE.value
    }
    master.tentacles = [commons_profile_data.TentaclesData(name=tentacle_name, config=master_config)]
    historical_1 = scripting_library.minimal_profile_data()
    hist_config_1 = {}
    historical_1.tentacles = [commons_profile_data.TentaclesData(name=tentacle_name, config=hist_config_1)]
    historical_2 = scripting_library.minimal_profile_data()
    hist_config_2 = {special_key: 1}
    historical_2.tentacles = [commons_profile_data.TentaclesData(name=tentacle_name, config=hist_config_2)]
    historicals = {1000.0: historical_1, 2000.0: historical_2}

    scripting_library.register_historical_configs(master, historicals, False, True)
    # no update as tentacle_name is not configurable tentacles and config keys
    assert hist_config_1 == {}
    assert hist_config_2 == {special_key: 1}

    # now using IndexTradingMode: a whitelisted tentacle
    for profile_data in (master, historical_1, historical_2):
        profile_data.tentacles[0].name = index_trading.IndexTradingMode.get_name()

    scripting_library.register_historical_configs(master, historicals, False, True)
    # configurable tentacles abd config keys are applied to historical configs
    assert hist_config_1 == {
        index_trading.IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE: "plop1",
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES: [
            {
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "plop1",
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 4
            },
            {
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "plop2",
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 20
            }
        ], 
        index_trading.IndexTradingModeProducer.SYNCHRONIZATION_POLICY: index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE.value
    }
    assert hist_config_2 == {
        special_key: 1, 
        index_trading.IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE: "plop1",
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES: [
            {
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "plop1",
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 4
            },
            {
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "plop2",
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 20
            }
        ], 
        index_trading.IndexTradingModeProducer.SYNCHRONIZATION_POLICY: index_trading.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE.value
    }
