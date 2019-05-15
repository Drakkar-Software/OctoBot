# #  Drakkar-Software OctoBot
# #  Copyright (c) Drakkar-Software, All rights reserved.
# #
# #  This library is free software; you can redistribute it and/or
# #  modify it under the terms of the GNU Lesser General Public
# #  License as published by the Free Software Foundation; either
# #  version 3.0 of the License, or (at your option) any later version.
# #
# #  This library is distributed in the hope that it will be useful,
# #  but WITHOUT ANY WARRANTY; without even the implied warranty of
# #  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# #  Lesser General Public License for more details.
# #
# #  You should have received a copy of the GNU Lesser General Public
# #  License along with this library.
import copy

from ccxt import InsufficientFunds

from core.channels import RECENT_TRADES_CHANNEL
from core.channels.exchange_channel import ExchangeChannel, ExchangeChannels
from core.producers.exchange.orders_updater import OrdersUpdater
from core.producers.exchange.simulator.exchange_updater_simulator import ExchangeUpdaterSimulator
from trading.exchanges import MissingOrderException
from trading.exchanges.data.exchange_personal_data import ExchangePersonalData
from config import OrderStatus, SIMULATOR_LAST_PRICES_TO_CHECK
from trading.trader.order import Order


class OrdersUpdaterSimulator(OrdersUpdater, ExchangeUpdaterSimulator):

    def __init__(self, channel: ExchangeChannel):
        ExchangeUpdaterSimulator.__init__(self, channel)
        OrdersUpdater.__init__(self, channel)
        self.exchange_personal_data: ExchangePersonalData = self.exchange_manager.exchange_dispatcher.get_exchange_personal_data()

        ExchangeChannels.get_chan(RECENT_TRADES_CHANNEL, self.exchange.get_name()).new_consumer(
            self.handle_recent_trade,
            filter_size=True)

    async def handle_recent_trade(self, symbol: str, recent_trade: dict):
        last_prices = self.exchange_manager.exchange_dispatcher.get_symbol_data(symbol=symbol) \
            .get_symbol_recent_trades(limit=SIMULATOR_LAST_PRICES_TO_CHECK)

        failed_order_updates = await self._update_orders_status(symbol=symbol, last_prices=last_prices)

        if failed_order_updates:
            self.logger.info(f"Forcing real trader refresh.")
            self.exchange_manager.trader.force_refresh_orders_and_portfolio()

    async def _update_order_status(self,
                                   order: Order,
                                   failed_order_updates: list,
                                   last_prices: list,
                                   simulated_time: bool = False):
        order_filled = False
        try:
            await order.update_order_status(last_prices, simulated_time=simulated_time)

            if order.get_status() == OrderStatus.FILLED:
                order_filled = True
                self.logger.info(f"{order.get_order_symbol()} {order.get_name()} (ID : {order.get_id()})"
                                 f" filled on {self.exchange.get_name()} "
                                 f"at {order.get_filled_price()}")
                await order.close_order()
        except MissingOrderException as e:
            self.logger.error(f"Missing exchange order when updating order with id: {e.order_id}. "
                              f"Will force a real trader refresh. ({e})")
            failed_order_updates.append(e.order_id)
        except InsufficientFunds as e:
            self.logger.error(f"Not enough funds to create order: {e} (updating {order}).")
        return order_filled

    async def _update_orders_status(self, symbol: str,
                                    last_prices: list,
                                    simulated_time: bool = False) -> list:
        """
        Ask orders to check their status
        Ask cancellation and filling process if it is required
        """
        failed_order_updates = []
        for order in copy.copy(self.exchange_personal_data.orders.get_open_orders(symbol=symbol)):
            order_filled = False
            try:
                # ask orders to update their status
                async with order.get_lock():
                    order_filled = await self._update_order_status(order,
                                                                   failed_order_updates,
                                                                   last_prices,
                                                                   simulated_time=simulated_time)
            except Exception as e:
                raise e
            finally:
                # ensure always call fill callback
                if order_filled:
                    await self.exchange_manager.trader.call_order_update_callback(order)
        return failed_order_updates

    # Currently called by backtesting
    # Will be called by Websocket to perform order status update if new data available
    # TODO : currently blocking, may implement queue if needed
    async def force_update_order_status(self, blocking=True, simulated_time: bool = False):
        # if blocking:
        #     for symbol in self.exchange_manager.traded_pairs:
        #         return await self._update_orders_status(symbol=symbol, simulated_time=simulated_time)
        # else:
        #     raise NotImplementedError("force_update_order_status(blocking=False) not implemented")
        #  TODO
        pass
