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
import octobot_trading.constants as trading_constants


class BacktestingExchangeConfig:
    def __init__(self):
        # future trading config data
        self.future_contract_type = trading_constants.DEFAULT_SYMBOL_FUTURE_CONTRACT_TYPE
        self.option_contract_type = trading_constants.DEFAULT_SYMBOL_OPTION_CONTRACT_TYPE
        self.funding_rate = trading_constants.DEFAULT_SYMBOL_FUNDING_RATE
