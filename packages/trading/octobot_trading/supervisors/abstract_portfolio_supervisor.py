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
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.supervisors.abstract_supervisor as abstract_supervisor


class AbstractPortfolioSupervisor(abstract_supervisor.AbstractSupervisor):
    @staticmethod
    def is_backtestable() -> bool:
        return True

    async def initialize(self) -> None:
        """
        Initialize balance channel consumer
        """
        self.consumers.append(await exchanges_channel.get_chan(
            trading_constants.BALANCE_CHANNEL, self.exchange_manager.id).new_consumer(self.on_balance_update))
        self.consumers.append(await exchanges_channel.get_chan(
            trading_constants.BALANCE_PROFITABILITY_CHANNEL, self.exchange_manager.id).new_consumer(
            self.on_balance_profitability_update))

    async def on_balance_update(self, exchange: str, exchange_id: str, balance):
        """
        Should be overwritten
        """

    async def on_balance_profitability_update(
            self,
            exchange: str,
            exchange_id: str,
            profitability,
            profitability_percent,
            market_profitability_percent,
            initial_portfolio_current_profitability,
    ):
        """
        Should be overwritten
        """
