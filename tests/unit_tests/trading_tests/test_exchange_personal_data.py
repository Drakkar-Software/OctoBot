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

import time

from config import CONFIG_PORTFOLIO_FREE, CONFIG_PORTFOLIO_USED, CONFIG_PORTFOLIO_TOTAL, OrderStatus
from octobot_trading.exchanges.data.exchange_personal_data import ExchangePersonalData


class TestExchangePersonalData:
    def test_update_portfolio(self):
        test_inst = ExchangePersonalData()

        # without pf
        test_inst.portfolio = {}
        test_inst.update_portfolio("BTC", 10, 7, 3)
        assert test_inst.portfolio["BTC"][CONFIG_PORTFOLIO_FREE] == 7
        assert test_inst.portfolio["BTC"][CONFIG_PORTFOLIO_USED] == 3
        assert test_inst.portfolio["BTC"][CONFIG_PORTFOLIO_TOTAL] == 10

        # with pf
        test_inst.update_portfolio("ETH", 100, 60, 40)
        assert test_inst.portfolio["BTC"][CONFIG_PORTFOLIO_FREE] == 7
        assert test_inst.portfolio["BTC"][CONFIG_PORTFOLIO_USED] == 3
        assert test_inst.portfolio["BTC"][CONFIG_PORTFOLIO_TOTAL] == 10
        assert test_inst.portfolio["ETH"][CONFIG_PORTFOLIO_FREE] == 60
        assert test_inst.portfolio["ETH"][CONFIG_PORTFOLIO_USED] == 40
        assert test_inst.portfolio["ETH"][CONFIG_PORTFOLIO_TOTAL] == 100

    def test_has_order(self):
        test_inst = ExchangePersonalData()

        # without orders
        test_inst.orders = {}
        assert not test_inst.has_order(10)
        test_inst.orders[10] = self.create_fake_order(10, None, None, None)
        assert test_inst.has_order(10)
        assert not test_inst.has_order(153)

    def test_upsert_order(self):
        test_inst = ExchangePersonalData()

        # without orders
        test_inst.orders = {}
        assert not test_inst.has_order(10)
        test_inst.upsert_order(10, None)
        assert test_inst.has_order(10)

    def test_set_orders(self):
        test_inst = ExchangePersonalData()

        # without orders
        test_inst.orders = {}
        assert not test_inst.has_order(10)
        assert not test_inst.has_order(20)
        test_inst.upsert_orders([
            {"id": 15},
            {"id": 10},
            {"id": 20},
            {"id": 15}
        ])
        assert test_inst.get_order(15)
        assert test_inst.has_order(15)
        assert test_inst.has_order(20)
        assert test_inst.has_order(10)
        assert not test_inst.has_order(12)
        assert not test_inst.has_order(30)

    def test_set_more_than_max_count_orders(self):
        test_inst = ExchangePersonalData()
        test_inst.orders = {}
        test_inst._MAX_ORDERS_COUNT = 500
        nb_max_stored_orders = test_inst._MAX_ORDERS_COUNT

        max_timestamp = 0
        for i in range(nb_max_stored_orders):
            time_stamp = time.time()
            test_inst.upsert_order(i, {"id": i,
                                       "timestamp": time_stamp,
                                       "status": OrderStatus.CLOSED.value})
            if i == nb_max_stored_orders/2:
                max_timestamp = time_stamp
            time.sleep(0.000000001)

        assert len(test_inst.orders) == nb_max_stored_orders
        test_inst.upsert_order(nb_max_stored_orders+1, {"id": nb_max_stored_orders+1,
                                                        "timestamp": time.time(),
                                                        "status": OrderStatus.CLOSED.value})

        assert not [order for order in test_inst.orders.values() if order["timestamp"] < max_timestamp]

        assert len(test_inst.orders) == nb_max_stored_orders/2+1

    @staticmethod
    def create_fake_order(o_id, status, symbol, timestamp):
        return {
            "id": o_id,
            "status": status,
            "symbol": symbol,
            "timestamp": timestamp
        }

    def test_select_orders(self):
        test_inst = ExchangePersonalData()

        symbol_1 = "BTC/USDT"
        symbol_2 = "ETH/BTC"
        symbol_3 = "ETH/USDT"

        # without orders
        test_inst.orders = {}
        assert test_inst.get_all_orders(symbol_1, None, None) == []
        assert test_inst.get_open_orders(symbol_2, None, None) == []
        assert test_inst.get_closed_orders(symbol_3, None, None) == []

        order_1 = self.create_fake_order(10, OrderStatus.CLOSED.value, symbol_1, 0)
        test_inst.upsert_order(10, order_1)
        assert test_inst.get_all_orders(symbol_1, None, None) == [order_1]
        assert test_inst.get_open_orders(symbol_1, None, None) == []
        assert test_inst.get_closed_orders(symbol_1, None, None) == [order_1]

        order_2 = self.create_fake_order(100, OrderStatus.OPEN.value, symbol_3, 0)
        test_inst.upsert_order(100, order_2)
        assert test_inst.get_all_orders(symbol_3, None, None) == [order_2]
        assert test_inst.get_open_orders(symbol_3, None, None) == [order_2]
        assert test_inst.get_closed_orders(symbol_3, None, None) == []
        assert test_inst.get_all_orders(symbol_2, None, None) == []
        assert test_inst.get_open_orders(symbol_2, None, None) == []
        assert test_inst.get_closed_orders(symbol_2, None, None) == []
        assert test_inst.get_all_orders(None, None, None) == [order_1, order_2]
        assert test_inst.get_open_orders(None, None, None) == [order_2]
        assert test_inst.get_closed_orders(None, None, None) == [order_1]

        order_3 = self.create_fake_order(10, OrderStatus.OPEN.value, symbol_2, 0)
        test_inst.upsert_order(10, order_3)
        assert test_inst.get_all_orders(symbol_2, None, None) == [order_3]
        assert test_inst.get_open_orders(symbol_2, None, None) == [order_3]
        assert test_inst.get_closed_orders(symbol_2, None, None) == []
        assert test_inst.get_all_orders(None, None, None) == [order_3, order_2]
        assert test_inst.get_open_orders(None, None, None) == [order_3, order_2]
        assert test_inst.get_closed_orders(None, None, None) == []
        assert test_inst.get_all_orders(symbol_1, None, None) == []
        assert test_inst.get_open_orders(symbol_1, None, None) == []
        assert test_inst.get_closed_orders(symbol_1, None, None) == []
        assert test_inst.get_all_orders(symbol_3, None, None) == [order_2]
        assert test_inst.get_open_orders(symbol_3, None, None) == [order_2]
        assert test_inst.get_closed_orders(symbol_3, None, None) == []

        order_4 = self.create_fake_order(11, OrderStatus.OPEN.value, symbol_1, 100)
        order_5 = self.create_fake_order(12, OrderStatus.CLOSED.value, symbol_2, 1000)
        order_6 = self.create_fake_order(13, OrderStatus.CLOSED.value, symbol_3, 50)
        test_inst.upsert_orders([order_4, order_5, order_6])
        assert test_inst.get_all_orders(symbol_1, None, None) == [order_4]
        assert test_inst.get_open_orders(symbol_1, None, None) == [order_4]
        assert test_inst.get_closed_orders(symbol_1, None, None) == []
        assert test_inst.get_all_orders(symbol_2, None, None) == [order_3, order_5]
        assert test_inst.get_open_orders(symbol_2, None, None) == [order_3]
        assert test_inst.get_closed_orders(symbol_2, None, None) == [order_5]
        assert test_inst.get_all_orders(symbol_3, None, None) == [order_2, order_6]
        assert test_inst.get_open_orders(symbol_3, None, None) == [order_2]
        assert test_inst.get_closed_orders(symbol_3, None, None) == [order_6]
        assert test_inst.get_all_orders(None, None, None) == [order_3, order_2, order_4, order_5, order_6]
        assert test_inst.get_open_orders(None, None, None) == [order_3, order_2, order_4]
        assert test_inst.get_closed_orders(None, None, None) == [order_5, order_6]

        # test limit
        assert test_inst.get_all_orders(None, None, 3) == [order_3, order_2, order_4]
        assert test_inst.get_open_orders(None, None, 3) == [order_3, order_2, order_4]
        assert test_inst.get_closed_orders(None, None, 3) == [order_5, order_6]

        # test timestamps
        assert test_inst.get_all_orders(None, 30, 3) == [order_3, order_2]
        assert test_inst.get_open_orders(None, 1000, None) == [order_3, order_2, order_4]
        assert test_inst.get_closed_orders(None, 60, 1) == [order_6]
