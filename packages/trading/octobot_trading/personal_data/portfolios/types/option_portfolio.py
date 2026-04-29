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
import octobot_trading.constants as constants

import octobot_trading.personal_data.portfolios.assets.option_asset as option_asset
import octobot_trading.personal_data.portfolios.types as types


class OptionPortfolio(types.FuturePortfolio):
    def create_currency_asset(self, currency, available=constants.ZERO, total=constants.ZERO):
        return option_asset.OptionAsset(name=currency, available=available, total=total)
