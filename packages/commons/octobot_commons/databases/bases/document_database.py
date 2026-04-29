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
import octobot_commons.logging


class DocumentDatabase:
    """
    DocumentDatabase is used to communicate with an underlying database
    """

    def __init__(self, database_adaptor):
        """
        DocumentDatabase constructor
        :param database_adaptor: database adaptor
        """
        self.adaptor = database_adaptor

    def initialize(self):
        """
        Initialize the database adaptor.
        """
        self.adaptor.initialize()

    def get_uuid(self, document) -> int:
        """
        Returns the uuid of the document
        :param document: the document
        """
        return self.adaptor.get_uuid(document)

    def get_db_path(self):
        """
        Select database path
        """
        return self.adaptor.db_path

    async def select(self, table_name: str, query, uuid=None) -> list:
        """
        Select data from the table_name table
        :param table_name: name of the table
        :param query: select query
        :param uuid: id of the document
        """
        return await self.adaptor.select(table_name, query, uuid=uuid)

    async def tables(self) -> list:
        """
        Select tables
        """
        return await self.adaptor.tables()

    async def insert(self, table_name: str, row: dict) -> int:
        """
        Insert dict data into the table_name table
        :param table_name: name of the table
        :param row: data to insert
        """
        return await self.adaptor.insert(table_name, row)

    async def upsert(self, table_name: str, row: dict, query, uuid=None) -> int:
        """
        Insert or update dict data into the table_name table
        :param table_name: name of the table
        :param row: data to insert
        :param query: select query
        :param uuid: id of the document
        """
        return await self.adaptor.upsert(table_name, row, query, uuid=uuid)

    async def insert_many(self, table_name: str, rows: list) -> list:
        """
        Insert multiple dict data into the table_name table
        :param table_name: name of the table
        :param rows: data to insert
        """
        return await self.adaptor.insert_many(table_name, rows)

    async def update(self, table_name: str, row: dict, query: dict, uuid=None) -> list:
        """
        Insert dict data into the table_name table
        :param table_name: name of the table
        :param row: data to update
        :param query: select statement
        :param uuid: id of the document
        """
        return await self.adaptor.update(table_name, row, query, uuid=uuid)

    async def update_many(self, table_name: str, update_values: list) -> list:
        """
        Update multiple values from the table_name table
        :param table_name: name of the table
        :param update_values: values to update
        """
        return await self.adaptor.update(table_name, update_values)

    async def delete(self, table_name: str, query, uuid=None) -> list:
        """
        Delete data from the table_name table
        :param table_name: name of the table
        :param query: select query
        :param uuid: id of the document
        """
        return await self.adaptor.delete(table_name, query, uuid=uuid)

    async def count(self, table_name: str, query) -> int:
        """
        Counts documents in the table_name table
        :param table_name: name of the table
        :param query: select query
        """
        return await self.adaptor.count(table_name, query)

    async def query_factory(self):
        """
        Creates a new empty select query
        """
        return await self.adaptor.query_factory()

    async def hard_reset(self):
        """
        Completely reset the database
        """
        self.get_logger().debug("hard resetting database")
        return await self.adaptor.hard_reset()

    def is_hard_reset_error(self, err: Exception) -> bool:
        """
        returns True if the given error should trigger
        a hard reset of the database
        """
        return self.adaptor.is_hard_reset_error(err)

    async def flush(self):
        """
        Flushes the database cache
        """
        self.get_logger().debug("flushing database")
        return await self.adaptor.flush()

    async def close(self):
        """
        Closes the database
        """
        self.get_logger().debug("closing database")
        return await self.adaptor.close()

    def get_logger(self):
        """
        :return: the database logger
        """
        return octobot_commons.logging.get_logger(str(self))

    def __str__(self):
        return f"{self.__class__.__name__} with adaptor: {self.adaptor}"

    @classmethod
    @contextlib.asynccontextmanager
    async def locked_database(cls, *args, **kwargs):
        """
        Instantiate and then ensure lock is acquired before initializing the database.
        Closes the database and then releases the lock when exiting
        :param args: args to pass to the database constructor
        :param kwargs: kwargs to pass to the database constructor
        """
        instance = None
        lock_acquired = False
        try:
            instance = cls(*args, **kwargs)
            if instance.adaptor.is_multiprocessing():
                await instance.adaptor.acquire()
                lock_acquired = True
            instance.initialize()
            yield instance
        finally:
            if instance is not None:
                try:
                    await instance.close()
                finally:
                    if lock_acquired and instance.adaptor.is_multiprocessing():
                        await instance.adaptor.release()
