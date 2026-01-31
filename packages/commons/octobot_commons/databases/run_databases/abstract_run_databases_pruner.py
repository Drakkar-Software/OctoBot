# pylint: disable=W0703
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
import time

import octobot_commons.enums as enums
import octobot_commons.logging as logging
import octobot_commons.databases.implementations as databases_implementations
import octobot_commons.databases.run_databases.utils as run_databases_utils


class AbstractRunDatabasesPruner:
    def __init__(self, run_databases_identifier, max_databases_size):
        self.logger = logging.get_logger(self.__class__.__name__)
        self.database_adaptor = run_databases_identifier.database_adaptor
        self.databases_root_identifier = run_databases_identifier.data_path
        self.max_databases_size = max_databases_size
        self.all_db_data = []
        self.backtesting_run_path_identifier = (
            run_databases_utils.get_backtesting_related_run_path_identifiers_str(
                self.database_adaptor
            )
        )
        self._run_db = run_databases_identifier.get_db_full_name(
            enums.RunDatabases.RUN_DATA_DB.value
        )

    async def explore(self):
        """
        Explore self.databases_root_identifier to gather storage
        statistics to be used in prune_oldest_run_databases
        """
        t_start = time.time()
        await self._explore_databases()
        total_time = round(time.time() - t_start, 2)
        if total_time > 1:
            self.logger.debug(
                f"Explored run databases for pruning in {total_time} seconds."
            )

    async def prune_oldest_run_databases(self):
        """
        Delete the necessary backtesting run data for the total backtesting storage
        size to be <= self.max_databases_size. Deletes oldest run data first
        """
        self.all_db_data = sorted(
            self.all_db_data, key=lambda data: data.last_modified_time
        )
        removed_databases = []
        while self._get_total_db_size() > self.max_databases_size:
            if await self._prune_database(self.all_db_data[0]):
                removed_databases.append(self.all_db_data[0])
                self.all_db_data = self.all_db_data[1:]
        if removed_databases:
            await self._update_backtesting_runs_metadata(removed_databases)
            self._log_summary(removed_databases)

    async def _explore_databases(self):
        raise NotImplementedError("_explore_databases is not implemented")

    async def _prune_database(self, db_data):
        raise NotImplementedError("_prune_database is not implemented")

    async def _get_global_runs_identifiers(self, removed_databases):
        raise NotImplementedError("_get_global_runs_identifiers is not implemented")

    async def _update_backtesting_runs_metadata(self, removed_databases):
        for global_runs_identifier in await self._get_global_runs_identifiers(
            removed_databases
        ):
            await self._update_metadata(global_runs_identifier)

    async def _update_metadata(self, global_runs_identifier):
        run_db_identifier = run_databases_utils.get_global_run_database_identifier(
            global_runs_identifier
        )
        if run_db_identifier is not None:
            remaining_run_ids = {
                int(identifier)
                for identifier in await run_db_identifier.get_backtesting_run_ids()
            }
            async with databases_implementations.DBWriterReader.database(
                run_db_identifier.get_backtesting_metadata_identifier()
            ) as reader_writer:
                found_runs = await reader_writer.all(enums.DBTables.METADATA.value)
                # iterate in reverse order to keep only latest appearance of each id
                metadata = []
                added_runs = set()
                for run in found_runs[::-1]:
                    run_id = run[enums.BacktestingMetadata.ID.value]
                    if run_id in remaining_run_ids and run_id not in added_runs:
                        metadata.append(run)
                        added_runs.add(run_id)
                await reader_writer.replace_all(enums.DBTables.METADATA.value, metadata)

    def _log_summary(self, removed_databases):
        first_removed = removed_databases[0].get_human_readable_last_modified_time()
        last_removed = removed_databases[-1].get_human_readable_last_modified_time()
        self.logger.debug(
            f"Deleted the {len(removed_databases)} oldest run data from the {first_removed} to the {last_removed}"
        )

    def _get_total_db_size(self):
        return sum(db_data.size for db_data in self.all_db_data)


class DBData:
    def __init__(self, identifier, parts):
        self.identifier = identifier
        self.parts = parts
        self.size = sum(part.size for part in self.parts)
        self.last_modified_time = max(part.last_modified_time for part in self.parts)

    def get_human_readable_last_modified_time(self):
        """
        :return: self.last_modified_time in a human-readable format
        """
        return time.strftime(
            "%Y-%m-%d %H:%M:%S", time.strptime(time.ctime(self.last_modified_time))
        )


class AbstractDBPartData:
    def __init__(self, identifier):
        self.identifier = identifier
        self.size = None
        self.last_modified_time = None
