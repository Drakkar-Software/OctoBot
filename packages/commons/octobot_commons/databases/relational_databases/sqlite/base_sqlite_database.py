# pylint: disable=C0116
#  Drakkar-Software OctoBot-Commons
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
import asyncio
import contextlib
import pathlib
import sqlite3

import octobot_commons.logging as logging
import octobot_commons.errors as errors
import octobot_commons.databases.relational_databases.sqlite.cursor_pool as cursor_pool
import octobot_commons.constants as constants

try:
    import aiosqlite
except ImportError:
    if constants.USE_MINIMAL_LIBS:
        class AiosqliteImportMock:
            def connect(self, *args):
                raise ImportError("aiosqlite not installed")

        aiosqlite = AiosqliteImportMock()
    else:
        raise

_write_locks: dict[str, asyncio.Lock] = {}


def _get_write_lock(file_path: str) -> asyncio.Lock:
    if file_path not in _write_locks:
        _write_locks[file_path] = asyncio.Lock()
    return _write_locks[file_path]


@contextlib.asynccontextmanager
async def sqlite_database_write_lock(file_path: str):
    async with _get_write_lock(file_path):
        yield


@contextlib.asynccontextmanager
async def open_sqlite_database(database_cls, file_path: str, read_only: bool = False):
    if read_only:
        database = database_cls(file_path, read_only=True)
        try:
            await database.initialize()
            yield database
        finally:
            await database.stop()
    else:
        async with sqlite_database_write_lock(file_path):
            database = database_cls(file_path, read_only=False)
            try:
                await database.initialize()
                yield database
            finally:
                await database.stop()


class BaseSQLiteDatabase:
    def __init__(self, file_name, read_only: bool = False):
        self.file_name = file_name
        self.read_only = read_only
        self.logger = logging.get_logger(self.__class__.__name__)
        self.connection = None
        self._cursor_pool = None

    def connection_pragmas(self) -> list[str]:
        # WAL: readers (mode=ro) get a consistent snapshot while writers are active;
        # uncommitted writer work stays in the WAL and is rolled back on recovery.
        # synchronous=FULL: fsync on commit so committed data survives sudden process kill.
        # busy_timeout: wait up to 5s when a read overlaps a writer checkpoint instead of failing immediately.
        return [
            "PRAGMA journal_mode=WAL",
            "PRAGMA synchronous=FULL",
            "PRAGMA busy_timeout=5000",
        ]

    def _ensure_writable(self) -> None:
        if self.read_only:
            raise errors.DatabaseReadOnlyError(
                f"Cannot write to read-only database (file: {self.file_name})"
            )

    async def initialize(self):
        try:
            if self.read_only:
                database_uri = f"{pathlib.Path(self.file_name).resolve().as_uri()}?mode=ro"
                self.connection = await aiosqlite.connect(database_uri, uri=True)
            else:
                self.connection = await aiosqlite.connect(self.file_name)
            self._cursor_pool = cursor_pool.CursorPool(self.connection)
            for pragma in self.connection_pragmas():
                async with self.aio_cursor() as cursor:
                    await cursor.execute(pragma)
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as err:
            raise errors.DatabaseNotFoundError(f"{err} (file: {self.file_name})")

    @contextlib.asynccontextmanager
    async def aio_cursor(self) -> sqlite3.Cursor:
        async with self._cursor_pool.idle_cursor() as cursor:
            yield cursor.cursor

    async def execute(self, sql: str, parameters=()) -> None:
        self._ensure_writable()
        async with self.aio_cursor() as cursor:
            await cursor.execute(sql, parameters)

    async def executemany(self, sql: str, parameters: list) -> None:
        self._ensure_writable()
        async with self.aio_cursor() as cursor:
            await cursor.executemany(sql, parameters)

    async def fetchall(self, sql: str, parameters=()) -> list:
        async with self.aio_cursor() as cursor:
            await cursor.execute(sql, parameters)
            return await cursor.fetchall()

    async def fetchone(self, sql: str, parameters=()) -> tuple | None:
        async with self.aio_cursor() as cursor:
            await cursor.execute(sql, parameters)
            return await cursor.fetchone()

    async def commit(self) -> None:
        self._ensure_writable()
        await self.connection.commit()

    async def stop(self):
        try:
            if self._cursor_pool is not None:
                await self._cursor_pool.close()
                self._cursor_pool = None
            if self.connection is not None and not self.read_only:
                # Normal shutdown: merge all WAL pages into the main DB and truncate the -wal file.
                # TRUNCATE resets the WAL to zero length so sidecar files do not accumulate across
                # open/close cycles. On SIGKILL this never runs; SQLite auto-checkpoint + next open
                # still recover.
                checkpoint_cursor = await self.connection.cursor()
                try:
                    await checkpoint_cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except sqlite3.OperationalError as error:
                    # TRUNCATE needs exclusive access; concurrent readers (same connection
                    # pool or another process) can still hold locks during shutdown.
                    # Skipping is safe: committed pages are already on disk (synchronous=FULL);
                    # only the -wal file may not be truncated until the next open/checkpoint.
                    self.logger.debug(
                        "wal_checkpoint(TRUNCATE) skipped during shutdown for %s: %s",
                        self.file_name,
                        error,
                    )
                finally:
                    await checkpoint_cursor.close()
        finally:
            if self.connection is not None:
                conn = self.connection
                self.connection = None
                await conn.close()
