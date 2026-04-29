# pylint: disable=E0611
#  Drakkar-Software OctoBot-Trading
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

import abc
import asyncio

import octobot_commons.logging as logging
import octobot_trading.constants
import octobot_trading.enums
import octobot_trading.exchange_channel as exchange_channel
import octobot_trading.exchange_data as exchange_data


class AbstractWebsocketExchange:
    __metaclass__ = abc.ABCMeta

    REQUIRED_ACTIVATED_TENTACLES = []
    EXCHANGE_FEEDS = {}

    INIT_REQUIRING_EXCHANGE_FEEDS = set()

    # Used to ignore a feed when at least one of the corresponding feed is supported
    IGNORED_FEED_PAIRS = {}

    SUPPORTS_LIVE_PAIR_ADDITION = False

    TIME_FRAME_RELATED_FEEDS = [
        octobot_trading.enums.WebsocketFeeds.CANDLE,
        octobot_trading.enums.WebsocketFeeds.KLINE,
    ]
    # Feeds to create above which not to use websockets
    MAX_HANDLED_FEEDS = octobot_trading.constants.NO_DATA_LIMIT

    def __init__(self, config, exchange_manager):
        self.config = config

        self.exchange_manager = exchange_manager
        self.exchange = self.exchange_manager.exchange
        self.exchange_id = self.exchange_manager.id

        self.bot_mainloop = asyncio.get_event_loop()

        self.currencies = []
        self.pairs = []
        self.time_frames = []
        self.channels = []

        self.books = {}

        self.client = None
        self.name = self.get_name()
        self.logger = logging.get_logger(self._get_logger_name())

    def _get_logger_name(self):
        return f"WebSocket - {self.name}"

    def initialize(self, currencies=None, pairs=None, time_frames=None, channels=None):
        self.pairs = [self.get_exchange_pair(pair) for pair in pairs] if pairs else []
        # inner list required for cythonization
        self.channels = list(set([self.feed_to_exchange(channel) for channel in channels])) if channels else []
        self.time_frames = [
            time_frame
            for time_frame in time_frames
            if self.is_time_frame_supported(time_frame)
        ] if time_frames is not None else []
        self.currencies = currencies if currencies else []

    @classmethod
    def update_exchange_feeds(cls, exchange_manager):
        """
        Called before exchange instantiation, should be used to patch cls.EXCHANGE_FEEDS if necessary
        """

    def is_time_frame_related_feed(self, feed):
        return feed in self.TIME_FRAME_RELATED_FEEDS

    def is_time_frame_supported(self, time_frame):
        raise NotImplementedError("is_time_frame_supported is not implemented")

    def get_exchange_credentials(self):
        return self.exchange_manager.get_exchange_credentials(self.exchange_manager.exchange_name)

    async def push_to_channel(self, channel_name, *args, **kwargs):
        try:
            asyncio.run_coroutine_threadsafe(
                exchange_channel.get_chan(channel_name, self.exchange_id).get_internal_producer().push(*args, **kwargs),
                self.bot_mainloop)
        except Exception as e:
            self.logger.error(f"Push to {channel_name} failed : {e}")

    # Abstract methods
    @classmethod
    def get_name(cls):
        raise NotImplementedError("get_name not implemented")

    @classmethod
    def has_name(cls, name: str) -> bool:
        raise NotImplementedError("has_name not implemented")

    @abc.abstractmethod
    async def init_websocket(self, time_frames, trader_pairs, tentacles_setup_config):
        raise NotImplementedError("init_websocket not implemented")

    @abc.abstractmethod
    async def start_sockets(self):
        raise NotImplementedError("start_sockets not implemented")

    @abc.abstractmethod
    async def wait_sockets(self):
        raise NotImplementedError("wait_sockets not implemented")

    @abc.abstractmethod
    def update_followed_pairs(self):
        raise NotImplementedError("updated_followed_pairs not implemented")

    @abc.abstractmethod
    async def _close_and_restart_sockets(self, debounce_duration=0):
        raise NotImplementedError("_close_and_restart_sockets not implemented")

    @abc.abstractmethod
    async def stop_sockets(self):
        """
        Stops the websocket. Can be restarted
        """
        raise NotImplementedError("stop_sockets not implemented")

    @abc.abstractmethod
    async def close_sockets(self):
        """
        Closes the websocket. Can't be restarted
        """
        raise NotImplementedError("close_sockets not implemented")

    @classmethod
    def get_exchange_feed(cls, feed) -> str:
        return cls.EXCHANGE_FEEDS.get(feed, octobot_trading.enums.WebsocketFeeds.UNSUPPORTED.value)

    @classmethod
    def is_feed_requiring_init(cls, feed) -> bool:
        return feed in cls.INIT_REQUIRING_EXCHANGE_FEEDS

    @classmethod
    def is_feed_supported(cls, feed_name) -> bool:
        return feed_name != octobot_trading.enums.WebsocketFeeds.UNSUPPORTED.value

    @classmethod
    def should_ignore_feed(cls, feed):
        """
        Checks if a feed should be ignored
        :param feed: the feed (instance of octobot_trading.enums.WebsocketFeeds)
        :return: True when the feed is already covered by another one
        """
        ignored_feed_candidate_list = cls.IGNORED_FEED_PAIRS.get(feed, [])
        if not ignored_feed_candidate_list:
            return False
        for feed_candidate, feed_value in cls.EXCHANGE_FEEDS.items():
            if feed_candidate in ignored_feed_candidate_list and \
                    cls.is_feed_supported(feed_value):
                return True
        return False

    def feed_to_exchange(self, feed):
        feed_name: str = self.get_exchange_feed(feed)
        if not self.is_feed_supported(feed_name):
            self.logger.error("{} is not supported on {}".format(feed, self.get_name()))
            raise ValueError(f"{feed} is not supported on {self.get_name()}")
        return feed

    def get_book_instance(self, symbol):
        try:
            return self.books[symbol]
        except KeyError:
            self.books[symbol] = exchange_data.OrderBookManager()
            return self.books[symbol]

    def get_pair_from_exchange(self, pair):
        raise NotImplementedError("get_pair_from_exchange is not implemented")

    def get_exchange_pair(self, pair):
        raise NotImplementedError("get_exchange_pair is not implemented")

    async def reset(self):
        raise NotImplementedError("reset is not implemented")

    def add_pairs(self, pairs, watching_only=False):
        """
        Add new pairs to self.filtered_pairs
        :param pairs: the list of pair to add
        :param watching_only: if pairs are for watching or trading purpose
        """
        raise NotImplementedError("add_pairs is not implemented")

    def remove_pairs(self, pairs, watching_only=False):
        """
        Remove pairs from self.filtered_pairs
        :param pairs: the list of pair to remove
        :param watching_only: if pairs are for watching or trading purpose
        """
        raise NotImplementedError("remove_pairs is not implemented")

    def get_max_handled_pair_with_time_frame(self):
        """
        :return: the maximum number of simultaneous pairs * time_frame that this exchange can handle.
        """
        return octobot_trading.constants.INFINITE_MAX_HANDLED_PAIRS_WITH_TIMEFRAME

    @classmethod
    def get_feeds_count(cls, pairs, time_frames) -> int:
        raise NotImplementedError(f"get_feeds_count is not implemented")

    def _should_authenticate(self):
        api_key, api_secret, _, _, _ = self.get_exchange_credentials()
        return not self.exchange_manager.without_auth \
            and not self.exchange_manager.is_trader_simulated \
            and api_key and api_secret

    def clear(self):
        self.exchange = None
        self.exchange_manager = None
