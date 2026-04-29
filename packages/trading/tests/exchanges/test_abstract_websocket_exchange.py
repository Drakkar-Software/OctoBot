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
import mock
import os
import octobot_trading.exchanges as exchanges
from octobot_trading.enums import WebsocketFeeds as Feeds
import pytest

from tests.exchanges import exchange_manager

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_should_ignore_feed(exchange_manager):
    if os.getenv('CYTHON_IGNORE'):
        return

    with mock.patch.object(exchanges.AbstractWebsocketExchange, 'get_name', mock.Mock()) as get_name_mock:
        get_name_mock.return_value = ""
        abstract_ws_exchange = exchanges.AbstractWebsocketExchange(exchange_manager.config, exchange_manager)

    # Don't ignore with default config
    assert not abstract_ws_exchange.should_ignore_feed(Feeds.CANDLE)
    assert not abstract_ws_exchange.should_ignore_feed(Feeds.TICKER)
    assert not abstract_ws_exchange.should_ignore_feed(Feeds.TRADES)

    # When no exchange feeds configured => don't ignore
    exchanges.AbstractWebsocketExchange.IGNORED_FEED_PAIRS = {
        Feeds.TRADES: [Feeds.TICKER]
    }
    assert not abstract_ws_exchange.should_ignore_feed(Feeds.CANDLE)
    assert not abstract_ws_exchange.should_ignore_feed(Feeds.TICKER)
    assert not abstract_ws_exchange.should_ignore_feed(Feeds.TRADES)

    # When the corresponding feed is not supported => don't ignore
    exchanges.AbstractWebsocketExchange.EXCHANGE_FEEDS = {
        Feeds.TRADES: "trades_feed",
        Feeds.TICKER: Feeds.UNSUPPORTED.value,
        Feeds.CANDLE: Feeds.UNSUPPORTED.value,
    }
    assert not abstract_ws_exchange.should_ignore_feed(Feeds.CANDLE)
    assert not abstract_ws_exchange.should_ignore_feed(Feeds.TICKER)
    assert not abstract_ws_exchange.should_ignore_feed(Feeds.TRADES)

    # When the corresponding feed is supported => ignore
    exchanges.AbstractWebsocketExchange.EXCHANGE_FEEDS = {
        Feeds.TRADES: "trades_feed",
        Feeds.TICKER: "ticker_feed",
        Feeds.CANDLE: Feeds.UNSUPPORTED.value,
    }
    assert not abstract_ws_exchange.should_ignore_feed(Feeds.CANDLE)
    assert not abstract_ws_exchange.should_ignore_feed(Feeds.TICKER)
    assert abstract_ws_exchange.should_ignore_feed(Feeds.TRADES)

