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

import octobot_trading.errors as errors
import octobot_trading.constants as constants
import octobot_trading.personal_data.portfolios.assets.spot_asset as spot_asset

ASSET_CURRENCY_NAME = "BTC"


def test___eq__():
    asset = spot_asset.SpotAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO)
    assert asset == spot_asset.SpotAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO)
    assert not asset == spot_asset.SpotAsset(ASSET_CURRENCY_NAME, constants.ONE_HUNDRED, constants.ZERO)
    assert not asset == spot_asset.SpotAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ONE_HUNDRED)


def test_update():
    asset = spot_asset.SpotAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO)
    assert not asset.update(available=constants.ZERO, total=constants.ZERO)
    assert asset.update(available=constants.ZERO, total=decimal.Decimal(5))
    assert asset.total == decimal.Decimal(5)


def test_set():
    asset = spot_asset.SpotAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO)
    assert not asset.set(available=constants.ZERO, total=constants.ZERO)
    assert asset.set(available=decimal.Decimal(5), total=decimal.Decimal(5))
    assert not asset.set(available=decimal.Decimal(5), total=decimal.Decimal(5))
    assert asset.available == decimal.Decimal(5)
    assert asset.total == decimal.Decimal(5)


def test_restore_available():
    asset = spot_asset.SpotAsset(ASSET_CURRENCY_NAME, available=constants.ONE, total=constants.ONE_HUNDRED)
    assert not asset.available == asset.total
    asset.restore_available()
    assert asset.available == asset.total == constants.ONE_HUNDRED


def test_reset():
    asset = spot_asset.SpotAsset(ASSET_CURRENCY_NAME, available=constants.ONE_HUNDRED, total=constants.ONE_HUNDRED)
    assert asset.available == asset.total == constants.ONE_HUNDRED
    asset.reset()
    assert asset.available == asset.total == constants.ZERO


def test_restore():
    asset = spot_asset.SpotAsset(ASSET_CURRENCY_NAME, total=constants.ONE_HUNDRED, available=constants.ONE_HUNDRED)

    asset.update(total=-decimal.Decimal(50))
    assert asset.total == decimal.Decimal(50)
    with pytest.raises(errors.PortfolioNegativeValueError):
        asset.update(total=-decimal.Decimal(70))
    assert asset.total == decimal.Decimal(50)

    asset.update(available=-decimal.Decimal(2.5))
    assert asset.available == decimal.Decimal(97.5)
    asset.update(available=-decimal.Decimal(2.5))
    assert asset.available == decimal.Decimal(95)
    with pytest.raises(errors.PortfolioNegativeValueError):
        asset.update(available=-decimal.Decimal(96))
    assert asset.available == decimal.Decimal(95)


def test_get_total_holdings():
    asset = spot_asset.SpotAsset(ASSET_CURRENCY_NAME, available=decimal.Decimal(12), total=constants.ONE_HUNDRED)
    assert asset.get_total_holdings() == constants.ONE_HUNDRED
