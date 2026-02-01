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
import json

import octobot_commons.constants as common_constants
import octobot_commons.errors as common_errors
import octobot_commons.databases as databases

import octobot_backtesting.constants as constants
import octobot_backtesting.data as data
import octobot_backtesting.enums as enums
import octobot_backtesting.importers as importers
import octobot_backtesting.importers.exchanges.util as importers_util


class SocialDataImporter(importers.DataImporter):
    def __init__(self, config, file_path):
        super().__init__(config, file_path)

        self.service_name = None
        self.sources = []
        self.symbols = []
        self.available_data_types = []
        self.has_all_events_history = False

    async def initialize(self) -> None:
        self.load_database()
        await self.database.initialize()

        # load description
        description = await self._get_database_description()
        self.service_name = description.get("service_name")
        self.sources = description.get("sources", [])
        self.symbols = description.get("symbols", [])
        self.has_all_events_history = bool(description.get("start_timestamp", 0))
        await self._init_available_data_types()

        self.logger.info(f"Loaded {self.service_name} data file with "
                         f"sources: {', '.join(self.sources) if self.sources else 'all'}, "
                         f"symbols: {', '.join(self.symbols) if self.symbols else 'all'}")

    def provides_accurate_price_time_frame(self) -> bool:
        return True

    async def _get_database_description(self):
        row = (await self.database.select(enums.DataTables.DESCRIPTION, size=1))[0]
        if row[2] == enums.DataType.SOCIAL.value:
            def _list(v):
                try:
                    out = json.loads(v) if v else []
                    return out if isinstance(out, list) else []
                except (json.JSONDecodeError, TypeError):
                    return []
            return {
                "timestamp": row[0],
                "version": row[1],
                "type": row[2],
                "service_name": row[3] if len(row) > 3 else "",
                "sources": _list(row[4]) if len(row) > 4 else [],
                "symbols": _list(row[5]) if len(row) > 5 else [],
                "start_timestamp": row[6] if len(row) > 6 else 0,
                "end_timestamp": row[7] if len(row) > 7 else 0,
            }
        return {
            "timestamp": row[0],
            "version": row[1],
            "service_name": row[2] if len(row) > 2 else "unknown",
            "sources": [],
            "symbols": [],
            "start_timestamp": 0,
            "end_timestamp": 0,
        }

    async def start(self) -> None:
        pass

    async def get_data_timestamp_interval(self, time_frame=None):
        """Get timestamp interval for social events"""
        minimum_timestamp: float = 0.0
        maximum_timestamp: float = 0.0

        if enums.SocialDataTables.SOCIAL_EVENTS in self.available_data_types:
            try:
                min_timestamp = (await self.database.select_min(enums.SocialDataTables.SOCIAL_EVENTS,
                                                                 [databases.SQLiteDatabase.TIMESTAMP_COLUMN]))[0][0]
                max_timestamp = (await self.database.select_max(enums.SocialDataTables.SOCIAL_EVENTS,
                                                                [databases.SQLiteDatabase.TIMESTAMP_COLUMN]))[0][0]
                if min_timestamp and max_timestamp:
                    minimum_timestamp = min_timestamp
                    maximum_timestamp = max_timestamp
            except (IndexError, common_errors.DatabaseNotFoundError):
                pass

        return minimum_timestamp, maximum_timestamp

    async def _init_available_data_types(self):
        self.available_data_types = [table for table in enums.SocialDataTables
                                     if await self.database.check_table_exists(table)
                                     and await self.database.check_table_not_empty(table)]

    async def _get_from_db(
            self, service_name, table,
            channel=None,
            symbol=None,
            limit=databases.SQLiteDatabase.DEFAULT_SIZE,
            timestamps=None,
            operations=None
    ):
        kwargs = {"service_name": service_name}
        if channel:
            kwargs["channel"] = channel
        if symbol:
            kwargs["symbol"] = symbol

        if timestamps:
            return await self.database.select_from_timestamp(
                table, size=limit,
                timestamps=timestamps,
                operations=operations,
                **kwargs
            )
        return await self.database.select(
            table, size=limit,
            **kwargs
        )

    async def get_social_events(self, service_name=None, channel=None, symbol=None,
                                limit=databases.SQLiteDatabase.DEFAULT_SIZE,
                                timestamps=None,
                                operations=None):
        """
        Get social events from database.
        :param service_name: Filter by service name (defaults to self.service_name)
        :param channel: Filter by channel
        :param symbol: Filter by symbol
        :param limit: Maximum number of events to return
        :param timestamps: List of timestamps to filter by
        :param operations: Operations for timestamp filtering
        :return: List of event dicts
        """
        service_name = service_name or self.service_name
        events = await self._get_from_db(
            service_name, enums.SocialDataTables.SOCIAL_EVENTS,
            channel=channel,
            symbol=symbol,
            limit=limit,
            timestamps=timestamps,
            operations=operations
        )
        # Parse JSON payloads
        result = []
        for event in events:
            event_dict = {
                "timestamp": event[0],
                "service_name": event[1],
                "channel": event[2],
                "symbol": event[3],
                "payload": json.loads(event[4]) if len(event) > 4 else {}
            }
            result.append(event_dict)
        return result

    async def get_social_events_from_timestamps(self, service_name=None, channel=None, symbol=None,
                                                 limit=databases.SQLiteDatabase.DEFAULT_SIZE,
                                                 inferior_timestamp=-1, superior_timestamp=-1):
        """
        Reads social events history from database and populates a local ChronologicalReadDatabaseCache.
        Warning: can't read data from before last given inferior_timestamp unless associated cache is reset
        """
        return await self._get_from_cache(service_name, channel, symbol, enums.SocialDataTables.SOCIAL_EVENTS,
                                          inferior_timestamp, superior_timestamp, self.get_social_events, limit)

    async def _get_from_cache(self, service_name, channel, symbol, data_type,
                              inferior_timestamp, superior_timestamp, set_cache_method, limit):
        cache_key = (service_name, channel, symbol, data_type)
        if not self.chronological_cache.has(cache_key):
            # ignore superior timestamp to select everything starting from inferior_timestamp and cache it
            select_superior_timestamp = -1
            timestamps, operations = importers_util.get_operations_from_timestamps(
                select_superior_timestamp,
                inferior_timestamp
            )
            # initializer without time_frame args are not expecting the time_frame argument, remove it
            # ignore the limit param as it might reduce the available cache and give false later select results
            init_cache_method_args = (
                service_name, channel, symbol, databases.SQLiteDatabase.DEFAULT_SIZE, timestamps, operations
            )
            self.chronological_cache.set(
                await set_cache_method(*init_cache_method_args),
                0,
                cache_key
            )
        return self.chronological_cache.get(inferior_timestamp, superior_timestamp, cache_key)
