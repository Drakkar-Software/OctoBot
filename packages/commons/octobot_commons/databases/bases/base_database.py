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
import contextlib
import numpy

import octobot_commons.databases.document_database_adaptors as adaptors
import octobot_commons.databases.bases.document_database as document_database
import octobot_commons.databases.database_caches as database_cache


class BaseDatabase:
    def __init__(
        self,
        file_path: str,
        database_adaptor=adaptors.TinyDBAdaptor,
        cache_size=None,
        enable_storage=True,
        **kwargs,
    ):
        self.enable_storage = enable_storage
        self._database = None
        if self.enable_storage and database_adaptor is not None:
            self._database = document_database.DocumentDatabase(
                database_adaptor(file_path, cache_size=cache_size, **kwargs)
            )
            self._database.initialize()
        self.are_data_initialized = False
        self.are_data_initialized_by_key = {}
        self.cache = database_cache.GenericDatabaseCache()

    def set_initialized_flags(self, value, keys=None):
        """
        Updates the initialized values of the given keys
        :param value: the updated initialized value
        :param keys: keys to update. Updated every key if left to None
        """
        self.are_data_initialized = value
        for key in keys or self.are_data_initialized_by_key.keys():
            self.are_data_initialized_by_key[key] = value

    def get_db_path(self):
        """
        :return: the path to the current database's path
        """
        return self._database.get_db_path()

    async def search(self, dict_query: dict = None):
        """
        :param dict_query: initialization dict for the query
        :return: a search query
        """
        if dict_query is None:
            return await self._database.query_factory()
        return (await self._database.query_factory()).fragment(dict_query)

    async def count(self, table_name: str, query) -> int:
        """
        :param table_name: the table to count data from
        :param query: the query to count results from
        :return: the number of elements that match the given query
        """
        return await self._database.count(table_name, query)

    async def flush(self):
        """
        Flushes the database, "committing" operations into the database
        """
        await self._database.flush()

    async def hard_reset(self):
        """
        Completely resets the database as if it just was created
        """
        return await self._database.hard_reset()

    def is_hard_reset_error(self, err: Exception) -> bool:
        """
        returns True if the given error should trigger
        a hard reset of the database
        """
        return self._database.is_hard_reset_error(err)

    async def close(self):
        """
        Closes the database, flushes it first
        """
        if self.enable_storage:
            await self.flush()
            await self._database.close()

    async def clear(self):
        """
        Clears the database, removing everything from it
        """
        self.cache.clear()

    async def contains_row(self, table: str, row: dict):
        """
        Returns true if the given rows are included in the given table, also looking into internal cache
        :param table: the table to look into
        :param row: the row to find
        """
        if self.cache.contains_row(table, row):
            return True
        return await self.count(table, await self.search(row)) > 0

    def __str__(self):
        return f"{self.__class__.__name__}, database: {self._database}"

    @classmethod
    def _create_database(
        cls,
        *args,
        required_adaptor=False,
        cache_size=None,
        database_adaptor=None,
        **kwargs,
    ):
        if required_adaptor:
            adaptor = kwargs.pop("database_adaptor", adaptors.TinyDBAdaptor)
            if adaptor is None:
                raise RuntimeError("database_adaptor parameter required")
            adaptor_instance = adaptor(*args, cache_size=cache_size, **kwargs)
            return (
                cls(
                    *args,
                    database_adaptor=database_adaptor,
                    cache_size=cache_size,
                    **kwargs,
                ),
                adaptor_instance,
            )
        return cls(*args, cache_size=cache_size, **kwargs), None

    @classmethod
    @contextlib.asynccontextmanager
    async def database(
        cls, *args, with_lock=False, cache_size=None, database_adaptor=None, **kwargs
    ):
        """
        Yields a database and closes it when exiting the context manager
        :param args: arguments to pass to the database constructor
        :param with_lock: When True, creating a lock synchronized database
        :param cache_size: size of the internal database cache
        :param database_adaptor: Database class to use
        :param kwargs: keyword arguments to pass to the database constructor
        """
        database, adaptor_instance = cls._create_database(
            *args,
            required_adaptor=with_lock,
            cache_size=cache_size,
            database_adaptor=database_adaptor,
            **kwargs,
        )
        if with_lock:
            async with document_database.DocumentDatabase.locked_database(
                adaptor_instance
            ) as locked_db:
                database._database = locked_db
                yield database
                # context manager is taking care of closing the database
            return
        try:
            yield database
        finally:
            await database.close()

    @staticmethod
    def get_serializable_value(value):
        """
        Returns a json serializable value of the given element. Mostly used to serialize numpy types
        :param value: the element
        """
        return value.item() if isinstance(value, numpy.generic) else value
