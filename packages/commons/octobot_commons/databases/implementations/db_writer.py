# pylint: disable=R0913,R0801
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
import octobot_commons.databases.bases.base_database as base_database
import octobot_commons.databases.document_database_adaptors as adaptors
import octobot_commons.errors as commons_errors
import octobot_commons.logging as commons_logging


class DBWriter(base_database.BaseDatabase):
    MAX_ROWS_BUFFER_SIZE = 500

    def __init__(
        self,
        file_path: str,
        database_adaptor=adaptors.TinyDBAdaptor,
        cache_size=None,
        **kwargs,
    ):
        super().__init__(
            file_path,
            database_adaptor=database_adaptor,
            cache_size=cache_size,
            **kwargs,
        )
        self.rows_buffer = {}
        self.rows_buffer_size = self.MAX_ROWS_BUFFER_SIZE

    async def log(self, table_name: str, row: dict, cache=True, rows_buffering=False):
        """
        Write a row into the given table
        :param table_name: name of the table
        :param row: row to write
        :param cache: When True, enables local cache
        :param rows_buffering: When True, defer actual database writing using a row buffer
        """
        if cache:
            try:
                self.cache.register(table_name, row)
            except commons_errors.UncachableValue:
                await self._database.insert(table_name, row)
        if rows_buffering:
            await self._buffer_row(table_name, row)
        else:
            await self._database.insert(table_name, row)

    async def update(self, table_name: str, row: dict, query, uuid=None):
        """
        Updates rows
        :param table_name: table to update data from
        :param row: updated data
        :param query: select query
        :param uuid: uuid to select data (enable faster operations)
        :return: the update result
        """
        return await self._database.update(table_name, row, query, uuid=uuid)

    async def upsert(
        self, table_name: str, row: dict, query, uuid=None, cache_query=None
    ):
        """
        Update or insert a row
        Upsert can be a very slow operation: avoid is as much as possible
        Upsert with uuid is fast though, try to use it when possible
        :param table_name: table to update data from
        :param row: updated data
        :param query: select query
        :param uuid: uuid to select data (enable faster operations)
        :param cache_query: query identifier associated to this row, can be used later on for faster upserts on
        the same row using cache
        :return: the upsert result when operating without cache
        """
        if uuid is not None or cache_query is None:
            return await self._database.upsert(table_name, row, query, uuid=uuid)
        if uuid := self.cache.cached_uuid(table_name, str(cache_query)):
            return await self._database.upsert(table_name, row, query, uuid=uuid)
        if result := self.cache.cached_query(table_name, str(cache_query)):
            result.update(row)
        else:
            await self._buffer_row(
                table_name, row, cache_query=cache_query, cache=False
            )
            self.cache.register(table_name, str(cache_query), result=row)
            return None

    async def update_many(self, table_name: str, update_values: list):
        """
        Updates multiple values at once, doesn't use cache
        """
        return await self._database.update_many(table_name, update_values)

    async def delete(self, table_name: str, dict_query: dict):
        """
        Deletes selected values at once, doesn't use cache
        """
        query = None
        if dict_query:
            if isinstance(dict_query, dict):
                self.cache.delete_from_rows_cache(table_name, dict_query)
                query = await self.search()
                for key, value in dict_query.items():
                    query = query[key] == value
            else:
                query = dict_query
        else:
            self.cache.clear(table_name)
        return await self._database.delete(table_name, query)

    async def delete_all(self, table_name: str):
        """
        Deletes all rows from a table
        """
        self.cache.clear(table_name)
        return await self._database.delete(table_name, None)

    async def log_many(self, table_name: str, rows: list, cache=True):
        """
        Inserts multiple values into the given table
        :param table_name: name of the table
        :param rows: rows to insert
        :param cache: when True, rows are written into a cache buffer and written in bulk when buffer will be full
        """
        if cache:
            for row in rows:
                try:
                    self.cache.register(table_name, row)
                except commons_errors.UncachableValue:
                    # can pass here since row will be inserted anyway
                    pass
        return await self._database.insert_many(table_name, rows)

    async def replace_all(self, table_name, rows: list, cache=True):
        """
        Deletes everything for the give table name and replace the content by the given rows
        :param table_name: name of the table
        :param rows: rows to insert
        :param cache: When True, rows will be registered in cache
        """
        await self.delete_all(table_name)
        await self.log_many(table_name, rows, cache=cache)

    async def flush(self):
        """
        Flushes all caches and "commit" to the database then forces the database to flush its own internal cache if any
        """
        try:
            await self._flush_all_rows_buffers(cache=True)
            await super().flush()
        except TypeError as err:
            commons_logging.get_logger(str(self)).exception(
                err,
                True,
                f"Error when writing database, this is probably due to a script that is "
                f"saving a non json-serializable value: {err}",
            )

    async def _buffer_row(self, table, row, cache_query=None, cache=True):
        try:
            self.rows_buffer[table].append((row, cache_query))
            if len(self.rows_buffer[table]) >= self.rows_buffer_size:
                await self._flush_rows_buffer(table, cache=cache)
        except KeyError:
            self.rows_buffer[table] = [(row, cache_query)]

    async def _flush_rows_buffer(self, table, cache=True):
        uuids = await self.log_many(
            table, tuple(row[0] for row in self.rows_buffer[table]), cache=cache
        )
        for index, row in enumerate(self.rows_buffer[table]):
            self.cache.register(table, str(row[1]), uuid=uuids[index])
        self.rows_buffer[table] = []

    async def _flush_all_rows_buffers(self, cache=True):
        for table, rows in self.rows_buffer.items():
            uuids = await self.log_many(
                table, tuple(row[0] for row in rows), cache=cache
            )
            if cache:
                for index, row in enumerate(rows):
                    self.cache.register(table, str(row[1]), uuid=uuids[index])
            self.rows_buffer[table] = []
