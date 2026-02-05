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
import os.path as path
import os
from datetime import datetime

import octobot_commons.databases as databases
import octobot_commons.enums as common_enums
import octobot_commons.time_frame_manager as tmf_manager
import octobot_commons.errors as commons_errors

import octobot_backtesting.constants as constants
import octobot_backtesting.enums as enums


def get_backtesting_file_name(clazz, identifier, data_format=enums.DataFormats.REGULAR_COLLECTOR_DATA):
    return f"{clazz.__name__}{constants.BACKTESTING_DATA_FILE_SEPARATOR}" \
           f"{identifier()}{get_file_ending(data_format)}"


def get_data_type(file_name):
    if file_name.endswith(constants.BACKTESTING_DATA_FILE_EXT):
        return enums.DataFormats.REGULAR_COLLECTOR_DATA


def get_file_ending(data_type):
    if data_type == enums.DataFormats.REGULAR_COLLECTOR_DATA:
        return constants.BACKTESTING_DATA_FILE_EXT


def get_date(time_info) -> str:
    """
    :param time_info: Timestamp in seconds of the time to convert
    :return: A human readable date at the backtesting data file time format
    """
    return datetime.fromtimestamp(time_info).strftime(constants.BACKTESTING_DATA_FILE_TIME_DISPLAY_FORMAT)


async def get_database_description(database):
    description = (await database.select(enums.DataTables.DESCRIPTION, size=1))[0]
    version = description[1]
    if version == "2.0":
        data_type = description[2]
        if data_type == enums.DataType.EXCHANGE.value:
            symbols = json.loads(description[4])
            time_frames = [common_enums.TimeFrames(tf) for tf in json.loads(description[5])]
            candles_count = (await database.select_count(
                enums.ExchangeDataTables.OHLCV, ["*"],
                time_frame=tmf_manager.find_min_time_frame(time_frames).value
            ))[0][0]
            candles_length = int(candles_count / len(symbols)) if symbols else 0
            return {
                enums.DataFormatKeys.TIMESTAMP.value: description[0],
                enums.DataFormatKeys.VERSION.value: description[1],
                enums.DataFormatKeys.DATA_TYPE.value: enums.DataType.EXCHANGE.value,
                enums.DataFormatKeys.EXCHANGE.value: description[3],
                enums.DataFormatKeys.SYMBOLS.value: symbols,
                enums.DataFormatKeys.TIME_FRAMES.value: time_frames,
                enums.DataFormatKeys.START_TIMESTAMP.value: description[6],
                enums.DataFormatKeys.END_TIMESTAMP.value: description[7],
                enums.DataFormatKeys.CANDLES_LENGTH.value: candles_length,
            }
        elif data_type == enums.DataType.SOCIAL.value:
            def _parse_list(value):
                try:
                    parsed = json.loads(value) if value else []
                    return parsed if isinstance(parsed, list) else []
                except (json.JSONDecodeError, TypeError):
                    return []

            sources = _parse_list(description[3]) if len(description) > 3 else []
            symbols = _parse_list(description[4]) if len(description) > 4 else []
            start_timestamp = description[5] if len(description) > 5 else 0
            end_timestamp = description[6] if len(description) > 6 else 0
            services = _parse_list(description[7]) if len(description) > 7 else []
            exchange = ""
            return {
                enums.DataFormatKeys.TIMESTAMP.value: description[0],
                enums.DataFormatKeys.VERSION.value: description[1],
                enums.DataFormatKeys.DATA_TYPE.value: enums.DataType.SOCIAL.value,
                enums.DataFormatKeys.EXCHANGE.value: exchange,
                enums.DataFormatKeys.SERVICES.value: services,
                enums.DataFormatKeys.SYMBOLS.value: symbols if isinstance(symbols, list) else [],
                enums.DataFormatKeys.TIME_FRAMES.value: [],
                enums.DataFormatKeys.START_TIMESTAMP.value: start_timestamp,
                enums.DataFormatKeys.END_TIMESTAMP.value: end_timestamp,
                enums.DataFormatKeys.CANDLES_LENGTH.value: 0,
            }
    elif version == "1.0":
        return {
            enums.DataFormatKeys.TIMESTAMP.value: description[0],
            enums.DataFormatKeys.VERSION.value: description[1],
            enums.DataFormatKeys.DATA_TYPE.value: enums.DataType.EXCHANGE.value,
            enums.DataFormatKeys.EXCHANGE.value: description[2],
            enums.DataFormatKeys.SYMBOLS.value: json.loads(description[3]),
            enums.DataFormatKeys.TIME_FRAMES.value: [common_enums.TimeFrames(tf) for tf in json.loads(description[4])],
            enums.DataFormatKeys.START_TIMESTAMP.value: 0,
            enums.DataFormatKeys.END_TIMESTAMP.value: 0,
            enums.DataFormatKeys.CANDLES_LENGTH.value:
                                    int((await database.select_count(enums.ExchangeDataTables.OHLCV, ["*"],\
                                    time_frame=tmf_manager.find_min_time_frame([common_enums.TimeFrames(tf)
                                                                    for tf in json.loads(description[4])]).value))[0][0]
                                    / len(json.loads(description[3])))
        }
    elif version == "1.1":
        return {
            enums.DataFormatKeys.TIMESTAMP.value: description[0],
            enums.DataFormatKeys.VERSION.value: description[1],
            enums.DataFormatKeys.DATA_TYPE.value: enums.DataType.EXCHANGE.value,
            enums.DataFormatKeys.EXCHANGE.value: description[2],
            enums.DataFormatKeys.SYMBOLS.value: json.loads(description[3]),
            enums.DataFormatKeys.TIME_FRAMES.value: [common_enums.TimeFrames(tf) for tf in json.loads(description[4])],
            enums.DataFormatKeys.START_TIMESTAMP.value: description[5],
            enums.DataFormatKeys.END_TIMESTAMP.value: description[6],
            enums.DataFormatKeys.CANDLES_LENGTH.value:
                                    int((await database.select_count(enums.ExchangeDataTables.OHLCV, ["*"],\
                                    time_frame=tmf_manager.find_min_time_frame([common_enums.TimeFrames(tf)
                                                                    for tf in json.loads(description[4])]).value))[0][0]
                                    / len(json.loads(description[3])))
        }
    else:
        raise RuntimeError(f"Unknown datafile version: {version}")


async def get_file_description(database_file):
    database = None
    try:
        database = databases.SQLiteDatabase(database_file)
        await database.initialize()
        description = await get_database_description(database)
    except (commons_errors.DatabaseNotFoundError, TypeError):
        description = None
    finally:
        if database is not None:
            await database.stop()
    return description


def is_valid_ending(ending):
    return ending in [constants.BACKTESTING_DATA_FILE_EXT]


def get_all_available_data_files(data_collector_path):
    try:
        files = [file
                 for file in os.listdir(data_collector_path)
                 if path.isfile(path.join(data_collector_path, file)) and is_valid_ending(path.splitext(file)[1])]
    except FileNotFoundError:
        files = []
    return files


def delete_data_file(data_collector_path, file_name):
    try:
        file_path = path.join(data_collector_path, file_name)
        if path.isfile(file_path):
            os.remove(file_path)
            return True, ""
        else:
            return False, f"file can't be found"
    except Exception as e:
        return False, e
