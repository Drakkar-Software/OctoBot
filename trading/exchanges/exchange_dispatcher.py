from trading.exchanges.exchange_symbol_data import SymbolData
from trading import AbstractExchange
from trading.exchanges.exchange_personal_data import ExchangePersonalData


class ExchangeDispatcher(AbstractExchange):
    def __init__(self, config, exchange_type, exchange, exchange_web_socket):
        super().__init__(config, exchange_type)

        self.exchange = exchange
        self.exchange_web_socket = None

        self.symbols_data = {}
        self.exchange_personal_data = ExchangePersonalData()

        self.logger.info("online with {0}".format(
            "REST api{0}".format(
                " and websocket api" if self.exchange_web_socket else ""
            )
        ))

    def _web_socket_available(self):
        return self.exchange_web_socket

    def is_websocket_available(self):
        if self._web_socket_available():
            return True
        else:
            return False

    def get_name(self):
        return self.exchange.get_name()

    def get_exchange_manager(self):
        return self.exchange.get_exchange_manager()

    def get_exchange(self):
        return self.exchange

    def get_exchange_personal_data(self):
        return self.exchange_personal_data

    def get_symbol_data(self, symbol):
        if symbol not in self.symbols_data:
            self.symbols_data[symbol] = SymbolData(symbol)
        return self.symbols_data[symbol]

    # total (free + used), by currency
    def get_balance(self):
        if not self._web_socket_available():
            self.exchange.get_balance()

        return self.exchange_personal_data.get_portfolio()

    def get_symbol_prices(self, symbol, time_frame, limit=None, return_list=True):
        symbol_data = self.get_symbol_data(symbol)

        self.exchange.get_symbol_prices(symbol=symbol, time_frame=time_frame, limit=limit)

        return symbol_data.get_symbol_prices(time_frame, limit, return_list)

    # return bid and asks on each side of the order book stack
    # careful here => can be for binance limit > 100 has a 5 weight and > 500 a 10 weight !
    def get_order_book(self, symbol, limit=50):
        if not self._web_socket_available():
            self.exchange.get_order_book(symbol, limit)

        return self.get_symbol_data(symbol).get_symbol_order_book(limit)

    def get_recent_trades(self, symbol, limit=50):
        if not self._web_socket_available():
            self.exchange.get_recent_trades(symbol=symbol)

        return self.get_symbol_data(symbol).get_symbol_recent_trades(limit)

    # A price ticker contains statistics for a particular market/symbol for some period of time in recent past (24h)
    def get_price_ticker(self, symbol):
        if not self._web_socket_available():
            self.exchange.get_price_ticker(symbol=symbol)

        return self.get_symbol_data(symbol).get_symbol_ticker()

    def get_all_currencies_price_ticker(self):
        return self.exchange.get_all_currencies_price_ticker()

    def get_market_status(self, symbol):
        return self.exchange.get_market_status(symbol)

    # ORDERS
    def get_order(self, order_id, symbol=None):
        if not self._web_socket_available():
            self.exchange.get_order(order_id, symbol=symbol)

        return self.exchange_personal_data.get_order(order_id)

    def get_all_orders(self, symbol=None, since=None, limit=None):
        if not self._web_socket_available():
            self.exchange.get_all_orders(symbol=symbol,
                                         since=since,
                                         limit=limit)

        return self.exchange_personal_data.get_all_orders(symbol, since, limit)

    def get_open_orders(self, symbol=None, since=None, limit=None, force_rest=False):
        if not self._web_socket_available():
            self.exchange.get_open_orders(symbol=symbol,
                                          since=since,
                                          limit=limit)

        return self.exchange_personal_data.get_open_orders(symbol, since, limit)

    def get_closed_orders(self, symbol=None, since=None, limit=None):
        if not self._web_socket_available():
            self.exchange.get_closed_orders(symbol=symbol,
                                            since=since,
                                            limit=limit)

        return self.exchange_personal_data.get_closed_orders(symbol, since, limit)

    def get_my_recent_trades(self, symbol=None, since=None, limit=None):
        if not self._web_socket_available():
            self.exchange.get_my_recent_trades(symbol=symbol,
                                               since=since,
                                               limit=limit)

        return self.exchange_personal_data.get_my_recent_trades(symbol=symbol,
                                                                since=since,
                                                                limit=limit)

    def cancel_order(self, order_id, symbol=None):
        return self.exchange.cancel_order(symbol=symbol,
                                          order_id=order_id)

    def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        return self.exchange.create_order(symbol=symbol,
                                          order_type=order_type,
                                          quantity=quantity,
                                          price=price,
                                          stop_price=stop_price)

    def stop(self):
        if self._web_socket_available():
            self.exchange_web_socket.stop()

    def get_uniform_timestamp(self, timestamp):
        return self.exchange.get_uniform_timestamp(timestamp)
