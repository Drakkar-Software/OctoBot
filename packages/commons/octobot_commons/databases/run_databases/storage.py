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

import octobot_commons.databases.run_databases.run_databases_provider as run_databases_provider
import octobot_commons.configuration as configuration
import octobot_commons.enums as enums
import octobot_commons.logging as logging


async def init_bot_storage(bot_id, run_database_identifier, clear_user_inputs):
    """
    Initializes the associated bot_id databases. Deletes any existing user input if clear_user_inputs is True
    """
    if not run_databases_provider.RunDatabasesProvider.instance().has_bot_id(bot_id):
        # only one run database per bot id
        await run_databases_provider.RunDatabasesProvider.instance().add_bot_id(
            bot_id, run_database_identifier
        )
        # always ensure database is valid
        run_db = run_databases_provider.RunDatabasesProvider.instance().get_run_db(
            bot_id
        )
        if run_database_identifier.enable_storage:
            await _repair_database_if_necessary(run_db)
            if clear_user_inputs:
                await configuration.clear_user_inputs(run_db)


async def close_bot_storage(bot_id):
    """
    :return: Close the bot_id associated run databases
    """
    if run_databases_provider.RunDatabasesProvider.instance().has_bot_id(bot_id):
        await run_databases_provider.RunDatabasesProvider.instance().close(bot_id)


async def _repair_database_if_necessary(database):
    try:
        # will raise if the db has an issue
        await database.all(enums.DBTables.METADATA.value)
    except json.JSONDecodeError:
        logging.get_logger(__name__).warning(
            f"Invalid database at {database}, resetting content."
        )
        # error in database, reset it
        await database.hard_reset()
