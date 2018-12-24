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

from config import *


class ExchangePersonalData:
    _MAX_ORDERS_COUNT = 20000

    # note: symbol keys are without /
    def __init__(self):
        self.portfolio = {}
        self.orders = {}

        self.portfolio_is_initialized = False
        self.orders_are_initialized = False

    def update_portfolio(self, currency, total, available, in_order):
        self.portfolio[currency] = {
            CONFIG_PORTFOLIO_FREE: available,
            CONFIG_PORTFOLIO_USED: in_order,
            CONFIG_PORTFOLIO_TOTAL: total
        }

    def init_portfolio(self):
        self.portfolio_is_initialized = True

    def init_orders(self):
        self.orders_are_initialized = True

    def get_portfolio_is_initialized(self):
        return self.portfolio_is_initialized

    def get_orders_are_initialized(self):
        return self.orders_are_initialized

    def set_portfolio(self, portfolio):
        self.portfolio = portfolio

    def get_portfolio(self):
        return self.portfolio

    def has_order(self, order_id):
        return order_id in self.orders

    def upsert_orders(self, orders):
        for order in orders:
            self.upsert_order(order["id"], order)

    def upsert_order(self, order_id, ccxt_order):
        self.orders[order_id] = ccxt_order
        if len(self.orders) > self._MAX_ORDERS_COUNT:
            self.remove_oldest_orders(int(self._MAX_ORDERS_COUNT / 2))

    def remove_oldest_orders(self, nb_to_remove):
        time_sorted_orders = sorted(self.orders.values(), key=lambda x: x["timestamp"])
        shrinked_list = [time_sorted_orders[i]
                         for i in range(0, nb_to_remove)
                         if (time_sorted_orders[i]["status"] == OrderStatus.OPEN.value
                             or time_sorted_orders[i]["status"] == OrderStatus.PARTIALLY_FILLED.value)]

        shrinked_list += [time_sorted_orders[i] for i in range(nb_to_remove, len(time_sorted_orders))]
        self.orders = {order["id"]: order for order in shrinked_list}

    def get_all_orders(self, symbol, since, limit):
        return self._select_orders(None, symbol, since, limit)

    def get_open_orders(self, symbol, since, limit):
        return self._select_orders(OrderStatus.OPEN.value, symbol, since, limit)

    def get_closed_orders(self, symbol, since, limit):
        return self._select_orders(OrderStatus.CLOSED.value, symbol, since, limit)

    def get_my_recent_trades(self, symbol, since, limit):
        # TODO
        return None

    def get_order(self, order_id):
        return self.orders[order_id]

    # private methods
    def _select_orders(self, state, symbol, since, limit):
        orders = [
            order
            for order in self.orders.values()
            if (
                    (state is None or order["status"] == state) and
                    (symbol is None or (symbol and order["symbol"] == symbol)) and
                    (since is None or (since and order['timestamp'] < since))
            )
        ]
        if limit is not None:
            return orders[0:limit]
        else:
            return orders
