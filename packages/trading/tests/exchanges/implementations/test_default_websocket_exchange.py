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
import asyncio
import mock

import octobot_trading.exchanges as exchanges
import octobot_trading.enums as enums
import pytest

from tests.exchanges import liquid_exchange_manager as liquid_exchange_manager_fixture, DEFAULT_EXCHANGE_NAME
from tests import skipped_on_github_CI

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class FeedCallback:
    def __init__(self, connector, feed):
        self.connector = connector
        self.feed = feed

    def __call__(self, *args, **kwargs):
        if not self.connector.called_feed_event[self.feed].is_set():
            self.connector.called_feed_event[self.feed].set()
            # debug print, start pytest with -s arg to see it in real time
            print(f"Set {self.feed} event from {kwargs}")


class MockedCCXTWebsocketConnector(exchanges.CCXTWebsocketConnector):
    IGNORED_FEED_PAIRS = {
        # Do not ignore Trades feed as it is required for the test
        # When candles are available : use min timeframe kline to push ticker
        enums.WebsocketFeeds.TICKER: [enums.WebsocketFeeds.KLINE]
    }
    EXCHANGE_FEEDS = {
        enums.WebsocketFeeds.CANDLE: True,
        enums.WebsocketFeeds.TICKER: True,
        enums.WebsocketFeeds.TRADES: True,
        enums.WebsocketFeeds.L1_BOOK: True,
    }

    def __init__(self, config, exchange_manager, adapter_class=None, additional_config=None, websocket_name=None):
        super().__init__(config, exchange_manager, adapter_class=adapter_class, additional_config=additional_config,
                         websocket_name=websocket_name)
        self.called_feed_event = {
            feed: asyncio.Event()
            for feed in self.EXCHANGE_FEEDS
        }
        self.callback_mocks = {
            feed: mock.Mock(side_effect=FeedCallback(self, feed))
            for feed in enums.WebsocketFeeds
        }

    async def await_each_feed_call(self, timeout):
        await asyncio.gather(
            *(
                asyncio.wait_for(event.wait(), timeout)
                for event in self.called_feed_event.values()
            )
        )

    async def ticker(self, ticker: dict, symbol=None, **kwargs):
        self.callback_mocks[enums.WebsocketFeeds.TICKER](ticker, symbol=symbol, **kwargs)

    async def recent_trades(self, trades: list, symbol=None, **kwargs):
        self.callback_mocks[enums.WebsocketFeeds.TRADES](trades, symbol=symbol, **kwargs)

    async def book(self, order_book: dict, symbol=None, **kwargs):
        self.callback_mocks[enums.WebsocketFeeds.L1_BOOK](order_book, symbol=symbol, **kwargs)

    async def candle(self, candles: list, symbol=None, timeframe=None, **kwargs):
        self.callback_mocks[enums.WebsocketFeeds.CANDLE](candles, symbol=symbol, timeframe=timeframe, **kwargs)

    async def funding(self, funding: dict, symbol=None, **kwargs):
        self.callback_mocks[enums.WebsocketFeeds.FUNDING](funding, symbol=symbol, **kwargs)

    async def open_interest(self, open_interest: dict, symbol=None, **kwargs):
        self.callback_mocks[enums.WebsocketFeeds.OPEN_INTEREST](open_interest, symbol=symbol, **kwargs)

    async def index(self, index: dict, symbol=None, **kwargs):
        self.callback_mocks[enums.WebsocketFeeds.FUTURES_INDEX](index, symbol=symbol, **kwargs)

    async def orders(self, orders: list, **kwargs):
        self.callback_mocks[enums.WebsocketFeeds.ORDERS](orders, **kwargs)

    async def trades(self, trades: list, **kwargs):
        self.callback_mocks[enums.WebsocketFeeds.TRADE](trades, **kwargs)

    async def balance(self, balance: dict, **kwargs):
        self.callback_mocks[enums.WebsocketFeeds.PORTFOLIO](balance, **kwargs)

    async def transaction(self, transaction: dict, **kwargs):
        self.callback_mocks[enums.WebsocketFeeds.TRANSACTIONS](transaction, **kwargs)

    @classmethod
    def get_name(cls):
        return DEFAULT_EXCHANGE_NAME


class MockedWebSocketExchange(exchanges.DefaultWebSocketExchange):
    DEFAULT_CONNECTOR_CLASS = MockedCCXTWebsocketConnector

    @classmethod
    def get_exchange_connector_class(cls, exchange_manager):
        return cls.DEFAULT_CONNECTOR_CLASS


@pytest.fixture
def default_websocket_exchange(liquid_exchange_manager_fixture):
    yield MockedWebSocketExchange(liquid_exchange_manager_fixture.config, liquid_exchange_manager_fixture)


async def _test_start_receive_feeds_and_stop(default_websocket_exchange, skipped_on_github_CI):
    await default_websocket_exchange.init_websocket(
        default_websocket_exchange.exchange_manager.exchange_config.traded_time_frames,
        default_websocket_exchange.exchange_manager.exchange_config.traded_symbol_pairs,
        default_websocket_exchange.exchange_manager.tentacles_setup_config
    )

    # usually last about 5s
    data_reception_timeout = 90
    try:
        await default_websocket_exchange.start_sockets()
        assert len(default_websocket_exchange.websocket_connectors[0].channels) == 4
        await default_websocket_exchange.websocket_connectors[0].await_each_feed_call(data_reception_timeout)
    finally:
        await default_websocket_exchange.stop_sockets()
        await default_websocket_exchange.close_sockets()
        default_websocket_exchange.clear()
