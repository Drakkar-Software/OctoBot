class Trade:
    def __init__(self, exchange, order):
        self.currency, self.market = order.get_currency_and_market()
        self.quantity = order.get_filled_quantity()
        self.price = order.get_filled_price()
        self.order_type = order.get_order_type()
        self.final_status = order.get_status()
        self.market_fees = order.get_market_total_fees()
        self.currency_fees = order.get_currency_total_fees()

        self.creation_time = order.get_creation_time()
        self.canceled_time = order.get_canceled_time()
        self.filled_time = order.get_executed_time()

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

    def get_market_fees(self):
        return self.market_fees

    def get_currency_fees(self):
        return self.currency_fees

    def get_final_status(self):
        return self.final_status

    def get_canceled_time(self):
        return self.canceled_time

    def get_filled_time(self):
        return self.filled_time

    def get_creation_time(self):
        return self.creation_time
