import mock
import pytest
import os
import asyncio
import sqlite3
import contextlib
import tempfile

import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.errors as errors
import octobot_commons.enums as enums
import octobot_backtesting.databases as backtesting_databases

import tests.database_test_util as database_test_util

pytestmark = pytest.mark.asyncio

DATA_FILE1 = "ExchangeHistoryDataCollector_1589740606.4862757.data"
DATA_FILE2 = "second_ExchangeHistoryDataCollector_1589740606.4862757.data"
STATIC_FIXTURE_PATHS = {
    DATA_FILE1: database_test_util.static_database_fixture_path(DATA_FILE1),
    DATA_FILE2: database_test_util.static_database_fixture_path(DATA_FILE2),
}
OHLCV = mock.Mock(value="ohlcv")
KLINE = mock.Mock(value="kline")


@pytest.fixture(scope="module", autouse=True)
def _static_fixtures_unchanged():
    mtimes_before = {
        file_name: os.path.getmtime(fixture_path)
        for file_name, fixture_path in STATIC_FIXTURE_PATHS.items()
    }
    yield
    for file_name, fixture_path in STATIC_FIXTURE_PATHS.items():
        assert os.path.getmtime(fixture_path) == mtimes_before[file_name]


@contextlib.asynccontextmanager
async def get_database(data_file=DATA_FILE1):
    fixture_path = STATIC_FIXTURE_PATHS[data_file]
    async with backtesting_databases.new_sqlite_database(fixture_path) as database:
        yield database
    await asyncio_tools.wait_asyncio_next_cycle()


@contextlib.asynccontextmanager
async def get_temp_empty_database():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
        database_name = temp_file.name
    try:
        async with backtesting_databases.new_sqlite_database(database_name, read_only=False) as database:
            yield database
    finally:
        await asyncio_tools.wait_asyncio_next_cycle()
        if os.path.isfile(database_name):
            os.remove(database_name)


async def test_invalid_file():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
        file_name = temp_file.name
    database = backtesting_databases.BacktestingDataSQLiteDatabase(file_name, read_only=False)
    try:
        await database.initialize()
        assert not await database.check_table_exists(KLINE)
        with pytest.raises(sqlite3.OperationalError):
            await database.check_table_not_empty(KLINE)
    finally:
        await database.stop()
        os.remove(file_name)


async def test_select():
    async with get_database() as database:
        with pytest.raises(errors.DatabaseNotFoundError):
            await database.select(KLINE)

        ohlcv = await database.select(OHLCV)
        assert len(ohlcv) == 6531

        ohlcv = await database.select(OHLCV, time_frame="1h")
        assert len(ohlcv) == 500

        ohlcv = await database.select(OHLCV, symbol="xyz")
        assert len(ohlcv) == 0

        ohlcv = await database.select(OHLCV, symbol="ETH/BTC")
        assert len(ohlcv) == 6531

        changed_order_ohlcv = await database.select(OHLCV, order_by="time_frame", symbol="ETH/BTC")
        assert changed_order_ohlcv[0] != ohlcv[0]

        ohlcv = await database.select(OHLCV, xyz="xyz")
        assert len(ohlcv) == 0


async def test_select_max():
    async with get_database() as database:
        assert await database.select_max(OHLCV, ["timestamp"]) == [(1590883200,)]
        assert await database.select_max(OHLCV, ["timestamp"], time_frame="1h") == [(1589742000,)]
        assert await database.select_max(OHLCV, ["timestamp"], ["symbol"], time_frame="1h") == \
            [(1589742000, "ETH/BTC")]


async def test_select_min():
    async with get_database() as database:
        assert await database.select_min(OHLCV, ["timestamp"]) == [(1500249600,)]
        assert await database.select_min(OHLCV, ["timestamp"], time_frame="1h") == [(1587945600,)]
        assert await database.select_min(OHLCV, ["timestamp"], ["symbol"], time_frame="1h") == \
            [(1587945600, "ETH/BTC")]


async def test_select_count():
    async with get_database() as database:
        assert await database.select_count(OHLCV, ["*"]) == [(6531,)]
        assert await database.select_count(OHLCV, ["*"], time_frame="1h") == [(500,)]
        assert await database.select_count(OHLCV, ["*"], time_frame="1M") == [(35,)]


async def test_select_from_timestamp():
    async with get_database() as database:
        operations = [enums.DataBaseOperations.INF_EQUALS.value]
        candles = await database.select_from_timestamp(OHLCV, ["1587960000"], operations)
        assert len(candles) > 0
        assert all(candle[0] <= 1587960000 for candle in candles)

        operations = [enums.DataBaseOperations.INF_EQUALS.value, enums.DataBaseOperations.SUP_EQUALS.value]
        candles = await database.select_from_timestamp(
            OHLCV, ["1587960000", "1587960000"], operations
        )
        assert len(candles) > 0
        assert all(candle[0] == 1587960000 for candle in candles)

        operations = [enums.DataBaseOperations.INF_EQUALS.value, enums.DataBaseOperations.SUP_EQUALS.value]
        candles = await database.select_from_timestamp(
            OHLCV, ["1587960000", "1587945600"], operations
        )
        assert len(candles) == 15
        assert all(1587945600 <= candle[0] <= 1587960000 for candle in candles)

        operations = [enums.DataBaseOperations.INF_EQUALS.value, enums.DataBaseOperations.SUP_EQUALS.value]
        candles = await database.select_from_timestamp(
            OHLCV, ["1587960000", "1587945600"], operations, symbol="xyz"
        )
        assert len(candles) == 0


async def test_gather_concurrent_select():
    async with get_database() as database:
        timestamps_1h = [ohlcv[0] for ohlcv in await database.select(OHLCV, time_frame="1h")]
        timestamps_4h = [ohlcv[0] for ohlcv in await database.select(OHLCV, time_frame="4h")]
        coros = [_check_select_result(database, timestamp, "1h") for timestamp in timestamps_1h]
        coros += [_check_select_result(database, timestamp, "4h") for timestamp in timestamps_4h]
        await asyncio.gather(*coros)


async def test_create_tasks_concurrent_selects():
    async with get_database() as database:
        timestamps_1h = [ohlcv[0] for ohlcv in await database.select(OHLCV, time_frame="1h")]
        timestamps_1m = [ohlcv[0] for ohlcv in await database.select(OHLCV, time_frame="1m")]
        timestamps_4h = [
            ohlcv[0] for ohlcv in await database.select(OHLCV, time_frame="4h", size=50)
        ]

        calls_count = len(timestamps_1h) + len(timestamps_4h) + len(timestamps_1m)
        failed_calls = []
        success_calls = []

        async def select_task(db, timestamp, time_frame):
            try:
                await _check_select_result(db, timestamp, time_frame)
                success_calls.append((timestamp, time_frame))
            except Exception as error:
                failed_calls.append((timestamp, time_frame, error))

        tasks = []
        for timestamp in timestamps_1h:
            tasks.append(asyncio.get_event_loop().create_task(select_task(database, timestamp, "1h")))
        for timestamp in timestamps_4h:
            tasks.append(asyncio.get_event_loop().create_task(select_task(database, timestamp, "4h")))
        for timestamp in timestamps_1m:
            tasks.append(asyncio.get_event_loop().create_task(select_task(database, timestamp, "1m")))
            await asyncio_tools.wait_asyncio_next_cycle()

        await asyncio.gather(*tasks)
        assert len(success_calls) == calls_count
        assert failed_calls == []


async def test_stop_while_concurrent_select():
    async with get_database() as database:
        timestamps = [ohlcv[0] for ohlcv in await database.select(OHLCV, time_frame="1h")]
        await _check_select_result(database, timestamps[0])
        asyncio.create_task(asyncio.wait(
            asyncio.gather(*[
                _check_select_result(database, timestamp, expected_exception=sqlite3.ProgrammingError)
                for timestamp in timestamps
            ])
        ))
        await asyncio_tools.wait_asyncio_next_cycle()


async def test_double_database():
    async with get_database() as database1, get_database(DATA_FILE2) as database2:
        timestamps1 = [ohlcv[0] for ohlcv in await database1.select(OHLCV, time_frame="1h")]
        timestamps2 = [ohlcv[0] for ohlcv in await database2.select(OHLCV, time_frame="1h")]
        await asyncio.gather(*[_check_select_result(database1, timestamp) for timestamp in timestamps1])
        await asyncio.gather(*[_check_select_result(database2, timestamp) for timestamp in timestamps2])


async def test_double_database_stop_while_concurrent_select():
    async with get_database() as database1, get_database(DATA_FILE2) as database2:
        timestamps1 = [ohlcv[0] for ohlcv in await database1.select(OHLCV, time_frame="1h")]
        timestamps2 = [ohlcv[0] for ohlcv in await database2.select(OHLCV, time_frame="1h")]
        await _check_select_result(database1, timestamps1[0])
        await _check_select_result(database2, timestamps2[0])
        asyncio.create_task(asyncio.wait(
            asyncio.gather(*[
                _check_select_result(database1, timestamp, expected_exception=sqlite3.ProgrammingError)
                for timestamp in timestamps1
            ])
        ))
        asyncio.create_task(asyncio.wait(
            asyncio.gather(*[
                _check_select_result(database2, timestamp, expected_exception=sqlite3.ProgrammingError)
                for timestamp in timestamps2
            ])
        ))
        await asyncio_tools.wait_asyncio_next_cycle()


async def test_insert():
    async with get_temp_empty_database() as temp_empty_database:
        await temp_empty_database.insert(OHLCV, symbol="xyz", timestamp=1, price=1, date="01")
        assert await temp_empty_database.select(OHLCV) == [(1, 'xyz', '1', '01')]


async def test_insert_all():
    async with get_temp_empty_database() as temp_empty_database:
        await temp_empty_database.insert_all(
            OHLCV,
            symbol=["xyz", "abc"],
            timestamp=[1, 2],
            price=[1, 10],
            date=["01", "05"],
        )
        assert await temp_empty_database.select(OHLCV) == [(2, 'abc', '10', '05'), (1, 'xyz', '1', '01')]
        assert await temp_empty_database.select(OHLCV, date="05") == [(2, 'abc', '10', '05')]


async def test_delete():
    async with get_temp_empty_database() as temp_empty_database:
        await temp_empty_database.insert_all(
            OHLCV,
            symbol=["xyz", "abc"],
            timestamp=[1, 2],
            price=[1, 10],
            date=["01", "05"],
        )
        assert await temp_empty_database.select(OHLCV) == [(2, 'abc', '10', '05'), (1, 'xyz', '1', '01')]
        await temp_empty_database.delete(OHLCV, symbol="plop")
        assert await temp_empty_database.select(OHLCV) == [(2, 'abc', '10', '05'), (1, 'xyz', '1', '01')]
        await temp_empty_database.delete(OHLCV, symbol="xyz")
        assert await temp_empty_database.select(OHLCV) == [(2, 'abc', '10', '05')]
        await temp_empty_database.insert_all(
            OHLCV,
            symbol=["hoho", "dd"],
            timestamp=[11, 11],
            price=[1, 10],
            date=["01", "05"],
        )
        assert await temp_empty_database.select(OHLCV) == [
            (11, 'dd', '10', '05'), (11, 'hoho', '1', '01'), (2, 'abc', '10', '05')
        ]
        await temp_empty_database.delete(OHLCV, timestamp="11")
        assert await temp_empty_database.select(OHLCV) == [(2, 'abc', '10', '05')]
        await temp_empty_database.delete(OHLCV, date="05")
        assert await temp_empty_database.select(OHLCV) == []


async def test_create_index():
    async with get_temp_empty_database() as temp_empty_database:
        await temp_empty_database.insert(OHLCV, 1, symbol="xyz", price="1", date="01")
        await temp_empty_database.create_index(OHLCV, ["symbol", "timestamp"])
        assert await temp_empty_database.select(OHLCV) == [(1, 'xyz', '1', '01')]


async def _check_select_result(database, timestamp, time_frame="1h", expected_exception=None):
    try:
        ohlcv = await database.select(OHLCV, time_frame=time_frame, timestamp=str(timestamp))
        assert len(ohlcv) == 1
        assert ohlcv[0][0] == timestamp
    except Exception as error:
        if error.__class__ is expected_exception:
            pass
        else:
            raise
