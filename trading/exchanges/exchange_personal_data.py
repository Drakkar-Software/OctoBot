from config.cst import *


class ExchangePersonalData:

    # note: symbol keys are without /
    def __init__(self):
        self.portfolio = {}
        self.orders = {}
        self.is_initialized = False

    def update_portfolio(self, currency, total, available, in_order):
        self.portfolio[currency] = {
            CONFIG_PORTFOLIO_FREE: available,
            CONFIG_PORTFOLIO_USED: in_order,
            CONFIG_PORTFOLIO_TOTAL: total
        }

    def get_portfolio(self):
        return self.portfolio

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
