#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

from config import TimeFrames, TimeFramesMinutes, MINUTE_TO_SECONDS
from octobot_websockets import ASK, BID, TICKER, L2_BOOK, TRADES, UNSUPPORTED
from octobot_websockets.callback import TickerCallback, BookCallback, TradeCallback
from octobot_websockets.feedhandler import FeedHandler
from trading.exchanges.websockets.abstract_websocket import AbstractWebSocket
from trading.exchanges.websockets.websocket_callbacks import OrderBookCallBack, \
    RecentTradesCallBack, TickersCallBack

from octobot_websockets.bitmex.bitmex import Bitmex

WEBSOCKET_CLASSES = {
    # "Bitfinex": Bitfinex,
    # "Bitfinex2": Bitfinex,
    "bitmex": Bitmex,
    # "Hitbtc": HitBTC,
    # "Coinbase": Coinbase,
    # "Coinbasepro": Coinbase,
    # "Exx": EXX,
    # "Poloniex": Poloniex, TODO Poloniex does not handle unsupported pairs
    # "Bitstamp": Bitstamp,
    # "Huobi": Huobi,  # Not supported by ccxt
    # "Gemini": Gemini TODO Gemini requires a websocket per trading pair
}


class OctoBotWebSocketClient(AbstractWebSocket):
    CF_MARKET_SEPARATOR = "-"

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self.exchange_manager = exchange_manager
        self.octobot_feed_handler = None

        self.open_sockets_keys = {}
        self.exchange_class = None

        self.trader_pairs = []
        self.time_frames = []

        self.is_handling_ohlcv = False
        self.is_handling_price_ticker = False
        self.is_handling_order_book = False
        self.is_handling_recent_trades = False
        self.is_handling_funding = False

        self.channels = []
        self.callbacks = {}

    def init_web_sockets(self, time_frames, trader_pairs):
        self.octobot_feed_handler = FeedHandler()
        self.exchange_class = self._get_octobot_feed_class(self.exchange_manager.exchange.get_name())
        self.trader_pairs = trader_pairs
        self.time_frames = time_frames

        if self.trader_pairs:
            self.add_recent_trade_feed()
            self.add_order_book_feed()
            self.add_tickers_feed()

            # ensure feeds are added
            self._create_octobot_feed_feeds()
        else:
            self.logger.warning(f"{self.exchange_manager.exchange_class_string.title()}'s "
                                f"websocket has no symbol to feed")

    # Feeds
    def add_recent_trade_feed(self):
        if self._is_feed_available(TRADES):
            recent_trade_callback = RecentTradesCallBack(self,
                                                         self.exchange_manager.recent_trade_consumer_producer.consumer)
            self._add_feed_and_run_if_required(TRADES, TradeCallback(recent_trade_callback.recent_trades_callback))
            self.is_handling_recent_trades = True
        else:
            self.logger.warning(f"{self.exchange_manager.exchange_class_string.title()}'s "
                                f"websocket is not handling recent trades")

    def add_order_book_feed(self):
        if self._is_feed_available(L2_BOOK):
            order_book_callback = OrderBookCallBack(self, self.exchange_manager.order_book_consumer_producer.consumer)
            self._add_feed_and_run_if_required(L2_BOOK, BookCallback(order_book_callback.l2_order_book_callback))
            self.is_handling_order_book = True
        else:
            self.logger.warning(f"{self.exchange_manager.exchange_class_string.title()}'s "
                                f"websocket is not handling order book")

    def add_tickers_feed(self):
        if self._is_feed_available(TICKER):
            tickers_callback = TickersCallBack(self, self.exchange_manager.ticker_consumer_producer.consumer)
            self._add_feed_and_run_if_required(TICKER, TickerCallback(tickers_callback.tickers_callback))
            self.is_handling_price_ticker = True
        else:
            self.logger.warning(f"{self.exchange_manager.exchange.get_name()}'s "
                                f"websocket is not handling tickers")

    def _is_feed_available(self, feed):
        try:
            feed_available = self.exchange_class.get_feeds()[feed]
            return feed_available is not UNSUPPORTED
        except (KeyError, ValueError):
            return False

    def _add_feed_and_run_if_required(self, feed, callback):
        # should run and reset channels (duplicate)
        if feed in self.channels:
            self._create_octobot_feed_feeds()
            self.channels = []
            self.callbacks = {}

        self.channels.append(feed)
        self.callbacks[feed] = callback

    def _create_octobot_feed_feeds(self):
        try:
            self.octobot_feed_handler.add_feed(
                self.exchange_class(pairs=self.trader_pairs,
                                    channels=self.channels,
                                    callbacks=self.callbacks))
        except ValueError as e:
            self.logger.exception(f"Fail to create feed : {e}")

    @classmethod
    def get_name(cls):
        return "octobot_feed"

    @classmethod
    def has_name(cls, name: str):
        return cls._get_octobot_feed_class(name) is not None

    @classmethod
    def _get_octobot_feed_class(cls, name):
        if name in WEBSOCKET_CLASSES:
            return WEBSOCKET_CLASSES[name]
        return None

    @staticmethod
    def get_websocket_client(config, exchange_manager):
        ws_client = OctoBotWebSocketClient(config, exchange_manager)
        return ws_client

    def start_sockets(self):
        is_websocket_running = False

        if self.is_handling_order_book or \
                self.is_handling_price_ticker or \
                self.is_handling_funding or \
                self.is_handling_ohlcv or \
                self.is_handling_recent_trades:
            self.octobot_feed_handler.run()
            is_websocket_running = True

        if not is_websocket_running:
            self.logger.error(f"{self.exchange_manager.exchange_class_string.title()}'s "
                              f"websocket is not handling anything, it will not be started, ")

    def close_and_restart_sockets(self):
        # TODO
        pass

    def stop_sockets(self):
        pass

    def get_symbol_data_from_pair(self, pair):
        symbol_data = self.exchange_manager.get_symbol_data(self._adapt_symbol(pair))

        if symbol_data:
            return symbol_data
        return None

    def handles_recent_trades(self):
        return self.is_handling_recent_trades  # TODO implement dynamicaly

    def handles_order_book(self):
        return self.is_handling_order_book  # TODO implement dynamicaly

    def handles_price_ticker(self):
        return self.is_handling_price_ticker  # TODO implement dynamicaly

    def handles_funding(self) -> bool:
        return False

    def handles_ohlcv(self) -> bool:
        return False

    def handles_balance(self) -> bool:
        return False

    def handles_orders(self) -> bool:
        return False

    # Converters
    def convert_into_ccxt_ticker(self, symbol, data, timestamp):
        iso8601 = None if (timestamp is None) else self.iso8601(timestamp)
        return {
            'symbol': symbol,
            'timestamp': timestamp,
            'datetime': iso8601,
            'high': self.safe_float(data, 'high'),
            'low': self.safe_float(data, 'low'),
            'volume': self.safe_float(data, 'volume'),
            'vwap': self.safe_float(data, 'vwap'),
            'open': self.safe_float(data, 'open'),
            'close': self.safe_float(data, 'close'),
            'last': self.safe_float(data, 'close')
        }

    def convert_into_ccxt_price_ticker(self, symbol, bid, ask, timestamp):
        return {
            'symbol': symbol,
            'timestamp': timestamp,
            'bid': bid,
            'ask': ask
        }

    def convert_into_ccxt_full_order_book(self, symbol, book, timestamp):
        return {
            'bids': book[BID],
            'asks': book[ASK],
            'timestamp': timestamp,
        }

    def convert_into_ccxt_updated_order_book(self, symbol, update, timestamp):
        pass

    def convert_into_ccxt_recent_trade(self, symbol, side, amount, price, timestamp):
        return {
            'timestamp': timestamp,
            'symbol': symbol,
            'side': side,
            'price': price,
            'amount': amount
        }

    def convert_into_ccxt_ohlcv(self, data, symbol):
        return [
            data[symbol]["timestamp"],
            AbstractWebSocket.safe_float(data[symbol], "open"),
            AbstractWebSocket.safe_float(data[symbol], "high"),
            AbstractWebSocket.safe_float(data[symbol], "low"),
            AbstractWebSocket.safe_float(data[symbol], "close"),
            AbstractWebSocket.safe_float(data[symbol], "volume"),
        ]

    def convert_into_ccxt_order(self, order):
        pass

    def convert_into_ccxt_funding(self, funding):
        pass

    @staticmethod
    def _convert_seconds_to_time_frame(time_frame_seconds) -> TimeFrames:
        return TimeFramesMinutes(time_frame_seconds / MINUTE_TO_SECONDS)

    @staticmethod
    def _convert_time_frame_minutes_to_seconds(time_frame) -> int:
        if isinstance(time_frame, TimeFramesMinutes.__class__):
            return time_frame.value * MINUTE_TO_SECONDS
        elif isinstance(time_frame, int):
            return time_frame * MINUTE_TO_SECONDS

    @staticmethod
    def parse_order_status(status):
        pass
