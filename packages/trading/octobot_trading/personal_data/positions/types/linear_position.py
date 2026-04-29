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
import decimal

import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.personal_data.positions.position as position_class


class LinearPosition(position_class.Position):
    def update_value(self):
        """
        Notional value = CONTRACT_QUANTITY * MARK_PRICE
        """
        self.value = self.size * self.mark_price

    def get_unrealized_pnl(self, price):
        """
        LONG_PNL = CONTRACT_QUANTITY x [MARK_PRICE - ENTRY_PRICE]
        SHORT_PNL = CONTRACT_QUANTITY x [ENTRY_PRICE - MARK_PRICE]
        :param price: the pnl calculation price
        :return: the unrealized pnl
        """
        # ensure update validity
        if price <= constants.ZERO or self.entry_price <= constants.ZERO:
            return constants.ZERO
        if self.is_long():
            return self.size * (price - self.entry_price)
        if self.is_short():
            return -self.size * (self.entry_price - price)
        return constants.ZERO

    def get_margin_from_size(self, size):
        """
        Calculates margin from size : margin = (Position quantity x entry price) / leverage
        """
        return (size * self.entry_price) / self.symbol_contract.current_leverage

    def get_size_from_margin(self, margin):
        """
        Calculates size from margin : size = (margin x leverage) / entry price
        """
        return (margin * self.symbol_contract.current_leverage) / self.entry_price

    def calculate_maintenance_margin(self):
        """
        :return: Maintenance margin = Position quantity x entry price x Maintenance margin rate
        """
        return self.size * self.entry_price * self.symbol_contract.maintenance_margin_rate

    def update_isolated_liquidation_price(self):
        """
        Updates isolated position liquidation price
        LONG LIQUIDATION PRICE = ENTRY_PRICE * (1 - Initial Margin Rate + MAINTENANCE_MARGIN_RATE)
        SHORT LIQUIDATION PRICE = ENTRY_PRICE * (1 + Initial Margin Rate - MAINTENANCE_MARGIN_RATE)
        - Long : - Extra Margin Added/ Contract Size
        - Short : + Extra Margin Added/ Contract Size
        """
        try:
            if self.is_long():
                self.liquidation_price = self.entry_price * (
                        constants.ONE - self.get_initial_margin_rate() + self.symbol_contract.maintenance_margin_rate)
            elif self.is_short():
                self.liquidation_price = self.entry_price * (
                        constants.ONE + self.get_initial_margin_rate() - self.symbol_contract.maintenance_margin_rate)
            else:
                self.liquidation_price = constants.ZERO
            self.update_fee_to_close()
        except (decimal.DivisionByZero, decimal.InvalidOperation):
            self.liquidation_price = constants.ZERO

    def get_bankruptcy_price(self, price, side, with_mark_price=False):
        """
        :param price: the price to compute bankruptcy from
        :param side: the side of the position
        :param with_mark_price: if price should be mark price instead of entry price
        :return: Bankruptcy Price
        Long position = Entry Price x (1 - Initial Margin Rate)
        Short position = Entry Price × (1 + Initial Margin Rate)
        """
        if side is enums.PositionSide.LONG:
            return self.mark_price if with_mark_price else \
                price * (constants.ONE - self.get_initial_margin_rate())
        elif side is enums.PositionSide.SHORT:
            return self.mark_price if with_mark_price else \
                price * (constants.ONE + self.get_initial_margin_rate())
        return constants.ZERO

    def get_fee_to_open(self, quantity, price, symbol):
        """
        :return: Fee to open = (Quantity * Mark Price) x Taker fee
        """
        return quantity * price * self.get_taker_fee(symbol)

    def get_fee_to_close(self, quantity, price, side, symbol, with_mark_price=False):
        """
        :return: Fee to close = (Quantity * Bankruptcy price) x Taker fee
        """
        return abs(quantity) * self.get_bankruptcy_price(price, side, with_mark_price=with_mark_price) * \
            self.get_taker_fee(symbol)

    def get_order_cost(self):
        """
        :return: Order Cost = Initial Margin + Two-Way Taker Fee
        """
        return self.initial_margin + self.get_two_way_taker_fee()

    def update_fee_to_close(self):
        """
        :return: Fee to close = (Quantity * Bankruptcy Price derived from mark price) x Taker fee
        """
        self.fee_to_close = self.get_fee_to_close(self.size, self.entry_price, self.side, self.symbol,
                                                  with_mark_price=True)
        self._update_margin()

    def update_average_entry_price(self, update_size, update_price):
        """
        Average entry price = total contract value in market / total quantity of contracts
        Total contract value in market = [(Current position quantity * Current position entry price)
                                          + (Update quantity * Update price)]
        """
        total_contract_value = self.size + update_size
        self.entry_price = ((self.size * self.entry_price + update_size * update_price) /
                            (total_contract_value if total_contract_value != constants.ZERO else constants.ONE))
        if self.entry_price < constants.ZERO:
            self.entry_price = constants.ZERO

    def update_average_exit_price(self, update_size, update_price):
        """
        Average exit price = total contract value in market / total quantity of contracts
        Total contract value in market = [(Current position quantity * Current position exit price)
                                          + (Update quantity * Update price)]
        """
        if self.exit_price == constants.ZERO:
            self.exit_price = update_price
        else:
            total_contract_value = self.already_reduced_size + update_size
            self.exit_price = ((self.already_reduced_size * self.exit_price + update_size * update_price) /
                               (total_contract_value if total_contract_value != constants.ZERO else constants.ONE))
        if self.exit_price < constants.ZERO:
            self.exit_price = constants.ZERO

    @staticmethod
    def is_inverse():
        return False
