from config.cst import *


class ExchangePersonalData:

    # note: symbol keys are without /
    def __init__(self):
        self.portfolio = {}
        self.orders = {}

        self.portfolio_is_initialized = False
        self.orders_are_initialized = False

    def update_portfolio(self, currency, total, available, in_order):
        self.portfolio[currency] = {
            CONFIG_PORTFOLIO_FREE: available,
            CONFIG_PORTFOLIO_USED: in_order,
            CONFIG_PORTFOLIO_TOTAL: total
        }

    def init_portfolio(self):
        self.portfolio_is_initialized = True

    def init_orders(self):
        self.orders_are_initialized = True

    def get_portfolio_is_initialized(self):
        return self.portfolio_is_initialized

    def get_orders_are_initialized(self):
        return self.orders_are_initialized

    def set_portfolio(self, portfolio):
        self.portfolio = portfolio

    def get_portfolio(self):
        return self.portfolio

    def has_order(self, order_id):
        return order_id in self.orders

    def set_order(self, order_id, order_data):
        self.orders[order_id] = order_data

    def set_orders(self, orders):
        for order in orders:
            self.set_order(order["id"], order)

    # maybe later add an order remover to free up memory ?
    def upsert_order(self, order_id, ccxt_order):
        self.orders[order_id] = ccxt_order

    def get_all_orders(self, symbol, since, limit):
        return self._select_orders(None, symbol, since, limit)

    def get_open_orders(self, symbol, since, limit):
        return self._select_orders(OrderStatus.OPEN.value, symbol, since, limit)

    def get_closed_orders(self, symbol, since, limit):
        return self._select_orders(OrderStatus.CLOSED.value, symbol, since, limit)

    def get_my_recent_trades(self, symbol, since, limit):
        # TODO
        return None

    def get_order(self, order_id):
        return self.orders[order_id]

    # private methods
    def _select_orders(self, state, symbol, since, limit):
        orders = [
            order
            for order in self.orders.values()
            if (
                    (state is None or order["status"] == state) and
                    (symbol is None or (symbol and order["symbol"] == symbol)) and
                    (since is None or (since and order['timestamp'] < since))
            )
        ]
        if limit is not None:
            return orders[0:limit]
        else:
            return orders
