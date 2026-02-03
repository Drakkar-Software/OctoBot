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
#  License along with this library.
import decimal

import octobot_trading.constants as constants
import octobot_trading.personal_data.portfolios.assets.margin_asset as margin_asset

ASSET_CURRENCY_NAME = "BTC"


def test___eq__():
    asset = margin_asset.MarginAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO)
    assert asset == margin_asset.MarginAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO)
    assert not asset == margin_asset.MarginAsset(ASSET_CURRENCY_NAME, constants.ONE_HUNDRED, constants.ZERO)
    assert not asset == margin_asset.MarginAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ONE_HUNDRED)
    assert not asset == margin_asset.MarginAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO,
                                                 borrowed=constants.ONE_HUNDRED)
    assert asset == margin_asset.MarginAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO,
                                             borrowed=constants.ZERO)
    assert not asset == margin_asset.MarginAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO,
                                                 interest=constants.ONE_HUNDRED)
    assert not asset == margin_asset.MarginAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO,
                                                 locked=constants.ONE_HUNDRED)


def test_update():
    asset = margin_asset.MarginAsset(ASSET_CURRENCY_NAME,
                                     available=constants.ZERO, total=constants.ZERO,
                                     borrowed=constants.ZERO, interest=constants.ZERO, locked=constants.ZERO)
    assert not asset.update(available=constants.ZERO, total=constants.ZERO)
    assert asset.update(available=constants.ZERO, total=decimal.Decimal(5))
    assert asset.total == decimal.Decimal(5)
    assert asset.update(available=constants.ZERO, borrowed=decimal.Decimal(15))
    assert asset.borrowed == decimal.Decimal(15)
    assert asset.total == decimal.Decimal(5)
    assert asset.available == constants.ZERO


def test_set():
    asset = margin_asset.MarginAsset(ASSET_CURRENCY_NAME,
                                     available=constants.ZERO, total=constants.ZERO,
                                     borrowed=constants.ZERO, interest=constants.ZERO, locked=constants.ZERO)
    assert not asset.set(available=constants.ZERO, total=constants.ZERO)
    assert asset.set(available=decimal.Decimal(5), total=decimal.Decimal(5), borrowed=decimal.Decimal(2),
                     interest=decimal.Decimal(2), locked=decimal.Decimal(7))
    assert not asset.set(available=decimal.Decimal(5), total=decimal.Decimal(5), borrowed=decimal.Decimal(2),
                         interest=decimal.Decimal(2), locked=decimal.Decimal(7))
    assert asset.available == decimal.Decimal(5)
    assert asset.total == decimal.Decimal(5)
    assert asset.borrowed == decimal.Decimal(2)
    assert asset.locked == decimal.Decimal(7)
    assert asset.interest == decimal.Decimal(2)


def test_restore_available():
    asset = margin_asset.MarginAsset(ASSET_CURRENCY_NAME, available=constants.ONE, total=constants.ONE_HUNDRED)
    assert not asset.available == asset.total
    asset.restore_available()
    assert asset.available == asset.total == constants.ONE_HUNDRED


def test_reset():
    asset = margin_asset.MarginAsset(ASSET_CURRENCY_NAME, available=constants.ONE_HUNDRED,
                                     total=constants.ONE_HUNDRED, borrowed=constants.ONE_HUNDRED,
                                     interest=constants.ONE_HUNDRED, locked=constants.ONE_HUNDRED)
    assert asset.available == asset.total == asset.interest == asset.borrowed == asset.locked == constants.ONE_HUNDRED
    asset.reset()
    assert asset.available == asset.total == asset.interest == asset.borrowed == asset.locked == constants.ZERO
