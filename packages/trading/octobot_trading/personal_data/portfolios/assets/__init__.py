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

from octobot_trading.personal_data.portfolios.assets import future_asset
from octobot_trading.personal_data.portfolios.assets import option_asset
from octobot_trading.personal_data.portfolios.assets import margin_asset
from octobot_trading.personal_data.portfolios.assets import spot_asset

from octobot_trading.personal_data.portfolios.assets.future_asset import (
    FutureAsset,
)
from octobot_trading.personal_data.portfolios.assets.option_asset import (
    OptionAsset,
)
from octobot_trading.personal_data.portfolios.assets.margin_asset import (
    MarginAsset,
)
from octobot_trading.personal_data.portfolios.assets.spot_asset import (
    SpotAsset,
)

__all__ = [
    "FutureAsset",
    "OptionAsset",
    "MarginAsset",
    "SpotAsset",
]
