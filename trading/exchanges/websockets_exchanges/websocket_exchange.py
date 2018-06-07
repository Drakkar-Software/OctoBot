from trading.exchanges.abstract_exchange import AbstractExchange


class WebSocketExchange(AbstractExchange):
    def __init__(self, config, exchange_type, exchange_manager, socket_manager):
        super().__init__(config, exchange_type)
        self.exchange_manager = exchange_manager
        self.socket_manager = socket_manager
        self._time_frames = []
        self._traded_pairs = []

        # websocket client
        self.client = None

        # We will need to create the rest client and fetch exchange config
        self.create_client()

    # websocket exchange startup
    def create_client(self):
        self.client = self.socket_manager.get_websocket_client(self.config)

        # init websocket
        self.client.init_web_sockets(self.exchange_manager.get_config_time_frame(),
                                     self.exchange_manager.get_traded_pairs())

        # start the websocket
        self.client.start_sockets()

    def get_client(self):
        return self.client

    def stop(self):
        self.client.stop_sockets()

    # total (free + used), by currency
    def get_balance(self):
        return self.client.get_portfolio()

    # ORDERS
    def get_order(self, order_id, symbol=None):
        return self.client.get_order(order_id, symbol=symbol)

    def get_all_orders(self, symbol=None, since=None, limit=None):
        return self.client.get_all_orders(symbol, since, limit)

    def get_open_orders(self, symbol=None, since=None, limit=None, force_rest=False):
        return self.client.get_open_orders(symbol, since, limit)

    def get_closed_orders(self, symbol=None, since=None, limit=None):
        return self.client.get_closed_orders(symbol, since, limit)

    # utility methods
    def init_orders_for_ws_if_possible(self, orders):
        if not self.client.orders_are_initialized():
            for order in orders:
                self.client.init_ccxt_order_from_other_source(order)

    def set_orders_are_initialized(self, value):
        self.client.set_orders_are_initialized(value)

    def orders_are_initialized(self):
        return self.client.orders_are_initialized()

    def handles_recent_trades(self):
        return self.client.handles_recent_trades()

    # Not implemented methods from AbstractExchange
    def get_order_book(self, symbol, limit=50):
        raise NotImplementedError("get_order_book not implemented")

    def get_market_price(self, symbol):
        raise NotImplementedError("get_market_price not implemented")

    def get_price_ticker(self, symbol):
        raise NotImplementedError("get_price_ticker not implemented")

    def get_all_currencies_price_ticker(self):
        raise NotImplementedError("get_all_currencies_price_ticker not implemented")

    def get_my_recent_trades(self, symbol=None, since=None, limit=None):
        raise NotImplementedError("get_my_recent_trades not implemented")

    def get_symbol_prices(self, symbol, time_frame, limit=None, data_frame=True):
        raise NotImplementedError("get_symbol_prices not implemented")

    def get_last_price_ticker(self, symbol):
        raise NotImplementedError("get_last_price_ticker not implemented")

    # implementation depends on the websocket exchange implementation
    def get_recent_trades(self, symbol):
        raise NotImplementedError("get_recent_trades not implemented")

    def cancel_order(self, order_id, symbol=None):
        raise NotImplementedError("cancel_order not implemented")

    def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        raise NotImplementedError("create_order not implemented")

    def get_market_status(self, symbol):
        raise NotImplementedError("get_market_status not implemented")

    def get_uniform_timestamp(self, timestamp):
        raise NotImplementedError("get_uniform_timestamp not implemented")
