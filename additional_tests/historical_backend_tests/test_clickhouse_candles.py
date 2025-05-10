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

from additional_tests.historical_backend_tests import clickhouse_client

import octobot_commons.enums as commons_enums


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_fetch_candles_history_range(clickhouse_client):
    min_time, max_time = await clickhouse_client.fetch_candles_history_range(
        "binance", "BTC/USDT", commons_enums.TimeFrames.FOUR_HOURS
    )
    assert 0 < min_time < max_time < time.time()


async def test_fetch_candles_history(clickhouse_client):
    start_time = 1718785679
    end_time = 1721377495
    candles_count = math.floor((end_time - start_time) / (
        commons_enums.TimeFramesMinutes[commons_enums.TimeFrames.FIFTEEN_MINUTES] * 60
    ))
    # requires multiple fetches
    assert candles_count  == 2879
    candles = await clickhouse_client.fetch_candles_history(
        "binance", "BTC/USDT", commons_enums.TimeFrames.FIFTEEN_MINUTES, start_time, end_time
    )
    fetched_count = candles_count + 1
    assert len(candles) == fetched_count
    assert (
        candles[0][commons_enums.PriceIndexes.IND_PRICE_TIME.value]
        != candles[0][commons_enums.PriceIndexes.IND_PRICE_OPEN.value]
        != candles[0][commons_enums.PriceIndexes.IND_PRICE_HIGH.value]
        != candles[0][commons_enums.PriceIndexes.IND_PRICE_LOW.value]
        != candles[0][commons_enums.PriceIndexes.IND_PRICE_CLOSE.value]
        != candles[0][commons_enums.PriceIndexes.IND_PRICE_VOL.value]
    )
    # candles are unique
    assert len(set(c[0] for c in candles)) == fetched_count
