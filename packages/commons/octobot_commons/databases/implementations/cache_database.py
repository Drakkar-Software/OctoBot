# pylint: disable=C0116,R0801
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
import copy
import sortedcontainers

import octobot_commons.enums as enums
import octobot_commons.databases.implementations.db_writer as writer
import octobot_commons.databases.document_database_adaptors as adaptors


class CacheDatabase(writer.DBWriter):
    CACHE_TABLE = enums.CacheDatabaseTables.CACHE.value
    CACHE_METADATA_TABLE = enums.CacheDatabaseTables.METADATA.value
    UUID_KEY = "uuid"

    def __init__(
        self,
        file_path: str,
        database_adaptor=adaptors.TinyDBAdaptor,
        cache_size=None,
        **kwargs
    ):
        super().__init__(
            file_path,
            database_adaptor=database_adaptor,
            cache_size=cache_size,
            **kwargs
        )
        self._are_metadata_written = False
        self._local_cache = None
        self.metadata = {
            enums.CacheDatabaseColumns.TYPE.value: self.__class__.__name__,
        }

    def get_non_default_metadata(self):
        metadata = copy.copy(self.metadata)
        metadata.pop(enums.CacheDatabaseColumns.TYPE.value)
        return metadata

    def add_metadata(self, additional_metadata: dict):
        self.metadata.update(additional_metadata)

    async def _ensure_metadata(self):
        if not self._are_metadata_written:
            await self._database.upsert(
                self.CACHE_METADATA_TABLE, self.metadata, None, uuid=1
            )
            self._are_metadata_written = True

    async def _ensure_local_cache(self, identifier_key, update=False):
        if update or self._local_cache is None:
            self._local_cache = sortedcontainers.SortedDict()
            for cache in await self.get_cache():
                cache[self.UUID_KEY] = self._database.get_uuid(cache)
                self._local_cache[cache[identifier_key]] = cache

    async def get_metadata(self):
        return await self._database.select(self.CACHE_METADATA_TABLE, None, uuid=1)

    async def get_cache(self):
        return await self._database.select(self.CACHE_TABLE, None)

    async def clear(self):
        await self._database.delete(self.CACHE_TABLE, None)
        await self._database.delete(self.CACHE_METADATA_TABLE, None)
        await super().clear()
        self._local_cache = sortedcontainers.SortedDict()
        self._are_metadata_written = False
        # always rewrite metadata as they are necessary to handle cache later
        await self._ensure_metadata()
        await self.flush()

    async def _get_from_local_cache(self, identifier_key, identifier_value, sub_key):
        await self._ensure_local_cache(identifier_key)
        return self._local_cache[identifier_value][sub_key]

    async def _needs_update(
        self, identifier_key, identifier_value, sub_key, value
    ) -> bool:
        try:
            return (
                await self._get_from_local_cache(
                    identifier_key, identifier_value, sub_key
                )
                != value
            )
        except KeyError:
            return True
