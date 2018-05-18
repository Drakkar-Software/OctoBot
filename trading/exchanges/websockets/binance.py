from trading.exchanges.websockets.abstract_websocket_manager import AbstractWebSocketManager
from binance.enums import *
from binance.websockets import BinanceSocketManager
from binance.client import Client
from ccxt.base.exchange import Exchange as ccxtExchange

from tools.symbol_util import merge_symbol


class BinanceWebSocketClient(AbstractWebSocketManager):

    _TICKER_KEY = "@ticker"
    _KLINE_KEY = "@kline"
    _MULTIPLEX_SOCKET_NAME = "multiplex"
    _USER_SOCKET_NAME = "user"

    def __init__(self, config):
        super().__init__(config)
        self.client = Client(config["exchanges"][self.get_name()]["api-key"],
                             self.config["exchanges"][self.get_name()]["api-secret"])
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
            self.close_sockets()
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

    def _create_ccxt_order(self, order):
        return {
            'info': order,
            'id': ccxtExchange.safe_string(order,"i"),
            'timestamp': order["T"],
            'datetime': ccxtExchange.iso8601(order["T"]),
            'lastTradeTimestamp': None,
            # 'symbol': symbol,
            # 'type': type,
            # 'side': side,
            # 'price': ccxtExchange.safe_float(order, "p"),
            # 'amount': amount,
            # 'cost': cost,
            # 'filled': filled,
            # 'remaining': remaining,
            # 'status': status,
            # 'fee': None,
        }

    def _update_orders(self, msg):
        self._create_ccxt_order(msg)

    def user_callback(self, msg):
        if msg["e"] == "outboundAccountInfo":
            self._update_portfolio(msg)
        elif msg["e"] == "executionReport":
            self._update_orders(msg)

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

    def close_sockets(self):
        if self.socket_manager:
            self.socket_manager.close()

    def start_sockets(self):
        if self.socket_manager:
            self.socket_manager.start()

    @staticmethod
    def get_websocket_client(config):
        ws_client = BinanceWebSocketClient(config)
        ws_client.socket_manager = BinanceSocketManager(ws_client.client)
        return ws_client
