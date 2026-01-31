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
import pytest

from tests import event_loop
from octobot_trading.api.channels import subscribe_to_ohlcv_channel, subscribe_to_trades_channel, \
    subscribe_to_order_channel

from tests.exchanges import exchange_manager

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def ohlcv_callback(
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        time_frame,
        candle
):
    pass


async def trades_callback(exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, trade, old_trade):
    pass


async def order_callback(self, exchange, exchange_id, cryptocurrency, symbol, order, update_type, is_from_bot):
    pass


async def test_subscribe_to_ohlcv_channel(exchange_manager):
    await subscribe_to_ohlcv_channel(ohlcv_callback, exchange_manager.id)


async def test_subscribe_to_trades_channel(exchange_manager):
    await subscribe_to_trades_channel(trades_callback, exchange_manager.id)


async def test_subscribe_to_order_channel(exchange_manager):
    await subscribe_to_order_channel(order_callback, exchange_manager.id)
