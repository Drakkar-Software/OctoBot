#  Drakkar-Software OctoBot
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

from config import CONFIG_ENABLED_OPTION, CONFIG_SIMULATOR, SIMULATOR_TRADER_STR
from trading.trader.trader import Trader

""" TraderSimulator has a role of exchange response simulator
- During order creation / filling / canceling process"""


class TraderSimulator(Trader):
    def __init__(self, config, exchange, order_refresh_time=None):
        self.simulate = True
        super().__init__(config, exchange, order_refresh_time)

        self.trader_type_str = SIMULATOR_TRADER_STR

    @staticmethod
    def enabled(config):
        return config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION]
