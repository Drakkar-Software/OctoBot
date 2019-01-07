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

class Trade:
    def __init__(self, exchange, order):
        self.currency, self.market = order.get_currency_and_market()
        self.quantity = order.get_filled_quantity()
        self.price = order.get_filled_price()
        self.order_type = order.get_order_type()
        self.final_status = order.get_status()
        self.fee = order.get_fee()
        self.order_id = order.get_id()
        self.side = order.get_side()

        self.creation_time = order.get_creation_time()
        self.canceled_time = order.get_canceled_time()
        self.filled_time = order.get_executed_time()
        self.symbol = order.get_order_symbol()

        self.simulated = order.trader.simulate

        self.exchange = exchange

    def get_price(self):
        return self.price

    def get_symbol(self):
        return self.symbol

    def get_order_id(self):
        return self.order_id

    def get_exchange_name(self):
        return self.exchange.get_name()

    def get_quantity(self):
        return self.quantity

    def get_currency(self):
        return self.currency

    def get_market(self):
        return self.market

    def get_fee(self):
        return self.fee

    def get_final_status(self):
        return self.final_status

    def get_canceled_time(self):
        return self.canceled_time

    def get_filled_time(self):
        return self.filled_time

    def get_creation_time(self):
        return self.creation_time

    def get_order_type(self):
        return self.order_type

    def get_simulated(self):
        return self.simulated

    def get_side(self):
        return self.side
