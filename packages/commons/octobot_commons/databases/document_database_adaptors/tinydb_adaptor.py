# pylint: disable=C0301, R0904, R1732, C0116, W0231, W0231
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
import json
import os

try:
    import tinydb
    import tinydb.storages
    import tinydb.middlewares
    import tinydb.table
except ImportError:
    pass

import octobot_commons.logging as commons_logging
import octobot_commons.constants as constants
import octobot_commons.errors as errors
import octobot_commons.databases.document_database_adaptors.abstract_document_database_adaptor as abstract_document_database_adaptor


class TinyDBAdaptor(abstract_document_database_adaptor.AbstractDocumentDatabaseAdaptor):
    """
    TinyDBAdaptor is an AbstractDatabaseAdaptor implemented using tinydb: a minimal python only
    local document database.
    Warning: loads the whole file in RAM and must be closed to ensure writing
    """

    DEFAULT_WRITE_CACHE_SIZE = 5000
    HARD_RESET_ERRORS = [
        json.JSONDecodeError
    ]  # errors that should trigger a hard reset

    def __init__(self, file_path: str, cache_size: int = None, **kwargs):
        """
        TinyDBAdaptor constructor.
        :param file_path: path to the database file
        :param cache_size: size of the in memory cache (number of operations before updating the file
        :param kwargs: unused
        """
        super().__init__(file_path)
        self.database = None
        self.cache_size = cache_size

    def initialize(self):
        """
        Initialize the database: opens the database file.
        """

        storage = self._get_storage()
        middleware = tinydb.middlewares.CachingMiddleware(storage)
        middleware.WRITE_CACHE_SIZE = self.cache_size or self.DEFAULT_WRITE_CACHE_SIZE
        try:
            self.database = tinydb.TinyDB(self.db_path, storage=middleware)
        except FileNotFoundError as err:
            raise errors.DatabaseNotFoundError(
                f'Can\'t open database at "{self.db_path}"'
            ) from err

    @staticmethod
    def _get_storage():
        class LazyJSONStorage(tinydb.storages.JSONStorage):
            def __init__(
                self,
                path: str,
                create_dirs=False,
                encoding=None,
                access_mode="r+",
                **kwargs,
            ):
                """
                Only creates the json file when actually needing to access it
                # from tinydb.storages.JSONStorage
                Create a new instance.

                Also creates the storage file, if it doesn't exist and the access mode is appropriate for writing.

                :param path: Where to store the JSON data.
                :param access_mode: mode in which the file is opened (r, r+, w, a, x, b, t, +, U)
                :type access_mode: str
                """

                tinydb.storages.Storage.__init__(self)

                self._mode = access_mode
                self.kwargs = kwargs

                # custom
                self._path = path
                self._create_dirs = create_dirs
                self._encoding = encoding
                self._lazy_handle = None

                # ensure path
                if not self._create_dirs:
                    self._ensure_path()

            def _ensure_path(self):
                dir_path = os.path.dirname(self._path)
                if dir_path and not os.path.exists(dir_path):
                    raise FileNotFoundError(self._path)

            @property
            def _handle(self):
                # create and open file once and only when self._handle is used
                if self._lazy_handle is None:
                    # Create the file if it doesn't exist and creating is allowed by the
                    # access mode
                    if any(
                        character in self._mode for character in ("+", "w", "a")
                    ):  # any of the writing modes
                        tinydb.storages.touch(self._path, create_dirs=self._create_dirs)

                    # Open the file for reading/writing
                    self._lazy_handle = open(
                        self._path, mode=self._mode, encoding=self._encoding
                    )
                return self._lazy_handle

            def close(self) -> None:
                if self._lazy_handle is None:
                    # never opened the file: don't call self._handle (that would create it)
                    return
                self._handle.close()
                self._lazy_handle = None

        return LazyJSONStorage

    @staticmethod
    def is_file_system_based() -> bool:
        """
        Returns True when this database is identified as a file in the current file system,
        False when it's managed by a database server
        """
        return True

    @staticmethod
    def get_db_file_ext() -> str:
        """
        Returns the database file extension. Implemented in file system based databases
        """
        return constants.TINYDB_EXT

    @staticmethod
    async def create_identifier(identifier):
        """
        Initialize the identifier by creating it in the database
        """
        if not os.path.exists(identifier):
            os.makedirs(identifier)

    @staticmethod
    async def identifier_exists(identifier, is_full_identifier) -> bool:
        """
        Returns True when the given identifier is part of an existing database identifier
        :param identifier: the identifier to look into
        :param is_full_identifier: when True, only check identifiers that don't have sub identifiers.
        When False, only check identifiers that have sub identifiers
        """
        return (
            os.path.isfile(identifier)
            if is_full_identifier
            else os.path.isdir(identifier)
        )

    @staticmethod
    async def get_sub_identifiers(identifier, ignored_identifiers):
        """
        Returns an iterable over the existing sub-identifiers under the given identifier
        """
        for folder in os.scandir(identifier):
            if (
                await TinyDBAdaptor.identifier_exists(folder, False)
                and folder.name not in ignored_identifiers
            ):
                yield folder.name

    @staticmethod
    async def get_single_sub_identifier(identifier, ignored_identifiers) -> str:
        """
        Returns the name of the only sub-identifier at a given parent identifier, None otherwise
        example use: get the name of the only exchange the backtesting happened on if it only ran on a single exchange,
        """
        exchange_folders = [
            folder.name
            for folder in os.scandir(identifier)
            if os.path.isdir(folder) and folder.name not in ignored_identifiers
        ]
        return exchange_folders[0] if len(exchange_folders) == 1 else None

    def get_uuid(self, document) -> int:
        """
        Returns the uuid of the document
        :param document: the document
        """
        return document.doc_id

    async def select(self, table_name: str, query, uuid=None) -> list:
        """
        Select data from the table_name table
        :param table_name: name of the table
        :param query: select query
        :param uuid: id of the document
        """
        if uuid is None:
            return (
                self.database.table(table_name).search(query)
                if query
                else self.database.table(table_name).all()
            )
        return self.database.table(table_name).get(doc_id=uuid)

    async def tables(self) -> list:
        """
        Select tables
        """
        return list(self.database.tables())

    async def insert(self, table_name: str, row: dict) -> int:
        """
        Insert dict data into the table_name table
        :param table_name: name of the table
        :param row: data to insert
        """
        return self.database.table(table_name).insert(row)

    async def upsert(self, table_name: str, row: dict, query, uuid=None) -> int:
        """
        Insert or update dict data into the table_name table
        :param table_name: name of the table
        :param row: data to insert
        :param query: select query
        :param uuid: id of the document
        """
        if uuid is None:
            return self.database.table(table_name).upsert(row, query)
        return self.database.table(table_name).upsert(
            tinydb.table.Document(row, doc_id=uuid)
        )

    async def insert_many(self, table_name: str, rows: list) -> list:
        """
        Insert multiple dict data into the table_name table
        :param table_name: name of the table
        :param rows: data to insert
        """
        return self.database.table(table_name).insert_multiple(rows)

    async def update(self, table_name: str, row: dict, query, uuid=None) -> list:
        """
        Select data from the table_name table
        :param table_name: name of the table
        :param row: data to update
        :param query: select query
        :param uuid: id of the document
        """
        if uuid is None:
            return self.database.table(table_name).update(row, query)
        return self.database.table(table_name).update(
            tinydb.table.Document(row, doc_id=uuid)
        )

    async def update_many(self, table_name: str, update_values: list) -> list:
        """
        Update multiple values from the table_name table
        :param table_name: name of the table
        :param update_values: values to update
        """
        return self.database.table(table_name).update_multiple(update_values)

    async def delete(self, table_name: str, query, uuid=None) -> list:
        """
        Delete data from the table_name table
        :param table_name: name of the table
        :param query: select query
        :param uuid: id of the document
        """
        if uuid is None:
            if query is None:
                return self.database.drop_table(table_name)
            return self.database.table(table_name).remove(query)
        return self.database.table(table_name).remove(doc_ids=(uuid,))

    async def count(self, table_name: str, query) -> int:
        """
        Counts documents in the table_name table
        :param table_name: name of the table
        :param query: select query
        """
        return self.database.table(table_name).count(query)

    async def query_factory(self):
        """
        Creates a new empty select query
        """
        return tinydb.Query()

    async def hard_reset(self):
        """
        Completely reset the database
        """
        await self.close()
        os.remove(self.db_path)
        self.initialize()

    async def flush(self):
        """
        Flushes the database cache
        """
        return self.database.storage.flush()

    async def close(self):
        """
        Closes the database
        """
        try:
            return self.database.close()
        except AttributeError:
            # when self.database didn't open properly
            pass
        except TypeError as err:
            commons_logging.get_logger(str(self)).exception(
                err,
                True,
                f"Error when writing database, this is probably due to a script that "
                f"is saving a non json-serializable value: {err}",
            )
