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

from trading.trader.order import OrderConstants
from trading.trader.portfolio import Portfolio
from tools.timestamp_util import convert_timestamp_to_datetime
from tools.number_util import round_into_str_with_max_digits


class PrettyPrinter:
    @staticmethod
    def open_order_pretty_printer(order):
        currency, market = order.get_currency_and_market()

        try:
            order_type_name = order.get_order_type().name
        except AttributeError:
            try:
                order_type_name = OrderConstants.TraderOrderTypeClasses[order.get_order_type()].__name__
            except KeyError:
                order_type_name = order.get_order_type().__class__.__name__

        return "{0}: {1} {2} at {3} {4} on {5}: {6} ".format(
            order_type_name,
            PrettyPrinter.get_min_string_from_number(order.get_origin_quantity()),
            currency,
            PrettyPrinter.get_min_string_from_number(order.get_origin_price()),
            market,
            order.get_exchange().get_name(),
            convert_timestamp_to_datetime(order.get_creation_time()))

    @staticmethod
    def trade_pretty_printer(trade):
        currency = trade.currency
        market = trade.market

        try:
            order_type_name = trade.order_type.name
        except AttributeError:
            try:
                order_type_name = OrderConstants.TraderOrderTypeClasses[trade.order_type].__name__
            except KeyError:
                order_type_name = trade.order_type.__class__.__name__

        return "{0}: {1} {2} at {3} {4} on {5}: {6} ".format(
            order_type_name,
            PrettyPrinter.get_min_string_from_number(trade.quantity),
            currency,
            PrettyPrinter.get_min_string_from_number(trade.price),
            market,
            trade.exchange.get_name(),
            convert_timestamp_to_datetime(trade.filled_time))

    @staticmethod
    def cryptocurrency_alert(crypto_currency, symbol, result, final_eval):
        return "OctoBot ALERT : #{0}\n Symbol : #{1}\n Result : {2}\n Evaluation : {3}".format(
            crypto_currency,
            symbol.replace("/", ""),
            str(result).split(".")[1],
            final_eval)

    @staticmethod
    def global_portfolio_pretty_print(global_portfolio, separator="\n"):
        result = ["{0} ({1}) {2}".format(
            PrettyPrinter.get_min_string_from_number(amounts[Portfolio.TOTAL]),
            PrettyPrinter.get_min_string_from_number(amounts[Portfolio.AVAILABLE]),
            currency)
            for currency, amounts in global_portfolio.items() if amounts[Portfolio.TOTAL] > 0]

        return separator.join(result)

    @staticmethod
    def portfolio_profitability_pretty_print(profitability, profitability_percent, reference):
        difference = "({0}%)".format(PrettyPrinter.get_min_string_from_number(profitability_percent, 5)) \
            if profitability_percent is not None else ""
        return "{0} {1} {2}".format(PrettyPrinter.get_min_string_from_number(profitability, 5),
                                    reference, difference)

    @staticmethod
    def get_min_string_from_number(number, max_digits=8):
        if round(number, max_digits) == 0.0:
            return "0"
        else:
            if number % 1 != 0:
                number_str = round_into_str_with_max_digits(number, max_digits)
                if "." in number_str:
                    number_str = number_str.rstrip("0.")
                return number_str
            else:
                return "{:f}".format(number).split(".")[0]
