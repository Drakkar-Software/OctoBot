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
import decimal
import pytest

import octobot_trading.constants as constants
import octobot_trading.errors as errors
import octobot_trading.personal_data as trading_personal_data

import octobot_commons.constants as commons_constants

from tests.exchanges import backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting


def test_try_convert_currency_value_using_multiple_pairs(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    value_converter = portfolio_manager.portfolio_value_holder.value_converter

    # try_convert_currency_value_using_multiple_pairs uses last_prices_by_trading_pair
    # try without last_prices_by_trading_pair
    assert value_converter.try_convert_currency_value_using_multiple_pairs("ETH", "BTC", constants.ONE, []) \
           is None
    assert value_converter.try_convert_currency_value_using_multiple_pairs("BTC", "BTC", constants.ONE, []) \
           is None
    assert value_converter.try_convert_currency_value_using_multiple_pairs("USDT", "BTC", constants.ONE, []) \
           is None
    assert value_converter.try_convert_currency_value_using_multiple_pairs("DOT", "BTC", constants.ONE, []) \
           is None
    assert value_converter.try_convert_currency_value_using_multiple_pairs("ADA", "BTC", constants.ONE, []) \
           is None

    # 1 ETH = 0.5 BTC
    value_converter.last_prices_by_trading_pair["ETH/BTC"] = decimal.Decimal("0.5")
    # 1 DOT = 0.2 ETH
    value_converter.update_last_price("DOT/ETH", decimal.Decimal("0.2"))
    # therefore 1 DOT = 0.2 ETH = 0.5 * 0.2 BTC = 0.1 BTC
    assert value_converter.try_convert_currency_value_using_multiple_pairs("DOT", "BTC", decimal.Decimal("2"), []) \
        == decimal.Decimal("0.2")

    # with reversed pair in bridge
    value_converter.last_prices_by_trading_pair["BTC/USDT"] = decimal.Decimal("10000")
    value_converter.last_prices_by_trading_pair["ADA/USDT"] = decimal.Decimal("2")
    # 1 ADA = 2 USDT == 2/10000 BTC
    assert value_converter.try_convert_currency_value_using_multiple_pairs("ADA", "BTC", decimal.Decimal(1), []) \
        == decimal.Decimal(2) / decimal.Decimal(10000)
    # now using bridges cache
    assert value_converter.try_convert_currency_value_using_multiple_pairs("ADA", "BTC", decimal.Decimal(2), []) \
        == decimal.Decimal(4) / decimal.Decimal(10000)
    # bridge is saved
    assert value_converter.get_saved_price_conversion_bridge("ADA", "BTC") == [
        ("ADA", "USDT"), ("USDT", "BTC")
    ]
    assert value_converter.convert_currency_value_from_saved_price_bridges(
        "ADA", "BTC", decimal.Decimal(10)
    ) == decimal.Decimal(20) / decimal.Decimal(10000)
    # without enough data
    value_converter.last_prices_by_trading_pair["CRO/PLOP"] = decimal.Decimal("2")
    assert value_converter.try_convert_currency_value_using_multiple_pairs("CRO", "BTC", constants.ONE, []) \
           is None
    # second time to make sure bridge cache is not creating issues
    assert value_converter.try_convert_currency_value_using_multiple_pairs("CRO", "BTC", constants.ONE, []) \
           is None
    with pytest.raises(KeyError):
        # no bridge saved as value is not available
        value_converter.get_saved_price_conversion_bridge("CRO", "BTC")
    with pytest.raises(errors.MissingPriceDataError):
        value_converter.convert_currency_value_from_saved_price_bridges(
            "CRO", "BTC", constants.ONE
        )
    with pytest.raises(errors.MissingPriceDataError):
        value_converter.convert_currency_value_from_saved_price_bridges(
            "PLOP", "BTC", constants.ONE
        )

    exchange_manager.exchange_config.traded_symbol_pairs.append("NANO/BTC")
    # part 1 of bridge data that has not been update but are in exchange config therefore will be available
    with pytest.raises(errors.PendingPriceDataError):
        value_converter.try_convert_currency_value_using_multiple_pairs("NANO", "BTC", constants.ONE, [])

    assert value_converter.try_convert_currency_value_using_multiple_pairs("XRP", "BTC", constants.ONE, []) \
           is None
    # provide first part of the bridge
    exchange_manager.exchange_config.traded_symbol_pairs.append("XRP/USDT")
    assert value_converter.is_missing_price_bridge("XRP", "BTC")
    assert value_converter.try_convert_currency_value_using_multiple_pairs("XRP", "BTC", constants.ONE, []) \
           is None
    value_converter.reset_missing_price_bridges()
    value_converter.update_last_price("DOT/ETH", decimal.Decimal("0.2"))
    with pytest.raises(errors.PendingPriceDataError):
        value_converter.try_convert_currency_value_using_multiple_pairs("XRP", "BTC", constants.ONE, [])


def test_try_convert_currency_value_using_multiple_pairs_with_nested_bridges(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    value_converter = portfolio_manager.portfolio_value_holder.value_converter

    assert value_converter.try_convert_currency_value_using_multiple_pairs("XRP", "BTC", constants.ONE, []) \
           is None
    # provide first part 1 of the bridge
    value_converter.last_prices_by_trading_pair["ADA/USDT"] = decimal.Decimal("2")
    exchange_manager.exchange_config.traded_symbol_pairs.append("BTC/USDT")
    with pytest.raises(errors.PendingPriceDataError):
        # missing part 2 price
        value_converter.try_convert_currency_value_using_multiple_pairs("ADA", "BTC", constants.ONE, [])
    value_converter.last_prices_by_trading_pair["BTC/USDT"] = decimal.Decimal("100")
    assert value_converter.try_convert_currency_value_using_multiple_pairs("ADA", "BTC", constants.ONE, []) == \
           decimal.Decimal(2) / decimal.Decimal(100)
    assert value_converter.get_saved_price_conversion_bridge("ADA", "BTC") == [
        ("ADA", "USDT"), ("USDT", "BTC")
    ]

    # need to go through BTC to get ETH price
    value_converter.last_prices_by_trading_pair["ETH/BTC"] = decimal.Decimal("0.1")
    assert value_converter.try_convert_currency_value_using_multiple_pairs("ADA", "ETH", constants.ONE, []) == \
           decimal.Decimal(2) / decimal.Decimal(100) / decimal.Decimal("0.1")
    assert value_converter.get_saved_price_conversion_bridge("ADA", "ETH") == [
        ("ADA", "USDT"), ("USDT", "BTC"), ("BTC", "ETH")
    ]
    assert value_converter.convert_currency_value_from_saved_price_bridges("ADA", "ETH", decimal.Decimal("1.2")) \
        == decimal.Decimal("1.2") * decimal.Decimal("2") / decimal.Decimal("100") / decimal.Decimal("0.1")
    # also saved intermediary bridges
    assert value_converter.get_saved_price_conversion_bridge("USDT", "ETH") == [
        ("USDT", "BTC"), ("BTC", "ETH")
    ]
    assert value_converter.convert_currency_value_from_saved_price_bridges("USDT", "ETH", constants.ONE) \
        == constants.ONE / decimal.Decimal("100") / decimal.Decimal("0.1")

    # need to go through BTC and ETH to get ETH XRP price
    value_converter.last_prices_by_trading_pair["XRP/ETH"] = decimal.Decimal("0.0000001")
    assert value_converter.try_convert_currency_value_using_multiple_pairs("ADA", "XRP", constants.ONE, []) == \
           decimal.Decimal(2) / decimal.Decimal(100) / decimal.Decimal("0.1") / decimal.Decimal("0.0000001")
    assert value_converter.get_saved_price_conversion_bridge("ADA", "XRP") == [
        ("ADA", "USDT"), ("USDT", "BTC"), ("BTC", "ETH"), ("ETH", "XRP")
    ]
    # now use bridges cache
    assert value_converter.try_convert_currency_value_using_multiple_pairs("ADA", "XRP", constants.ONE, []) == \
           decimal.Decimal(2) / decimal.Decimal(100) / decimal.Decimal("0.1") / decimal.Decimal("0.0000001")
    assert value_converter.convert_currency_value_from_saved_price_bridges(
        "ADA", "XRP", decimal.Decimal("0.0001")
    ) == decimal.Decimal("0.0001") * decimal.Decimal(2) / decimal.Decimal(100) / \
        decimal.Decimal("0.1") / decimal.Decimal("0.0000001")


def test_get_usd_like_value(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    value_converter = portfolio_manager.portfolio_value_holder.value_converter
    # no last_prices_by_trading_pair
    assert value_converter.get_usd_like_value(commons_constants.USD_LIKE_COINS[0], decimal.Decimal("11")) \
           == decimal.Decimal("11")
    assert value_converter.get_usd_like_value(commons_constants.USD_LIKE_COINS[-1], decimal.Decimal("11")) \
           == decimal.Decimal("11")
    with pytest.raises(errors.MissingPriceDataError):
        value_converter.get_usd_like_value("BTC", decimal.Decimal("11"))

    value_converter.update_last_price("BTC/USDC", decimal.Decimal("30000"))
    assert value_converter.get_usd_like_value("BTC", decimal.Decimal("11")) \
           == decimal.Decimal("11") * decimal.Decimal("30000")

    with pytest.raises(errors.MissingPriceDataError):
        value_converter.get_usd_like_value("ETH", decimal.Decimal("11"))


def test_can_convert_symbol_to_usd_like():
    assert trading_personal_data.ValueConverter.can_convert_symbol_to_usd_like("BTC/USDT") is True
    assert trading_personal_data.ValueConverter.can_convert_symbol_to_usd_like(
        f"{commons_constants.USD_LIKE_COINS[4]}/BTC"
    ) is True
    assert trading_personal_data.ValueConverter.can_convert_symbol_to_usd_like("BTC/ETH") is False
