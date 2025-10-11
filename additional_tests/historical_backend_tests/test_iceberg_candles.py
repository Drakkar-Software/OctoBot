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
import datetime
import enum

from additional_tests.historical_backend_tests import iceberg_client

import octobot.constants as constants
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


async def test_concurrent_insert_candles_history(iceberg_client):
    assert iceberg_client.enable_async_batch_inserts is True # default value
    temp_test_table = "temp_test_ohlcv_history_table" # use temp test table
    
    class _TableNames(enum.Enum):
        OHLCV_HISTORY = "temp_test_ohlcv_history_table"

    with (
        mock.patch.object(iceberg_historical_backend_client, "TableNames", _TableNames),
        mock.patch.object(constants, "CREATE_ICEBERG_DB_IF_MISSING", True),
    ):
        exchange = "binance"
        symbol = "BTC/USDC"
        time_frame = commons_enums.TimeFrames.FIFTEEN_MINUTES
        # iceberg_client.drop_table(temp_test_table) # in case table is not empty
        assert len(await iceberg_client.fetch_extended_candles_history(
            exchange, [symbol], [time_frame], 0, 1818785688
        )) == 0, (
            f"Test table is not empty"
        )
        try:
            rows_1 = [
                [iceberg_client.get_formatted_time(1718785679), exchange, symbol, time_frame.value, 80, 100, 79, 85, 12312],
                [iceberg_client.get_formatted_time(1718785680), exchange, symbol, time_frame.value, 85, 86, 84, 86, 12312],
            ]
            rows_2 = [
                [iceberg_client.get_formatted_time(1718785681), exchange, symbol, time_frame.value, 86, 87, 85, 87, 12312],
                [iceberg_client.get_formatted_time(1718785682), exchange, symbol, time_frame.value, 87, 88, 86, 88, 12312],
            ]
            rows_3 = [
                [iceberg_client.get_formatted_time(1718785683), exchange, symbol, time_frame.value, 88, 89, 87, 89, 12312],
                [iceberg_client.get_formatted_time(1718785684), exchange, symbol, time_frame.value, 89, 90, 88, 90, 12312],
            ]
            column_names = [
                "timestamp", "exchange_internal_name", "symbol", "time_frame", "open", "high", "low", "close", "volume"
            ]
            await asyncio.gather(
                iceberg_client.insert_candles_history(rows_1, column_names),
                iceberg_client.insert_candles_history(rows_2, column_names),
                iceberg_client.insert_candles_history(rows_3, column_names),
            )
            assert len(iceberg_client._pending_insert_data_by_table) == 1
            assert sum(
                len(pending_data.data)
                for pending_data in iceberg_client._pending_insert_data_by_table[
                    iceberg_historical_backend_client.TableNames.OHLCV_HISTORY
                ]
            ) == len(rows_1) + len(rows_2) + len(rows_3)
            # didn't insert yet: max pending rows is not reached, it will now be reached
            assert await iceberg_client.fetch_extended_candles_history(
                exchange, [symbol], [time_frame], 0, 1818785688
            ) == []
            with mock.patch.object(iceberg_historical_backend_client, "_MAX_PENDING_BATCH_INSERT_SIZE", 3):
                rows_4 = [
                    # will trigger insert of previous pending rows
                    [iceberg_client.get_formatted_time(1718785685), exchange, symbol, time_frame.value, 90, 91, 89, 91, 12312],
                    [iceberg_client.get_formatted_time(1718785686), exchange, symbol, time_frame.value, 91, 92, 90, 92, 12312],
                    [iceberg_client.get_formatted_time(1718785687), exchange, symbol, time_frame.value, 91.5, 92, 90, 92, 12312],
                ]
                rows_5 = [
                    # will  trigger another insert
                    [iceberg_client.get_formatted_time(1718785688), exchange, symbol, time_frame.value, 92, 93, 91, 93, 12312],
                    [iceberg_client.get_formatted_time(1718785689), exchange, symbol, time_frame.value, 93, 94, 92, 94, 12312],
                    [iceberg_client.get_formatted_time(1718785690), exchange, symbol, time_frame.value, 93, 94, 92, 94, 12312],
                ]
                # inserting: max pending rows is reached, it will now be inserted
                await asyncio.gather(
                    iceberg_client.insert_candles_history(rows_4, column_names),
                    iceberg_client.insert_candles_history(rows_5, column_names),
                )
                # rows have been inserted
                fetched_rows = await iceberg_client.fetch_extended_candles_history(
                    exchange, [symbol], [time_frame], 0, 1818785688
                )
                expected_rows = [
                    [row[3], row[2], history_backend_util.get_utc_timestamp_from_datetime(
                        datetime.datetime.strptime(row[0], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=datetime.timezone.utc)
                    )] + row[4:]
                    for row in rows_1 + rows_2 + rows_3 + rows_4 + rows_5
                ]
                assert fetched_rows == expected_rows
                # no remaining pending rows
                assert iceberg_client._pending_insert_data_by_table == {}
        finally:
            # test complete: delete test table
            iceberg_client.drop_table(temp_test_table)


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
