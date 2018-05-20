from trading import AbstractExchange


class ExchangeDispatcher(AbstractExchange):
    def __init__(self, config, exchange_type, exchange, exchange_web_socket):
        super().__init__(config, exchange_type)

        self.exchange = exchange
        self.exchange_web_socket = exchange_web_socket

        self.logger.info("online with {0}".format(
            "REST api{0}".format(
                " and websocket api" if self.exchange_web_socket else ""
            )
        ))

    def _web_socket_available(self):
        return self.exchange_web_socket

    def get_name(self):
        return self.exchange.get_name()

    def get_exchange_manager(self):
        return self.exchange.get_exchange_manager()

    def get_exchange(self):
        return self.exchange

    # total (free + used), by currency
    def get_balance(self):
        if self._web_socket_available() and self.exchange_web_socket.get_client().portfolio_is_initialized():
            return self.exchange_web_socket.get_portfolio()
        else:
            return self.exchange.get_balance()

    def get_symbol_prices(self, symbol, time_frame, limit=None, data_frame=True):
        if self._web_socket_available() and self.exchange_web_socket.candles_are_initialized(symbol, time_frame):
            candle_dataframe, candles = self.exchange_web_socket.get_symbol_prices(symbol=symbol,
                                                                                   time_frame=time_frame,
                                                                                   limit=limit,
                                                                                   data_frame=data_frame)
            return candle_dataframe

        needs_to_init_candles = self._web_socket_available() and \
            not self.exchange_web_socket.candles_are_initialized(symbol, time_frame)
        select_limit = limit
        if needs_to_init_candles:
            data_frame = True
            select_limit = None
        candle_dataframe, candles = self.exchange.get_symbol_prices(symbol=symbol,
                                                                    time_frame=time_frame,
                                                                    limit=select_limit,
                                                                    data_frame=data_frame)
        if needs_to_init_candles:
            self.exchange_web_socket.init_candle_data(symbol, time_frame, candles, candle_dataframe)
        return candle_dataframe[-limit:] if limit is not None else candle_dataframe

    # return bid and asks on each side of the order book stack
    def get_order_book(self, symbol, limit=50):
        if self._web_socket_available():
            pass

        return self.exchange.get_order_book(symbol, limit)

    def get_recent_trades(self, symbol):
        if self._web_socket_available() and self.exchange_web_socket.handles_recent_trades():
            return self.exchange_web_socket.get_recent_trades(symbol=symbol)

        return self.exchange.get_recent_trades(symbol=symbol)

    def get_market_price(self, symbol):
        if self._web_socket_available():
            pass

        return self.exchange.get_market_price(symbol=symbol)

    # A price ticker contains statistics for a particular market/symbol for the last instant
    def get_last_price_ticker(self, symbol):
        if self._web_socket_available() and self.exchange_web_socket.get_client().last_price_ticker_is_initialized(
                symbol):
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
        if self._web_socket_available() and self.exchange_web_socket.get_client().has_order(order_id):
            return self.exchange_web_socket.get_order(order_id)
        else:
            order = self.exchange.get_order(order_id=order_id)
            if self._web_socket_available():
                self.exchange_web_socket.init_orders_for_ws_if_possible([order])
            return order

    def get_all_orders(self, symbol=None, since=None, limit=None):
        if self._web_socket_available() and self.exchange_web_socket.orders_are_initialized():
            return self.exchange_web_socket.get_all_orders(symbol=symbol,
                                                           since=since,
                                                           limit=limit)
        else:
            orders = self.exchange.get_all_orders(symbol=symbol,
                                                  since=since,
                                                  limit=limit)
            if self._web_socket_available():
                self.exchange_web_socket.init_orders_for_ws_if_possible(orders)
            return orders

    def get_open_orders(self, symbol=None, since=None, limit=None):
        if self._web_socket_available() and self.exchange_web_socket.orders_are_initialized():
            return self.exchange_web_socket.get_open_orders(symbol=symbol,
                                                            since=since,
                                                            limit=limit)
        else:
            orders = self.exchange.get_open_orders(symbol=symbol,
                                                   since=since,
                                                   limit=limit)
            if self._web_socket_available():
                self.exchange_web_socket.init_orders_for_ws_if_possible(orders)
            return orders

    def get_closed_orders(self, symbol=None, since=None, limit=None):
        if self._web_socket_available() and self.exchange_web_socket.orders_are_initialized():
            return self.exchange_web_socket.get_closed_orders(symbol=symbol,
                                                              since=since,
                                                              limit=limit)
        else:
            orders = self.exchange.get_closed_orders(symbol=symbol,
                                                     since=since,
                                                     limit=limit)
            if self._web_socket_available():
                self.exchange_web_socket.init_orders_for_ws_if_possible(orders)
            return orders

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

    def set_orders_are_initialized(self, value):
        if self._web_socket_available():
            self.exchange_web_socket.set_orders_are_initialized(value)

    def stop(self):
        if self._web_socket_available():
            self.exchange_web_socket.stop()
