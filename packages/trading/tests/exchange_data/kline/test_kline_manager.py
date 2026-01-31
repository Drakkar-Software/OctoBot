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
import pytest_asyncio
from math import nan
from octobot_commons.enums import PriceIndexes

from octobot_trading.exchange_data.kline.kline_manager import KlineManager
from tests.test_utils.random_numbers import random_kline, random_price, random_timestamp, random_quantity
from tests import event_loop

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture()
async def kline_manager():
    k_manager = KlineManager()
    await k_manager.initialize()
    return k_manager


async def test_init(kline_manager):
    assert not kline_manager.kline == []


async def test_reset_kline(kline_manager):
    kline_manager.kline = random_kline()
    assert len(kline_manager.kline) == 6
    if not os.getenv('CYTHON_IGNORE'):
        kline_manager._reset_kline()
        assert kline_manager.kline == [nan] * len(PriceIndexes)


async def test_kline_update(kline_manager):
    rc_1 = random_kline()
    kline_manager.kline_update(rc_1)
    assert kline_manager.kline[PriceIndexes.IND_PRICE_CLOSE.value] == rc_1[PriceIndexes.IND_PRICE_CLOSE.value]

    # trigger a new candle
    rc_2 = [0] * len(PriceIndexes)
    rc_2[PriceIndexes.IND_PRICE_CLOSE.value] = 0
    rc_2[PriceIndexes.IND_PRICE_OPEN.value] = 0
    rc_2[PriceIndexes.IND_PRICE_HIGH.value] = 0
    rc_2[PriceIndexes.IND_PRICE_LOW.value] = 0
    rc_2[PriceIndexes.IND_PRICE_VOL.value] = 0
    rc_2[PriceIndexes.IND_PRICE_TIME.value] = random_timestamp()
    kline_manager.kline_update(rc_2)
    assert kline_manager.kline != rc_1

    # don't trigger a new candle
    first_kline = [0] * len(PriceIndexes)
    first_kline[PriceIndexes.IND_PRICE_CLOSE.value] = 0
    first_kline[PriceIndexes.IND_PRICE_OPEN.value] = 0
    first_kline[PriceIndexes.IND_PRICE_HIGH.value] = 0
    first_kline[PriceIndexes.IND_PRICE_LOW.value] = 0
    first_kline[PriceIndexes.IND_PRICE_VOL.value] = 0
    first_kline[PriceIndexes.IND_PRICE_TIME.value] = rc_2[PriceIndexes.IND_PRICE_TIME.value]
    assert kline_manager.kline == first_kline

    # shouldn't use new low
    rc_3 = rc_2
    rc_3[PriceIndexes.IND_PRICE_LOW.value] = random_price(1)
    kline_manager.kline_update(rc_3)
    assert kline_manager.kline == first_kline

    # should use new low
    rc_4 = rc_3
    new_high = random_price(10)
    rc_4[PriceIndexes.IND_PRICE_HIGH.value] = new_high
    kline_manager.kline_update(rc_4)
    second_kline = first_kline
    second_kline[PriceIndexes.IND_PRICE_HIGH.value] = new_high
    assert kline_manager.kline == second_kline

    # shouldn't use new low
    rc_5 = rc_4
    rc_5[PriceIndexes.IND_PRICE_HIGH.value] = new_high - 1
    kline_manager.kline_update(rc_5)
    assert kline_manager.kline == second_kline

    # should use new low
    rc_6 = rc_5
    rc_6[PriceIndexes.IND_PRICE_HIGH.value] = new_high + 1
    third_kline = second_kline
    third_kline[PriceIndexes.IND_PRICE_HIGH.value] = new_high + 1
    kline_manager.kline_update(rc_6)
    assert kline_manager.kline == third_kline

    # should use new vol
    rc_7 = rc_6
    new_vol = random_quantity()
    rc_7[PriceIndexes.IND_PRICE_VOL.value] = new_vol
    kline_4 = third_kline
    kline_4[PriceIndexes.IND_PRICE_VOL.value] = new_vol
    kline_manager.kline_update(rc_7)
    assert kline_manager.kline == kline_4

    # should use new close
    rc_8 = rc_7
    new_price = random_price()
    rc_8[PriceIndexes.IND_PRICE_CLOSE.value] = new_price
    kline_5 = kline_4
    kline_5[PriceIndexes.IND_PRICE_CLOSE.value] = new_price
    kline_manager.kline_update(rc_8)
    assert kline_manager.kline == kline_5

    # shouldn't use new open
    rc_9 = rc_8
    new_open = random_price()
    rc_9[PriceIndexes.IND_PRICE_OPEN.value] = new_open
    kline_manager.kline_update(rc_9)
    assert kline_manager.kline == kline_5
