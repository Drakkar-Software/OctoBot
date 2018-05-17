from trading.exchanges.websockets.abstract_websocket_manager import AbstractWebSocketManager
from binance.enums import *
from binance.websockets import BinanceSocketManager
from binance.client import Client

from tools.symbol_util import merge_symbol


class BinanceWebSocketClient(AbstractWebSocketManager):

    _TICKER_KEY = "@ticker"
    _KLINE_KEY = "@kline"

    def __init__(self, config):
        super().__init__(config)
        self.client = Client(config["exchanges"][self.get_name()]["api-key"],
                             self.config["exchanges"][self.get_name()]["api-secret"])
        self.socket_manager = None

    @classmethod
    def get_name(cls):
        return "binance"

    def get_last_price_ticker(self, symbol):
        return float(self.currency_database.symbol_tickers[merge_symbol(symbol)]["c"])

    def all_currencies_prices_callback(self, msg):
        if msg['data']['e'] == 'error':
            # close and restart the socket
            self.close_sockets()
            self.start_sockets()
        else:
            msg_stream_type = msg["stream"]
            if self._TICKER_KEY in msg_stream_type:
                self.currency_database.set_ticker(msg["data"]["s"],
                                                  msg["data"])
            if self._KLINE_KEY in msg_stream_type:
                self.currency_database.add_price(msg["data"]["s"],
                                                 msg["data"]["k"]["i"],
                                                 msg["data"]["k"]["t"],
                                                 msg["data"])

    def init_all_currencies_prices_web_socket(self, time_frames, trader_pairs):
        # add klines
        prices = ["{}{}_{}".format(merge_symbol(symbol).lower(), self._KLINE_KEY, time_frame.value)
                  for time_frame in time_frames
                  for symbol in trader_pairs]
        # add tickers
        for symbol in trader_pairs:
            prices.append("{}{}".format(merge_symbol(symbol).lower(), self._TICKER_KEY))
        connection_key = self.socket_manager.start_multiplex_socket(prices, self.all_currencies_prices_callback)
        return connection_key

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
        ws_client.socket_manager = BinanceSocketManager(ws_client)
        return ws_client
