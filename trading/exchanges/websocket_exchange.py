import logging

from ccxt import OrderNotFound, BaseError

from config.cst import *
from trading.exchanges.abstract_exchange import AbstractExchange
from tools.time_frame_manager import TimeFrameManager


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

        self.client = self.socket_manager.get_websocket_client(self.config, self.exchange_type)

        # init websockets retrieved data
        self._set_config_time_frame()
        self._set_config_traded_pairs()

        # init websocket
        self.client.init_web_sockets(self._time_frames, self._traded_pairs)

        # start the websocket
        self.client.start_sockets()

    def get_client(self):
        return self.client

    def stop(self):
        self.client.stop_sockets()

    def _set_config_time_frame(self):
        for time_frame in TimeFrameManager.get_config_time_frame(self.config):
            if self.exchange_manager.time_frame_exists(time_frame.value):
                self._time_frames.append(time_frame)

    def _set_config_traded_pairs(self):
        for cryptocurrency in self.config[CONFIG_CRYPTO_CURRENCIES]:
            for symbol in self.config[CONFIG_CRYPTO_CURRENCIES][cryptocurrency][CONFIG_CRYPTO_PAIRS]:
                if self.exchange_manager.symbol_exists(symbol):
                    self._traded_pairs.append(symbol)

    # total (free + used), by currency
    def get_balance(self):
        return self.client.get_portfolio()

    # todo
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
    # todo
    def get_order_book(self, symbol, limit=30):
        return self.client.fetchOrderBook(symbol, limit)

    # todo
    def get_recent_trades(self, symbol):
        try:
            return self.client.fetch_trades(symbol)
        except BaseError as e:
            self.logger.error("Failed to get recent trade {0}".format(e))
            return None

    # todo
    def get_market_price(self, symbol):
        order_book = self.get_order_book(symbol)
        bid = order_book['bids'][0][0] if len(order_book['bids']) > 0 else None
        ask = order_book['asks'][0][0] if len(order_book['asks']) > 0 else None
        spread = (ask - bid) if (bid and ask) else None
        return {'bid': bid, 'ask': ask, 'spread': spread}

    # A price ticker contains statistics for a particular market/symbol for the last instant
    def get_last_price_ticker(self, symbol):
        return self.client.get_last_price_ticker(symbol=symbol)

    # A price ticker contains statistics for a particular market/symbol for some period of time in recent past (24h)
    # todo
    def get_price_ticker(self, symbol):
        try:
            return self.client.fetch_ticker(symbol)
        except BaseError as e:
            self.logger.error("Failed to get_price_ticker {0}".format(e))
            return None

    # todo
    def get_all_currencies_price_ticker(self):
        try:
            self.all_currencies_price_ticker = self.client.fetch_tickers()
            return self.all_currencies_price_ticker
        except BaseError as e:
            self.logger.error("Failed to get_all_currencies_price_ticker {0}".format(e))
            return None

    # ORDERS
    def get_order(self, order_id):
        return self.client.get_order(order_id)

    def get_all_orders(self, symbol=None, since=None, limit=None):
        return self.client.get_all_orders(symbol, since, limit)

    def get_open_orders(self, symbol=None, since=None, limit=None):
        return self.client.get_open_orders(symbol, since, limit)

    def get_closed_orders(self, symbol=None, since=None, limit=None):
        return self.client.get_closed_orders(symbol, since, limit)

    # todo
    def get_my_recent_trades(self, symbol=None, since=None, limit=None):
        return self.client.fetchMyTrades(symbol=symbol, since=since, limit=limit, params={})

    # todo
    def cancel_order(self, order_id, symbol=None):
        try:
            self.client.cancel_order(order_id, symbol=symbol)
            return True
        except OrderNotFound:
            self.logger.error("Order {0} was not found".format(order_id))
            return False

    # todo
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
