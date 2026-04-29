#  Drakkar-Software OctoBot
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
import os
from contextlib import asynccontextmanager


import octobot_commons.errors as commons_errors
from octobot_backtesting.importers.exchanges.exchange_importer import ExchangeDataImporter
from octobot_backtesting.enums import ExchangeDataTables
from octobot_commons.enums import TimeFrames

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


# use context manager instead of fixture to prevent pytest threads issues
@asynccontextmanager
async def get_importer():
    database_file = os.path.join("tests", "static", "ExchangeHistoryDataCollector_1589740606.4862757.data")
    importer = ExchangeDataImporter({}, database_file)
    try:
        await importer.initialize()
        yield importer
    finally:
        await importer.stop()


async def test_initialize():
    async with get_importer() as importer:
        assert importer.exchange_name == "binance"
        assert importer.symbols == ["ETH/BTC"]
        assert importer.time_frames == [TimeFrames(tf)
                                        for tf in ("1m", "3m", "5m", "15m", "30m", "1h", "2h",
                                        "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M")]
        assert importer.available_data_types == [ExchangeDataTables.OHLCV]


async def test_get_data_timestamp_interval():
    async with get_importer() as importer:
        # over all data
        assert await importer.get_data_timestamp_interval() == (1589710680, 1590883200)
        # for 1h time frame
        assert await importer.get_data_timestamp_interval("1h") == (1587945600, 1589742000)
        # for 1M time frame
        assert await importer.get_data_timestamp_interval("1M") == (1501459200, 1590883200)


async def test_get_ohlcv():
    async with get_importer() as importer:
        # default values
        ohlcv = await importer.get_ohlcv()
        assert len(ohlcv) == 500
        # same symbol, cryptocurrency and exchange in all data (one symbol in datafile)
        exchange = ohlcv[0][1]
        cryptocurrency = ohlcv[0][2]
        symbol = ohlcv[0][3]
        assert all(data[1] == exchange for data in ohlcv)
        assert all(data[2] == cryptocurrency for data in ohlcv)
        assert all(data[3] == symbol for data in ohlcv)
        # same time frame
        assert all(data[4] == "1h" for data in ohlcv)
        # valid ohlcv data
        assert all(
            len(data[5]) == 6 and all(isinstance(element, float)
                                      for element in data[5])
            for data in ohlcv)

        # custom values
        ohlcv = await importer.get_ohlcv(exchange_name="binance", symbol="ETH/BTC",
                                         time_frame=TimeFrames.ONE_WEEK, limit=10)
        assert len(ohlcv) == 10
        assert all(data[4] == TimeFrames.ONE_WEEK.value for data in ohlcv)

        # unknown values
        ohlcv = await importer.get_ohlcv(exchange_name="binance", symbol="ETH/XXX", time_frame=TimeFrames.ONE_WEEK)
        assert len(ohlcv) == 0


async def test_get_ohlcv_from_timestamps():
    async with get_importer() as importer:
        # default values
        ohlcv = await importer.get_ohlcv_from_timestamps()
        assert len(ohlcv) == 500
        assert all(data[4] == "1h" for data in ohlcv)
        # timestamp select
        ohlcv = await importer.get_ohlcv_from_timestamps(inferior_timestamp=1587978000, superior_timestamp=1588060800)
        assert len(ohlcv) == 24
        assert all(1587978000 <= data[0] <= 1588060800 for data in ohlcv)


async def test_get_ticker():
    async with get_importer() as importer:
        # TODO complete this test when available datafile with ticker data
        with pytest.raises(commons_errors.DatabaseNotFoundError):
            await importer.get_ticker()


async def test_get_ticker_from_timestamps():
    async with get_importer() as importer:
        # TODO complete this test when available datafile with ticker data
        with pytest.raises(commons_errors.DatabaseNotFoundError):
            await importer.get_ticker_from_timestamps()


async def test_get_order_book():
    async with get_importer() as importer:
        # TODO complete this test when available datafile with order book data
        with pytest.raises(commons_errors.DatabaseNotFoundError):
            await importer.get_order_book()


async def test_get_order_book_from_timestamps():
    async with get_importer() as importer:
        # TODO complete this test when available datafile with order book data
        with pytest.raises(commons_errors.DatabaseNotFoundError):
            await importer.get_order_book_from_timestamps()


async def test_get_recent_trades():
    async with get_importer() as importer:
        # TODO complete this test when available datafile with recent trades data
        with pytest.raises(commons_errors.DatabaseNotFoundError):
            await importer.get_recent_trades()


async def test_get_recent_trades_from_timestamps():
    async with get_importer() as importer:
        # TODO complete this test when available datafile with recent trades data
        with pytest.raises(commons_errors.DatabaseNotFoundError):
            await importer.get_recent_trades_from_timestamps()


async def test_get_kline():
    async with get_importer() as importer:
        # TODO complete this test when available datafile with kline data
        with pytest.raises(commons_errors.DatabaseNotFoundError):
            await importer.get_kline()


async def test_get_kline_from_timestamps():
    async with get_importer() as importer:
        # TODO complete this test when available datafile with kline data
        with pytest.raises(commons_errors.DatabaseNotFoundError):
            await importer.get_kline_from_timestamps()
