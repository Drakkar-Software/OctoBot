import os
import asyncio
import contextlib
import sqlite3
import tempfile

import mock
import pytest

import octobot_commons.errors as errors
import octobot_commons.databases.relational_databases.sqlite.base_sqlite_database as base_sqlite_database_module

pytestmark = pytest.mark.asyncio


class TestBaseSQLiteDatabaseConnectionPragmas:
    async def test_pragma_applied_on_initialize(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
            file_name = temp_file.name
        database = base_sqlite_database_module.BaseSQLiteDatabase(file_name)
        try:
            await database.initialize()
            journal_mode = await database.fetchone("PRAGMA journal_mode")
            synchronous_mode = await database.fetchone("PRAGMA synchronous")
            assert journal_mode[0] == "wal"
            assert synchronous_mode[0] == 2  # FULL
        finally:
            await database.stop()
            os.remove(file_name)


class TestBaseSQLiteDatabaseInitializeStop:
    async def test_initialize_and_stop(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
            file_name = temp_file.name
        database = base_sqlite_database_module.BaseSQLiteDatabase(file_name)
        try:
            await database.initialize()
            assert database.connection is not None
            await database.stop()
            assert database.connection is None
        finally:
            os.remove(file_name)

    async def test_stop_succeeds_when_checkpoint_would_be_busy(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
            file_name = temp_file.name
        database = base_sqlite_database_module.BaseSQLiteDatabase(file_name)
        try:
            await database.initialize()
            checkpoint_cursor = mock.AsyncMock()
            checkpoint_cursor.execute = mock.AsyncMock(
                side_effect=sqlite3.OperationalError("database table is locked"),
            )
            checkpoint_cursor.close = mock.AsyncMock()
            with mock.patch.object(
                database.connection,
                "cursor",
                mock.AsyncMock(return_value=checkpoint_cursor),
            ):
                await database.stop()
            assert database.connection is None
        finally:
            os.remove(file_name)


class TestBaseSQLiteDatabaseExecuteFetch:
    @contextlib.asynccontextmanager
    async def _empty_database(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
            file_name = temp_file.name
        database = base_sqlite_database_module.BaseSQLiteDatabase(file_name)
        await database.initialize()
        try:
            await database.execute(
                "CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)"
            )
            yield database
        finally:
            await database.stop()
            os.remove(file_name)

    async def test_execute_fetchone_fetchall_and_commit(self):
        async with self._empty_database() as database:
            await database.execute(
                "INSERT INTO sample (value) VALUES (?)",
                ("first",),
            )
            await database.commit()
            row = await database.fetchone("SELECT value FROM sample WHERE id = ?", (1,))
            assert row == ("first",)
            rows = await database.fetchall("SELECT value FROM sample")
            assert rows == [("first",)]

    async def test_executemany(self):
        async with self._empty_database() as database:
            await database.executemany(
                "INSERT INTO sample (value) VALUES (?)",
                [("one",), ("two",)],
            )
            await database.commit()
            rows = await database.fetchall("SELECT value FROM sample ORDER BY id")
            assert rows == [("one",), ("two",)]


class TestBaseSQLiteDatabaseReadOnly:
    @contextlib.asynccontextmanager
    async def _database_with_sample_table(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
            file_name = temp_file.name
        writable_database = base_sqlite_database_module.BaseSQLiteDatabase(file_name)
        await writable_database.initialize()
        await writable_database.execute(
            "CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)"
        )
        await writable_database.execute(
            "INSERT INTO sample (value) VALUES (?)",
            ("stored",),
        )
        await writable_database.commit()
        await writable_database.stop()

        read_only_database = base_sqlite_database_module.BaseSQLiteDatabase(file_name, read_only=True)
        await read_only_database.initialize()
        try:
            yield read_only_database
        finally:
            await read_only_database.stop()
            os.remove(file_name)

    async def test_fetchall_allowed_on_read_only_connection(self):
        async with self._database_with_sample_table() as database:
            rows = await database.fetchall("SELECT value FROM sample")
            assert rows == [("stored",)]

    async def test_execute_raises_on_read_only_connection(self):
        async with self._database_with_sample_table() as database:
            with pytest.raises(errors.DatabaseReadOnlyError):
                await database.execute("INSERT INTO sample (value) VALUES (?)", ("blocked",))

    async def test_commit_raises_on_read_only_connection(self):
        async with self._database_with_sample_table() as database:
            with pytest.raises(errors.DatabaseReadOnlyError):
                await database.commit()


class TestSqliteDatabaseWriteLock:
    async def test_concurrent_write_locks_for_same_path_serialize(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
            file_name = temp_file.name
        lock_order: list[str] = []

        async def hold_write_lock(lock_name: str):
            async with base_sqlite_database_module.sqlite_database_write_lock(file_name):
                lock_order.append(f"{lock_name}_start")
                await asyncio.sleep(0.05)
                lock_order.append(f"{lock_name}_end")

        await asyncio.gather(hold_write_lock("first"), hold_write_lock("second"))
        assert lock_order.index("first_start") < lock_order.index("first_end")
        assert lock_order.index("second_start") < lock_order.index("second_end")
        assert (
            lock_order.index("first_end") < lock_order.index("second_start")
            or lock_order.index("second_end") < lock_order.index("first_start")
        )
        os.remove(file_name)
