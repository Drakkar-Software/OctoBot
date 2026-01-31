# pylint: disable=W0101
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
import copy
import decimal
import time
import typing

import ccxt
import ccxt.pro as ccxtpro

import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.time_frame_manager as time_frame_manager

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.abstract_websocket_exchange as abstract_websocket_exchange
import octobot_trading.exchanges.connectors.ccxt.ccxt_client_util as ccxt_client_util
import octobot_trading.exchanges.connectors.ccxt.ccxt_adapter as ccxt_adapter
from octobot_trading.enums import (
    ExchangeConstantsOrderBookInfoColumns as ECOBIC,
    ExchangeConstantsTickersColumns as Ectc,
)
from octobot_trading.enums import WebsocketFeeds as Feeds


class CCXTWebsocketConnector(abstract_websocket_exchange.AbstractWebsocketExchange):
    INIT_REQUIRING_EXCHANGE_FEEDS = [Feeds.CANDLE]
    SUPPORTS_LIVE_PAIR_ADDITION = True
    FEED_INITIALIZATION_TIMEOUT = 15 * commons_constants.MINUTE_TO_SECONDS
    MIN_CONNECTION_CLOSE_INTERVAL = 2 * commons_constants.MINUTE_TO_SECONDS
    NO_MESSAGE_DISCONNECTED_TIMEOUT = 4 * commons_constants.MINUTE_TO_SECONDS
    RECREATE_CLIENT_ON_DISCONNECT = (
        False  # when True, a new ccxt websocket client will replace the previous
    )
    # one when the exchange is disconnected
    USE_REST_CONNECTOR_ADDITIONAL_CONFIG = False # if True, the additional config from the associated rest connector will be used
    FIX_CANDLES_TIMEZONE_IF_NEEDED: bool = False  # if True, the candles timestamps will be fixed to the UTC timezone, used when WS is returning candle timestamps in a non UTC timezone

    IGNORED_FEED_PAIRS = {
        # When ticker or future index is available : no need to calculate mark price from recent trades
        Feeds.TRADES: [Feeds.TICKER, Feeds.FUTURES_INDEX],
        # When candles are available : use min timeframe kline to push ticker
        Feeds.TICKER: [Feeds.KLINE],
        # When funding can be found in websocket ticker
        # Feeds.FUNDING: [Feeds.TICKER],
    }

    PAIR_INDEPENDENT_CHANNELS = [
        Feeds.PORTFOLIO,
        Feeds.ORDERS,
        Feeds.CREATE_ORDER,
        Feeds.CANCEL_ORDER,
        Feeds.TRADE,
        Feeds.LEDGER,
        Feeds.PORTFOLIO,
    ]
    WATCHED_PAIR_CHANNELS = [
        Feeds.TRADES,
        Feeds.TICKER,
        Feeds.CANDLE,
    ]
    CURRENT_TIME_FILTERED_CHANNELS = [
        Feeds.TRADES,
        Feeds.ORDERS,
        Feeds.TRADE,
    ]
    CANDLE_TIME_FILTERED_CHANNELS = [
        Feeds.CANDLE,
        Feeds.KLINE,
    ]
    # https://docs.ccxt.com/en/latest/ccxt.pro.manual.html?rtd_search=fetchLedger#real-time-vs-throttling
    # THROTTLED_CHANNELS are updated at each self.throttled_ws_updates.
    # Used as real time channels when self.throttled_ws_updates is 0
    # self.throttled_ws_updates is using trading_constants.THROTTLED_WS_UPDATES by default
    THROTTLED_CHANNELS = [
        Feeds.TICKER,
        Feeds.TRADES,
        Feeds.L1_BOOK,
        Feeds.L2_BOOK,
        Feeds.L3_BOOK,
    ]
    AUTHENTICATED_CHANNELS = [
        trading_enums.WebsocketFeeds.ORDERS,
        trading_enums.WebsocketFeeds.PORTFOLIO,
        trading_enums.WebsocketFeeds.TRADE,
        trading_enums.WebsocketFeeds.POSITION,
    ]
    EXCHANGE_CONSTRUCTOR_KWARGS = {}
    SHORT_RECONNECT_DELAY = 0.5
    LONG_RECONNECT_DELAY = 5

    def __init__(
        self,
        config,
        exchange_manager,
        adapter_class=None,
        additional_config=None,
        websocket_name=None,
    ):
        super().__init__(config, exchange_manager)
        self.filtered_pairs: list[str] = []
        self.watched_pairs: list[str] = []
        self.min_timeframe: typing.Optional[commons_enums.TimeFrames] = None
        self._previous_open_candles: dict[str, dict[str, dict]] = {}
        self._subsequent_unordered_candles_count: dict[
            str, dict[str, tuple[int, float]]
        ] = {}  # dict values: tuple(candle_count, candle_time)
        self._errors_count: dict[str, dict[str, int]] = {}
        self._start_time_millis: typing.Optional[int] = (
            None  # used for the "since" param in CURRENT/CANDLE_TIME_FILTERED_CHANNELS
        )
        self.websocket_name: str = websocket_name or self.get_name()

        self.local_loop: typing.Optional[asyncio.AbstractEventLoop] = None

        self.should_stop: bool = False
        self.is_authenticated: bool = False
        self.adapter: ccxt_adapter.CCXTAdapter = self.get_adapter_class(adapter_class)(
            self
        )
        self.additional_config: typing.Optional[dict[str, typing.Any]] = (
            additional_config
        )
        if self.USE_REST_CONNECTOR_ADDITIONAL_CONFIG:
            self.additional_config = {
                **(self.additional_config or {}),
                **self.exchange_manager.exchange.get_extended_additional_connector_config()
            }
        self.headers: dict[str, str] = {}
        self.options: dict[str, typing.Any] = {
            "newUpdates": True,  # only get new updates from trades and ohlcv (don't return the full cached history)
            "OHLCVLimit": trading_constants.CCXT_OHLCV_CACHE_LIMIT,
            "tradesLimit": trading_constants.CCXT_TRADES_CACHE_LIMIT,
            "ordersLimit": trading_constants.CCXT_ORDERS_CACHE_LIMIT,
            "watchOrderBookLimit": trading_constants.CCXT_WATCH_ORDER_BOOK_LIMIT,
        }
        # add default options
        self.add_options(
            ccxt_client_util.get_ccxt_client_login_options(self.exchange_manager)
        )
        self.client: ccxt.Exchange = None  # type: ignore # ccxt.pro exchange: a ccxt.async_support exchange with websocket capabilities
        self.feed_tasks: dict[str, asyncio.Task] = {}
        self._last_close_time: float = 0
        self._last_message_time: float = 0
        self.throttled_ws_updates: float = trading_constants.THROTTLED_WS_UPDATES

        self.candle_delay_seconds: float = 0

        self._create_client()

    """
    Methods
    """

    def get_feed_name(self):
        return self.websocket_name

    def start(self):
        asyncio.run(self._inner_start())

    async def _inner_start(self):
        self._start_time_millis = self.client.milliseconds()
        self.stopped_event = asyncio.Event()
        self.local_loop = asyncio.get_event_loop()
        await self._init_client()
        # keep loop open till stop is called
        await self.stopped_event.wait()

    def get_adapter_class(self, adapter_class):
        return adapter_class or ccxt_adapter.CCXTAdapter

    def add_headers(self, headers_dict):
        """
        Add new headers to ccxt client
        :param headers_dict: the additional header keys and values as dict
        """
        self.headers.update(headers_dict)
        if self.client is not None:
            ccxt_client_util.add_headers(self.client, headers_dict)

    def add_options(self, options_dict):
        """
        Add new options to ccxt client
        :param options_dict: the additional option keys and values as dict
        """
        self.options.update(options_dict)
        if self.client is not None:
            ccxt_client_util.add_options(self.client, options_dict)

    async def _inner_stop(self):
        self.should_stop = True
        try:
            if self.client is not None:
                await self.client.close()
            self.stopped_event.set()
        except Exception as e:
            self.logger.exception(e, False)
            self.logger.error(f"Failed to stop websocket feed : {e}")

    async def stop(self):
        """
        Reimplementation of self.client.stop() without calling loop.run_until_complete()
        """
        if asyncio.get_event_loop() is self.local_loop:
            await self._inner_stop()
        else:
            asyncio_tools.run_coroutine_in_asyncio_loop(
                self._inner_stop(), self.local_loop
            )

    async def close(self):
        """
        Can't call self.client.close() because it uses loop operations
        """

    def add_pairs(self, pairs, watching_only=False):
        """
        Add new pairs to self.filtered_pairs
        :param pairs: the list of pair to add
        :param watching_only: if pairs are for watching or trading purpose
        """
        for pair in pairs:
            self._add_pair(pair, watching_only=watching_only)

    def remove_pairs(self, pairs, watching_only=False):
        """
        Remove pairs from self.filtered_pairs
        :param pairs: the list of pair to remove
        :param watching_only: if pairs are for watching or trading purpose
        """
        for pair in pairs:
            self._remove_pair(pair, watching_only=watching_only)

    async def _inner_update_followed_pairs(self):
        if self.initialized_event is None:
            # should never happen
            return
        if not self.initialized_event.is_set():
            await self.initialized_event.wait()
        self._filter_exchange_symbols()
        self._subscribe_channels_feeds(True)

    def update_followed_pairs(self):
        asyncio_tools.run_coroutine_in_asyncio_loop(
            self._inner_update_followed_pairs(), self.local_loop
        )

    @classmethod
    def is_supporting_exchange(cls, exchange_candidate_name) -> bool:
        return cls.get_name() == exchange_candidate_name

    def is_time_frame_supported(self, time_frame):
        return time_frame.value in ccxt_client_util.get_time_frames(self.client)

    def get_pair_from_exchange(self, pair):
        """
        Convert a ccxt symbol format to uniformized symbol format
        :param pair: the pair to format
        :return: the formatted pair when success else an empty string
        """
        # octobot uses the ccxt format for pairs
        return pair

    def get_exchange_pair(self, pair) -> str:
        """
        Convert an uniformized symbol format to a ccxt symbol format
        :param pair: the pair to format
        :return: the ccxt pair when success else an empty string
        """
        # octobot uses the ccxt format for pairs
        return pair

    """
    Private methods
    """

    def _create_client(self):
        """
        Creates ccxt client instance
        """
        client_class = getattr(ccxtpro, self.get_feed_name())
        self.client, self.is_authenticated = ccxt_client_util.create_client(
            client_class,
            self.exchange_manager,
            self.logger,
            self.options,
            self.headers,
            self.additional_config,
            self._should_authenticate(),
            keys_adapter=self._get_keys_adapter(),
            # Always disable request counter: ws exchange will be started in a different async loop,
            # which is not yet supported
            allow_request_counter=False,
        )
        if self.exchange_manager.exchange.is_supporting_sandbox():
            ccxt_client_util.set_sandbox_mode(self, self.exchange_manager.is_sandboxed)
    
    def _get_keys_adapter(self):
        return None

    def _should_authenticate(self):
        if self.exchange_manager.exchange.requires_authentication(
            self.exchange_manager.exchange.tentacle_config, None, None
        ):
            return True
        return self._has_authenticated_channel() and super()._should_authenticate()

    def _has_authenticated_channel(self) -> bool:
        for feed in self.AUTHENTICATED_CHANNELS:
            if feed in self.EXCHANGE_FEEDS:
                return True
        return False

    def _is_authenticated_feed(self, feed):
        return feed in self.AUTHENTICATED_CHANNELS

    async def _init_client(self):
        """
        Prepares client configuration and instantiates client feeds
        """
        try:
            self.initialized_event = asyncio.Event()
            self.logger.info(
                f"Loading {self.exchange_manager.exchange_name} websocket exchange markets"
            )
            await self.client.load_markets()
            self._filter_exchange_pairs_and_timeframes()
            self._subscribe_feeds()
        except Exception as e:
            self.logger.exception(
                e, True, f"Failed to subscribe when creating websocket feed : {e}"
            )
        finally:
            self.initialized_event.set()

    async def _close_exchange_to_force_reconnect(self):
        if (
            time.time() - self._last_close_time > self.MIN_CONNECTION_CLOSE_INTERVAL
            and not self.should_stop
        ):
            # Close client to force connections re-open. The next watch_xyz will recreate the connection
            self._last_close_time = time.time()
            self.logger.debug(f"Closing exchange connection.")
            await self.client.close()
            if self.RECREATE_CLIENT_ON_DISCONNECT:
                self._create_client()
            self.logger.debug(
                "Exchange connection closed. The next watch-xyz will re-open it."
            )
            return True
        return False

    def _subscribe_feeds(self):
        """
        Prepares the subscription of unauthenticated and authenticated feeds and subscribe all
        """
        if self._should_run_candle_feed():
            if self.min_timeframe is None:
                self.logger.error(
                    f"Missing min_timeframe in exchange websocket with candle feeds. This probably means that no "
                    f"required time frame is supported by this exchange's websocket "
                    f"(valid_candle_intervals: {ccxt_client_util.get_time_frames(self.client)})"
                )
            self._subscribe_candle_feed()

        # drop unsupported channels
        self.channels = [
            channel
            for channel in self.channels
            if self._is_supported_channel(channel)
            and channel != self.EXCHANGE_FEEDS.get(Feeds.CANDLE)
        ]

        self._subscribe_channels_feeds(False)

    def _should_use_authenticated_feeds(self):
        """
        :return: True when authenticated feeds shouldn't be added
        """
        return (
            self._should_authenticate()
            and self.exchange.authenticated()
            and not self.exchange_manager.is_sandboxed
        )

    def _is_supported_channel(self, channel):
        """
        Checks if the channel is supported
        :param channel: the channel name
        :return: True if the channel is not unsupported, not ignored
        and if it's an authenticated channel if the exchange is authenticated
        """
        if (
            self._is_authenticated_feed(channel)
            and not self._should_use_authenticated_feeds()
        ):
            return False
        return not (
            self.EXCHANGE_FEEDS.get(channel, Feeds.UNSUPPORTED.value)
            == Feeds.UNSUPPORTED.value
            or self.should_ignore_feed(channel)
        )

    @classmethod
    def get_exchange_feed(cls, feed) -> str:
        feed_value = cls.EXCHANGE_FEEDS.get(
            feed, trading_enums.WebsocketFeeds.UNSUPPORTED.value
        )
        if cls.is_feed_supported(feed_value):
            return feed.value
        return trading_enums.WebsocketFeeds.UNSUPPORTED.value

    def _subscribe_candle_feed(self):
        """
        Subscribes a new candle feed for each time frame
        """
        self._subscribe_additional_pairs_special_time_frames_candle_feed()
        for time_frame in self.time_frames:
            # regular time frames are subscribed for all pairs (both configured and additional)
            self._subscribe_feed(
                Feeds.CANDLE,
                symbols=self.filtered_pairs,
                time_frame=time_frame.value,
            )

    def _subscribe_additional_pairs_special_time_frames_candle_feed(self):
        """
        Additional pairs may require special time frames: support it for them
        """
        additionnal_pairs = [
            pair
            for pair in self.filtered_pairs
            if pair in self.exchange_manager.exchange_config.additional_traded_pairs
        ]
        for time_frame in self.exchange_manager.exchange_config.additional_time_frames:
            self._subscribe_feed(
                Feeds.CANDLE,
                symbols=additionnal_pairs,
                time_frame=time_frame.value,
            )

    def _subscribe_channels_feeds(self, pairs_related_channels_only):
        """
        Subscribes all time frame unrelated feeds
        """
        if not pairs_related_channels_only:
            self._subscribe_pair_independent_feed()
        self._subscribe_traded_pairs_feed()
        self._subscribe_watched_pairs_feed()

    def _subscribe_pair_independent_feed(self):
        """
        Subscribes all pair unrelated feeds
        """
        feeds = [
            channel
            for channel in self.channels
            if self._is_pair_independent_feed(channel)
        ]
        for feed in feeds:
            self._subscribe_feed(
                feed,
            )

    def _subscribe_traded_pairs_feed(self):
        """
        Subscribes all time frame unrelated feeds for traded pairs
        """
        if not self.filtered_pairs:
            return
        feeds = [
            channel
            for channel in self.channels
            if not self._is_pair_independent_feed(channel)
        ]
        for feed in feeds:
            self._subscribe_feed(
                feed,
                symbols=self.filtered_pairs,
            )

    def _subscribe_watched_pairs_feed(self):
        """
        Subscribes feeds for watched pairs (only on one timeframe for multiple timeframes feeds)
        """
        if not self.watched_pairs:
            return
        feeds = [
            channel
            for channel in self.WATCHED_PAIR_CHANNELS
            if self._is_supported_channel(channel)
            and (channel in self.channels or not self.channels)
        ]
        for feed in feeds:
            self._subscribe_feed(
                feed,
                symbols=self.watched_pairs,
            )

    def _get_feed_default_kwargs(self):
        return {}

    def _get_feed_generator_by_feed(self):
        return {
            # Subscribed feeds
            # Unauthenticated
            Feeds.TRADES: self._get_generator("watchTrades"),
            Feeds.TICKER: self._get_generator("watchTicker"),
            Feeds.CANDLE: self._get_generator("watchOHLCV"),
            Feeds.KLINE: self._get_generator("watchOHLCV"),
            Feeds.L1_BOOK: self._get_generator("watchOrderBook"),
            Feeds.L2_BOOK: self._get_generator("watchOrderBook"),
            Feeds.L3_BOOK: self._get_generator("watchOrderBook"),
            Feeds.MARKETS: self._get_generator("watchMarkets"),
            Feeds.FUNDING: Feeds.UNSUPPORTED,
            Feeds.LIQUIDATIONS: Feeds.UNSUPPORTED,
            Feeds.OPEN_INTEREST: Feeds.UNSUPPORTED,
            Feeds.FUTURES_INDEX: Feeds.UNSUPPORTED,
            # Authenticated
            Feeds.TRANSACTIONS: self._get_generator("watchTransactions"),
            Feeds.PORTFOLIO: self._get_generator("watchBalance"),
            Feeds.ORDERS: self._get_generator("watchOrders"),
            Feeds.TRADE: self._get_generator("watchMyTrades"),
            Feeds.LEDGER: self._get_generator("watchLedger"),
            Feeds.POSITION: Feeds.UNSUPPORTED,
            # Publish feeds
            Feeds.CREATE_ORDER: self._get_generator("watchCreateOrder"),
            Feeds.CANCEL_ORDER: self._get_generator("watchCancelOrder"),
        }

    def _get_generator(self, method_name):
        return (
            getattr(self.client, method_name)
            if hasattr(self.client, method_name)
            and self.client.has.get(method_name, False)
            else Feeds.UNSUPPORTED
        )

    def _get_callback_by_feed(self):
        return {
            # Unauthenticated
            Feeds.TRADES: self.recent_trades,
            Feeds.TICKER: self.ticker,
            Feeds.CANDLE: self.candle,
            Feeds.KLINE: self.candle,
            Feeds.FUNDING: self.funding,
            Feeds.OPEN_INTEREST: self.open_interest,
            Feeds.L1_BOOK: self.book,
            Feeds.L2_BOOK: self.book,
            Feeds.L3_BOOK: self.book,
            Feeds.MARKETS: self.markets,
            # Authenticated
            Feeds.TRANSACTIONS: self.transaction,
            Feeds.PORTFOLIO: self.balance,
            Feeds.ORDERS: self.orders,
            Feeds.TRADE: self.trades,
        }

    def _get_since_filter_value(self, feed, time_frame):
        if feed in self.CURRENT_TIME_FILTERED_CHANNELS:
            return self._start_time_millis
        elif feed in self.CANDLE_TIME_FILTERED_CHANNELS:
            candles_ms = (
                commons_enums.TimeFramesMinutes[commons_enums.TimeFrames(time_frame)]
                * commons_constants.MSECONDS_TO_MINUTE
            )
            time_delta = self._start_time_millis % candles_ms
            return self._start_time_millis - time_delta
        return None

    def _subscribe_feed(
        self, feed, symbols=None, time_frame=None, since=None, limit=None, params=None
    ):
        """
        Subscribe a new feed
        :param feed: the feed to subscribe to
        :param symbols: the feed symbols
        :param time_frame: the feed time_frame
        :param since: the ccxt feed since arg
        :param limit: the ccxt feed limit arg
        :param params: the ccxt feed param arg
        """
        try:
            feed_callback = self._get_callback_by_feed()[feed]
            feed_generator = self._get_feed_generator_by_feed()[feed]
            if Feeds.UNSUPPORTED in (feed_callback, feed_generator):
                raise KeyError
        except KeyError:
            self.logger.error(f"Impossible to subscribe to {feed}: feed not supported")
            return
        added_subscriptions = []
        has_added_feed = False
        if feed in self.TIME_FRAME_RELATED_FEEDS and time_frame is None:
            time_frame = self.min_timeframe.value
        kwargs = copy.copy(self._get_feed_default_kwargs())
        if time_frame is not None:
            kwargs["timeframe"] = time_frame
        if since is not None:
            kwargs["since"] = since
        else:
            auto_since = self._get_since_filter_value(feed, time_frame)
            if auto_since is not None:
                kwargs["since"] = auto_since
            elif feed in self.CURRENT_TIME_FILTERED_CHANNELS:
                kwargs["since"] = self._start_time_millis
            elif feed in self.CANDLE_TIME_FILTERED_CHANNELS:
                kwargs["since"] = self._start_time_millis
        if limit is not None:
            kwargs["limit"] = limit
        if params is not None:
            kwargs["params"] = params
        if symbols is not None:
            for symbol in symbols:
                kwargs["symbol"] = symbol
                # one task per symbol: ccxt_pro is not handling multi symbol generators
                if self._create_task_if_necessary(
                    feed, feed_callback, feed_generator, **kwargs
                ):
                    added_subscriptions.append(symbol)
                    has_added_feed = True
        else:
            # no symbol param
            if self._create_task_if_necessary(
                feed, feed_callback, feed_generator, **kwargs
            ):
                has_added_feed = True

        symbols_str = (
            f"for {', '.join(added_subscriptions)} " if added_subscriptions else ""
        )
        time_frame_str = f"on {time_frame}" if time_frame else ""
        if has_added_feed:
            self.logger.debug(
                f"Subscribed to {feed.value} {symbols_str}{time_frame_str}"
            )
        else:
            self.logger.debug(
                f"No new feed to subscribe to on {feed.value} (inputs: {symbols_str}{time_frame_str})"
            )

    async def _feed_task(self, feed, callback, watch_func, *g_args, **g_kwargs):
        if not await self._wait_for_initialization(feed, *g_args, **g_kwargs):
            self.logger.error(
                f"Aborting {feed.value} feed connection with {g_kwargs}: "
                f"missing required initialization data"
            )
            return
        enable_throttling = (
            feed in self.THROTTLED_CHANNELS and self.throttled_ws_updates != 0.0
        )
        ws_des = f"{watch_func.__name__} {g_kwargs}"
        subsequent_disconnections = 0
        already_got_feed_stopping_error = False
        already_got_closed_by_user_error = False
        spamming_logs_warning_interval = 5000
        spamming_logs_debug_interval = 1000
        while not self.should_stop:
            try:
                update_data = await watch_func(*g_args, **g_kwargs)

                self._last_message_time = time.time()
                if subsequent_disconnections > 0:
                    self.logger.debug(f"Reconnected to {ws_des}")
                subsequent_disconnections = 0
                already_got_closed_by_user_error = False
                if update_data:
                    # Use a copy of the update data as it will be edited by adapters.
                    # We should avoid editing the original object since it is also used in ccxt internally buffers
                    await callback(copy.deepcopy(update_data), **g_kwargs)
                if enable_throttling:
                    # ccxt keeps updating the internal structures while waiting
                    # https://docs.ccxt.com/en/latest/ccxt.pro.manual.html?rtd_search=fetchLedger#incremental-data-structures
                    await asyncio.sleep(self.throttled_ws_updates)
            except ccxt.NetworkError as err:
                # short reconnect on ping pong timeout or 1st reconnect
                is_ping_pong_error = isinstance(err, ccxt.RequestTimeout)
                if (
                    is_ping_pong_error
                    and time.time() - self._last_message_time
                    < self.NO_MESSAGE_DISCONNECTED_TIMEOUT
                ):
                    # last message not received long ago: the websocket is probably not disconnected, it's just a
                    # pong timeout, which can happen: there is no issue, instantly reconnect feed
                    self.logger.debug(
                        f"Instantly reconnecting {ws_des} feed after ping-pong timeout."
                    )
                    continue
                reconnect_delay = (
                    self.SHORT_RECONNECT_DELAY
                    if (subsequent_disconnections == 0 or is_ping_pong_error)
                    else self.LONG_RECONNECT_DELAY
                )
                self.logger.debug(
                    f"Can't connect to exchange {ws_des} websocket: {err}. "
                    f"Retrying in {reconnect_delay} seconds"
                )
                if await self._close_exchange_to_force_reconnect():
                    message = (
                        f"Closed exchange connection to force reconnect. Error: {err}"
                    )
                    if (
                        subsequent_disconnections > 1
                        and subsequent_disconnections % 5 == 0
                    ):
                        self.logger.error(
                            f"Multiple disconnections in a row [{subsequent_disconnections}] for {ws_des}. {message}"
                        )
                    else:
                        self.logger.debug(message)
                await asyncio.sleep(reconnect_delay)
                self.logger.debug(f"Reconnecting to {ws_des}")
                # self.client might have changed
                watch_func = self._get_feed_generator_by_feed()[feed]
                subsequent_disconnections += (
                    1  # wait for a longer time before the next reconnect
                )
            except ccxt.BadRequest as err:
                message = f"Impossible to start {ws_des} feed due to exchange refusing the connection request: {err}."
                self.logger.exception(
                    err,
                    True,
                    f"{message} {'Will retry once' if not already_got_feed_stopping_error else 'Now stopping'}.",
                )
                if already_got_feed_stopping_error:
                    # there is a real issue when connecting to the feed. Don't loop
                    return
                already_got_feed_stopping_error = True
                await asyncio.sleep(self.LONG_RECONNECT_DELAY)  # avoid spamming
                # self.client might have changed
                watch_func = self._get_feed_generator_by_feed()[feed]
            except ccxt.NotSupported as err:
                self.logger.exception(
                    err,
                    True,
                    f"Impossible to start {ws_des} feed: {err}. "
                    f"Stopping it. Please report to the OctoBot team if you see this error",
                )
                return
            except Exception as err:
                count_error = True
                if isinstance(err, ccxt.ExchangeClosedByUser):
                    if self.should_stop:
                        # normal when stopping websocket
                        self.logger.debug(
                            f"Disconnected {ws_des}: connection closed as {self.get_name()} is stopping ({err})"
                        )
                        return
                    # happening when auto-stopping websocket (calling self._close_exchange_to_force_reconnect)
                    # from another task: current task also raised ccxt.ExchangeClosedByUser
                    # this is normal as long as it happens only once after a reconnection
                    if not already_got_closed_by_user_error:
                        count_error = False
                        self.logger.debug(
                            f"{ws_des} connection automatically closed, reconnecting in {self.LONG_RECONNECT_DELAY}"
                            f" seconds ({err})"
                        )
                        already_got_closed_by_user_error = True
                if count_error:
                    error_count = self._increment_error_counter(
                        g_kwargs.get("time_frame"), err
                    )
                    error_message = (
                        f"Unexpected error when handling {ws_des} feed: {err} "
                        f"({err.__class__.__name__}) ({error_count} times)"
                    )
                    if error_count == 1:
                        self.logger.exception(err, True, error_message)
                    elif error_count % spamming_logs_warning_interval == 0:
                        self.logger.warning(error_message)
                    elif error_count % spamming_logs_debug_interval == 0:
                        self.logger.debug(error_message)
                await asyncio.sleep(self.LONG_RECONNECT_DELAY)  # avoid spamming
                subsequent_disconnections += (
                    1  # wait for a longer time before the next reconnect
                )
                # self.client might have changed
                watch_func = self._get_feed_generator_by_feed()[feed]

    def _create_task_if_necessary(self, feed, feed_callback, feed_generator, **kwargs):
        identifier = self._get_feed_identifier(feed_generator, kwargs)
        if identifier not in self.feed_tasks:
            self.logger.info(
                f"Subscribing to {feed.value} with {kwargs} ({len(self.feed_tasks)} total feeds)"
            )
            self.feed_tasks[identifier] = asyncio.create_task(
                self._feed_task(feed, feed_callback, feed_generator, **kwargs)
            )
            return True
        return False

    async def _wait_for_initialization(self, feed, *g_args, **g_kwargs):
        if (
            not self.is_feed_requiring_init(feed)
            or g_kwargs["symbol"] not in self.filtered_pairs
        ):
            # no need to wait for pairs not in self.filtered_pairs
            return True
        is_initialized_func = None
        if feed is Feeds.CANDLE:

            def candle_is_initialized_func():
                if self.exchange_manager is None:
                    # Should only happen in tests / unusual environments. Or there is a real issue.
                    self.logger.error(
                        f"No exchange manager when starting websocket connector."
                    )
                    return False
                try:
                    return (
                        self.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
                            g_kwargs["symbol"], allow_creation=False
                        )
                        .symbol_candles[commons_enums.TimeFrames(g_kwargs["timeframe"])]
                        .candles_initialized
                    )
                except KeyError:
                    return False

            is_initialized_func = candle_is_initialized_func
        if is_initialized_func is None:
            return True
        if is_initialized_func():
            return True
        self.logger.debug(
            f"Waiting for initialization before starting {feed.value} feed with {g_kwargs}"
        )
        t0 = time.time()
        while (
            not self.should_stop and time.time() - t0 < self.FEED_INITIALIZATION_TIMEOUT
        ):
            # add timeout
            if is_initialized_func():
                self.logger.debug(
                    f"Starting {feed.value} feed with {g_kwargs}: initialization complete"
                )
                return True
            # quickly update at first
            await asyncio.sleep(
                0.1 if time.time() - t0 < self.FEED_INITIALIZATION_TIMEOUT / 10 else 1
            )
        return is_initialized_func()

    def _get_feed_identifier(self, feed_generator, kwargs):
        # since is not part of the identifier as it depends on the start time
        kwargs_str = ", ".join([f"{k}: {v}" for k, v in kwargs.items() if k != "since"])
        return f"{feed_generator.__name__}{kwargs_str}"

    def _filter_exchange_pairs_and_timeframes(self):
        """
        Populates self.filtered_pairs and self.min_timeframe
        """
        self._add_exchange_symbols()
        self._init_exchange_time_frames()

    def _add_pair(self, pair, watching_only):
        """
        Add a pair to self.filtered_pairs if supported
        :param pair: the pair to add
        :param watching_only: when True add pair to watched_pairs else to filtered_pairs
        """
        if watching_only:
            if pair not in self.watched_pairs:
                self.watched_pairs.append(pair)
        else:
            if pair not in self.filtered_pairs:
                self.filtered_pairs.append(pair)

    def _remove_pair(self, pair, watching_only):
        """
        Remove a pair from self.filtered_pairs if supported
        :param pair: the pair to remove
        :param watching_only: when True remove pair from watched_pairs else from filtered_pairs
        """
        if watching_only:
            if pair in self.watched_pairs:
                self.watched_pairs.remove(pair)
        else:
            if pair in self.filtered_pairs:
                self.filtered_pairs.remove(pair)

    def _add_exchange_symbols(self):
        """
        Populates self.filtered_pairs from self.pairs when pair is supported by the ccxt exchange
        """
        for pair in self.pairs:
            self._add_pair(pair, watching_only=False)
        self._filter_exchange_symbols()

    def _filter_exchange_symbols(self):
        pre_filter_watched_pairs = copy.copy(self.watched_pairs)
        self.watched_pairs = [
            pair for pair in pre_filter_watched_pairs if self._is_supported_pair(pair)
        ]
        pre_filter_filtered_pairs = copy.copy(self.filtered_pairs)
        self.filtered_pairs = [
            pair for pair in pre_filter_filtered_pairs if self._is_supported_pair(pair)
        ]
        unsupported_pairs = []
        for pairs, pre_filter_pairs in (
            (self.watched_pairs, pre_filter_watched_pairs),
            (self.filtered_pairs, pre_filter_filtered_pairs),
        ):
            if len(pre_filter_filtered_pairs) > len(pairs):
                unsupported_pairs += [
                    pair for pair in pre_filter_pairs if pair not in pairs
                ]
        if unsupported_pairs:
            self.logger.error(
                f"{unsupported_pairs} pair is not supported by this exchange's websocket"
            )

    def _add_time_frame(self, filtered_timeframes, time_frame, log_on_error):
        """
        Add a time frame to filtered_timeframes if supported
        :param time_frame: the time frame to add
        """
        if self.is_time_frame_supported(time_frame):
            filtered_timeframes.append(time_frame)
        elif log_on_error:
            self.logger.error(
                f"{time_frame.value} time frame is not supported by this exchange's websocket"
            )

    def _init_exchange_time_frames(self):
        """
        Populates self.min_timeframe from self.time_frames when time frame is supported by the ccxt exchange
        Leaves self.min_timeframe at None if no timeframe is available on this exchange ws
        """
        # Log error only if necessary (self.min_timeframe is used by candle feed only)
        log_on_error = self._should_run_candle_feed()
        filtered_timeframes = []
        for time_frame in self.time_frames:
            self._add_time_frame(filtered_timeframes, time_frame, log_on_error)
        if filtered_timeframes:
            self.min_timeframe = time_frame_manager.find_min_time_frame(
                filtered_timeframes
            )

    def _should_run_candle_feed(self):
        return (
            self.EXCHANGE_FEEDS.get(Feeds.CANDLE, Feeds.UNSUPPORTED.value)
            != Feeds.UNSUPPORTED.value
        )

    def _is_supported_pair(self, pair):
        return pair in ccxt_client_util.get_symbols(self.client, True)

    def _is_pair_independent_feed(self, feed):
        return feed in self.PAIR_INDEPENDENT_CHANNELS

    @classmethod
    def get_feeds_count(cls, pairs, time_frames) -> int:
        total_count = 0
        if pairs:
            # rounding: account for 1 feed per symbol
            total_count = len(pairs)
            if cls.get_exchange_feed(trading_enums.WebsocketFeeds.CANDLE):
                # rounding: account for 1 per timeframe per symbol
                total_count += len(pairs) * len(time_frames)
        return total_count

    def _convert_book_prices_to_orders(self, book_prices_and_volumes, book_side):
        """
        Convert a book_prices format : {PRICE_1: SIZE_1, PRICE_2: SIZE_2...}
        to OctoBot's order book format
        :param book_prices: an order book dictionary (order_book.SortedDict)
        :param book_side: a TradeOrderSide value
        :return: the list of order book data converted
        """
        return [
            {
                ECOBIC.PRICE.value: float(book_price_and_volume[0]),
                ECOBIC.SIZE.value: float(book_price_and_volume[1]),
                ECOBIC.SIDE.value: book_side,
            }
            for book_price_and_volume in book_prices_and_volumes
        ]

    """
    Callbacks
    """

    async def ticker(self, ticker: dict, symbol=None, **kwargs):
        """
        :param ticker: the ccxt ticker dict
        :param symbol: the feed symbol
        :param kwargs: the feed kwargs
        """
        adapted = self.adapter.adapt_ticker(ticker)
        await self.push_to_channel(
            trading_constants.TICKER_CHANNEL,
            symbol,
            adapted,
        )

    async def recent_trades(self, trades: list, symbol=None, **kwargs):
        """
        :param trades: the ccxt ticker list
        :param symbol: the feed symbol
        :param kwargs: the feed kwargs
        """
        adapted = self.adapter.adapt_public_recent_trades(trades)
        await self.push_to_channel(
            trading_constants.RECENT_TRADES_CHANNEL, symbol, adapted
        )

    async def book(self, order_book: dict, symbol=None, **kwargs):
        """
        :param order_book: the ccxt order_book dict
        :param symbol: the feed symbol
        :param kwargs: the feed kwargs
        """
        book_instance = self.get_book_instance(symbol)

        book_instance.handle_book_adds(
            self._convert_book_prices_to_orders(
                order_book[ECOBIC.ASKS.value], trading_enums.TradeOrderSide.SELL.value
            )
            + self._convert_book_prices_to_orders(
                order_book[ECOBIC.BIDS.value], trading_enums.TradeOrderSide.BUY.value
            )
        )

        await self.push_to_channel(
            trading_constants.ORDER_BOOK_CHANNEL,
            symbol,
            book_instance.asks,
            book_instance.bids,
            update_order_book=False,
        )

    async def markets(self, markets: list, symbol=None, **kwargs):
        """
        :param market: the ccxt market dict
        :param symbol: the feed symbol
        :param kwargs: the feed kwargs
        """
        raise NotImplementedError("markets callback is not implemented")

    async def candle(self, candles: list, symbol=None, timeframe=None, **kwargs):
        """
        :param candles: the ccxt ohlcv list
        :param symbol: the feed symbol
        :param timeframe: the feed timeframe
        :param kwargs: the feed kwargs
        """
        time_frame = commons_enums.TimeFrames(timeframe)
        if self.FIX_CANDLES_TIMEZONE_IF_NEEDED:
            try:
                candles = self._fix_candles_timestamps(candles, time_frame)
            except ValueError as err:
                self.logger.info(f"Skipped websocket candle({symbol} {timeframe}): {err}")
                return
        kline = self.adapter.adapt_kline([copy.deepcopy(candles[-1])])[0]
        adapted = self.adapter.adapt_ohlcv(candles, time_frame=time_frame)
        last_candle = adapted[-1]
        if symbol not in self.watched_pairs:
            for candle in adapted:
                previous_candle = self._get_previous_open_candle(timeframe, symbol)
                is_previous_candle_closed = False
                if previous_candle is not None:
                    current_candle_time = candle[
                        commons_enums.PriceIndexes.IND_PRICE_TIME.value
                    ]
                    previous_candle_time = previous_candle[
                        commons_enums.PriceIndexes.IND_PRICE_TIME.value
                    ]
                    if previous_candle_time < current_candle_time:
                        # new candle is after the previous one: the previous one is now closed
                        is_previous_candle_closed = True
                    elif previous_candle_time > current_candle_time:
                        # should not happen: exchange feed is providing past candles after newer ones
                        # candle feed should be marked as unsupported in this exchange (at least for now)

                        # update internal candle store to still keep track of the most up to date candle
                        await self.exchange_manager.get_symbol_data(
                            symbol
                        ).handle_candles_update(
                            time_frame,
                            candle,
                            replace_all=False,
                            partial=False,
                            upsert=True,
                        )
                        is_new_unordered_candle = (
                            self._register_subsequent_unordered_candle(
                                timeframe, symbol, time_frame, current_candle_time
                            )
                        )
                        subsequent_unordered_candles = (
                            self._get_subsequent_unordered_candles_count(
                                timeframe, symbol
                            )
                        )
                        error_message = (
                            f"Ignored unexpected candle for {symbol} on {timeframe}: "
                            f"candle time {current_candle_time}, "
                            f"previous candle time: {previous_candle_time} "
                            f"({subsequent_unordered_candles} unordered candles in a row)."
                        )
                        if is_new_unordered_candle:
                            self.logger.warning(error_message)
                        # prevent spamming
                        elif subsequent_unordered_candles < 3 or (
                            subsequent_unordered_candles % 1000 == 0
                        ):
                            self.logger.debug(error_message)
                        if candle is last_candle:
                            # last candle in loop: don't go any further
                            return
                        else:
                            # go to next candle in loop
                            continue
                if is_previous_candle_closed:
                    # OHLCV_CHANNEL only takes closed candles
                    await self.push_to_channel(
                        trading_constants.OHLCV_CHANNEL,
                        time_frame,
                        symbol,
                        previous_candle,
                    )
                self._register_previous_open_candle(timeframe, symbol, candle)
            await self.push_to_channel(
                trading_constants.KLINE_CHANNEL, time_frame, symbol, kline
            )

        # Push a new ticker if necessary : only push on the min timeframe
        if time_frame is self.min_timeframe:
            ticker = {
                Ectc.HIGH.value: kline[commons_enums.PriceIndexes.IND_PRICE_HIGH.value],
                Ectc.LOW.value: kline[commons_enums.PriceIndexes.IND_PRICE_LOW.value],
                Ectc.BID.value: None,
                Ectc.BID_VOLUME.value: None,
                Ectc.ASK.value: None,
                Ectc.ASK_VOLUME.value: None,
                Ectc.OPEN.value: kline[commons_enums.PriceIndexes.IND_PRICE_OPEN.value],
                Ectc.CLOSE.value: kline[
                    commons_enums.PriceIndexes.IND_PRICE_CLOSE.value
                ],
                Ectc.LAST.value: kline[
                    commons_enums.PriceIndexes.IND_PRICE_CLOSE.value
                ],
                Ectc.PREVIOUS_CLOSE.value: None,
                # do not include volume as this is not the ticker volume but the current candle volume
                Ectc.BASE_VOLUME.value: None,
                Ectc.TIMESTAMP.value: self.exchange.get_exchange_current_time(),
            }
            await self.push_to_channel(trading_constants.TICKER_CHANNEL, symbol, ticker)

    async def funding(self, funding: dict, symbol=None, **kwargs):
        """
        Unsupported, feed list https://docs.ccxt.com/en/latest/ccxt.pro.manual.html?rtd_search=fetchLedger#prerequisites
        :param funding: the ccxt funding dict
        :param symbol: the feed symbol
        :param kwargs: the feed kwargs
        """
        # TODO update this when supported
        raise NotImplementedError("funding callback is not implemented")
        adapted = self.adapter.parse_funding_rate(funding)
        predicted_funding_rate = adapted.get(
            trading_enums.ExchangeConstantsFundingColumns.PREDICTED_FUNDING_RATE.value,
            trading_constants.NaN,
        )
        await self.push_to_channel(
            trading_constants.FUNDING_CHANNEL,
            symbol,
            decimal.Decimal(
                adapted[
                    trading_enums.ExchangeConstantsFundingColumns.FUNDING_RATE.value
                ]
            ),
            predicted_funding_rate=decimal.Decimal(
                str(predicted_funding_rate or trading_constants.NaN)
            ),
            next_funding_time=adapted[
                trading_enums.ExchangeConstantsFundingColumns.NEXT_FUNDING_TIME.value
            ],
            last_funding_time=adapted[
                trading_enums.ExchangeConstantsFundingColumns.LAST_FUNDING_TIME.value
            ],
        )

    async def open_interest(self, open_interest: dict, symbol=None, **kwargs):
        """
        Unsupported, feed list https://docs.ccxt.com/en/latest/ccxt.pro.manual.html?rtd_search=fetchLedger#prerequisites
        :param open_interest: the ccxt open_interest dict
        :param symbol: the feed symbol
        :param kwargs: the feed kwargs
        """
        # TODO update this when supported
        raise NotImplementedError("open_interest callback is not implemented")

    async def index(self, index: dict, symbol=None, **kwargs):
        """
        Unsupported, feed list https://docs.ccxt.com/en/latest/ccxt.pro.manual.html?rtd_search=fetchLedger#prerequisites
        :param index: the ccxt index dict
        :param symbol: the feed symbol
        :param kwargs: the feed kwargs
        """
        # TODO update this when supported
        raise NotImplementedError("index callback is not implemented")

    async def orders(self, orders: list, **kwargs):
        """
        :param orders: the ccxt orders list
        :param kwargs: the feed kwargs
        """
        # TODO update this when supported (ccxt is supporting it)
        raise NotImplementedError("orders callback is not implemented")
        symbol = None  # todo
        adapted = self.adapter.adapt_orders(orders, symbol=symbol)
        await self.push_to_channel(trading_constants.ORDERS_CHANNEL, adapted)

    async def trades(self, trades: list, **kwargs):
        """
        :param trades: the ccxt trades list
        :param kwargs: the feed kwargs
        """
        # TODO update this when supported (ccxt is supporting it)
        raise NotImplementedError("trades callback is not implemented")
        adapted = self.adapter.adapt_trades(self.exchange.parse_trade(trades))
        await self.push_to_channel(trading_constants.TRADES_CHANNEL, adapted)

    async def balance(self, balance: dict, **kwargs):
        """
        :param balance: the ccxt balance dict
        :param kwargs: the feed kwargs
        """
        # TODO update this when supported (ccxt is supporting it)
        raise NotImplementedError("balance callback is not implemented")
        await self.push_to_channel(
            trading_constants.BALANCE_CHANNEL,
            self.adapter.parse_balance(balance.balance),
        )

    async def transaction(self, transaction: dict, **kwargs):
        """
        :param transaction: the ccxt transaction dict
        :param kwargs: the feed kwargs
        """
        # TODO update this when supported (ccxt is supporting it). Use watchLedger ?
        raise NotImplementedError("transaction callback is not implemented")

    def _register_previous_open_candle(self, time_frame, symbol, candle):
        try:
            self._previous_open_candles[time_frame][symbol] = candle
        except KeyError:
            if time_frame not in self._previous_open_candles:
                self._previous_open_candles[time_frame] = {}
            self._previous_open_candles[time_frame][symbol] = candle

    def _get_previous_open_candle(self, time_frame, symbol):
        try:
            return self._previous_open_candles[time_frame][symbol]
        except KeyError:
            return None

    def _register_subsequent_unordered_candle(
        self, time_frame, symbol, parsed_timeframe, current_candle_time
    ):
        try:
            count, last_candle_time = self._subsequent_unordered_candles_count[
                time_frame
            ][symbol]
            if (
                current_candle_time - last_candle_time
                >= commons_enums.TimeFramesMinutes[parsed_timeframe]
                * commons_constants.MINUTE_TO_SECONDS
                * 1.5
            ):
                # candle is not subsequent from the previous one: reset count
                count = 0
            self._subsequent_unordered_candles_count[time_frame][symbol] = (
                count + 1,
                current_candle_time,
            )
            return False
        except KeyError:
            if time_frame not in self._subsequent_unordered_candles_count:
                self._subsequent_unordered_candles_count[time_frame] = {}
            self._subsequent_unordered_candles_count[time_frame][symbol] = (
                1,
                current_candle_time,
            )
            return True

    def _get_subsequent_unordered_candles_count(self, time_frame, symbol):
        try:
            return self._subsequent_unordered_candles_count[time_frame][symbol][0]
        except KeyError:
            return 0

    def _increment_error_counter(self, time_frame, error):
        error_key = error.__class__.__name__
        try:
            self._errors_count[time_frame][error_key] += 1
        except KeyError:
            if time_frame not in self._errors_count:
                self._errors_count[time_frame] = {}
            self._errors_count[time_frame][error_key] = 1
        return self._errors_count[time_frame][error_key]

    def _fix_candles_timestamps(self, candles: list, time_frame: commons_enums.TimeFrames) -> list:
        for candle in candles:
            candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value] = self._get_utc_candle_timestamp(
                candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value], time_frame
            )
        return candles

    def _get_utc_candle_timestamp(self, timestamp: float, time_frame: commons_enums.TimeFrames) -> float:
        uniformized_timestamp = self.adapter.get_uniformized_timestamp(timestamp)
        if self.candle_delay_seconds != 0:
            return uniformized_timestamp + self.candle_delay_seconds
        current_time = self.exchange_manager.exchange.get_exchange_current_time()
        if current_time % commons_constants.MINUTE_TO_SECONDS > 20:
            # avoid new candle side effects: if current time is less than 20 seconds older than the current minute, ignore it
            expected_timestamp = time_frame_manager.get_last_timeframe_time(time_frame, current_time)
            delay = expected_timestamp - uniformized_timestamp
            hours_delay = delay / commons_constants.HOURS_TO_SECONDS
            if int(hours_delay) != hours_delay:
                # should not happen: raise if it does
                raise ValueError(
                    f"can't compute utc candle timestamp at this time (delay is not a whole number of hours, {delay=})"
                )
            self.candle_delay_seconds = delay
            self.logger.info(
                f"Applying websocket candle delay of {delay} seconds (= {hours_delay} hours)"
            )
            return uniformized_timestamp + self.candle_delay_seconds
        raise ValueError("can't compute utc candle timestamp at this time (too close to the next minute)")
