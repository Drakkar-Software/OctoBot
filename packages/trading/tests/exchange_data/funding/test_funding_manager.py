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
import decimal

import pytest
import pytest_asyncio

import octobot_trading.constants as constants
from octobot_trading.exchange_data.funding.funding_manager import FundingManager
from tests.test_utils.random_numbers import random_timestamp, random_funding_rate
from tests import event_loop

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture()
async def funding_manager():
    fund_manager = FundingManager()
    await fund_manager.initialize()
    return fund_manager


async def test_init(funding_manager):
    assert funding_manager.next_update == 0
    assert funding_manager.last_updated == 0
    assert funding_manager.funding_rate.is_nan()
    assert funding_manager.funding_rate is constants.NaN
    assert funding_manager.predicted_funding_rate.is_nan()
    assert funding_manager.predicted_funding_rate is constants.NaN


async def test_reset_funding(funding_manager):
    funding_manager.next_update = random_timestamp()
    funding_manager.last_updated = random_timestamp()
    funding_manager.funding_rate = decimal.Decimal(random_funding_rate())
    funding_manager.predicted_funding_rate = decimal.Decimal(random_funding_rate())
    funding_manager.reset_funding()
    assert funding_manager.next_update == 0
    assert funding_manager.last_updated == 0
    assert funding_manager.funding_rate.is_nan()
    assert funding_manager.funding_rate is constants.NaN
    assert funding_manager.predicted_funding_rate.is_nan()
    assert funding_manager.predicted_funding_rate is constants.NaN


async def test_funding_update(funding_manager):
    last_updated = random_timestamp()
    next_updated = random_timestamp(last_updated)
    funding_rate = decimal.Decimal(random_funding_rate())
    predicted_funding_rate = decimal.Decimal(random_funding_rate())
    funding_manager.funding_update(funding_rate, predicted_funding_rate, next_updated, last_updated)
    assert funding_manager.next_update == next_updated
    assert funding_manager.last_updated == last_updated
    assert funding_manager.funding_rate == funding_rate
    assert funding_manager.predicted_funding_rate == predicted_funding_rate
