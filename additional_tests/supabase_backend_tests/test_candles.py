#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import math
import time
import pytest

import octobot_commons.enums as commons_enums
from additional_tests.supabase_backend_tests import authenticated_client_1, anon_client


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_fetch_candles_history_range_as_auth(authenticated_client_1):
    # locale db
    min_time, max_time = await authenticated_client_1.fetch_candles_history_range(
        "binance", "BTC/USDT", commons_enums.TimeFrames.FOUR_HOURS, False
    )
    assert 0 < min_time < max_time < time.time()

    # prod db
    prod_min_time, prod_max_time = await authenticated_client_1.fetch_candles_history_range(
        "binance", "BTC/USDT", commons_enums.TimeFrames.FOUR_HOURS, True
    )
    assert 0 < prod_min_time < prod_max_time < time.time()
    assert prod_min_time != min_time
    assert prod_max_time != max_time


async def test_fetch_candles_history_range_as_anon(anon_client):
    # locale db
    min_time, max_time = await anon_client.fetch_candles_history_range(
        "binance", "BTC/USDT", commons_enums.TimeFrames.FOUR_HOURS, False
    )
    assert 0 < min_time < max_time < time.time()

    # prod db
    prod_min_time, prod_max_time = await anon_client.fetch_candles_history_range(
        "binance", "BTC/USDT", commons_enums.TimeFrames.FOUR_HOURS, True
    )
    assert 0 < prod_min_time < prod_max_time < time.time()
    assert prod_min_time != min_time
    assert prod_max_time != max_time


async def test_fetch_candles_history(anon_client):
    start_time = 1718785679
    end_time = 1721377495
    candles_count = math.floor((end_time - start_time) / (
        commons_enums.TimeFramesMinutes[commons_enums.TimeFrames.FIFTEEN_MINUTES] * 60
    ))
    # requires multiple fetches
    assert candles_count  == 2879
    candles = await anon_client.fetch_candles_history(
        "binance", "BTC/USDT", commons_enums.TimeFrames.FIFTEEN_MINUTES, start_time, end_time
    )
    fetched_count = candles_count + 1
    assert len(candles) == fetched_count
    # candles are unique
    assert len(set(c[0] for c in candles)) == fetched_count
