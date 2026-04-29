#  Drakkar-Software OctoBot-Tentacles
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

import pytest

import octobot_commons.channels_name as channels_name
import octobot_commons.enums as commons_enums
import octobot_commons.tests as commons_tests
import octobot_trading.exchanges as exchanges
import octobot_trading.util.test_tools.websocket_test_tools as websocket_test_tools
from ...okx_websocket_feed import OKXCryptofeedWebsocketConnector

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_start_spot_websocket():
    config = commons_tests.load_test_config()
    async with websocket_test_tools.ws_exchange_manager(config, OKXCryptofeedWebsocketConnector.get_name()) \
            as exchange_manager_instance:
        await websocket_test_tools.test_unauthenticated_push_to_channel_coverage_websocket(
            websocket_exchange_class=exchanges.CryptofeedWebSocketExchange,
            websocket_connector_class=OKXCryptofeedWebsocketConnector,
            exchange_manager=exchange_manager_instance,
            config=config,
            symbols=["BTC/USDT", "ETH/USDT"],
            time_frames=[commons_enums.TimeFrames.ONE_HOUR],
            expected_pushed_channels={
                channels_name.OctoBotTradingChannelsName.MARK_PRICE_CHANNEL.value,
            },
            time_before_assert=20
        )
