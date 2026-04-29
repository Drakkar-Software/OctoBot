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
import copy
import pytest

import octobot_trading.util as util
import octobot_trading.constants as trading_constants
import octobot_commons.symbols as symbol_util
import octobot_commons.constants as commons_constants

from tests import config


def test_is_trader_enabled(config):
    _test_enabled(config, util.is_trader_enabled, commons_constants.CONFIG_TRADER, False)


def test_is_trader_simulator_enabled(config):
    _test_enabled(config, util.is_trader_simulator_enabled, commons_constants.CONFIG_SIMULATOR, True)


def test_is_trade_history_loading_enabled(config):
    assert util.is_trade_history_loading_enabled(config) is True
    config[commons_constants.CONFIG_TRADER][commons_constants.CONFIG_LOAD_TRADE_HISTORY] = False
    assert util.is_trade_history_loading_enabled(config) is False
    config.pop(commons_constants.CONFIG_TRADER)
    assert util.is_trade_history_loading_enabled(config) is True
    assert util.is_trade_history_loading_enabled(config, False) is False


def test_is_currency_enabled(config):
    config[commons_constants.CONFIG_CRYPTO_CURRENCIES]["Bitcoin"][commons_constants.CONFIG_ENABLED_OPTION] = True
    assert util.is_currency_enabled(config, "Bitcoin", True) is True
    assert util.is_currency_enabled(config, "Bitcoin", False) is True
    config[commons_constants.CONFIG_CRYPTO_CURRENCIES]["Bitcoin"][commons_constants.CONFIG_ENABLED_OPTION] = False
    assert util.is_currency_enabled(config, "Bitcoin", True) is False
    config[commons_constants.CONFIG_CRYPTO_CURRENCIES]["Bitcoin"].pop(commons_constants.CONFIG_ENABLED_OPTION, None)
    assert util.is_currency_enabled(config, "Bitcoin", True) is True
    assert util.is_currency_enabled(config, "Bitcoin", False) is False
    assert util.is_currency_enabled(config, "Hello", False) is False


def test_get_symbols(config):
    assert util.get_symbols(config, True) == FULL_PAIRS_LIST
    # with wildcard currency
    config[commons_constants.CONFIG_CRYPTO_CURRENCIES]["Bitcoin"][commons_constants.CONFIG_CRYPTO_PAIRS] = \
        commons_constants.CONFIG_WILDCARD
    list_without_bitcoin = _filter_by_base(FULL_PAIRS_LIST, "BTC")
    assert util.get_symbols(config, True) == list_without_bitcoin

    # with disabled currency
    config[commons_constants.CONFIG_CRYPTO_CURRENCIES]["Bitcoin"][commons_constants.CONFIG_CRYPTO_PAIRS] = [
        'BTC/USDT',
        'BTC/USD'
    ]
    config[commons_constants.CONFIG_CRYPTO_CURRENCIES]["Bitcoin"][commons_constants.CONFIG_ENABLED_OPTION] = False
    list_without_bitcoin = _filter_by_base(FULL_PAIRS_LIST, "BTC")
    assert util.get_symbols(config, True) == list_without_bitcoin
    assert util.get_symbols(config, False) == FULL_PAIRS_LIST

    # with empty pairs
    config[commons_constants.CONFIG_CRYPTO_CURRENCIES]["Ethereum"][commons_constants.CONFIG_CRYPTO_PAIRS] = []
    assert util.get_symbols(config, False) == _filter_by_base(FULL_PAIRS_LIST, "ETH")

    # with broken config
    config[commons_constants.CONFIG_CRYPTO_CURRENCIES] = []
    assert util.get_symbols(config, False) == []
    config.pop(commons_constants.CONFIG_CRYPTO_CURRENCIES, None)
    assert util.get_symbols(config, False) == []


def test_get_all_currencies(config):
    symbols = set()
    for pair in FULL_PAIRS_LIST:
        symbols.update(symbol_util.parse_symbol(pair).base_and_quote())
    assert util.get_all_currencies(config) == symbols
    assert util.get_all_currencies(config, enabled_only=True) == symbols

    # with disabled currency
    config[commons_constants.CONFIG_CRYPTO_CURRENCIES]["Bitcoin"][commons_constants.CONFIG_ENABLED_OPTION] = False
    assert util.get_all_currencies(config) == symbols
    symbols_without_bitcoin_symbols = copy.copy(symbols)
    with pytest.raises(KeyError):
        symbols_without_bitcoin_symbols.remove("EUR")
    symbols_without_bitcoin_symbols.remove("USD")
    assert util.get_all_currencies(config, enabled_only=True) == symbols_without_bitcoin_symbols
    assert util.get_all_currencies(config, enabled_only=False) == symbols


def test_get_pairs(config):
    assert util.get_pairs(config, "BTC") == _select_by_base_or_quote(FULL_PAIRS_LIST, "BTC")
    assert util.get_pairs(config, "ADA") == ["ADA/BTC"]

    # with disabled currency
    config[commons_constants.CONFIG_CRYPTO_CURRENCIES]["Bitcoin"][commons_constants.CONFIG_ENABLED_OPTION] = False
    assert util.get_pairs(config, "BTC", enabled_only=False) == _select_by_base_or_quote(FULL_PAIRS_LIST, "BTC")
    assert util.get_pairs(config, "BTC", enabled_only=True) != _select_by_base_or_quote(FULL_PAIRS_LIST, "BTC")
    assert util.get_pairs(config, "BTC", enabled_only=True) == _filter_by_base(_select_by_base_or_quote(FULL_PAIRS_LIST,
                                                                                                        "BTC"),
                                                                               "BTC")


def test_get_market_pair(config):
    config[commons_constants.CONFIG_TRADING][commons_constants.CONFIG_TRADER_REFERENCE_MARKET] = "BTC"
    assert util.get_market_pair(config, "ETH") == ("ETH/BTC", False)
    assert util.get_market_pair(config, "ADA") == ("ADA/BTC", False)
    assert util.get_market_pair(config, "USDT") == ("BTC/USDT", True)
    assert util.get_market_pair(config, "BTC") == ("", False)

    # with disabled currency
    config[commons_constants.CONFIG_CRYPTO_CURRENCIES]["Cardano"][commons_constants.CONFIG_ENABLED_OPTION] = False
    assert util.get_market_pair(config, "ADA", enabled_only=False) == ("ADA/BTC", False)
    assert util.get_market_pair(config, "ADA", enabled_only=True) == ("", False)


def test_get_reference_market(config):
    config[commons_constants.CONFIG_TRADING][commons_constants.CONFIG_TRADER_REFERENCE_MARKET] = "BTC"
    assert util.get_reference_market(config) == "BTC"
    config[commons_constants.CONFIG_TRADING][commons_constants.CONFIG_TRADER_REFERENCE_MARKET] = "BTC1"
    assert util.get_reference_market(config) == "BTC1"
    config[commons_constants.CONFIG_TRADING].pop(commons_constants.CONFIG_TRADER_REFERENCE_MARKET, None)
    assert util.get_reference_market(config) == trading_constants.DEFAULT_REFERENCE_MARKET


def test_get_traded_pairs_by_currency(config):
    assert util.get_traded_pairs_by_currency(config) == FULL_PAIRS_BY_CRYPTO_DICT
    # with wildcard currency
    config[commons_constants.CONFIG_CRYPTO_CURRENCIES]["Bitcoin"][commons_constants.CONFIG_CRYPTO_PAIRS] = \
        commons_constants.CONFIG_WILDCARD
    dict_without_bitcoin = _replace_value_by_key(FULL_PAIRS_BY_CRYPTO_DICT, "Bitcoin", commons_constants.CONFIG_WILDCARD)
    assert util.get_traded_pairs_by_currency(config) == dict_without_bitcoin

    # with disabled currency
    config[commons_constants.CONFIG_CRYPTO_CURRENCIES]["Bitcoin"][commons_constants.CONFIG_CRYPTO_PAIRS] = [
        'BTC/USDT',
        'BTC/USD'
    ]
    config[commons_constants.CONFIG_CRYPTO_CURRENCIES]["Bitcoin"][commons_constants.CONFIG_ENABLED_OPTION] = False
    dict_without_bitcoin = _filter_by_key(FULL_PAIRS_BY_CRYPTO_DICT, "Bitcoin")
    assert util.get_traded_pairs_by_currency(config) == dict_without_bitcoin

    # with empty pairs
    config[commons_constants.CONFIG_CRYPTO_CURRENCIES]["Bitcoin"][commons_constants.CONFIG_CRYPTO_PAIRS] = []
    assert util.get_traded_pairs_by_currency(config) == _filter_by_key(FULL_PAIRS_BY_CRYPTO_DICT, "Bitcoin")


FULL_PAIRS_LIST = [
    'BTC/USDT',
    'BTC/USD',
    'ETH/USDT',
    'ETH/BTC',
    'ADA/BTC',
    'LINK/BTC',
]

FULL_PAIRS_BY_CRYPTO_DICT = {
    'Bitcoin': ['BTC/USDT', 'BTC/USD'],
    'Ethereum': ['ETH/USDT', 'ETH/BTC'],
    'Chainlink': ['LINK/BTC'],
    'Cardano': ['ADA/BTC'],
}


def _test_enabled(config, func, config_key, current_val):
    assert func(config) is current_val
    config[config_key][commons_constants.CONFIG_ENABLED_OPTION] = not current_val
    assert func(config) is not current_val
    config[config_key].pop(commons_constants.CONFIG_ENABLED_OPTION, None)
    assert func(config) is False
    config.pop(config_key, None)
    assert func(config) is False


def _filter_by_base(pairs, filtered_base):
    return [s for s in pairs if symbol_util.parse_symbol(s).base != filtered_base]


def _filter_by_key(pairs_by_cypto, filtered_key):
    return {
        crypto: pairs
        for crypto, pairs in pairs_by_cypto.items()
        if crypto != filtered_key
    }


def _replace_value_by_key(pairs_by_cypto, filtered_key, replaced_value):
    return {
        crypto: pairs if crypto != filtered_key else replaced_value
        for crypto, pairs in pairs_by_cypto.items()
    }


def _select_by_base_or_quote(pairs, base_or_quote):
    return [s for s in pairs if base_or_quote in symbol_util.parse_symbol(s).base_and_quote()]
