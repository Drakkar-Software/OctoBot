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

import octobot_trading.constants as constants
import octobot_trading.personal_data.portfolios.assets.option_asset as option_asset

ASSET_CURRENCY_NAME = "BTC"


def test_str():
    asset = option_asset.OptionAsset(ASSET_CURRENCY_NAME, constants.ZERO, constants.ZERO)
    result = str(asset)
    assert "OptionAsset" in result
    assert ASSET_CURRENCY_NAME in result
    assert "Available: 0.0" in result
    assert "Total: 0.0" in result
    assert "Initial Margin: 0.0" in result
    assert "Wallet Balance: 0.0" in result
    assert "Unrealized PNL: 0.0" in result
    assert "Order Margin: 0.0" in result
    assert "Position Margin: 0.0" in result

    asset = option_asset.OptionAsset(ASSET_CURRENCY_NAME,
                                     available=decimal.Decimal(10),
                                     total=decimal.Decimal(100),
                                     initial_margin=decimal.Decimal(20),
                                     wallet_balance=decimal.Decimal(80),
                                     position_margin=decimal.Decimal(15),
                                     order_margin=decimal.Decimal(5),
                                     unrealized_pnl=decimal.Decimal(25))
    result = str(asset)
    assert "OptionAsset" in result
    assert ASSET_CURRENCY_NAME in result
    assert "Available: 10.0" in result
    assert "Total: 100.0" in result
    assert "Initial Margin: 20.0" in result
    assert "Wallet Balance: 80.0" in result
    assert "Unrealized PNL: 25.0" in result
    assert "Order Margin: 5.0" in result
    assert "Position Margin: 15.0" in result
