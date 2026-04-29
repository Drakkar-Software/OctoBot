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
from octobot_trading.personal_data import OptionPortfolio


def test_create_currency_asset():
    portfolio = OptionPortfolio("test_exchange")
    
    # Test with default values
    asset = portfolio.create_currency_asset("BTC")
    assert isinstance(asset, option_asset.OptionAsset)
    assert asset.name == "BTC"
    assert asset.available == constants.ZERO
    assert asset.total == constants.ZERO
    
    # Test with custom values
    asset = portfolio.create_currency_asset("USDT", available=decimal.Decimal(100), total=decimal.Decimal(200))
    assert isinstance(asset, option_asset.OptionAsset)
    assert asset.name == "USDT"
    assert asset.available == decimal.Decimal(100)
    assert asset.total == decimal.Decimal(200)
    
    # Test with different currency
    asset = portfolio.create_currency_asset("ETH", available=decimal.Decimal(5.5), total=decimal.Decimal(10.5))
    assert isinstance(asset, option_asset.OptionAsset)
    assert asset.name == "ETH"
    assert asset.available == decimal.Decimal(5.5)
    assert asset.total == decimal.Decimal(10.5)
