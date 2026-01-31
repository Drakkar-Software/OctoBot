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
import octobot_commons.logging as logging

import octobot_trading.util as util


class MarketsManager(util.Initializable):
    def __init__(self):  # Required for python development
        super().__init__()
        self.logger: logging.BotLogger = logging.get_logger(self.__class__.__name__)
        self.markets: dict[str, any] = {}

    async def initialize_impl(self):
        self._reset_kline()

    def _reset_kline(self):
        self.markets = {}

    def markets_update(self, markets):
        self.markets = markets
