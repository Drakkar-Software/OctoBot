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
import octobot_commons.databases.implementations.cache_database as cache_database
import octobot_commons.enums as commons_enums
import octobot_commons.errors as errors


class CacheTimestampDatabase(cache_database.CacheDatabase):
    async def get(
        self,
        timestamp: float,
        name: str = commons_enums.CacheDatabaseColumns.VALUE.value,
    ) -> dict:
        """
        Returns the value associated to the given timestamp
        :param timestamp: timestamp to get data for
        :param name: identifier of the value to get, default is commons_enums.CacheDatabaseColumns.VALUE.value
        """
        try:
            return await self._get_from_local_cache(
                commons_enums.CacheDatabaseColumns.TIMESTAMP.value, timestamp, name
            )
        except KeyError as err:
            raise errors.NoCacheValue(
                f"No cache value associated to {timestamp}"
                if err.args[0] == timestamp
                else f"No {name} value associated to {timestamp} cache."
            )

    async def get_values(
        self,
        timestamp: float,
        name: str = commons_enums.CacheDatabaseColumns.VALUE.value,
        limit=-1,
        min_timestamp=0,
    ) -> list:
        """
        Returns all the values up to the given timestamp
        :param timestamp: last timestamp to read get data to
        :param name: identifier of the value to get, default is commons_enums.CacheDatabaseColumns.VALUE.value
        :param limit: maximum number of elements to return
        :param min_timestamp: timestamp to start returning data from
        """
        try:
            await self._ensure_local_cache(
                commons_enums.CacheDatabaseColumns.TIMESTAMP.value
            )
            values = [
                values[name]
                for value_timestamp, values in self._local_cache.items()
                if min_timestamp <= value_timestamp <= timestamp and name in values
            ]
            if limit != -1:
                return values[-limit:]
            return values
        except IndexError:
            raise errors.NoCacheValue(f"No cache value associated to {name}")
        except KeyError:
            raise errors.NoCacheValue(f"No {name} value associated to {name} cache.")

    async def set(
        self,
        timestamp: float,
        value,
        name: str = commons_enums.CacheDatabaseColumns.VALUE.value,
    ) -> None:
        """
        Sets a value at the given timestamp associated to the given identifier
        :param timestamp: timestamp to set data to
        :param value: value to set
        :param name: identifier of the value to set, default is commons_enums.CacheDatabaseColumns.VALUE.value
        """
        await self._ensure_metadata()
        saved_value = self.get_serializable_value(value)
        if await self._needs_update(
            commons_enums.CacheDatabaseColumns.TIMESTAMP.value,
            timestamp,
            name,
            saved_value,
        ):
            uuid = None
            set_value = {
                commons_enums.CacheDatabaseColumns.TIMESTAMP.value: timestamp,
                name: saved_value,
            }
            if timestamp in self._local_cache:
                # set uuid in case this value already exist in db
                uuid = self._local_cache[timestamp].get(self.UUID_KEY)
                self._local_cache[timestamp][
                    commons_enums.CacheDatabaseColumns.TIMESTAMP.value
                ] = timestamp
                self._local_cache[timestamp][name] = saved_value
            else:
                self._local_cache[timestamp] = set_value
            await self.upsert(
                self.CACHE_TABLE,
                set_value,
                None,
                uuid=uuid,
                cache_query={
                    commons_enums.CacheDatabaseColumns.TIMESTAMP.value: timestamp
                },
            )

    async def set_values(
        self,
        timestamps,
        values,
        name: str = commons_enums.CacheDatabaseColumns.VALUE.value,
        additional_values_by_key: dict = None,
    ) -> None:
        """
        Sets values at the given timestamps associated to the given identifiers
        :param timestamps: timestamps to set data to
        :param values: value to set
        :param name: identifier of the values to set, default is commons_enums.CacheDatabaseColumns.VALUE.value
        :param additional_values_by_key: other key/values to set a these timestamps
        """
        await self._ensure_local_cache(
            commons_enums.CacheDatabaseColumns.TIMESTAMP.value
        )
        to_bulk_update = {
            name: [self.get_serializable_value(value) for value in values]
        }
        if additional_values_by_key:
            to_bulk_update.update(
                {
                    key: [self.get_serializable_value(value) for value in values]
                    for key, values in additional_values_by_key.items()
                }
            )
        # use optimized multiple insert to speed up the database insert operation
        await self._bulk_update_values(timestamps, to_bulk_update)

    async def _bulk_update_values(self, timestamps, to_bulk_update):
        await self._ensure_metadata()
        rows = []
        can_just_insert_data = True
        key = None
        try:
            # try to write data in the scenario their timestamp is not in cache already: can insert directly
            for index, timestamp in enumerate(timestamps):
                if timestamp in self._local_cache:
                    row = self._local_cache[timestamp]
                    # will have to update data
                    can_just_insert_data = False
                else:
                    row = {
                        commons_enums.CacheDatabaseColumns.TIMESTAMP.value: timestamp
                    }
                for key, values in to_bulk_update.items():
                    row[key] = values[index]
                self._local_cache[timestamp] = row
                rows.append(row)
            if can_just_insert_data:
                await self.log_many(self.CACHE_TABLE, rows)
            else:
                await self._update_full_database()
        except IndexError:
            raise RuntimeError(
                f"Data to set are required to have the same length as the timestamps list. "
                f"Error on the {key} values"
            )

    async def _update_full_database(self):
        # to be called to avoid multiple upsert / update which can be very slow: take full advantage of multiple inserts
        # 1. recreate all database elements from self._local_cache
        all_rows = []
        for element in self._local_cache.values():
            # remove artificial data if any
            element.pop(self.UUID_KEY, None)
            all_rows.append(element)
        # 2. delete database content
        await self.delete_all(self.CACHE_TABLE)
        # 3. insert all local cache
        await self.log_many(self.CACHE_TABLE, all_rows)
        # 4. reset self._local_cache
        await self._ensure_local_cache(
            commons_enums.CacheDatabaseColumns.TIMESTAMP.value, update=True
        )

    async def _timestamp_query(self, timestamp):
        return (await self._database.query_factory()).t == timestamp

    async def get_cache(self):
        """
        :return: the sorted read cache values
        """
        # relies on the fact that python dicts keep order
        return sorted(
            await self._database.select(self.CACHE_TABLE, None),
            key=lambda x: x[commons_enums.CacheDatabaseColumns.TIMESTAMP.value],
        )
