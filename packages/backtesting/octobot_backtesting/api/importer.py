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
import octobot_backtesting.enums as backtesting_enums
import octobot_backtesting.importers as importers
import octobot_backtesting.util as util

import octobot_commons.errors as commons_errors
import octobot_commons.databases as databases


async def create_importer(config, backtesting_file, default_importer=None):
    return await util.create_importer_from_backtesting_file_name(config, backtesting_file,
                                                                 default_importer=default_importer)


def get_available_data_types(importer) -> list:
    return importer.available_data_types


def get_data_file(importer) -> str:
    return importer.file_path


def get_data_file_from_importers(available_importers, symbol, time_frame) -> str:
    for importer in available_importers:
        if symbol in get_available_symbols(importer) and \
                time_frame in get_available_time_frames(importer):
            return get_data_file_path(importer)
    return None


def get_data_file_path(importer) -> str:
    return importer.adapt_file_path_if_necessary()


def get_available_time_frames(exchange_importer) -> list:
    return exchange_importer.time_frames


def get_available_symbols(exchange_importer) -> list:
    return [symbol for symbol in exchange_importer.symbols]


async def get_data_timestamp_interval(exchange_importer, time_frame=None) -> (float, float):
    time_frame_value = time_frame.value if time_frame is not None else None
    return await exchange_importer.get_data_timestamp_interval(time_frame=time_frame_value)


async def get_all_ohlcvs(database_path, exchange_name, symbol, time_frame,
                         inferior_timestamp=-1, superior_timestamp=-1) -> list:
    timestamps, operations = importers.get_operations_from_timestamps(superior_timestamp, inferior_timestamp)
    try:
        async with databases.new_sqlite_database(database_path) as database:
            candles = await database.select_from_timestamp(backtesting_enums.ExchangeDataTables.OHLCV,
                                                           exchange_name=exchange_name, symbol=symbol,
                                                           time_frame=time_frame.value,
                                                           timestamps=timestamps,
                                                           operations=operations)
        return [candle_with_metadata[-1]
                for candle_with_metadata in sorted(importers.import_ohlcvs(candles), key=lambda x: x[0])]
    except commons_errors.DatabaseNotFoundError:
        return []


async def stop_importer(importer) -> None:
    await importer.stop()
