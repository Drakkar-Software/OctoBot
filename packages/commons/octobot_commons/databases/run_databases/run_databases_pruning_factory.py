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
import octobot_commons.databases.run_databases.file_system_run_databases_pruner as file_system_run_databases_pruner


def run_databases_pruner_factory(run_databases_identifier, max_db_size):
    """
    :return: A RunDatabasesPruner instance
    """
    if run_databases_identifier.database_adaptor.is_file_system_based():
        return file_system_run_databases_pruner.FileSystemRunDatabasesPruner(
            run_databases_identifier,
            max_db_size,
        )
    raise NotImplementedError("Only file system based database pruner is implemented")
