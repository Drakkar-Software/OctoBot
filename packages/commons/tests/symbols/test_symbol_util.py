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
import octobot_commons.symbols


def test_parse_symbol():
    assert octobot_commons.symbols.parse_symbol("BTC/USDT") == octobot_commons.symbols.Symbol("BTC/USDT")


def test_merge_symbol():
    assert octobot_commons.symbols.merge_symbol("BTC/USDT") == "BTCUSDT"
    assert octobot_commons.symbols.merge_symbol("BTC/USDT:USDT") == "BTCUSDT_USDT"


def test_merge_currencies():
    assert octobot_commons.symbols.merge_currencies("BTC", "USDT") == "BTC/USDT"
    assert octobot_commons.symbols.merge_currencies("BTC", "USDT", "BTC") == "BTC/USDT:BTC"
    assert octobot_commons.symbols.merge_currencies("BTC", "USDT", settlement_asset="XXX", market_separator="g", settlement_separator="d") == "BTCgUSDTdXXX"
    assert (
        octobot_commons.symbols.merge_currencies(
            "will-bitcoin-replace-sha-256-before-2027",
            "USDC",
            "USDC",
            "261231",
            "0",
            octobot_commons.enums.OptionTypes.PUT.value
        )
        == "will-bitcoin-replace-sha-256-before-2027/USDC:USDC-261231-0-P"
    )
    assert (
        octobot_commons.symbols.merge_currencies(
            "will-bitcoin-replace-sha-256-before-2027",
            "USDC",
            "USDC",
            "261231",
            "0",
            "test"
        )
        == "will-bitcoin-replace-sha-256-before-2027/USDC:USDC-261231-0-TEST"
    )
    assert (
        octobot_commons.symbols.merge_currencies(
            "will-bitcoin-replace-sha-256-before-2027",
            "USDC",
            "USDC",
            "261231",
            "0",
            None
        )
        == "will-bitcoin-replace-sha-256-before-2027/USDC:USDC"
    )


def test_convert_symbol():
    assert octobot_commons.symbols.convert_symbol("BTC-USDT", symbol_separator="-") == "BTC/USDT"


def test_is_symbol():
    # Test with default separator (/)
    assert octobot_commons.symbols.is_symbol("BTC/USDT") is True
    assert octobot_commons.symbols.is_symbol("ETH/USDT") is True
    assert octobot_commons.symbols.is_symbol("BTC/USDT:USDT") is True
    assert octobot_commons.symbols.is_symbol("BTC") is False
    assert octobot_commons.symbols.is_symbol("USDT") is False
    assert octobot_commons.symbols.is_symbol("ETH") is False
    
    # Test with custom separator (-)
    assert octobot_commons.symbols.is_symbol("BTC-USDT", separator="-") is True
    assert octobot_commons.symbols.is_symbol("ETH-USDT", separator="-") is True
    assert octobot_commons.symbols.is_symbol("BTC", separator="-") is False
    assert octobot_commons.symbols.is_symbol("USDT", separator="-") is False
    
    # Test with custom separator (:)
    assert octobot_commons.symbols.is_symbol("BTC/USDT:USDT", separator=":") is True
    assert octobot_commons.symbols.is_symbol("BTC/USDT", separator=":") is False
    assert octobot_commons.symbols.is_symbol("BTC", separator=":") is False
    
    # Test with custom separator (|)
    assert octobot_commons.symbols.is_symbol("BTC|USDT", separator="|") is True
    assert octobot_commons.symbols.is_symbol("BTC", separator="|") is False
    
    # Test edge cases
    assert octobot_commons.symbols.is_symbol("", separator="/") is False
    assert octobot_commons.symbols.is_symbol("/", separator="/") is True
    assert octobot_commons.symbols.is_symbol("BTC/USDT/ETH", separator="/") is True


import pytest

import octobot_commons.constants as commons_constants


class TestTradingTypeFromSymbol:
    def test_spot_symbol_returns_spot(self):
        assert octobot_commons.symbols.trading_type_from_symbol("BTC/USDT") == commons_constants.CONFIG_EXCHANGE_SPOT

    def test_futures_symbol_returns_future(self):
        assert (
            octobot_commons.symbols.trading_type_from_symbol("BTC/USDT:USDT")
            == commons_constants.CONFIG_EXCHANGE_FUTURE
        )

    def test_option_symbol_returns_option(self):
        assert (
            octobot_commons.symbols.trading_type_from_symbol("BTC/USDT:USDT-211225-60000-P")
            == commons_constants.CONFIG_EXCHANGE_OPTION
        )

    def test_unknown_symbol_raises_value_error(self):
        with pytest.raises(ValueError):
            octobot_commons.symbols.trading_type_from_symbol("BTC")


class TestTradingTypeFromTradedSymbols:
    def test_all_spot_symbols_return_spot(self):
        assert octobot_commons.symbols.trading_type_from_traded_symbols(
            ["BTC/USDT", "ETH/USDT"]
        ) == commons_constants.CONFIG_EXCHANGE_SPOT

    def test_all_futures_symbols_return_future(self):
        assert octobot_commons.symbols.trading_type_from_traded_symbols(
            ["BTC/USDT:USDT", "ETH/USDT:USDT"]
        ) == commons_constants.CONFIG_EXCHANGE_FUTURE

    def test_empty_symbols_raises_value_error(self):
        with pytest.raises(ValueError):
            octobot_commons.symbols.trading_type_from_traded_symbols([])

    def test_mixed_symbol_types_raise_ambiguous_error(self):
        with pytest.raises(octobot_commons.errors.AmbiguousTradedSymbolsTradingTypeError):
            octobot_commons.symbols.trading_type_from_traded_symbols(["BTC/USDT", "BTC/USDT:USDT"])


class TestMergeSymbolNetworkDex:
    def test_strips_network_and_dex_suffix(self):
        assert octobot_commons.symbols.merge_symbol("SOL/USDT@solana!raydium") == "SOLUSDT"


class TestConvertSymbolBaseAndQuoteOnlyNetworkDex:
    def test_strips_network_and_dex_suffix(self):
        assert (
            octobot_commons.symbols.convert_symbol(
                "SOL/USDT@solana!raydium",
                symbol_separator="/",
                base_and_quote_only=True,
            )
            == "SOL/USDT"
        )
