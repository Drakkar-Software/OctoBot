import logging


class AbstractExchange:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        self.exchange = None
        self.exchange_web_socket = None

    def _web_socket_available(self):
        if self.exchange_web_socket and self.exchange_web_socket.portfolio_is_initialized():
            return True
        else:
            return False

    # total (free + used), by currency
    def get_balance(self):
        if self._web_socket_available():
            return self.exchange_web_socket.get_portfolio()
        else:
            return self.exchange.get_balance()

    def get_symbol_prices(self, symbol, time_frame, limit=None, data_frame=True):
        if self._web_socket_available():
            pass

        return self.exchange.get_symbol_prices(symbol=symbol,
                                               time_frame=time_frame,
                                               limit=limit,
                                               data_frame=data_frame)

    # return bid and asks on each side of the order book stack
    def get_order_book(self, symbol, limit=30):
        if self._web_socket_available():
            pass

        return self.exchange.fetchOrderBook(symbol=symbol,
                                            limit=limit)

    def get_recent_trades(self, symbol):
        if self._web_socket_available():
            pass

        return self.exchange.get_recent_trades(symbol=symbol)

    def get_market_price(self, symbol):
        if self._web_socket_available():
            pass

        return self.exchange.get_market_price(symbol=symbol)

    # A price ticker contains statistics for a particular market/symbol for the last instant
    def get_last_price_ticker(self, symbol):
        if self._web_socket_available():
            return self.exchange_web_socket.get_last_price_ticker(symbol=symbol)
        else:
            return self.exchange.get_last_price_ticker(symbol=symbol)

    # A price ticker contains statistics for a particular market/symbol for some period of time in recent past (24h)
    def get_price_ticker(self, symbol):
        if self._web_socket_available():
            pass

        return self.exchange.get_price_ticker(symbol=symbol)

    def get_all_currencies_price_ticker(self):
        if self._web_socket_available():
            pass

        return self.exchange.get_all_currencies_price_ticker()

    # ORDERS
    def get_order(self, order_id):
        if self._web_socket_available():
            pass

        return self.exchange.get_order(order_id=order_id)

    def get_all_orders(self, symbol=None, since=None, limit=None):
        if self._web_socket_available():
            pass

        return self.exchange.get_all_orders(symbol=symbol,
                                            since=since,
                                            limit=limit)

    def get_open_orders(self, symbol=None, since=None, limit=None):
        if self._web_socket_available():
            pass

        return self.exchange.get_open_orders(symbol=symbol,
                                             since=since,
                                             limit=limit)

    def get_closed_orders(self, symbol=None, since=None, limit=None):
        if self._web_socket_available():
            pass

        return self.exchange.get_closed_orders(symbol=symbol,
                                               since=since,
                                               limit=limit)

    def get_my_recent_trades(self, symbol=None, since=None, limit=None):
        if self._web_socket_available():
            pass

        return self.exchange.get_my_recent_trades(symbol=symbol,
                                                  since=since,
                                                  limit=limit)

    def cancel_order(self, order_id, symbol=None):
        if self._web_socket_available():
            pass

        return self.exchange.cancel_order(symbol=symbol,
                                          order_id=order_id)

    def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        if self._web_socket_available():
            pass

        return self.exchange.create_order(symbol=symbol,
                                          order_type=order_type,
                                          quantity=quantity,
                                          price=price,
                                          stop_price=stop_price)
