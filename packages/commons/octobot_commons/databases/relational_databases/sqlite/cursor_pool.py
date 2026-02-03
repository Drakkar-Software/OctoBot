#  Drakkar-Software OctoBot-Backtesting
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

import octobot_commons.databases.relational_databases.sqlite.cursor_wrapper as cursor_wrapper


class CursorPool:
    def __init__(self, db_connection):
        self._db_connection = db_connection
        self._cursors = []

    @contextlib.asynccontextmanager
    async def idle_cursor(self) -> cursor_wrapper.CursorWrapper:
        """
        Yields an idle cursor, creates a new one if necessary
        """
        cursor = None
        try:
            cursor = await self._get_or_create_idle_cursor()
            cursor.idle = False
            yield cursor
        finally:
            if cursor is not None:
                cursor.idle = True

    async def close(self):
        """
        Close every cursor
        """
        await asyncio.gather(*(cursor.close() for cursor in self._cursors))

    async def _get_or_create_idle_cursor(self) -> cursor_wrapper.CursorWrapper:
        for cursor in self._cursors:
            if cursor.idle:
                return cursor
        cursor = cursor_wrapper.CursorWrapper(await self._db_connection.cursor())
        self._cursors.append(cursor)
        return cursor
