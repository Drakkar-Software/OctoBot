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
import pytest_asyncio

from octobot_trading.exchange_data.markets.markets_manager import MarketsManager
from tests import event_loop

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture()
async def markets_manager():
    markets_manager = MarketsManager()
    await markets_manager.initialize()
    return markets_manager


async def test_init(markets_manager):
    assert not markets_manager.markets == []
