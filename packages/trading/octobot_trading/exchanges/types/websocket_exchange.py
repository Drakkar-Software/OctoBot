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
import asyncio
import typing
import sys
import concurrent.futures as futures

import octobot_commons.html_util as html_util
import octobot_commons.enums as commons_enums

import octobot_commons.thread_util as thread_util
import octobot_trading.constants
import octobot_trading.enums
import octobot_trading.exchanges.abstract_websocket_exchange as abstract_websocket


class WebSocketExchange(abstract_websocket.AbstractWebsocketExchange):
    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self.exchange_manager = exchange_manager
        self.exchange_name: str = exchange_manager.exchange_name

        self.websocket_connectors: list = []
        self.websocket_connectors_tasks: list[asyncio.Task] = []

        self.websocket_connectors_executors: typing.Optional[futures.ThreadPoolExecutor] = None
        self.websocket_connector = None # type: ignore

        self.pairs: list[str] = []
        self.time_frames: list[commons_enums.TimeFrames] = []

        self.channels: list[octobot_trading.enums.WebsocketFeeds] = []
        self.handled_feeds: dict[octobot_trading.enums.WebsocketFeeds, bool] = {}

        self.is_websocket_running: bool = False
        self.is_websocket_authenticated: bool = False
        self.is_beyond_feed_exchange_limit: bool = False

        self.restart_task: typing.Optional[asyncio.Task] = None

    @classmethod
    def get_exchange_connector_class(cls, exchange_manager):
        raise NotImplementedError("get_exchange_connector_class is not implemented")

    def create_feeds(self):
        raise NotImplementedError("create_feeds is not implemented")

    async def init_websocket(self, time_frames, trader_pairs, tentacles_setup_config):
        self.websocket_connector = self.get_exchange_connector_class(self.exchange_manager)
        self.websocket_connector.update_exchange_feeds(self.exchange_manager)
        self.pairs = trader_pairs
        self.time_frames = time_frames

        if self.pairs:
            if self._has_too_many_feeds_to_handle():
                self.logger.info(
                    f"Disabling websocket: {self.get_connector_feeds_count()} "
                    f"feeds are required and {self.get_connector_max_handled_feeds()} are supported at most."
                )
                self.is_beyond_feed_exchange_limit = True
                return
            # unauthenticated
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.TRADES)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.L1_BOOK)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.L2_BOOK)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.L3_BOOK)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.BOOK_DELTA)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.BOOK_TICKER)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.OPEN_INTEREST)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.MINI_TICKER)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.TICKER)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.FUNDING)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.MARK_PRICE)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.VOLUME)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.LIQUIDATIONS)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.FUTURES_INDEX)

            if self.time_frames:
                await self.add_feed(octobot_trading.enums.WebsocketFeeds.CANDLE)
                await self.add_feed(octobot_trading.enums.WebsocketFeeds.KLINE)

            # authenticated
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.POSITION)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.PORTFOLIO)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.TRADE)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.ORDERS)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.CREATE_ORDER)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.CANCEL_ORDER)
            await self.add_feed(octobot_trading.enums.WebsocketFeeds.LEDGER)

            # ensure feeds are added
            self.create_feeds()
        else:
            self.logger.warning(
                f"{self.exchange_manager.exchange_name.title()}'s websocket has no symbol to feed"
            )

    async def add_feed(self, feed_name):
        if self.is_feed_available(feed_name):
            self.channels.append(feed_name)
            self.handled_feeds[feed_name] = True
            self.logger.debug(f"{self.exchange_manager.exchange_name}'s websocket is handling {feed_name.value}")
        else:
            self.handled_feeds[feed_name] = False
            self.logger.debug(f"{self.exchange_manager.exchange_name}'s websocket is not handling {feed_name.value}")

    def is_feed_available(self, feed):
        try:
            feed_available = self.websocket_connector.get_exchange_feed(feed)
            return feed_available is not octobot_trading.enums.WebsocketFeeds.UNSUPPORTED.value
        except (KeyError, ValueError):
            return False

    def is_feed_requiring_init(self, feed):
        return self.websocket_connector.is_feed_requiring_init(feed)

    @classmethod
    def get_name(cls):
        return cls.__name__

    @classmethod
    def has_name(cls, exchange_manager: object) -> bool:  # pylint: disable=arguments-renamed
        return cls.get_exchange_connector_class(exchange_manager) is not None

    def is_time_frame_related_feed(self, feed):
        return self.websocket_connectors[0].is_time_frame_related_feed(feed)

    def is_time_frame_supported(self, time_frame):
        return all([
            connector.is_time_frame_supported(time_frame)
            for connector in self.websocket_connectors
        ])

    async def start_sockets(self):
        if any(self.handled_feeds.values() and self.websocket_connectors):
            try:
                self.websocket_connectors_executors = futures.ThreadPoolExecutor(
                    max_workers=len(self.websocket_connectors),
                    thread_name_prefix=f"{self.get_name()}-{self.exchange_name}-pool-executor",

                )

                self.websocket_connectors_tasks = [
                    asyncio.get_event_loop().run_in_executor(self.websocket_connectors_executors, websocket.start)
                    for websocket in self.websocket_connectors
                ]

                self.is_websocket_running = True
            except ValueError as e:
                self.logger.error(
                    f"Failed to start websocket on {self.exchange_name} : {html_util.get_html_summary_if_relevant(e)}"
                )

        if self.websocket_connectors and not self.is_websocket_running:
            self.logger.debug(f"{self.exchange_manager.exchange_name.title()}'s "
                              f"websocket is not handling anything, it will not be started.")

    async def wait_sockets(self):
        await asyncio.wait(self.websocket_connectors_tasks)

    def _supports_live_pair_addition(self):
        for websocket in self.websocket_connectors:
            if not websocket.SUPPORTS_LIVE_PAIR_ADDITION:
                return False
        return True

    async def updated_followed_pairs(self):
        for websocket in self.websocket_connectors:
            websocket.update_followed_pairs()

    async def _inner_close_and_restart_sockets(self, debounce_duration):
        # asyncio.sleep to make it easily cancellable to reschedule later calls
        await asyncio.sleep(debounce_duration)
        for websocket in self.websocket_connectors:
            await websocket.reset()

    async def handle_updated_pairs(self, debounce_duration=0):
        if self._supports_live_pair_addition():
            await self.updated_followed_pairs()
        else:
            await self._close_and_restart_sockets(debounce_duration=debounce_duration)

    async def _close_and_restart_sockets(self, debounce_duration=0):
        if self.restart_task is not None and not self.restart_task.done():
            self.restart_task.cancel()
        self.restart_task = asyncio.create_task(self._inner_close_and_restart_sockets(debounce_duration))

    async def stop_sockets(self):
        """
        Stops the websocket. Can be restarted
        """
        try:
            for websocket in self.websocket_connectors:
                await websocket.stop()
        except Exception as e:
            self.logger.error(f"Error when stopping sockets : {html_util.get_html_summary_if_relevant(e)}")

    async def close_sockets(self):
        """
        Closes the websocket. Can't be restarted
        """
        try:
            for websocket in self.websocket_connectors:
                await websocket.close()
        except Exception as e:
            self.logger.error(f"Error when closing sockets : {html_util.get_html_summary_if_relevant(e)}")
        for websocket_task in self.websocket_connectors_tasks:
            websocket_task.cancel()
        if sys.version_info.minor >= 9:
            self.websocket_connectors_executors.shutdown(True)
        else:
            thread_util.stop_thread_pool_executor_non_gracefully(self.websocket_connectors_executors)
        self.websocket_connectors_executors = None

    def add_pairs(self, pairs, watching_only=False):
        for websocket in self.websocket_connectors:
            websocket.add_pairs(pairs, watching_only=watching_only)

    def remove_pairs(self, pairs, watching_only=False):
        for websocket in self.websocket_connectors:
            websocket.remove_pairs(pairs, watching_only=watching_only)

    def _has_too_many_feeds_to_handle(self) -> bool:
        if self.get_connector_max_handled_feeds() == octobot_trading.constants.NO_DATA_LIMIT:
            return False
        return self.get_connector_feeds_count() >= self.get_connector_max_handled_feeds()

    def get_connector_feeds_count(self):
        return self.websocket_connector.get_feeds_count(self.pairs, self.time_frames)

    def get_connector_max_handled_feeds(self):
        return self.websocket_connector.MAX_HANDLED_FEEDS

    def clear(self):
        super(WebSocketExchange, self).clear()
        for connector in self.websocket_connectors:
            connector.clear()
