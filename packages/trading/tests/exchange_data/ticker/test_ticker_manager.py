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

from octobot_trading.exchange_data.ticker.ticker_manager import TickerManager
from octobot_trading.enums import ExchangeConstantsMiniTickerColumns, ExchangeConstantsTickersColumns
from tests.test_utils.random_numbers import random_price, random_quantity, random_timestamp
from tests import event_loop

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture()
async def ticker_manager():
    t_manager = TickerManager()
    await t_manager.initialize()
    return t_manager


async def test_init(ticker_manager):
    assert not ticker_manager.ticker == {}
    assert not ticker_manager.mini_ticker == {}


async def test_update_and_reset_ticker(ticker_manager):
    price = random_price()
    tm = random_timestamp()
    vlm = random_quantity()
    ticker_manager.ticker_update({
        ExchangeConstantsTickersColumns.ASK.value: price,
        ExchangeConstantsTickersColumns.ASK_VOLUME.value: vlm,
        ExchangeConstantsTickersColumns.TIMESTAMP.value: tm
    })
    assert ticker_manager.ticker[ExchangeConstantsTickersColumns.ASK.value] == price
    assert ticker_manager.ticker[ExchangeConstantsTickersColumns.ASK_VOLUME.value] == vlm
    assert ticker_manager.ticker[ExchangeConstantsTickersColumns.TIMESTAMP.value] == tm
    if not os.getenv('CYTHON_IGNORE'):
        ticker_manager.reset_ticker()
        assert ticker_manager.ticker == {
            ExchangeConstantsTickersColumns.ASK.value: nan,
            ExchangeConstantsTickersColumns.ASK_VOLUME.value: nan,
            ExchangeConstantsTickersColumns.BID.value: nan,
            ExchangeConstantsTickersColumns.BID_VOLUME.value: nan,
            ExchangeConstantsTickersColumns.OPEN.value: nan,
            ExchangeConstantsTickersColumns.LOW.value: nan,
            ExchangeConstantsTickersColumns.HIGH.value: nan,
            ExchangeConstantsTickersColumns.CLOSE.value: nan,
            ExchangeConstantsTickersColumns.LAST.value: nan,
            ExchangeConstantsTickersColumns.AVERAGE.value: nan,
            ExchangeConstantsTickersColumns.SYMBOL.value: nan,
            ExchangeConstantsTickersColumns.QUOTE_VOLUME.value: nan,
            ExchangeConstantsTickersColumns.BASE_VOLUME.value: nan,
            ExchangeConstantsTickersColumns.TIMESTAMP.value: 0,
            ExchangeConstantsTickersColumns.VWAP.value: nan
        }


async def test_update_and_reset_mini_ticker(ticker_manager):
    vol = random_quantity()
    open_p = random_price()
    ticker_manager.mini_ticker_update({
            ExchangeConstantsMiniTickerColumns.HIGH_PRICE.value: random_price(),
            ExchangeConstantsMiniTickerColumns.LOW_PRICE.value: random_price(),
            ExchangeConstantsMiniTickerColumns.OPEN_PRICE.value: open_p,
            ExchangeConstantsMiniTickerColumns.CLOSE_PRICE.value: random_price(),
            ExchangeConstantsMiniTickerColumns.VOLUME.value: vol,
            ExchangeConstantsMiniTickerColumns.TIMESTAMP.value: random_timestamp()
        })
    assert ticker_manager.mini_ticker[ExchangeConstantsMiniTickerColumns.VOLUME.value] == vol
    assert ticker_manager.mini_ticker[ExchangeConstantsMiniTickerColumns.OPEN_PRICE.value] == open_p
    if not os.getenv('CYTHON_IGNORE'):
        ticker_manager.reset_mini_ticker()
        assert ticker_manager.mini_ticker == {
                ExchangeConstantsMiniTickerColumns.HIGH_PRICE.value: nan,
                ExchangeConstantsMiniTickerColumns.LOW_PRICE.value: nan,
                ExchangeConstantsMiniTickerColumns.OPEN_PRICE.value: nan,
                ExchangeConstantsMiniTickerColumns.CLOSE_PRICE.value: nan,
                ExchangeConstantsMiniTickerColumns.VOLUME.value: nan,
                ExchangeConstantsMiniTickerColumns.TIMESTAMP.value: 0
            }
