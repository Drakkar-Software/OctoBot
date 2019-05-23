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
import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
from threading import Thread
from typing import List, Dict

from config import TimeFrames, TimeFramesMinutes, MINUTE_TO_SECONDS
from octobot_channels.channels import TICKER_CHANNEL, ORDER_BOOK_CHANNEL, RECENT_TRADES_CHANNEL
from octobot_channels.channels.exchange.exchange_channel import ExchangeChannels
from octobot_websockets.callback import TradeCallback, BookCallback, TickerCallback
from octobot_websockets.constants import TICKER, L2_BOOK, TRADES, UNSUPPORTED
from octobot_websockets.feeds.bitmex import Bitmex
from octobot_websockets.feeds.feed import Feed
from trading.exchanges.websockets.abstract_websocket import AbstractWebSocket
from trading.exchanges.websockets.websocket_callbacks import OrderBookCallBack, \
    RecentTradesCallBack, TickersCallBack

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
        self.exchange_name: str = exchange_manager.exchange.get_name()
        self.octobot_websockets: List[Feed] = []
        self.octobot_websockets_t: List[Thread] = []
        self.octobot_websockets_executors: ThreadPoolExecutor = None

        self.open_sockets_keys: Dict = {}
        self.exchange_class: Feed.__class__ = None

        self.trader_pairs: List = []
        self.time_frames: List = []

        self.is_handling_ohlcv: bool = False
        self.is_handling_price_ticker: bool = False
        self.is_handling_order_book: bool = False
        self.is_handling_recent_trades: bool = False
        self.is_handling_funding: bool = False

        self.channels: List = []
        self.callbacks: Dict = {}

    def init_web_sockets(self, time_frames: List, trader_pairs: List):
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
            self.logger.warning(f"{self.exchange_manager.exchange.get_name().title()}'s "
                                f"websocket has no symbol to feed")

    # Feeds
    def add_recent_trade_feed(self):
        if self._is_feed_available(TRADES):
            recent_trade_callback = RecentTradesCallBack(self,
                                                         ExchangeChannels.get_chan(RECENT_TRADES_CHANNEL,
                                                                                   self.exchange_name))

            self._add_feed_and_run_if_required(TRADES, TradeCallback(recent_trade_callback.recent_trades_callback))
            self.is_handling_recent_trades = True
        else:
            self.logger.warning(f"{self.exchange_manager.exchange_class_string.title()}'s "
                                f"websocket is not handling recent trades")

    def add_order_book_feed(self):
        if self._is_feed_available(L2_BOOK):
            order_book_callback = OrderBookCallBack(self, ExchangeChannels.get_chan(ORDER_BOOK_CHANNEL,
                                                                                    self.exchange_name))

            self._add_feed_and_run_if_required(L2_BOOK, BookCallback(order_book_callback.l2_order_book_callback))
            self.is_handling_order_book = True
        else:
            self.logger.warning(f"{self.exchange_manager.exchange_class_string.title()}'s "
                                f"websocket is not handling order book")

    def add_tickers_feed(self):
        if self._is_feed_available(TICKER):
            tickers_callback = TickersCallBack(self, ExchangeChannels.get_chan(TICKER_CHANNEL,
                                                                               self.exchange_name))

            self._add_feed_and_run_if_required(TICKER, TickerCallback(tickers_callback.tickers_callback))
            self.is_handling_price_ticker = True
        else:
            self.logger.warning(f"{self.exchange_manager.exchange.get_name()}'s "
                                f"websocket is not handling tickers")

    def _is_feed_available(self, feed: Feed) -> bool:
        try:
            feed_available = self.exchange_class.get_feeds()[feed]
            return feed_available is not UNSUPPORTED
        except (KeyError, ValueError):
            return False

    def _add_feed_and_run_if_required(self, feed: List, callback):
        # should run and reset channels (duplicate)
        if feed in self.channels:
            self._create_octobot_feed_feeds()
            self.channels = []
            self.callbacks = {}

        self.channels.append(feed)
        self.callbacks[feed] = callback

    def _create_octobot_feed_feeds(self):
        try:
            self.octobot_websockets.append(
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
            self.octobot_websockets_executors = ThreadPoolExecutor(max_workers=len(self.octobot_websockets))
            for websocket in self.octobot_websockets:
                asyncio.get_event_loop().run_in_executor(self.octobot_websockets_executors, websocket.start)
            is_websocket_running = True

        if not is_websocket_running:
            self.logger.error(f"{self.exchange_manager.exchange.get_name().title()}'s "
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

    def handles_recent_trades(self) -> bool:
        return self.is_handling_recent_trades  # TODO implement dynamicaly

    def handles_order_book(self) -> bool:
        return self.is_handling_order_book  # TODO implement dynamicaly

    def handles_price_ticker(self) -> bool:
        return self.is_handling_price_ticker  # TODO implement dynamicaly

    def handles_funding(self) -> bool:
        return False

    def handles_ohlcv(self) -> bool:
        return False

    def handles_balance(self) -> bool:
        return False

    def handles_orders(self) -> bool:
        return False

    @staticmethod
    def _convert_seconds_to_time_frame(time_frame_seconds) -> TimeFrames:
        return TimeFramesMinutes(time_frame_seconds / MINUTE_TO_SECONDS)

    @staticmethod
    def _convert_time_frame_minutes_to_seconds(time_frame) -> int:
        if isinstance(time_frame, TimeFramesMinutes.__class__):
            return time_frame.value * MINUTE_TO_SECONDS
        elif isinstance(time_frame, int):
            return time_frame * MINUTE_TO_SECONDS
        else:
            return time_frame

    @staticmethod
    def parse_order_status(status):
        pass
