#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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
import mock
import pytest
import asyncio
import pyiceberg.table

from additional_tests.historical_backend_tests import iceberg_client
import octobot.community.history_backend.iceberg_historical_backend_client as iceberg_historical_backend_client
import octobot.community.history_backend.util as history_backend_util

import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


EXCHANGE = "binance"
SYMBOL = "BTC/USDC"
SHORT_TIME_FRAME = commons_enums.TimeFrames.FIFTEEN_MINUTES


async def test_fetch_candles_history_range(iceberg_client):
    # unknown candles
    min_time, max_time = await iceberg_client.fetch_candles_history_range(
        EXCHANGE+"plop", SYMBOL, SHORT_TIME_FRAME
    )
    assert min_time == max_time == 0

    # known candles
    min_time, max_time = await iceberg_client.fetch_candles_history_range(
        EXCHANGE, SYMBOL, SHORT_TIME_FRAME
    )
    assert 0 < min_time < max_time < time.time()


async def test_fetch_candles_history(iceberg_client):
    start_time = 1718785679
    end_time = 1721377495
    candles_count = math.floor((end_time - start_time) / (
        commons_enums.TimeFramesMinutes[SHORT_TIME_FRAME] * 60
    ))
    # requires multiple fetches
    assert candles_count  == 2879
    candles = await iceberg_client.fetch_candles_history(
        EXCHANGE, SYMBOL, SHORT_TIME_FRAME, start_time, end_time
    )
    assert sorted(candles, key=lambda c: c[0]) == candles
    fetched_count = candles_count + 1
    assert len(candles) == fetched_count
    # will fail if parsed time is not UTC
    assert candles[0][commons_enums.PriceIndexes.IND_PRICE_TIME.value] == 1718785800
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


async def test_fetch_candles_history_asynchronousness(iceberg_client):
    start_time = 1718785679
    end_time_1 = 1721377495
    end_time_2 = 1721377495 + 2 * commons_constants.DAYS_TO_SECONDS
    end_time_3 = 1721377495 + 23 * commons_constants.DAYS_TO_SECONDS

    scan_call_times = []
    _to_arrow_call_times = []
    _to_arrow_return_times = []

    def _get_or_create_table(*args, **kwargs):
        table = original_get_or_create_table(*args, **kwargs)
        original_scan = table.scan


        def _scan(*args, **kwargs):
            scan_call_times.append(time.time())
            scan_result = original_scan(*args, **kwargs)
            original_to_arrow = scan_result.to_arrow

            def _to_arrow(*args, **kwargs):
                _to_arrow_call_times.append(time.time())
                try:
                    return original_to_arrow(*args, **kwargs)
                finally:
                    _to_arrow_return_times.append(time.time())

            scan_result.to_arrow = _to_arrow
            return scan_result

        table.scan = mock.Mock(side_effect=_scan)
        return table

    original_get_or_create_table = iceberg_client._get_or_create_table
    with (
        mock.patch.object(iceberg_client, "_get_or_create_table", mock.Mock(side_effect=_get_or_create_table)) as get_or_create_table_mock
    ):
        candles_1, candles_2, candles_3 = await asyncio.gather(
            iceberg_client.fetch_candles_history(
                EXCHANGE, SYMBOL, SHORT_TIME_FRAME, start_time, end_time_1
            ),
            iceberg_client.fetch_candles_history(
                EXCHANGE, SYMBOL, SHORT_TIME_FRAME, start_time, end_time_2
            ),
            iceberg_client.fetch_candles_history(
                EXCHANGE, SYMBOL, SHORT_TIME_FRAME, start_time, end_time_3
            ),
        )
        assert get_or_create_table_mock.call_count == 3
        assert len(scan_call_times) == 3
        assert len(_to_arrow_call_times) == 3
        assert len(_to_arrow_return_times) == 3
    
    assert scan_call_times[0] <= scan_call_times[1] <= scan_call_times[2]
    assert _to_arrow_call_times[0] <= _to_arrow_call_times[1] <= _to_arrow_call_times[2]
    assert _to_arrow_return_times[0] < _to_arrow_return_times[1] < _to_arrow_return_times[2]

    # all to_arrow calls have been performed before the first to_arrow return, 
    # which means they are running concurrently in this async context
    assert max(_to_arrow_call_times) < min(_to_arrow_return_times)

    assert len(candles_1) > 2000
    assert len(candles_2) > len(candles_1)
    assert len(candles_3) > len(candles_2)


async def test_deduplicate(iceberg_client):
    start_time = 1718785679
    end_time = 1721377495
    candles = await iceberg_client.fetch_extended_candles_history(
        EXCHANGE, [SYMBOL], [SHORT_TIME_FRAME], start_time, end_time
    )
    assert all(c[0] == SHORT_TIME_FRAME.value for c in candles)
    assert all(c[1] == SYMBOL for c in candles)
    duplicated = candles + candles
    assert len(duplicated) == len(candles) * 2
    assert sorted(candles, key=lambda c: c[2]) == candles
    deduplicated = history_backend_util.deduplicate(duplicated, [0, 1, 2])
    # deduplicated and still sorted
    assert deduplicated == candles
