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

from cryptofeed import FeedHandler
from cryptofeed.backends.aggregate import OHLCV
from cryptofeed.callback import Callback, TickerCallback, TradeCallback, BookCallback, FundingCallback
from cryptofeed.defines import TRADES, TICKER, L2_BOOK, BID, ASK, FUNDING
from cryptofeed.feed import Feed
from cryptofeed.standards import feed_to_exchange

from config import MARKET_SEPARATOR, TimeFrames, TimeFramesMinutes, MINUTE_TO_SECONDS
from trading.exchanges.websockets_exchanges import AbstractWebSocket
from trading.exchanges.websockets_exchanges.websocket import cryptofeed_classes
from trading.exchanges.websockets_exchanges.websocket.cryptofeed_callbacks import OHLCVCallBack, OrderBookCallBack, \
    RecentTradesCallBack, TickersCallBack, FundingCallBack
from trading.exchanges.websockets_exchanges.websocket.websocket import WebSocket


class CryptoFeedWebSocketClient(WebSocket):
    CF_MARKET_SEPARATOR = "-"

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)

        self.cryptofeed_handler = None

        self.open_sockets_keys = {}
        self.exchange_class = None

        self.trader_pairs = []
        self.time_frames = []
        self.converted_traded_pairs = []
        self.fixed_converted_traded_pairs = []

        self.is_handling_ohlcv = False
        self.is_handling_price_ticker = False
        self.is_handling_order_book = False
        self.is_handling_recent_trades = False
        self.is_handling_funding = False

        self.channels = []
        self.callbacks = {}

    def init_web_sockets(self, time_frames, trader_pairs):
        self.cryptofeed_handler = FeedHandler()
        self.exchange_class = self._get_cryptofeed_class(self.exchange_manager.exchange_class_string.title())
        self.trader_pairs = trader_pairs
        self.time_frames = time_frames
        self.converted_traded_pairs = self._get_converted_traded_pairs(trader_pairs)

        if self.converted_traded_pairs:
            self.add_recent_trade_feed()
            self.add_order_book_feed()
            self.add_tickers_feed()
            self.add_ohlcv_feed()

            # Not implemented
            # self.add_funding_feed()

            # ensure feeds are added
            self._create_cryptofeed_feeds()
        else:
            self.logger.warning(f"{self.exchange_manager.exchange_class_string.title()}'s "
                                f"websocket has no symbol to feed")

    # Feeds
    def add_recent_trade_feed(self):
        if self._is_feed_available(TRADES):
            self._add_feed_and_run_if_required(TRADES, TradeCallback(RecentTradesCallBack(self).recent_trades_callback))
            self.is_handling_recent_trades = True
        else:
            self.logger.warning(f"{self.exchange_manager.exchange_class_string.title()}'s "
                                f"websocket is not handling recent trades")

    def add_order_book_feed(self):
        if self._is_feed_available(L2_BOOK):
            self._add_feed_and_run_if_required(L2_BOOK, BookCallback(OrderBookCallBack(self).l2_order_book_callback))
            self.is_handling_order_book = True
        else:
            self.logger.warning(f"{self.exchange_manager.exchange_class_string.title()}'s "
                                f"websocket is not handling order book")

    def add_tickers_feed(self):
        if self._is_feed_available(TICKER):
            self._add_feed_and_run_if_required(TICKER, TickerCallback(TickersCallBack(self).tickers_callback))
            self.is_handling_price_ticker = True
        else:
            self.logger.warning(f"{self.exchange_manager.exchange_class_string.title()}'s "
                                f"websocket is not handling tickers")

    def add_ohlcv_feed(self):
        if self._is_feed_available(TRADES):
            for time_frame in self.time_frames:
                self._add_feed_and_run_if_required(
                    TRADES,
                    OHLCV(Callback(OHLCVCallBack(self, time_frame).ohlcv_callback),
                          window=self._convert_time_frame_minutes_to_seconds(TimeFramesMinutes[time_frame])))

            # add real time handler
            self._add_feed_and_run_if_required(
                TRADES,
                OHLCV(Callback(OHLCVCallBack(self, 0).ohlcv_callback), window=0))

            self.is_handling_ohlcv = True
        else:
            self.logger.warning(f"{self.exchange_manager.exchange_class_string.title()}'s "
                                f"websocket is not handling ohlcv")

    def add_funding_feed(self):
        if self._is_feed_available(FUNDING):
            self._add_feed_and_run_if_required(FUNDING, FundingCallback(FundingCallBack(self).funding_callback))
            self.is_handling_funding = True
        else:
            self.logger.warning(f"{self.exchange_manager.exchange_class_string.title()}'s "
                                f"websocket is not handling funding")

    def _is_feed_available(self, feed):
        try:
            feed_to_exchange(self.exchange_class.id, feed)
            return True
        except (KeyError, ValueError):
            return False

    def _add_feed_and_run_if_required(self, feed, callback):
        # should run and reset channels (duplicate)
        if feed in self.channels:
            self._create_cryptofeed_feeds()
            self.channels = []
            self.callbacks = {}

        self.channels.append(feed)
        self.callbacks[feed] = callback

    def _create_cryptofeed_feeds(self):
        try:
            self.cryptofeed_handler.add_feed(
                self.exchange_class(pairs=self.converted_traded_pairs,
                                    channels=self.channels,
                                    callbacks=self.callbacks))
        except ValueError:
            if not self.fixed_converted_traded_pairs:
                self.fixed_converted_traded_pairs = self._get_converted_traded_pairs(self.trader_pairs, with_fix=True)

            self.cryptofeed_handler.add_feed(
                self.exchange_class(pairs=self.fixed_converted_traded_pairs,
                                    channels=self.channels,
                                    callbacks=self.callbacks))

    def _get_converted_traded_pairs(self, trader_pairs, with_fix=False):
        converted_pairs = []
        for symbol in trader_pairs:
            adapted_symbol = self._adapt_symbol(symbol, with_fix=with_fix)
            if adapted_symbol:
                converted_pairs.append(adapted_symbol)
        return converted_pairs

    @classmethod
    def get_name(cls):
        return "CryptoFeed"

    @classmethod
    def has_name(cls, name: str):
        return cls._get_cryptofeed_class(name) is not None or name.title() in cryptofeed_classes

    @classmethod
    def _get_cryptofeed_class(cls, name):
        if name in cryptofeed_classes:
            return cryptofeed_classes[name.title()]
        else:
            for feed_class in Feed.__subclasses__():
                if feed_class.__name__ == name.title():
                    return feed_class

    @staticmethod
    def get_websocket_client(config, exchange_manager):
        ws_client = CryptoFeedWebSocketClient(config, exchange_manager)
        return ws_client

    def start_sockets(self):
        is_websocket_running = False

        if self.is_handling_order_book or \
                self.is_handling_price_ticker or \
                self.is_handling_funding or \
                self.is_handling_ohlcv or \
                self.is_handling_recent_trades:
            self.cryptofeed_handler.run()
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
        symbol_data = None
        if pair in self.converted_traded_pairs:
            symbol_data = self.exchange_manager.get_symbol_data(self._adapt_symbol(pair))
        elif pair in self.fixed_converted_traded_pairs:
            symbol_data = self.exchange_manager.get_symbol_data(self._adapt_symbol(pair, with_fix=True))

        if symbol_data and symbol_data.ticker_is_initialized():
            return symbol_data
        return None

    def handles_recent_trades(self):
        return self.is_handling_recent_trades  # TODO implement dynamicaly

    def handles_order_book(self):
        return self.is_handling_order_book  # TODO implement dynamicaly

    def handles_price_ticker(self):
        return self.is_handling_price_ticker  # TODO implement dynamicaly

    def handles_ohlcv(self):
        return self.is_handling_ohlcv  # TODO implement dynamicaly

    def handles_funding(self):
        return self.is_handling_funding  # TODO implement dynamicaly

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

    def convert_into_ccxt_ohlcv(self, data, symbol, timestamp):
        return [
            timestamp,
            AbstractWebSocket.safe_float(data[symbol], "open"),
            AbstractWebSocket.safe_float(data[symbol], "high"),
            AbstractWebSocket.safe_float(data[symbol], "low"),
            AbstractWebSocket.safe_float(data[symbol], "close"),
            AbstractWebSocket.safe_float(data[symbol], "volume"),
        ]

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

    def _adapt_symbol(self, symbol, with_fix=False):
        if MARKET_SEPARATOR in symbol:
            symbol_proposal = symbol.replace(MARKET_SEPARATOR, self.CF_MARKET_SEPARATOR)
            if with_fix:
                return self._fix_adapt_symbol(symbol, symbol_proposal)
            else:
                return symbol_proposal
        else:
            if self.CF_MARKET_SEPARATOR in symbol:
                symbol = symbol.replace(self.CF_MARKET_SEPARATOR, MARKET_SEPARATOR)
            symbol_proposal = symbol
            if with_fix:
                return self._fix_adapt_symbol(symbol, symbol_proposal, with_id=False)
            else:
                return symbol_proposal

    def _fix_adapt_symbol(self, symbol, symbol_proposal, with_id=True):
        if with_id:
            # bitmex support
            if hasattr(self.exchange_class, 'get_active_symbols'):
                if symbol_proposal in self.exchange_class.get_active_symbols():
                    return symbol_proposal
            return self.exchange_manager.get_exchange_symbol_id(symbol)
        else:
            return self.exchange_manager.get_exchange_symbol(symbol)
