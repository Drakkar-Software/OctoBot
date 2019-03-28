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

import asyncio
from concurrent.futures import CancelledError
import copy
from ccxt.async_support import BaseError, InsufficientFunds

from backtesting import backtesting_enabled
from config import ORDER_REFRESHER_TIME, OrderStatus, ORDER_REFRESHER_TIME_WS, ExchangeConstantsTickersColumns as eC
from tools.logging.logging_util import get_logger
from trading.trader.order import Order, StopLossLimitOrder, StopLossOrder
from trading.exchanges.exchange_exceptions import MissingOrderException


class OrdersManager:
    """ OrdersManager class will perform the supervision of each open order of the exchange trader
    Data updating process is generic but a specific implementation is called for each type of order
    (TraderOrderTypeClasses)
    The task will perform this data update and the open orders status check each ORDER_REFRESHER_TIME seconds
    This class is particularly needed when exchanges doesn't offer stop loss orders
    This class has an essential role for the trader simulator """

    def __init__(self, config, trader):
        self.config = config
        self.keep_running = True
        self.trader = trader
        self.order_list = []
        self.last_symbol_prices = {}
        self.logger = get_logger(f"{self.__class__.__name__}{'Simulator' if self.trader.simulate else ''}"
                                 f"[{self.trader.exchange.get_name()}]")

        if self.trader.get_exchange().is_web_socket_available():
            self.order_refresh_time = ORDER_REFRESHER_TIME_WS
        else:
            self.order_refresh_time = ORDER_REFRESHER_TIME

    def add_order_to_list(self, order):
        if self.should_add_order(order):
            self.order_list.append(order)
            self.logger.debug(f"Order added to open orders (total: {len(self.order_list)} open order"
                              f"{'s' if len(self.order_list) > 1 else ''})")
        else:
            self.logger.debug(f"Order not added to open orders (already in open order: {self._order_in_list(order)}) "
                              f"(total: {len(self.order_list)} open order{'s' if len(self.order_list) > 1 else ''})")

    def should_add_order(self, order):
        return not self._order_in_list(order) and \
               (self.trader.simulate or not self._already_has_real_or_linked_order(order))

    def _order_in_list(self, order):
        return order in self.order_list

    def _already_has_real_or_linked_order(self, order):
        if order.get_id() is not None:
            return self.has_order_id_in_list(order.get_id())
        else:
            return (isinstance(order, (StopLossLimitOrder, StopLossOrder)) and
                    self._already_an_order_linked_to_these_real_orders(order.get_linked_orders())
                    )

    def _already_an_order_linked_to_these_real_orders(self, linked_orders):
        target_linked_ids = set(linked.get_id() for linked in linked_orders)
        return \
            any(order for order in self.order_list
                if order.linked_orders and set(linked.get_id() for linked in order.linked_orders) == target_linked_ids)

    def has_order_id_in_list(self, order_id):
        return any([order.get_id() == order_id for order in self.order_list])

    def get_orders_with_symbol(self, symbol):
        return [order for order in self.order_list if order.symbol == symbol]

    def remove_order_from_list(self, order):
        """
        Remove the specified order of the current open_order list (when the order is filled or canceled)
        """
        try:
            if self._order_in_list(order):
                self.order_list.remove(order)
                self.logger.debug(f"{order.get_order_symbol()} {order.get_name()} (ID : {order.get_id()}) "
                                  f"removed on {self.trader.get_exchange().get_name()}")
            else:
                self.logger.warning(f"Trying to remove order from order manager which is not in order_manager list: "
                                    f"{order.get_order_symbol()} {order.get_name()} (ID : {order.get_id()} "
                                    f"on {self.trader.get_exchange().get_name()}")
        except Exception as e:
            self.logger.error(str(e))
            self.logger.exception(e)

    def stop(self):
        self.keep_running = False

    async def _update_last_symbol_list(self, uniformize_timestamps=False):
        """
        Update each open order symbol with exchange data
        """
        updated = []
        task_list = []
        for order in self.order_list:
            if isinstance(order, Order) and order.get_order_symbol() not in updated:
                task_list.append(self._update_last_symbol_prices(order.get_order_symbol(), uniformize_timestamps))

                updated.append(order.get_order_symbol())
        try:
            await asyncio.gather(*task_list)
        except CancelledError:
            self.logger.info("Update last symbol price tasks cancelled.")

    async def _update_last_symbol_prices(self, symbol, uniformize_timestamps=False):
        """
        Ask to update a specific symbol with exchange data
        """

        exchange = self.trader.get_exchange()

        if backtesting_enabled(self.config):
            last_symbol_price = await self.trader.get_exchange().get_recent_trades(symbol)

        # Exchange call when not backtesting
        else:
            last_symbol_price = []
            try:
                last_symbol_price = await exchange.get_recent_trades(symbol)
            except BaseError as e:
                self.logger.warning(f"Failed to get recent trade: {e}, skipping simulated {symbol} order(s) update for "
                                    f"this time. Next update in {self.order_refresh_time} second(s).")
            if uniformize_timestamps and last_symbol_price:
                timestamp_sample = last_symbol_price[0][eC.TIMESTAMP.value]
                if exchange.get_exchange_manager().need_to_uniformize_timestamp(timestamp_sample):
                    for order in last_symbol_price:
                        order[eC.TIMESTAMP.value] = exchange.get_uniform_timestamp(order[eC.TIMESTAMP.value])

        # Check if exchange request failed
        if last_symbol_price:
            self.last_symbol_prices[symbol] = last_symbol_price

    def get_open_orders(self):
        return self.order_list

    def set_order_refresh_time(self, seconds):
        self.order_refresh_time = seconds

    # Currently called by backtesting
    # Will be called by Websocket to perform order status update if new data available
    # TODO : currently blocking, may implement queue if needed
    async def force_update_order_status(self, blocking=True, simulated_time=False):
        if blocking:
            return await self._update_orders_status(simulated_time=simulated_time)
        else:
            raise NotImplementedError("force_update_order_status(blocking=False) not implemented")

    async def _update_order_status(self, order, failed_order_updates, simulated_time=False):
        order_filled = False
        try:
            await order.update_order_status(simulated_time=simulated_time)

            if order.get_status() == OrderStatus.FILLED:
                order_filled = True
                self.logger.info(f"{order.get_order_symbol()} {order.get_name()} (ID : {order.get_id()})"
                                 f" filled on {self.trader.get_exchange().get_name()} "
                                 f"at {order.get_filled_price()}")
                await order.close_order()
        except MissingOrderException as e:
            self.logger.error(f"Missing exchange order when updating order with id: {e.order_id}. "
                              f"Will force a real trader refresh. ({e})")
            failed_order_updates.append(e.order_id)
        except InsufficientFunds as e:
            self.logger.error(f"Not enough funds to create order: {e} (updating {order}).")
        return order_filled

    async def _update_orders_status(self, simulated_time=False):
        """
        Prepare order status updating by getting price data
        then ask orders to check their status
        Finally ask cancellation and filling process if it is required
        """

        failed_order_updates = []
        # update all prices
        await self._update_last_symbol_list(True)

        for order in copy.copy(self.order_list):

            order_filled = False
            try:
                # ask orders to update their status
                async with order.get_lock():
                    odr = order
                    # update symbol prices from exchange
                    if odr.get_order_symbol() in self.last_symbol_prices:
                        odr.set_last_prices(self.last_symbol_prices[odr.get_order_symbol()])

                    if odr in self.order_list:
                        order_filled = await self._update_order_status(odr, failed_order_updates, simulated_time)
            except Exception as e:
                raise e
            finally:
                # ensure always call fill callback
                if order_filled:
                    await self.trader.call_order_update_callback(order)
        return failed_order_updates

    async def poll_update(self):
        """
        Async method that will periodically update orders status with update_orders_status
        Should never be called in backtesting
        """
        while self.keep_running:
            try:
                # call update status
                failed_order_updates = await self._update_orders_status()
                if failed_order_updates:
                    self.logger.info(f"Forcing real trader refresh.")
                    self.trader.force_refresh_orders_and_portfolio()
            except Exception as e:
                self.logger.error(f"Error when updating orders ({e})")
                self.logger.exception(e)

            await asyncio.sleep(self.order_refresh_time)
