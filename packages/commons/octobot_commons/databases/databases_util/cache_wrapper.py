# pylint: disable=R0902
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


class CacheWrapper:
    def __init__(
        self, file_path, cache_type, database_adaptor, tentacles_requirements, **kwargs
    ):
        self.file_path = file_path
        self.cache_type = cache_type
        self.database_adaptor = database_adaptor
        self.db_kwargs = kwargs
        self._cache_database = None
        self._db_path = None
        self.previous_db_metadata = None
        self.tentacles_requirements = tentacles_requirements.summary()

    def get_database(self) -> tuple:
        """
        Returns the database, creates it if messing
        """
        if self._cache_database is None:
            self._cache_database = self.cache_type(
                self.file_path, database_adaptor=self.database_adaptor, **self.db_kwargs
            )
            self._db_path = self._cache_database.get_db_path()
            return self._cache_database, True
        return self._cache_database, False

    def is_open(self):
        """
        :return: True if a database is open
        """
        return self._cache_database is not None

    async def close(self):
        """
        Closes the current database. Stores its metadata into self.previous_db_metadata
        """
        if self.is_open():
            self.previous_db_metadata = self._cache_database.get_non_default_metadata()
            await self._cache_database.close()
            self._cache_database = None
            return True
        return False

    async def clear(self):
        """
        Clears the database, deleting its data
        """
        if self._cache_database is not None:
            await self._cache_database.clear()

    def get_path(self):
        """
        :return: the database path
        """
        return self._db_path
