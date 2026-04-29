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
import octobot_trading.errors as errors
import octobot_trading.enums as enums
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_commons.symbols as symbols


class TradePnl:
    def __init__(self, entries, closes):
        self.entries = entries
        self.closes = closes

    def get_entry_time(self) -> float:
        try:
            return min(
                entry.executed_time
                for entry in self.entries
            )
        except ValueError as err:
            raise errors.IncompletePNLError from err

    def get_close_time(self) -> float:
        try:
            return max(
                close.executed_time
                for close in self.closes
            )
        except ValueError as err:
            raise errors.IncompletePNLError from err

    def get_total_entry_quantity(self) -> decimal.Decimal:
        return sum(
            entry.executed_quantity
            for entry in self.entries
        ) or constants.ZERO

    def get_total_close_quantity(self) -> decimal.Decimal:
        return sum(
            close.executed_quantity
            for close in self.closes
        ) or constants.ZERO

    def get_entry_price(self) -> decimal.Decimal:
        try:
            return sum(
                entry.executed_price
                for entry in self.entries
            ) / len(self.entries)
        except ZeroDivisionError as err:
            raise errors.IncompletePNLError from err

    def get_close_price(self) -> decimal.Decimal:
        try:
            return sum(
                close.executed_price
                for close in self.closes
            ) / len(self.closes)
        except ZeroDivisionError as err:
            raise errors.IncompletePNLError from err

    def get_entry_total_cost(self):
        return self.get_entry_price() * self.get_total_entry_quantity()

    def get_close_total_cost(self):
        return self.get_close_price() * self.get_total_close_quantity()

    def get_close_ratio(self):
        try:
            if self.entries[0].side is enums.TradeOrderSide.BUY:
                return min(self.get_total_close_quantity() / self.get_total_entry_quantity(), constants.ONE)
            return min(self.get_close_total_cost() / self.get_entry_total_cost(), constants.ONE)
        except (IndexError, decimal.DivisionByZero, decimal.InvalidOperation) as err:
            raise errors.IncompletePNLError from err

    def get_closed_entry_value(self) -> decimal.Decimal:
        return self.get_entry_price() * self.get_total_entry_quantity()

    def get_closed_close_value(self) -> decimal.Decimal:
        return self.get_close_price() * self.get_closed_pnl_quantity()

    def get_closed_pnl_quantity(self):
        try:
            if self.entries[0].side is enums.TradeOrderSide.BUY:
                # entry is a buy, exit is a sell: take exit size capped at the entry size
                # (can't account in pnl for more than what has been bought)
                return min(self.get_total_close_quantity(), self.get_total_entry_quantity())
            # entry is a sell, exit is a buy: take closing size capped at the equivalent entry cost
            # (can't account in pnl for more than what has been sold for entry)
            entry_cost = self.get_entry_price() * self.get_total_entry_quantity()
            max_close_quantity = entry_cost / self.get_close_price()
            return min(self.get_total_close_quantity(), max_close_quantity)
        except IndexError as err:
            raise errors.IncompletePNLError from err

    def _get_fees(self, trade) -> decimal.Decimal:
        if not trade.fee:
            return constants.ZERO
        symbol = symbols.parse_symbol(trade.symbol)
        # return fees denominated in quote
        fees = order_util.get_fees_for_currency(trade.fee, symbol.quote)
        return fees \
            + order_util.get_fees_for_currency(trade.fee, symbol.base) * trade.executed_price

    def get_paid_special_fees_by_currency(self) -> dict:
        """
        :return: a dict containing fees paid in currencies different from the base or quote of the trades pair
        values are not converted into base currency of the trading pair
        """
        if not self.entries:
            return {}
        try:
            fees = {}
            base_and_quote = symbols.parse_symbol(self.entries[0].symbol).base_and_quote()
            for trade in (*self.entries, *self.closes):
                if trade.fee:
                    currency = trade.fee[enums.FeePropertyColumns.CURRENCY.value]
                    if currency in base_and_quote:
                        # not a special fee
                        continue
                    if currency in fees:
                        fees[currency] += order_util.get_fees_for_currency(trade.fee, currency)
                    else:
                        fees[currency] = order_util.get_fees_for_currency(trade.fee, currency)
            return fees
        except IndexError as err:
            raise errors.IncompletePNLError from err

    def get_paid_regular_fees_in_quote(self) -> decimal.Decimal:
        """
        :return: the total value (in quote) of paid fees when paid in base or quote of the trades pair
        """
        return sum(
            self._get_fees(trade)
            for trade in (*self.entries, *self.closes)
        ) or constants.ZERO

    def get_profits(self) -> (decimal.Decimal, decimal.Decimal):
        """
        :return: the pnl profits as flat value and percent
        """
        close_holdings = self.get_closed_close_value() - self.get_paid_regular_fees_in_quote()
        entry_holdings = self.get_closed_entry_value() * self.get_close_ratio()
        try:
            percent_profit = (close_holdings * constants.ONE_HUNDRED / entry_holdings) - constants.ONE_HUNDRED
        except (decimal.DivisionByZero, decimal.InvalidOperation):
            percent_profit = constants.ZERO
        return (
            close_holdings - entry_holdings,
            percent_profit
        )
