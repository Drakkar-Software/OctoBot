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
import os
import typing

import octobot_backtesting.constants as constants
import octobot_backtesting.collectors as collectors
import octobot_backtesting.importers as importers
import octobot_commons.tentacles_management as tentacles_management
import octobot_commons.logging as commons_logging


async def create_importer_from_backtesting_file_name(config,
                                                     backtesting_file,
                                                     default_importer=None) -> typing.Optional[importers.DataImporter]:
    collector_klass = tentacles_management.get_deep_class_from_parent_subclasses(
        _parse_class_name_from_backtesting_file(backtesting_file), collectors.DataCollector)
    if collector_klass:
        importer_class = collector_klass.IMPORTER
    else:
        commons_logging.get_logger().debug(f"No specific exchange importer identified for '{backtesting_file}' "
                                           f"(maybe its filename has been changed). Using {default_importer.__name__}.")
        importer_class = default_importer
    importer = importer_class(config, backtesting_file) if importer_class else None

    if not importer:
        return None

    await importer.initialize()
    return importer


def get_default_importer(default_collector_class=collectors.AbstractExchangeHistoryCollector) -> importers.DataImporter:
    available_collectors = tentacles_management.get_all_classes_from_parent(default_collector_class)
    try:
        return available_collectors[0].IMPORTER
    except KeyError:
        return None


def _parse_class_name_from_backtesting_file(backtesting_file):
    return os.path.basename(backtesting_file).split(constants.BACKTESTING_DATA_FILE_SEPARATOR)[0]
