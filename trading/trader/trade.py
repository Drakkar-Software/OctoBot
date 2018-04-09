class Trade:
    def __init__(self, exchange, order):
        self.currency, self.market = order.get_currency_and_market()
        self.quantity = order.get_filled_quantity()
        self.price = order.get_filled_price()
        self.order_type = order.get_order_type()
        self.final_status = order.get_status()
        self.fees = order.get_total_fees()

        self.exchange = exchange

    def get_price(self):
        return self.price

    def get_exchange_name(self):
        return self.exchange.get_name()

    def get_quantity(self):
        return self.quantity

    def get_currency(self):
        return self.currency

    def get_market(self):
        return self.market

    def get_fees(self):
        return self.fees

    def get_final_status(self):
        return self.final_status
