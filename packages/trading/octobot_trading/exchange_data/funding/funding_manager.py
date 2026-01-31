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

import octobot_commons.logging as logging
import octobot_trading.constants as constants
import octobot_trading.util as util


class FundingManager(util.Initializable):
    def __init__(self):
        super().__init__()
        self.logger: logging.BotLogger = logging.get_logger(self.__class__.__name__)
        self.funding_rate: decimal.Decimal = constants.NaN
        self.predicted_funding_rate: decimal.Decimal = constants.NaN
        self.next_update: float = 0
        self.last_updated: float = 0
        self.reset_funding()

    async def initialize_impl(self):
        self.reset_funding()

    def initialized(self):
        return self.funding_rate.is_nan()

    def reset_funding(self):
        self.funding_rate = constants.NaN
        self.predicted_funding_rate = constants.NaN
        self.next_update = 0
        self.last_updated = 0

    def funding_update(self, funding_rate, predicted_funding_rate, next_funding_time, timestamp):
        if funding_rate and next_funding_time:
            self.funding_rate = funding_rate
            self.predicted_funding_rate = predicted_funding_rate
            self.next_update = next_funding_time
            self.last_updated = timestamp
