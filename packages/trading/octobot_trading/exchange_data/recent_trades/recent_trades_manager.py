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
import collections

import octobot_commons.logging as logging

import octobot_trading.util as util


class RecentTradesManager(util.Initializable):
    MAX_RECENT_TRADES_COUNT = 100
    MAX_LIQUIDATIONS_COUNT = 20

    def __init__(self):
        super().__init__()
        self.logger: logging.BotLogger = logging.get_logger(self.__class__.__name__)
        self.recent_trades: collections.deque[dict] = collections.deque(maxlen=self.MAX_RECENT_TRADES_COUNT)
        self.liquidations: collections.deque[dict] = collections.deque(maxlen=self.MAX_LIQUIDATIONS_COUNT)
        self._reset_recent_trades()

    async def initialize_impl(self):
        self._reset_recent_trades()

    def set_all_recent_trades(self, recent_trades):
        if recent_trades:
            self.recent_trades = recent_trades
            return self.recent_trades

    def add_new_trades(self, recent_trades):
        if recent_trades:
            new_recent_trades: list = [
                trade
                for trade in recent_trades
                if trade not in self.recent_trades
            ]
            self.recent_trades.extend(new_recent_trades)
            return new_recent_trades

    def add_new_liquidations(self, liquidations):
        if liquidations:
            new_liquidations: list = [
                liquidation
                for liquidation in liquidations
                if liquidation not in self.liquidations]
            self.liquidations.extend(new_liquidations)
            return new_liquidations

    def _reset_recent_trades(self):
        self.recent_trades = collections.deque(maxlen=self.MAX_RECENT_TRADES_COUNT)
        self.liquidations = collections.deque(maxlen=self.MAX_LIQUIDATIONS_COUNT)
