import datetime

from trading.trader.order import OrderConstants
from trading.trader.portfolio import Portfolio


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
            datetime.datetime.fromtimestamp(
                order.get_creation_time()
            ).strftime('%d/%m/%y %H:%M'))

    @staticmethod
    def trade_pretty_printer(trade):
        currency = trade.get_currency()
        market = trade.get_market()

        try:
            order_type_name = trade.get_order_type().name
        except AttributeError:
            try:
                order_type_name = OrderConstants.TraderOrderTypeClasses[trade.get_order_type()].__name__
            except KeyError:
                order_type_name = trade.get_order_type().__class__.__name__

        return "{0}: {1} {2} at {3} {4} on {5}: {6} ".format(
            order_type_name,
            PrettyPrinter.get_min_string_from_number(trade.get_quantity()),
            currency,
            PrettyPrinter.get_min_string_from_number(trade.get_price()),
            market,
            trade.get_exchange_name(),
            datetime.datetime.fromtimestamp(
                trade.get_filled_time()
            ).strftime('%d/%m/%y %H:%M'))

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
                number_str = "{:.{}f}".format(round(number, max_digits), max_digits)
                if "." in number_str:
                    number_str = number_str.rstrip("0.")
                return number_str
            else:
                return "{:f}".format(number).split(".")[0]
