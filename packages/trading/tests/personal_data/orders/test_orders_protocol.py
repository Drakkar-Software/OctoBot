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

import mock

import octobot_trading.personal_data.orders.protocol as orders_protocol_module


class TestOpenOrderExchangeIdsFromProtocolOrders:
    def test_extracts_exchange_ids_from_protocol_orders(self):
        protocol_orders = [
            mock.Mock(exchange_id="order-1"),
            mock.Mock(exchange_id=None),
            mock.Mock(exchange_id="order-2"),
        ]
        exchange_ids = orders_protocol_module.open_order_exchange_ids_from_protocol_orders(
            protocol_orders,
        )
        assert exchange_ids == {"order-1", "order-2"}
