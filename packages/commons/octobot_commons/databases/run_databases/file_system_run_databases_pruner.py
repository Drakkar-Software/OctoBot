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
import os
import shutil

import octobot_commons.databases.run_databases.abstract_run_databases_pruner as abstract_run_databases_pruner


class FileSystemRunDatabasesPruner(
    abstract_run_databases_pruner.AbstractRunDatabasesPruner
):
    async def _explore_databases(self):
        self.all_db_data = [
            abstract_run_databases_pruner.DBData(
                directory,
                [FileSystemDBPartData(f) for f in self._get_all_files(directory)],
            )
            for directory in self._get_file_system_runs(self.databases_root_identifier)
        ]

    async def _prune_database(self, db_data):
        try:
            shutil.rmtree(db_data.identifier)
            return True
        except Exception as err:
            self.logger.exception(err, True, f"Error when deleting run database: {err}")
            return False

    async def _get_global_runs_identifiers(self, removed_databases):
        return {
            os.path.dirname(removed_database.identifier)
            for removed_database in removed_databases
        }

    def _get_file_system_runs(self, root):
        try:
            # use os.scandir as it is much faster than os.walk
            for entry in os.scandir(root):
                if self._is_run_top_level_folder(entry):
                    yield entry
                elif entry.is_dir():
                    yield from self._get_file_system_runs(entry)
        except FileNotFoundError:
            # nothing to explore
            pass

    def _get_all_files(self, root):
        for entry in os.scandir(root):
            if entry.is_file():
                yield entry
            elif entry.is_dir():
                yield from self._get_all_files(entry)

    def _is_run_top_level_folder(self, dir_entry):
        return os.path.isfile(os.path.join(dir_entry, self._run_db)) and any(
            identifier in dir_entry.path
            for identifier in self.backtesting_run_path_identifier
        )


class FileSystemDBPartData(abstract_run_databases_pruner.AbstractDBPartData):
    def __init__(self, identifier):
        super().__init__(identifier)
        self.size = os.path.getsize(self.identifier)
        self.last_modified_time = os.path.getmtime(self.identifier)
