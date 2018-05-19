from config.cst import *
from trading.exchanges.websockets.abstract_websocket_manager import AbstractWebSocketManager
from binance.websockets import BinanceSocketManager
from binance.client import Client
from twisted.internet import reactor

from tools.symbol_util import merge_symbol


class BinanceWebSocketClient(AbstractWebSocketManager):
    _TICKER_KEY = "@ticker"
    _KLINE_KEY = "@kline"
    _MULTIPLEX_SOCKET_NAME = "multiplex"
    _USER_SOCKET_NAME = "user"
    _STATUSES = {
        'NEW': 'open',
        'PARTIALLY_FILLED': 'open',
        'FILLED': 'closed',
        'CANCELED': 'canceled',
    }

    def __init__(self, config):
        super().__init__(config)
        self.client = Client(self.config[CONFIG_EXCHANGES][self.get_name()][CONFIG_EXCHANGE_KEY],
                             self.config[CONFIG_EXCHANGES][self.get_name()][CONFIG_EXCHANGE_SECRET])
        self.socket_manager = None
        self.open_sockets_keys = {}

    @classmethod
    def get_name(cls):
        return "binance"

    def get_last_price_ticker(self, symbol):
        return float(self.exchange_data.symbol_tickers[merge_symbol(symbol)]["c"])

    def all_currencies_prices_callback(self, msg):
        if msg['data']['e'] == 'error':
            # close and restart the socket
            # self.close_sockets()
            self.start_sockets()
        else:
            msg_stream_type = msg["stream"]
            if self._TICKER_KEY in msg_stream_type:
                self.exchange_data.set_ticker(msg["data"]["s"],
                                              msg["data"])
            elif self._KLINE_KEY in msg_stream_type:
                self.exchange_data.add_price(msg["data"]["s"],
                                             msg["data"]["k"]["i"],
                                             msg["data"]["k"]["t"],
                                             msg["data"])

    def _update_portfolio(self, msg):
        for currency in msg['B']:
            free = float(currency['f'])
            locked = float(currency['f'])
            total = free + locked
            self.exchange_data.update_portfolio(currency['a'], total, free, locked)

    @staticmethod
    def parse_order_status(status):
        return BinanceWebSocketClient._STATUSES[status] if status in BinanceWebSocketClient._STATUSES \
            else status.lower()

    @staticmethod
    def convert_into_ccxt_order(order):
        status = AbstractWebSocketManager.safe_value(order, 'X')
        if status is not None:
            status = BinanceWebSocketClient.parse_order_status(status)
        price = AbstractWebSocketManager.safe_float(order, "p")
        amount = AbstractWebSocketManager.safe_float(order, "q")
        filled = AbstractWebSocketManager.safe_float(order, "z", 0.0)
        cost = None
        remaining = None
        if filled is not None:
            if amount is not None:
                remaining = max(amount - filled, 0.0)
            if price is not None:
                cost = price * filled
        return {
            'info': order,
            'id': AbstractWebSocketManager.safe_string(order, "i"),
            'timestamp': order["T"],
            'datetime': AbstractWebSocketManager.iso8601(order["T"]),
            'lastTradeTimestamp': None,
            # warning string has no / between currency and market !!!
            'symbol': AbstractWebSocketManager.safe_string(order, "s"),
            'type': AbstractWebSocketManager.safe_lower_string(order, "o"),
            'side': AbstractWebSocketManager.safe_lower_string(order, "S"),
            'price': price,
            'amount': amount,
            'cost': cost,
            'filled': filled,
            'remaining': remaining,
            'status': status,
            'fee': AbstractWebSocketManager.safe_float(order, "n", None),
        }

    def user_callback(self, msg):
        if msg["e"] == "outboundAccountInfo":
            self._update_portfolio(msg)
        elif msg["e"] == "executionReport":
            self._update_order(msg)

    def _init_price_sockets(self, time_frames, trader_pairs):
        # add klines
        prices = ["{}{}_{}".format(merge_symbol(symbol).lower(), self._KLINE_KEY, time_frame.value)
                  for time_frame in time_frames
                  for symbol in trader_pairs]
        # add tickers
        for symbol in trader_pairs:
            prices.append("{}{}".format(merge_symbol(symbol).lower(), self._TICKER_KEY))
        connection_key = self.socket_manager.start_multiplex_socket(prices, self.all_currencies_prices_callback)
        self.open_sockets_keys[self._MULTIPLEX_SOCKET_NAME] = connection_key

    def _init_user_socket(self):
        connection_key = self.socket_manager.start_user_socket(self.user_callback)
        self.open_sockets_keys[self._USER_SOCKET_NAME] = connection_key

    def init_web_sockets(self, time_frames, trader_pairs):
        self._init_price_sockets(time_frames, trader_pairs)
        self._init_user_socket()

    def get_socket_manager(self):
        return self.socket_manager

    def stop_sockets(self):
        if self.socket_manager:
            self.socket_manager.close()

        # ?
        reactor.stop()

    def start_sockets(self):
        if self.socket_manager:
            self.socket_manager.start()

    @staticmethod
    def get_websocket_client(config):
        ws_client = BinanceWebSocketClient(config)
        ws_client.socket_manager = BinanceSocketManager(ws_client.client)
        return ws_client
