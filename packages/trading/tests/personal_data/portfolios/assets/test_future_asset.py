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
import octobot_trading.personal_data.portfolios.assets.future_asset as future_asset

ASSET_CURRENCY_NAME = "BTC"


def test___eq__():
    asset = future_asset.FutureAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO)
    assert asset == future_asset.FutureAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO)
    assert not asset == future_asset.FutureAsset(ASSET_CURRENCY_NAME, constants.ONE_HUNDRED, constants.ZERO)
    assert not asset == future_asset.FutureAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ONE_HUNDRED)
    assert not asset == future_asset.FutureAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO,
                                                 wallet_balance=constants.ONE_HUNDRED)
    assert asset == future_asset.FutureAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO,
                                             wallet_balance=constants.ZERO)
    assert not asset == future_asset.FutureAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO,
                                                 position_margin=constants.ONE_HUNDRED)
    assert not asset == future_asset.FutureAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO,
                                                 order_margin=constants.ONE_HUNDRED)
    assert not asset == future_asset.FutureAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO,
                                                 initial_margin=constants.ONE_HUNDRED)


def test_update():
    asset = future_asset.FutureAsset(ASSET_CURRENCY_NAME,
                                     available=constants.ZERO, total=constants.ZERO, order_margin=constants.ZERO,
                                     initial_margin=constants.ZERO, wallet_balance=constants.ZERO,
                                     position_margin=constants.ZERO)
    assert not asset.update(available=constants.ZERO, total=constants.ZERO, initial_margin=constants.ZERO,
                            unrealized_pnl=constants.ZERO, position_margin=constants.ZERO)
    assert asset.total == constants.ZERO
    assert asset.update(total=decimal.Decimal(5), available=constants.ZERO, position_margin=constants.ZERO,
                        unrealized_pnl=constants.ZERO, initial_margin=constants.ZERO)
    assert asset.total == decimal.Decimal(5)
    assert asset.update(available=constants.ZERO, total=decimal.Decimal(6), unrealized_pnl=decimal.Decimal(10),
                        position_margin=constants.ZERO, initial_margin=constants.ZERO)
    assert asset.total == decimal.Decimal(21)
    assert asset.wallet_balance == decimal.Decimal(11)
    assert asset.update(available=constants.ZERO, total=decimal.Decimal(1), unrealized_pnl=decimal.Decimal(10),
                        initial_margin=decimal.Decimal(3), position_margin=constants.ZERO)
    assert asset.wallet_balance == decimal.Decimal(12)
    assert asset.total == decimal.Decimal(32)
    assert asset.initial_margin == decimal.Decimal(3)
    assert asset.available == decimal.Decimal(12)


def test_set():
    asset = future_asset.FutureAsset(ASSET_CURRENCY_NAME,
                                     available=constants.ZERO, total=constants.ZERO, order_margin=constants.ZERO,
                                     initial_margin=constants.ZERO, wallet_balance=constants.ZERO,
                                     position_margin=constants.ZERO)
    assert not asset.set(available=constants.ZERO, total=constants.ZERO, margin_balance=constants.ZERO,
                         initial_margin=constants.ZERO,
                         order_margin=constants.ZERO,
                         position_margin=constants.ZERO,
                         unrealized_pnl=constants.ZERO)
    assert asset.set(total=decimal.Decimal(5),
                     available=decimal.Decimal(5),
                     margin_balance=decimal.Decimal(2),
                     initial_margin=constants.ZERO,
                     order_margin=constants.ZERO,
                     position_margin=constants.ZERO,
                     unrealized_pnl=constants.ZERO)
    assert not asset.set(total=decimal.Decimal(5),
                         available=decimal.Decimal(5),
                         margin_balance=decimal.Decimal(2),
                         initial_margin=constants.ZERO,
                         order_margin=constants.ZERO,
                         position_margin=constants.ZERO,
                         unrealized_pnl=constants.ZERO)
    assert asset.available == decimal.Decimal(5)
    assert asset.total == decimal.Decimal(2)
    assert asset.wallet_balance == decimal.Decimal(5)
    assert asset.set(total=decimal.Decimal(-5),
                     available=decimal.Decimal(-5),
                     margin_balance=decimal.Decimal(-5),
                     initial_margin=decimal.Decimal(-5),
                     order_margin=decimal.Decimal(-5),
                     position_margin=decimal.Decimal(-5),
                     unrealized_pnl=decimal.Decimal(-5))
    assert asset.set(total=constants.ZERO,
                     available=constants.ZERO,
                     margin_balance=constants.ZERO,
                     initial_margin=constants.ZERO,
                     order_margin=constants.ZERO,
                     position_margin=constants.ZERO,
                     unrealized_pnl=constants.ZERO)


def test_restore_available():
    asset = future_asset.FutureAsset(ASSET_CURRENCY_NAME, available=constants.ONE, total=constants.ONE_HUNDRED)
    assert not asset.available == asset.total
    asset.restore_available()
    assert asset.available == asset.total == constants.ONE_HUNDRED


def test_reset():
    asset = future_asset.FutureAsset(ASSET_CURRENCY_NAME,
                                     available=constants.ONE_HUNDRED, total=constants.ONE_HUNDRED,
                                     initial_margin=constants.ONE_HUNDRED, wallet_balance=constants.ONE_HUNDRED,
                                     order_margin=constants.ONE_HUNDRED, position_margin=constants.ONE_HUNDRED)
    assert asset.available == asset.total == asset.initial_margin == asset.wallet_balance == asset.position_margin \
           == asset.order_margin == constants.ONE_HUNDRED
    asset.reset()
    assert asset.available == asset.total == asset.initial_margin == asset.wallet_balance == asset.position_margin \
           == asset.order_margin == constants.ZERO


def test_restore():
    asset = future_asset.FutureAsset(ASSET_CURRENCY_NAME, total=constants.ONE_HUNDRED, available=constants.ONE_HUNDRED,
                                     order_margin=constants.ZERO,
                                     initial_margin=constants.ONE_HUNDRED, wallet_balance=constants.ONE_HUNDRED,
                                     position_margin=constants.ZERO)
    asset.update(total=-decimal.Decimal(50))
    assert asset.total == decimal.Decimal(50)
    with pytest.raises(errors.PortfolioNegativeValueError):
        asset.update(total=-decimal.Decimal(70))
    assert asset.total == decimal.Decimal(50)

    asset.update(position_margin=decimal.Decimal(2.5))
    assert asset.position_margin == decimal.Decimal(2.5)
    asset.update(position_margin=decimal.Decimal(2.5))
    assert asset.position_margin == decimal.Decimal(5)
    assert asset.available == decimal.Decimal(45)
    with pytest.raises(errors.PortfolioNegativeValueError):
        asset.update(position_margin=decimal.Decimal(46))
    assert asset.position_margin == decimal.Decimal(5)
    assert asset.available == decimal.Decimal(45)


def test_get_total_holdings():
    asset = future_asset.FutureAsset(ASSET_CURRENCY_NAME, available=decimal.Decimal(12), total=constants.ONE_HUNDRED, wallet_balance=decimal.Decimal(42))
    assert asset.get_total_holdings() == decimal.Decimal(42)
