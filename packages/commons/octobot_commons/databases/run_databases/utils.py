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

# pathlib.Path should not be used to keep consistency with str paths
import pathlib

import octobot_commons.enums as enums
import octobot_commons.logging as logging
import octobot_commons.constants as constants
import octobot_commons.databases.run_databases.run_databases_identifier as run_databases_identifier


def get_backtesting_related_run_path_identifiers_str(database_adaptor):
    """
    :return: database identifier fragments associated to the given database_adaptor used
    in backtesting
    """
    separator = (
        os.path.sep if database_adaptor.is_file_system_based else constants.DB_SEPARATOR
    )
    return {
        f"{separator}{enums.RunDatabases.BACKTESTING.value}{separator}",
        f"{separator}{enums.RunDatabases.OPTIMIZER.value}{separator}",
    }


def get_global_run_database_identifier(runs_identifier):
    """
    :return: a RunDatabasesIdentifier associated to the given runs_identifier
    """
    # used to split paths into str parts
    split_path = pathlib.Path(runs_identifier).parts
    try:
        if split_path[-2] == enums.RunDatabases.OPTIMIZER.value:
            # in optimizer
            # ex: [..., 'DipAnalyserTradingMode', 'Dip Analyser strat designer test', 'optimizer', 'optimizer_1']
            optimizer_id = (
                run_databases_identifier.RunDatabasesIdentifier.parse_optimizer_id(
                    split_path[-1]
                )
            )
            campaign_name = split_path[-3]
            trading_mode = split_path[-4]
            return run_databases_identifier.RunDatabasesIdentifier(
                trading_mode,
                optimization_campaign_name=campaign_name,
                backtesting_id=0,
                optimizer_id=optimizer_id,
            )
        # in backtesting
        # ex: [..., 'DipAnalyserTradingMode', 'Dip Analyser strat designer test', 'backtesting']
        campaign_name = split_path[-2]
        trading_mode = split_path[-3]
        return run_databases_identifier.RunDatabasesIdentifier(
            trading_mode,
            optimization_campaign_name=campaign_name,
            backtesting_id=0,
        )
    except IndexError as err:
        logging.get_logger("run_databases_utils").exception(
            err, True, f"Unhandled backtesting data path format: {runs_identifier}"
        )
        return None
