from trading.trader.order import OrderConstants
from trading.trader.portfolio import Portfolio


class PrettyPrinter:
    @staticmethod
    def open_order_pretty_printer(order):
        currency, market = order.get_currency_and_market()

        try:
            order_type_name = OrderConstants.TraderOrderTypeClasses[order.get_order_type()].__name__
        except KeyError:
            order_type_name = order.get_order_type().__class__.__name__

        return "{0} (on {1}) : {2:f} {3} at {4:f} {5}".format(
            order_type_name,
            order.get_exchange().get_name(),
            round(order.get_origin_quantity(), 7),
            currency,
            round(order.get_origin_price(), 7),
            market)

    @staticmethod
    def trade_pretty_printer(trade):
        currency = trade.get_currency()
        market = trade.get_market()

        try:
            order_type_name = OrderConstants.TraderOrderTypeClasses[trade.get_order_type()].__name__
        except KeyError:
            order_type_name = trade.get_order_type().__class__.__name__

        return "{0} (on {1}) : {2:f} {3} at {4:f} {5}".format(
            order_type_name,
            trade.get_exchange_name(),
            round(trade.get_quantity(), 7),
            currency,
            round(trade.get_price(), 7),
            market)


    @staticmethod
    def cryptocurrency_alert(crypto_currency, symbol, result, final_eval):
        return "CryptoBot ALERT : #{0}\n Symbol : #{1}\n Result : {2}\n Evaluation : {3}".format(
            crypto_currency,
            symbol.replace("/", ""),
            str(result).split(".")[1],
            final_eval)

    @staticmethod
    def global_portfolio_pretty_print(global_portfolio, separator="\n"):
        result = ["{0} ({1}) {2}".format(amounts[Portfolio.TOTAL], amounts[Portfolio.AVAILABLE], currency)
                  for currency, amounts in global_portfolio.items()]

        return separator.join(result)

    @staticmethod
    def portfolio_profitability_pretty_print(profitability, profitability_percent, reference):
        difference = "({0:f}%)".format(round(profitability_percent, 5)) if profitability_percent is not None else ""
        return "{0:f} {1} {2}".format(round(profitability, 5), reference, difference)
