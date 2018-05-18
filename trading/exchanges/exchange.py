import logging

from ccxt import OrderNotFound, BaseError

from config.cst import *
from trading.exchanges.abstract_exchange import AbstractExchange


class Exchange(AbstractExchange):
    def __init__(self, config, exchange_type, exchange_manager):
        super().__init__(config, exchange_type)
        self.exchange_manager = exchange_manager

        # ccxt client
        self.client = None

        # balance additional info
        self.info_list = None
        self.free = None
        self.used = None
        self.total = None

        # We will need to create the rest client and fetch exchange config
        self.create_client()
        self.client.load_markets()

        self.all_currencies_price_ticker = None

    # ccxt exchange instance creation
    def create_client(self):
        if self.exchange_manager.check_config(self.get_name()):
            self.client = self.exchange_type({
                'apiKey': self.config["exchanges"][self.name]["api-key"],
                'secret': self.config["exchanges"][self.name]["api-secret"],
                'verbose': False,
                'enableRateLimit': True
            })
        else:
            self.client = self.exchange_type({'verbose': False})
        self.client.logger.setLevel(logging.INFO)

    def get_client(self):
        return self.client

    # total (free + used), by currency
    def get_balance(self):
        balance = self.client.fetchBalance()

        # store portfolio global info
        self.info_list = balance[CONFIG_PORTFOLIO_INFO]
        self.free = balance[CONFIG_PORTFOLIO_FREE]
        self.used = balance[CONFIG_PORTFOLIO_USED]
        self.total = balance[CONFIG_PORTFOLIO_TOTAL]

        # remove not currency specific keys
        balance.pop(CONFIG_PORTFOLIO_INFO, None)
        balance.pop(CONFIG_PORTFOLIO_FREE, None)
        balance.pop(CONFIG_PORTFOLIO_USED, None)
        balance.pop(CONFIG_PORTFOLIO_TOTAL, None)

        return balance

    def get_symbol_prices(self, symbol, time_frame, limit=None, data_frame=True):
        if limit:
            candles = self.client.fetch_ohlcv(symbol, time_frame.value, limit=limit)
        else:
            candles = self.client.fetch_ohlcv(symbol, time_frame.value)

        if data_frame:
            return self.exchange_manager.candles_array_to_data_frame(candles)
        else:
            return candles

    # return up to ten bidasks on each side of the order book stack
    def get_order_book(self, symbol, limit=30):
        return self.client.fetchOrderBook(symbol, limit)

    def get_recent_trades(self, symbol):
        try:
            return self.client.fetch_trades(symbol)
        except BaseError as e:
            self.logger.error("Failed to get recent trade {0}".format(e))
            return None

    def get_market_price(self, symbol):
        order_book = self.get_order_book(symbol)
        bid = order_book['bids'][0][0] if len(order_book['bids']) > 0 else None
        ask = order_book['asks'][0][0] if len(order_book['asks']) > 0 else None
        spread = (ask - bid) if (bid and ask) else None
        return {'bid': bid, 'ask': ask, 'spread': spread}

    # A price ticker contains statistics for a particular market/symbol for the last instant
    def get_last_price_ticker(self, symbol):
        try:
            return self.client.fetch_ticker(symbol)[ExchangeConstantsTickersColumns.LAST.value]
        except BaseError as e:
            self.logger.error("Failed to get_price_ticker {0}".format(e))
            return None

    # A price ticker contains statistics for a particular market/symbol for some period of time in recent past (24h)
    def get_price_ticker(self, symbol):
        try:
            return self.client.fetch_ticker(symbol)
        except BaseError as e:
            self.logger.error("Failed to get_price_ticker {0}".format(e))
            return None

    def get_all_currencies_price_ticker(self):
        try:
            self.all_currencies_price_ticker = self.client.fetch_tickers()
            return self.all_currencies_price_ticker
        except BaseError as e:
            self.logger.error("Failed to get_all_currencies_price_ticker {0}".format(e))
            return None

    # ORDERS
    def get_order(self, order_id):
        if self.websocket_client and self.websocket_client.has_order(order_id):
            return self.websocket_client.get_order(order_id)
        else:
            if self.client.has['fetchOrder']:
                order = self.client.fetch_order(order_id)
                self.init_orders_for_ws_if_possible([order])
                return order
            else:
                raise Exception("This exchange doesn't support fetchOrder")

    def init_orders_for_ws_if_possible(self, orders):
        if self.websocket_client and not self.websocket_client.orders_are_initialized():
            for order in orders:
                self.websocket_client.init_ccxt_order_from_other_source(order)

    def set_orders_are_initialized(self, value):
        self.websocket_client.set_orders_are_initialized(value)

    def get_all_orders(self, symbol=None, since=None, limit=None):
        if self.websocket_client and self.websocket_client.orders_are_initialized():
            return self.websocket_client.get_all_orders(symbol, since, limit)
        else:
            if self.client.has['fetchOrders']:
                orders = self.client.fetchOrders(symbol=symbol, since=since, limit=limit, params={})
                self.init_orders_for_ws_if_possible(orders)
                return orders
            else:
                raise Exception("This exchange doesn't support fetchOrders")

    def get_open_orders(self, symbol=None, since=None, limit=None):
        if self.websocket_client and self.websocket_client.orders_are_initialized():
            return self.websocket_client.get_open_orders(symbol, since, limit)
        else:
            if self.client.has['fetchOpenOrders']:
                orders = self.client.fetchOpenOrders(symbol=symbol, since=since, limit=limit, params={})
                self.init_orders_for_ws_if_possible(orders)
                return orders
            else:
                raise Exception("This exchange doesn't support fetchOpenOrders")

    def get_closed_orders(self, symbol=None, since=None, limit=None):
        if self.websocket_client and self.websocket_client.orders_are_initialized():
            return self.websocket_client.get_closed_orders(symbol, since, limit)
        else:
            if self.client.has['fetchClosedOrders']:
                orders = self.client.fetchClosedOrders(symbol=symbol, since=since, limit=limit, params={})
                self.init_orders_for_ws_if_possible(orders)
                return orders
            else:
                raise Exception("This exchange doesn't support fetchClosedOrders")

    def get_my_recent_trades(self, symbol=None, since=None, limit=None):
        return self.client.fetchMyTrades(symbol=symbol, since=since, limit=limit, params={})

    def cancel_order(self, order_id, symbol=None):
        try:
            self.client.cancel_order(order_id, symbol=symbol)
            return True
        except OrderNotFound:
            self.logger.error("Order {0} was not found".format(order_id))
            return False

    # todo { 'type': 'trailing-stop' }
    def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        try:
            if order_type == TraderOrderType.BUY_MARKET:
                return self.client.create_market_buy_order(symbol, quantity)
            elif order_type == TraderOrderType.BUY_LIMIT:
                return self.client.create_limit_buy_order(symbol, quantity, price)
            elif order_type == TraderOrderType.SELL_MARKET:
                return self.client.create_market_sell_order(symbol, quantity)
            elif order_type == TraderOrderType.SELL_LIMIT:
                return self.client.create_limit_sell_order(symbol, quantity, price)
            elif order_type == TraderOrderType.STOP_LOSS:
                return None
            elif order_type == TraderOrderType.STOP_LOSS_LIMIT:
                return None
            elif order_type == TraderOrderType.TAKE_PROFIT:
                return None
            elif order_type == TraderOrderType.TAKE_PROFIT_LIMIT:
                return None
        except Exception as e:
            self.logger.error("Failed to create order : {0}".format(e))
