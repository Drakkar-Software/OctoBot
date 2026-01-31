# pylint: disable=E0611
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

import octobot_trading.exchange_channel as exchange_channel
import octobot_trading.constants as constants
import octobot_trading.personal_data.orders.channel.orders_updater as orders_updater


class OrdersUpdaterSimulator(orders_updater.OrdersUpdater):
    async def start(self):
        # on simulator, orders are fetched from the start
        self.channel.exchange_manager.exchange_personal_data.on_completed_orders_fetch()
        await exchange_channel.get_chan(constants.RECENT_TRADES_CHANNEL, self.channel.exchange_manager.id) \
            .new_consumer(self.ignore_recent_trades_update)
        for symbol in self.channel.exchange_manager.exchange_config.traded_symbol_pairs:
            self._set_initialized_event(symbol)

    async def ignore_recent_trades_update(self, exchange: str, exchange_id: str,
                                          cryptocurrency: str, symbol: str, recent_trades: list):
        """
        Used to subscribe at least one recent trades consumer during backtesting
        """

    async def _restore_required_virtual_orders(self):
        # nothing to do
        pass
