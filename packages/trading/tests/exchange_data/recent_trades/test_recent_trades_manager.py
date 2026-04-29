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
import os

import pytest

from tests.exchange_data import recent_trades_manager, price_events_manager

# All test coroutines will be treated as marked.
from tests.test_utils.random_numbers import random_recent_trade, random_recent_trades
from tests import event_loop

pytestmark = pytest.mark.asyncio


async def test_initialize(recent_trades_manager):
    assert not recent_trades_manager.recent_trades
    assert not recent_trades_manager.liquidations
    with pytest.raises(IndexError):
        recent_trades_manager.recent_trades[0]
    with pytest.raises(IndexError):
        recent_trades_manager.liquidations[0]


async def test_set_all_recent_trades(recent_trades_manager):
    # if setting no new trades
    recent_trades_manager.set_all_recent_trades([])
    assert not recent_trades_manager.recent_trades
    recent_trades_manager.set_all_recent_trades(None)
    assert not recent_trades_manager.recent_trades

    # test removing all previous values
    recent_trades_manager.recent_trades.append(1)
    assert 1 in recent_trades_manager.recent_trades
    trades = random_recent_trades()
    recent_trades_manager.set_all_recent_trades(trades)
    assert trades[-1] in recent_trades_manager.recent_trades
    assert 1 not in recent_trades_manager.recent_trades

    # test set values
    recent_trade_1 = random_recent_trade()
    recent_trade_2 = random_recent_trade()
    recent_trade_3 = random_recent_trade()
    trades = [recent_trade_3, recent_trade_2, recent_trade_1]
    recent_trades_manager.set_all_recent_trades(trades)
    assert recent_trade_1 in recent_trades_manager.recent_trades
    assert recent_trade_2 in recent_trades_manager.recent_trades
    assert recent_trades_manager.recent_trades[-1] == recent_trade_1
    assert recent_trades_manager.recent_trades[-2] == recent_trade_2
    assert recent_trades_manager.recent_trades[-3] == recent_trade_3


async def test_add_new_trades(recent_trades_manager):
    # if adding no new trades
    recent_trades_manager.add_new_trades([])
    assert not recent_trades_manager.recent_trades
    recent_trades_manager.add_new_trades(None)
    assert not recent_trades_manager.recent_trades

    # test set values
    recent_trade_1 = random_recent_trade()
    recent_trade_2 = random_recent_trade()
    recent_trade_3 = random_recent_trade()
    recent_trade_4 = random_recent_trade()
    recent_trade_5 = random_recent_trade()
    trades = [recent_trade_1, recent_trade_2]
    recent_trades_manager.add_new_trades(trades)
    assert recent_trade_1 in recent_trades_manager.recent_trades
    assert recent_trade_2 in recent_trades_manager.recent_trades
    assert recent_trades_manager.recent_trades[0] == recent_trade_1
    assert recent_trades_manager.recent_trades[1] == recent_trade_2
    with pytest.raises(IndexError):
        recent_trades_manager.recent_trades[2]

    # test add duplicate
    trades = [recent_trade_2, recent_trade_3, recent_trade_4]
    recent_trades_manager.add_new_trades(trades)
    assert recent_trades_manager.recent_trades[0] == recent_trade_1
    assert recent_trades_manager.recent_trades[1] == recent_trade_2
    assert recent_trades_manager.recent_trades[2] == recent_trade_3
    assert recent_trades_manager.recent_trades[3] == recent_trade_4
    with pytest.raises(IndexError):
        recent_trades_manager.recent_trades[4]

    trades = [recent_trade_2, recent_trade_5]
    recent_trades_manager.add_new_trades(trades)
    assert recent_trades_manager.recent_trades[0] == recent_trade_1
    assert recent_trades_manager.recent_trades[1] == recent_trade_2
    assert recent_trades_manager.recent_trades[2] == recent_trade_3
    assert recent_trades_manager.recent_trades[3] == recent_trade_4
    assert recent_trades_manager.recent_trades[4] == recent_trade_5


async def test_add_new_liquidations(recent_trades_manager):
    # if adding no new liquidations
    recent_trades_manager.add_new_liquidations([])
    assert not recent_trades_manager.liquidations
    recent_trades_manager.add_new_liquidations(None)
    assert not recent_trades_manager.liquidations


async def test_reset_recent_trades(recent_trades_manager):
    if not os.getenv('CYTHON_IGNORE'):
        recent_trades_manager.recent_trades.append(1)
        recent_trades_manager.liquidations.append(2)
        assert recent_trades_manager.recent_trades
        assert recent_trades_manager.liquidations
        recent_trades_manager._reset_recent_trades()
        assert not recent_trades_manager.recent_trades
        assert not recent_trades_manager.liquidations
        with pytest.raises(IndexError):
            recent_trades_manager.recent_trades[0]
        with pytest.raises(IndexError):
            recent_trades_manager.liquidations[0]
