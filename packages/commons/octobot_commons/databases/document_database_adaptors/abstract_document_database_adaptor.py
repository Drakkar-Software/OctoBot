# pylint: disable=W0613, R0904
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
import octobot_commons.multiprocessing_util as multiprocessing_util
import octobot_commons.enums as commons_enums


class AbstractDocumentDatabaseAdaptor:
    """
    AbstractDatabaseAdaptor is an interface listing document databases public methods
    """

    HARD_RESET_ERRORS = []  # errors that should trigger a hard reset

    def __init__(self, db_path: str, **kwargs):
        """
        TinyDBAdaptor constructor
        :param db_path: database path
        :param kwargs: kwargs to pass to the underlying db driver constructor
        """
        self.db_path = db_path

    def initialize(self):
        """
        Initialize the database.
        """
        raise NotImplementedError("initialize is not implemented")

    @staticmethod
    def is_file_system_based() -> bool:
        """
        Returns True when this database is identified as a file in the current file system,
        False when it's managed by a database server
        """
        raise NotImplementedError("is_file_system_based is not implemented")

    @staticmethod
    def get_db_file_ext() -> str:
        """
        Returns the database file extension. Implemented in file system based databases
        """
        raise NotImplementedError("get_db_file_ext")

    @staticmethod
    async def create_identifier(identifier):
        """
        Initialize the identifier by creating it in the database
        """
        raise NotImplementedError("identifier")

    @staticmethod
    async def identifier_exists(identifier, is_full_identifier) -> bool:
        """
        Returns True when the given identifier is part of an existing database identifier
        :param identifier: the identifier to look into
        :param is_full_identifier: when True, only check identifiers that don't have sub identifiers.
        When False, only check identifiers that have sub identifiers
        """
        raise NotImplementedError("identifier_exists")

    @staticmethod
    async def get_sub_identifiers(identifier, ignored_identifiers):
        """
        Returns an iterable over the existing sub-identifiers under the given identifier
        """
        raise NotImplementedError("get_sub_identifiers")

    @staticmethod
    async def get_single_sub_identifier(identifier, ignored_identifiers) -> str:
        """
        Returns the name of the only sub-identifier at a given parent identifier, None otherwise
        example use: get the name of the only exchange the backtesting happened on if it only ran on a single exchange,
        """
        raise NotImplementedError("get_single_sub_identifier")

    def get_uuid(self, document) -> int:
        """
        Returns the uuid of the document
        :param document: the document
        """
        raise NotImplementedError("get_uuid is not implemented")

    async def select(self, table_name: str, query, uuid=None) -> list:
        """
        Select data from the table_name table
        :param table_name: name of the table
        :param query: select query
        :param uuid: id of the document
        """
        raise NotImplementedError("select is not implemented")

    async def insert(self, table_name: str, row: dict) -> int:
        """
        Insert dict data into the table_name table
        :param table_name: name of the table
        :param row: data to insert
        """
        raise NotImplementedError("insert is not implemented")

    async def upsert(self, table_name: str, row: dict, query, uuid=None) -> int:
        """
        Insert or update dict data into the table_name table
        :param table_name: name of the table
        :param row: data to insert
        :param query: select query
        :param uuid: id of the document
        """
        raise NotImplementedError("upsert is not implemented")

    async def tables(self) -> list:
        """
        Select tables
        """
        raise NotImplementedError("tables is not implemented")

    async def insert_many(self, table_name: str, rows: list) -> list:
        """
        Insert multiple dict data into the table_name table
        :param table_name: name of the table
        :param rows: data to insert
        """
        raise NotImplementedError("insert_many is not implemented")

    async def update(self, table_name: str, row: dict, query, uuid=None) -> list:
        """
        Select data from the table_name table
        :param table_name: name of the table
        :param row: data to update
        :param query: select query
        :param uuid: id of the document
        """
        raise NotImplementedError("update is not implemented")

    async def update_many(self, table_name: str, update_values: list) -> list:
        """
        Update multiple values from the table_name table
        :param table_name: name of the table
        :param update_values: values to update
        """
        raise NotImplementedError("update_many is not implemented")

    async def delete(self, table_name: str, query, uuid=None) -> list:
        """
        Delete data from the table_name table
        :param table_name: name of the table
        :param query: select query
        :param uuid: id of the document
        """
        raise NotImplementedError("delete is not implemented")

    async def count(self, table_name: str, query) -> int:
        """
        Counts documents in the table_name table
        :param table_name: name of the table
        :param query: select query
        """
        raise NotImplementedError("count is not implemented")

    async def query_factory(self):
        """
        Creates a new empty select query
        """
        raise NotImplementedError("query_factory is not implemented")

    async def hard_reset(self):
        """
        Completely reset the database
        """
        raise NotImplementedError("hard_reset is not implemented")

    @classmethod
    def is_hard_reset_error(cls, error) -> bool:
        """
        returns True if the given error should trigger
        a hard reset of the database
        """
        for error_class in cls.HARD_RESET_ERRORS:
            if isinstance(error, error_class):
                return True
        return False

    async def flush(self):
        """
        Flushes the database cache
        """
        raise NotImplementedError("flush is not implemented")

    async def close(self):
        """
        Closes the database
        """
        raise NotImplementedError("close is not implemented")

    def __str__(self):
        return f"{self.__class__.__name__} [{self.db_path}]"

    @staticmethod
    def is_multiprocessing():
        """
        Returns True if the current process is run in a multiprocessing context using the multiprocessing_util module.
        """
        try:
            multiprocessing_util.get_lock(
                commons_enums.MultiprocessingLocks.DBLock.value
            )
            return True
        except KeyError:
            # no lock to acquire: we are not in a multiprocessing context
            return False

    @staticmethod
    def _get_lock():
        return multiprocessing_util.get_lock(
            commons_enums.MultiprocessingLocks.DBLock.value
        )

    async def acquire(self):
        """
        Acquires the database lock.
        """
        self._get_lock().acquire()

    async def release(self):
        """
        Releases the database lock.
        """
        self._get_lock().release()
