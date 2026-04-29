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
#  License along with this library.*
import copy

import pytest

import octobot_commons.profiles as profiles
import octobot_commons.profiles.profile_data as profile_data_import
import octobot_commons.constants as constants
import octobot_commons.enums as enums

from tests.profiles import get_profile_path, profile


@pytest.fixture
def profile_data_dict():
    return {
        'distribution': 'not_default',
        'profile_details': {
            'name': 'profile_name 42',
            'id': 'default',
            'version': "42.42.1b",
            'bot_id': "1234-1224-0000",
            'user_id': "plop-id",
            'nested_strategy_config_id': "123-1221"
        },
        'crypto_currencies': [
            {
                'trading_pairs': ['BTC/USDT'],
                'name': 'Bitcoin',
                'enabled': True
            },
            {
                'trading_pairs': ['ETH/USDT'],
                'name': 'ETH',
                'enabled': False
            }
        ], 'exchanges': [
            {
                'exchange_credential_id': '123-plop',
                'exchange_id': '123-exchange',
                'exchange_account_id': '123-exchange_account_id',
                'exchange_type': 'spot',
                'internal_name': 'cryptocom',
                'sandboxed': True,
            }
        ], 'future_exchange_data': {
            'default_leverage': 10,
            'symbol_data': [
                {
                    'symbol': 'BTC/USDT',
                    'leverage': None,
                },
                {
                    'symbol': 'ETH/USDT',
                    'leverage': 5,
                }
            ]
        }, 'trader': {
            'enabled': True
        }, 'trader_simulator': {
            'enabled': False,
            'starting_portfolio': {
                'BTC': 10,
                'USDT': 1000
            },
            'maker_fees': 0.1,
            'taker_fees': 0.1
        }, 'trading': {
            'reference_market': 'BTC',
            'paused': False,
            'minimal_funds': [
                {
                    "asset": "BTC",
                    "available": 12,
                    "total": 12,
                },
                {
                    "asset": "PLOP",
                    "available": 0.1111,
                    "total": 0.2222,
                }
            ],
            'sub_portfolio': {
                "BTC": 0.1,
                "USDT": 1000
            },
            'risk': 0.5,
            'sellable_assets': ["BTC", "ETH"]
        }, 'tentacles': [
            {
                'name': 'plopEvaluator',
                'config': {},
            },
            {
                'name': 'plopEvaluator',
                'config': {
                    'a': True,
                    'other': {
                        'l': [1, 2],
                        'n': None,
                    }
                },
            },
        ], 'options': {
            'values': {
                'plop_key': 'hola senior'
            }
        }, 'backtesting_context': {
            'start_time_delta': 11313.22,
            'update_interval': 444,
            'starting_portfolio': {
                'plop_key': 'hola senior'
            },
            'exchanges': [
                'binance', 'kucoin'
            ]
        }
    }


@pytest.fixture
def min_profile_data_dict():
    return {
        'profile_details': {
            'name': 'min_profile',
        },
        'crypto_currencies': [
            {
                'trading_pairs': ['BTC/USDT'],
            },
            {
                'trading_pairs': ['ETH/USDT'],
                'enabled': False
            }
        ], 'trading': {
            'reference_market': 'BTC',
        }, 'tentacles': [
            {
                'name': 'plopEvaluator',
                'config': {},
            },
            {
                'name': 'plopEvaluator',
                'config': {
                    'a': True,
                    'other': {
                        'l': [1, 2],
                        'n': None,
                    }
                },
            },
        ],
        'backtesting_context': {
            'start_time_delta': 11313.22
        }, 'options': {
            'values': {
                'plop_key': 'hola !!!',
                'jour': 'nuit',
            }
        }
    }


def test_from_profile(profile):
    profile_data = profiles.ProfileData.from_profile(profile.read_config())
    # check one element per attribute to be sure it's all parsed
    assert profile_data.distribution == "default"
    assert profile_data.profile_details.name == "default"
    assert profile_data.crypto_currencies[0].trading_pairs == ['BTC/USDT']
    assert profile_data.exchanges == []
    assert profile_data.trader.enabled is False
    assert profile_data.trader_simulator.enabled is True
    assert profile_data.trader_simulator.starting_portfolio == {'BTC': 10, 'USDT': 1000}
    assert profile_data.trading.risk == 0.5
    assert profile_data.tentacles == []


def test_to_profile(profile):
    profile_data = profiles.ProfileData.from_profile(profile.read_config())
    created_profile = profile_data.to_profile("plop_path")
    # force missing values
    for crypto_data in profile.config[constants.CONFIG_CRYPTO_CURRENCIES].values():
        crypto_data[constants.CONFIG_ENABLED_OPTION] = crypto_data.get(constants.CONFIG_ENABLED_OPTION, True)
    # remove not stored values
    profile.config[constants.CONFIG_EXCHANGES] = {}
    profile.avatar = profile.description = ""
    profile.complexity = enums.ProfileComplexity.MEDIUM
    profile.risk = enums.ProfileRisk.MODERATE
    profile.profile_type = enums.ProfileType.LIVE
    profile.origin_url = None
    # if both parsing and transforming return the same profile as original one, the whole chain works
    profile_dict = profile.as_dict()
    assert profile_dict == created_profile.as_dict()


def test_from_dict(profile_data_dict):
    # use second MinimalFund syntax
    profile_data_dict = copy.deepcopy(profile_data_dict)
    profile_data_dict["trading"]['minimal_funds'].append(
        {
            "asset": "ETH",
            "value": 111.2,
        }
    )
    profile_data = profiles.ProfileData.from_dict(profile_data_dict)
    # check one element per attribute to be sure it's all parsed
    assert profile_data.profile_details.name == "profile_name 42"
    assert profile_data.crypto_currencies[0].trading_pairs == ['BTC/USDT']
    assert profile_data.distribution == "not_default"
    assert profile_data.future_exchange_data.default_leverage == 10
    assert profile_data.future_exchange_data.symbol_data[0].symbol == "BTC/USDT"
    assert profile_data.future_exchange_data.symbol_data[0].leverage == None
    assert profile_data.future_exchange_data.symbol_data[1].symbol == "ETH/USDT"
    assert profile_data.future_exchange_data.symbol_data[1].leverage == 5
    assert profile_data.exchanges[0].exchange_credential_id == "123-plop"
    assert profile_data.exchanges[0].exchange_account_id == "123-exchange_account_id"
    assert profile_data.exchanges[0].internal_name == "cryptocom"
    assert profile_data.exchanges[0].sandboxed is True
    assert profile_data.exchanges[0].exchange_type == "spot"
    assert profile_data.trader.enabled is True
    assert profile_data.trader_simulator.enabled is False
    assert profile_data.trader_simulator.starting_portfolio == {'BTC': 10, 'USDT': 1000}
    assert profile_data.trading.risk == 0.5
    assert profile_data.trading.minimal_funds == [
        profiles.MinimalFund("BTC", 12, 12),
        profiles.MinimalFund("PLOP", 0.1111, 0.2222),
        profiles.MinimalFund("ETH", 111.2, 111.2),
    ]
    assert profile_data.tentacles[0].name == "plopEvaluator"
    assert profile_data.tentacles[1].config["other"]["l"] == [1, 2]


def test_from_min_dict(min_profile_data_dict):
    profile_data = profiles.ProfileData.from_dict(min_profile_data_dict)
    # check one element per attribute to be sure it's all parsed
    assert profile_data.profile_details.name == "min_profile"
    assert profile_data.crypto_currencies[0].trading_pairs == ['BTC/USDT']
    assert profile_data.crypto_currencies[0].name is None
    assert profile_data.crypto_currencies[0].enabled is True
    assert profile_data.crypto_currencies[1].trading_pairs == ['ETH/USDT']
    assert profile_data.crypto_currencies[1].name is None
    assert profile_data.crypto_currencies[1].enabled is False
    assert profile_data.future_exchange_data.default_leverage is None
    assert profile_data.future_exchange_data.symbol_data == []
    assert profile_data.exchanges == []
    assert profile_data.trader.enabled is True
    assert profile_data.trader_simulator.enabled is False
    assert profile_data.trader_simulator.starting_portfolio == {}
    assert profile_data.trading.risk == 1
    assert profile_data.tentacles[0].name == "plopEvaluator"
    assert profile_data.tentacles[1].config["other"]["l"] == [1, 2]
    assert profile_data.options.values["jour"] == "nuit"
    assert profile_data.options.values["plop_key"] == "hola !!!"
    assert profile_data.distribution == constants.DEFAULT_DISTRIBUTION
    full_profile_data_dict = profile_data.to_dict(include_default_values=True)
    assert len(full_profile_data_dict) > len(min_profile_data_dict)
    profile_data_dict = profile_data.to_dict(include_default_values=False)
    # default values in values but: keys are present except for exchanges & distribution, which content is empty (default)
    full_profile_data_dict_keys_without_exchange = list(full_profile_data_dict.keys())
    full_profile_data_dict_keys_without_exchange.remove("exchanges")
    full_profile_data_dict_keys_without_exchange.remove("distribution")
    assert sorted(list(profile_data_dict.keys()) + ["_updated_fields", ]) == sorted(full_profile_data_dict_keys_without_exchange)


def test_from_dict_objects(profile_data_dict):
    profile_data_objects = profiles.ProfileData.from_dict(profile_data_dict)
    profile_data = profiles.ProfileData.from_dict({
        "profile_details": profile_data_objects.profile_details,
        "crypto_currencies": profile_data_objects.crypto_currencies,
        "exchanges": profile_data_objects.exchanges,
        "trader": profile_data_objects.trader,
        "trader_simulator": profile_data_objects.trader_simulator,
        "trading": profile_data_objects.trading,
        "tentacles": profile_data_objects.tentacles,
        "options": profile_data_objects.options,
    })
    # check one element per attribute to be sure it's all parsed
    assert profile_data.profile_details.version == "42.42.1b"
    assert profile_data.profile_details.nested_strategy_config_id == "123-1221"
    assert profile_data.crypto_currencies[0].trading_pairs == ['BTC/USDT']
    assert profile_data.exchanges[0].exchange_credential_id == "123-plop"
    assert profile_data.exchanges[0].exchange_account_id == "123-exchange_account_id"
    assert profile_data.trader.enabled is True
    assert profile_data.trader_simulator.enabled is False
    assert profile_data.trader_simulator.starting_portfolio == {'BTC': 10, 'USDT': 1000}
    assert profile_data.trading.risk == 0.5
    assert profile_data.trading.paused is False
    assert profile_data.tentacles[0].name == "plopEvaluator"
    assert profile_data.tentacles[1].config["other"]["l"] == [1, 2]
    assert profile_data.options.values['plop_key'] == 'hola senior'
    assert profile_data.backtesting_context == profile_data_import.BacktestingContext()


def test_to_dict(profile_data_dict):
    profile_data = profiles.ProfileData.from_dict(profile_data_dict)
    # if both parsing and transforming return the same profile as original one, the whole chain works
    assert profile_data_dict == _remove_updated_fields(profile_data.to_dict())

    dict_without_default_values = profile_data.to_dict(include_default_values=False)
    assert profile_data_dict != _remove_updated_fields(dict_without_default_values)

    # ensure no empty elements
    assert len(dict_without_default_values) == len(profile_data_dict)
    for values in dict_without_default_values.values():
        assert len(values)


def test_get_update(profile_data_dict):
    """Test get_update() method with various field changes and edge cases"""
    profile_data_1 = profiles.ProfileData.from_dict(profile_data_dict)
    profile_data_2 = copy.deepcopy(profile_data_1)
    
    # Test simple field changes
    profile_data_2.profile_details.name = "new_profile_name"
    profile_data_2.trading.risk = 0.8
    update = profile_data_1.get_update(profile_data_2)
    assert update.profile_details.name == "new_profile_name"
    assert update.profile_details._updated_fields == ["name"]
    assert update.trading.risk == 0.8
    assert update.trading._updated_fields == ["risk"]
    assert "profile_details" in update._updated_fields
    assert "trading" in update._updated_fields
    
    # Test nested object changes
    profile_data_2.profile_details.version = "1.0.0"
    profile_data_2.trading.reference_market = "USDT"
    update = profile_data_1.get_update(profile_data_2)
    assert set(update.profile_details._updated_fields) == {"name", "version"}
    assert set(update.trading._updated_fields) == {"risk", "reference_market"}
    
    # Test list field changes
    profile_data_2.crypto_currencies[0].enabled = False
    profile_data_2.crypto_currencies[0].trading_pairs = ["BTC/USDT", "ETH/USDT"]
    new_exchange = profile_data_import.ExchangeData(
        exchange_type="futures",
        internal_name="binance",
        sandboxed=False
    )
    profile_data_2.exchanges.append(new_exchange)
    profile_data_2.tentacles[1].config["new_key"] = "new_value"
    update = profile_data_1.get_update(profile_data_2)
    assert update.crypto_currencies[0].enabled is False
    assert update.crypto_currencies[0]._updated_fields == ["trading_pairs", "enabled"]
    assert len(update.exchanges) == len(profile_data_2.exchanges)
    assert update.exchanges[-1].internal_name == "binance"
    assert "crypto_currencies" in update._updated_fields
    assert "exchanges" in update._updated_fields
    assert "tentacles" in update._updated_fields
    
    # Test no changes
    profile_data_3 = copy.deepcopy(profile_data_2)
    update = profile_data_2.get_update(profile_data_3)
    assert update._updated_fields == []
    
    # Test empty to populated
    profile_data_empty = profiles.ProfileData()
    update = profile_data_empty.get_update(profile_data_1)
    assert "profile_details" in update._updated_fields
    assert "crypto_currencies" in update._updated_fields
    assert "trading" in update._updated_fields


def test_update(profile_data_dict):
    """Test update() method with various field changes, lists, and edge cases"""
    # Test simple field updates
    profile_data_1 = profiles.ProfileData.from_dict(profile_data_dict)
    profile_data_2 = copy.deepcopy(profile_data_1)
    profile_data_2.profile_details.name = "updated_name"
    profile_data_2.trading.risk = 0.9
    update = profile_data_1.get_update(profile_data_2)
    original_name = profile_data_1.profile_details.name
    original_risk = profile_data_1.trading.risk
    profile_data_1.update(update)
    assert profile_data_1.profile_details.name == "updated_name"
    assert profile_data_1.trading.risk == 0.9
    assert profile_data_1.profile_details.name != original_name
    assert profile_data_1.trading.risk != original_risk
    
    # Test nested object updates
    profile_data_1 = profiles.ProfileData.from_dict(profile_data_dict)
    profile_data_2 = copy.deepcopy(profile_data_1)
    profile_data_2.profile_details.version = "2.0.0"
    profile_data_2.trader.enabled = False
    profile_data_2.trader_simulator.enabled = True
    profile_data_2.trader_simulator.maker_fees = 0.2
    update = profile_data_1.get_update(profile_data_2)
    profile_data_1.update(update)
    assert profile_data_1.profile_details.version == "2.0.0"
    assert profile_data_1.trader.enabled is False
    assert profile_data_1.trader_simulator.enabled is True
    assert profile_data_1.trader_simulator.maker_fees == 0.2
    
    # Test list element modifications
    profile_data_1 = profiles.ProfileData.from_dict(profile_data_dict)
    profile_data_2 = copy.deepcopy(profile_data_1)
    profile_data_2.crypto_currencies[0].enabled = False
    profile_data_2.crypto_currencies[0].trading_pairs.append("LTC/USDT")
    profile_data_2.exchanges[0].sandboxed = False
    update = profile_data_1.get_update(profile_data_2)
    original_enabled = profile_data_1.crypto_currencies[0].enabled
    profile_data_1.update(update)
    assert profile_data_1.crypto_currencies[0].enabled is False
    assert profile_data_1.crypto_currencies[0].enabled != original_enabled
    assert "LTC/USDT" in profile_data_1.crypto_currencies[0].trading_pairs
    assert profile_data_1.exchanges[0].sandboxed is False
    
    # Test adding list elements
    profile_data_1 = profiles.ProfileData.from_dict(profile_data_dict)
    profile_data_2 = copy.deepcopy(profile_data_1)
    new_crypto = profile_data_import.CryptoCurrencyData(
        trading_pairs=["LTC/USDT"],
        name="Litecoin",
        enabled=True
    )
    profile_data_2.crypto_currencies.append(new_crypto)
    new_tentacle = profile_data_import.TentaclesData(
        name="NewEvaluator",
        config={"key": "value"}
    )
    profile_data_2.tentacles.append(new_tentacle)
    update = profile_data_1.get_update(profile_data_2)
    original_crypto_count = len(profile_data_1.crypto_currencies)
    original_tentacle_count = len(profile_data_1.tentacles)
    profile_data_1.update(update)
    assert len(profile_data_1.crypto_currencies) == original_crypto_count + 1
    assert profile_data_1.crypto_currencies[-1].name == "Litecoin"
    assert len(profile_data_1.tentacles) == original_tentacle_count + 1
    assert profile_data_1.tentacles[-1].name == "NewEvaluator"
    
    # Test removing list elements
    profile_data_1 = profiles.ProfileData.from_dict(profile_data_dict)
    profile_data_2 = copy.deepcopy(profile_data_1)
    profile_data_2.crypto_currencies.pop()
    profile_data_2.tentacles.pop()
    update = profile_data_1.get_update(profile_data_2)
    original_crypto_count = len(profile_data_1.crypto_currencies)
    original_tentacle_count = len(profile_data_1.tentacles)
    profile_data_1.update(update)
    assert len(profile_data_1.crypto_currencies) == original_crypto_count - 1
    assert len(profile_data_1.tentacles) == original_tentacle_count - 1
    
    # Test future exchange data updates
    profile_data_1 = profiles.ProfileData.from_dict(profile_data_dict)
    profile_data_2 = copy.deepcopy(profile_data_1)
    profile_data_2.future_exchange_data.default_leverage = 20
    profile_data_2.future_exchange_data.symbol_data[0].leverage = 15
    update = profile_data_1.get_update(profile_data_2)
    original_leverage = profile_data_1.future_exchange_data.default_leverage
    profile_data_1.update(update)
    assert profile_data_1.future_exchange_data.default_leverage == 20
    assert profile_data_1.future_exchange_data.default_leverage != original_leverage
    assert profile_data_1.future_exchange_data.symbol_data[0].leverage == 15
    
    # Test trading minimal_funds updates
    profile_data_1 = profiles.ProfileData.from_dict(profile_data_dict)
    profile_data_2 = copy.deepcopy(profile_data_1)
    new_fund = profile_data_import.MinimalFund("ETH", 50.0, 50.0)
    profile_data_2.trading.minimal_funds.append(new_fund)
    profile_data_2.trading.minimal_funds[0].available = 20.0
    update = profile_data_1.get_update(profile_data_2)
    original_fund_count = len(profile_data_1.trading.minimal_funds)
    profile_data_1.update(update)
    assert len(profile_data_1.trading.minimal_funds) == original_fund_count + 1
    assert profile_data_1.trading.minimal_funds[0].available == 20.0
    assert profile_data_1.trading.minimal_funds[-1].asset == "ETH"
    
    # Test update without _updated_fields (should not update)
    profile_data_1 = profiles.ProfileData.from_dict(profile_data_dict)
    profile_data_2 = copy.deepcopy(profile_data_1)
    profile_data_2.profile_details.name = "should_not_update"
    profile_data_2.trading.risk = 0.99
    update = profile_data_1.get_update(profile_data_2)
    update._updated_fields = []
    update.profile_details._updated_fields = []
    update.trading._updated_fields = []
    original_name = profile_data_1.profile_details.name
    original_risk = profile_data_1.trading.risk
    profile_data_1.update(update)
    assert profile_data_1.profile_details.name == original_name
    assert profile_data_1.trading.risk == original_risk


def test_get_update_and_update_roundtrip(profile_data_dict):
    """Test that get_update() and update() work together correctly"""
    profile_data_1 = profiles.ProfileData.from_dict(profile_data_dict)
    profile_data_2 = copy.deepcopy(profile_data_1)
    
    # Make various changes
    profile_data_2.profile_details.name = "roundtrip_name"
    profile_data_2.profile_details.version = "3.0.0"
    profile_data_2.trading.risk = 0.7
    profile_data_2.trading.reference_market = "ETH"
    profile_data_2.crypto_currencies[0].enabled = False
    profile_data_2.trader.enabled = True
    
    # Get update and apply it
    update = profile_data_1.get_update(profile_data_2)
    profile_data_1.update(update)
    
    # Verify profile_data_1 matches profile_data_2 for changed fields
    assert profile_data_1.profile_details.name == profile_data_2.profile_details.name
    assert profile_data_1.profile_details.version == profile_data_2.profile_details.version
    assert profile_data_1.trading.risk == profile_data_2.trading.risk
    assert profile_data_1.trading.reference_market == profile_data_2.trading.reference_market
    assert profile_data_1.crypto_currencies[0].enabled == profile_data_2.crypto_currencies[0].enabled
    assert profile_data_1.trader.enabled == profile_data_2.trader.enabled


def _remove_updated_fields(profile_data_dict: dict) -> dict:
    profile_data_dict.pop("_updated_fields", None)
    for value in profile_data_dict.values():
        if isinstance(value, dict):
            _remove_updated_fields(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _remove_updated_fields(item)
    return profile_data_dict
