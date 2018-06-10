from binance.client import Client, BinanceAPIException
from binance.websockets import BinanceSocketManager
from binance.client import Client, BinanceAPIException
from twisted.internet import reactor

from config.cst import *
from tools.symbol_util import merge_symbol
from trading.exchanges.websockets_exchanges.abstract_websocket import AbstractWebSocket


class BinanceWebSocketClient(AbstractWebSocket):
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

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self.client = Client(self.config[CONFIG_EXCHANGES][self.name][CONFIG_EXCHANGE_KEY],
                             self.config[CONFIG_EXCHANGES][self.name][CONFIG_EXCHANGE_SECRET])
        self.socket_manager = None
        self.open_sockets_keys = {}

    @staticmethod
    def get_websocket_client(config, exchange_manager):
        ws_client = BinanceWebSocketClient(config, exchange_manager)
        ws_client.socket_manager = BinanceSocketManager(ws_client.client)
        return ws_client

    def init_web_sockets(self, time_frames, trader_pairs):
        try:
            self._init_price_sockets(time_frames, trader_pairs)
            self._init_user_socket()
        except BinanceAPIException as e:
            self.logger.error("error when connecting to binance websockets: {0}".format(e))

    def start_sockets(self):
        if self.socket_manager:
            self.socket_manager.start()

    def stop_sockets(self):
        if self.socket_manager:
            self.socket_manager.close()

    def get_socket_manager(self):
        return self.socket_manager

    @classmethod
    def get_name(cls):
        return "binance"

    # Binance rest API documentation
    # (https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md):
    #
    # Recent trades list
    # GET /api/v1/trades
    # Get recent trades(up to last 500).
    #
    # Weight: 1
    #
    # and:
    #
    # Compressed/Aggregate trades list
    # GET /api/v1/aggTrades
    # Get compressed, aggregate trades. Trades that fill at the time, from the same order, with the same price will
    # have the quantity aggregated.
    #
    # Weight: 1
    #
    # => Better using rest exchange services to save cpu resources (minimal rest request weigh).
    @classmethod
    def handles_recent_trades(cls):
        return False

    @classmethod
    def handles_order_book(cls):
        return False

    @classmethod
    def handles_price_ticker(cls):
        return True

    @staticmethod
    def parse_order_status(status):
        return BinanceWebSocketClient._STATUSES[status] if status in BinanceWebSocketClient._STATUSES \
            else status.lower()

    @staticmethod
    def convert_into_ccxt_order(order):
        status = AbstractWebSocket.safe_value(order, 'X')
        if status is not None:
            status = BinanceWebSocketClient.parse_order_status(status)
        price = AbstractWebSocket.safe_float(order, "p")
        amount = AbstractWebSocket.safe_float(order, "q")
        filled = AbstractWebSocket.safe_float(order, "z", 0.0)
        cost = None
        remaining = None
        if filled is not None:
            if amount is not None:
                remaining = max(amount - filled, 0.0)
            if price is not None:
                cost = price * filled
        return {
            'info': order,
            'id': AbstractWebSocket.safe_string(order, "i"),
            'timestamp': order["T"],
            'datetime': AbstractWebSocket.iso8601(order["T"]),
            'lastTradeTimestamp': None,
            # TODO string has no / between currency and market => need to add it !!!
            'symbol': AbstractWebSocket.safe_string(order, "s"),
            'type': AbstractWebSocket.safe_lower_string(order, "o"),
            'side': AbstractWebSocket.safe_lower_string(order, "S"),
            'price': price,
            'amount': amount,
            'cost': cost,
            'filled': filled,
            'remaining': remaining,
            'status': status,
            'fee': AbstractWebSocket.safe_float(order, "n", None),
        }

    def all_currencies_prices_callback(self, msg):
        if msg['data']['e'] == 'error':
            # close and restart the socket
            # self.close_sockets()
            self.start_sockets()
        else:
            msg_stream_type = msg["stream"]
            if self._TICKER_KEY in msg_stream_type:
                self.exchange_manager.get_symbol_data(msg["data"]["s"]).update_symbol_ticker(msg["data"])
            elif self._KLINE_KEY in msg_stream_type:
                self.get_symbol_data(msg["data"]["s"]).update_symbol_candles(
                    self._convert_time_frame(msg["data"]["k"]["i"]),
                    self._create_candle(msg["data"]["k"]),
                    start_candle_time=msg["data"]["k"]["t"],
                    replace_all=False)

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

    # candle: list[0:5]  #time, open, high, low, close, vol
    @staticmethod
    def _create_candle(kline_data):
        return [
            kline_data["t"],  # time
            AbstractWebSocket.safe_float(kline_data, "o"),  # open
            AbstractWebSocket.safe_float(kline_data, "h"),  # high
            AbstractWebSocket.safe_float(kline_data, "l"),  # low
            AbstractWebSocket.safe_float(kline_data, "c"),  # close
            AbstractWebSocket.safe_float(kline_data, "v"),  # vol
        ]

    def _update_portfolio(self, msg):
        for currency in msg['B']:
            free = float(currency['f'])
            locked = float(currency['l'])
            total = free + locked
            self.exchange_manager.get_personal_data().update_portfolio(currency['a'], total, free, locked)

    # unimplemented methods
    @staticmethod
    def format_price_ticker(price_ticker):
        pass

    def init_all_currencies_prices_web_socket(self, time_frames, trader_pairs):
        pass

    @staticmethod
    def _adapt_symbol(symbol):
        return symbol
