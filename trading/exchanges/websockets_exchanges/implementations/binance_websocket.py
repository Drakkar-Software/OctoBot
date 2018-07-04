from binance.client import Client, BinanceAPIException
from binance.websockets import BinanceSocketManager
import logging

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

    def convert_into_ccxt_ticker(self, ticker):
        timestamp = self.safe_integer(ticker, 'C')
        iso8601 = None if (timestamp is None) else self.iso8601(timestamp)
        symbol = self._adapt_symbol(self.safe_string(ticker, 's'))
        last = self.safe_float(ticker, 'c')
        return {
            'symbol': symbol,
            'timestamp': timestamp,
            'datetime': iso8601,
            'high': self.safe_float(ticker, 'h'),
            'low': self.safe_float(ticker, 'l'),
            'bid': self.safe_float(ticker, 'b'),
            'bidVolume': self.safe_float(ticker, 'B'),
            'ask': self.safe_float(ticker, 'a'),
            'askVolume': self.safe_float(ticker, 'A'),
            'vwap': self.safe_float(ticker, 'w'),
            'open': self.safe_float(ticker, 'o'),
            'close': last,
            'last': last,
            'previousClose': self.safe_float(ticker, 'x'),  # previous day close
            'change': self.safe_float(ticker, 'p'),
            'percentage': self.safe_float(ticker, 'P'),
            'average': None,
            'baseVolume': self.safe_float(ticker, 'v'),
            'quoteVolume': self.safe_float(ticker, 'q'),
            'info': ticker,
        }

    def convert_into_ccxt_order(self, order):
        status = self.safe_value(order, 'X')
        if status is not None:
            status = self.parse_order_status(status)
        price = self.safe_float(order, "p")
        amount = self.safe_float(order, "q")
        filled = self.safe_float(order, "z", 0.0)
        cost = None
        remaining = None
        if filled is not None:
            if amount is not None:
                remaining = max(amount - filled, 0.0)
            if price is not None:
                cost = price * filled
        return {
            'info': order,
            'id': self.safe_string(order, "i"),
            'timestamp': order["T"],
            'datetime': self.iso8601(order["T"]),
            'lastTradeTimestamp': None,
            'symbol': self._adapt_symbol(self.safe_string(order, "s")),
            'type': self.safe_lower_string(order, "o"),
            'side': self.safe_lower_string(order, "S"),
            'price': price,
            'amount': amount,
            'cost': cost,
            'filled': filled,
            'remaining': remaining,
            'status': status,
            'fee': self.safe_float(order, "n", None),
        }

    def all_currencies_prices_callback(self, msg):

        # TODO
        # ORDER BOOK : Stream Name: <symbol>@depth<levels>
        # Recent trades : Stream Name: <symbol>@trade

        if msg['data']['e'] == 'error':
            # close and restart the socket
            # self.close_sockets()
            logging.getLogger(self.get_name()).error("error in websocket all_currencies_prices_callback, "
                                                     "call start_sockets()")
            self.start_sockets()
        else:
            msg_stream_type = msg["stream"]

            symbol_data = self.exchange_manager.get_symbol_data(self._adapt_symbol(msg["data"]["s"]))

            if self._TICKER_KEY in msg_stream_type:
                if symbol_data.price_ticker_is_initialized():
                    symbol_data.update_symbol_ticker(self.convert_into_ccxt_ticker(msg["data"]))

            elif self._KLINE_KEY in msg_stream_type:
                time_frame = self._convert_time_frame(msg["data"]["k"]["i"])
                if symbol_data.candles_are_initialized(time_frame):
                    symbol_data.update_symbol_candles(
                        time_frame,
                        self._create_candle(msg["data"]["k"]),
                        replace_all=False)

    def user_callback(self, msg):
        if msg["e"] == "outboundAccountInfo":
            self._update_portfolio(msg)
        elif msg["e"] == "executionReport":
            self._update_order(msg)
        elif msg['e'] == 'error':
            logging.getLogger(self.get_name()).error("error in websocket user_callback, call start_sockets()")
            self.start_sockets()


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
        if self.exchange_manager.get_personal_data().get_portfolio_is_initialized():
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

    def _adapt_symbol(self, symbol):
        if "USD" in symbol and not "USDT" in symbol:
            symbol += "T"

        if "/" in symbol:
            symbol = merge_symbol(symbol)

        if not self.exchange_manager.get_is_simulated():
            return self._parse_symbol_from_ccxt(symbol)
        else:
            # used only for tests
            return symbol
