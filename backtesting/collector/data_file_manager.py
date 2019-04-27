#  Drakkar-Software OctoBot
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
import json
import gzip
from os.path import basename, isfile, join, splitext
from os import listdir, remove

from tools.symbol_util import merge_currencies
from tools.time_frame_manager import TimeFrameManager
from config import CONFIG_DATA_COLLECTOR_PATH, TimeFrames, BacktestingDataFormats


DATA_FILE_EXT = ".data"
DATA_FILE_TIME_WRITE_FORMAT = '%Y%m%d_%H%M%S'
DATA_FILE_TIME_READ_FORMAT = DATA_FILE_TIME_WRITE_FORMAT.replace("_", "")
DATA_FILE_TIME_DISPLAY_FORMAT = '%d %B %Y at %H:%M:%S'
TIME_FRAMES_TO_DISPLAY = [TimeFrames.THIRTY_MINUTES.value, TimeFrames.ONE_HOUR.value,
                          TimeFrames.FOUR_HOURS.value, TimeFrames.ONE_DAY.value]


def interpret_file_name(file_name):
    data = basename(file_name).split("_")
    try:
        exchange_name = data[0]
        symbol = merge_currencies(data[1], data[2])
        data_type = get_data_type(file_name)
        file_ext = get_file_ending(data_type)
        timestamp = data[3] + data[4].replace(file_ext, "")
    except KeyError:
        exchange_name = None
        symbol = None
        timestamp = None
        data_type = None

    return exchange_name, symbol, timestamp, data_type


def build_file_name(exchange, symbol, ending=DATA_FILE_EXT):
    symbol_str = symbol.replace('/', '_').replace('-', '_').upper()
    return f"{exchange.strip().lower()}_{symbol_str}_" \
           f"{time.strftime(DATA_FILE_TIME_WRITE_FORMAT)}{ending}"


def write_data_file(file_name, content):
    with gzip.open(file_name, 'wt') as json_file:
        json.dump(content, json_file)


def read_data_file(file_name):
    try:
        # try zipfile
        with gzip.open(file_name, 'r') as file_to_parse:
            file_content = json.loads(file_to_parse.read())
    except OSError:
        # try without unzip
        with open(file_name) as file_to_parse:
            file_content = json.loads(file_to_parse.read())
    return file_content


def get_data_type(file_name):
    if file_name.endswith(DATA_FILE_EXT):
        return BacktestingDataFormats.REGULAR_COLLECTOR_DATA


def get_file_ending(data_type):
    if data_type == BacktestingDataFormats.REGULAR_COLLECTOR_DATA:
        return DATA_FILE_EXT


def get_time_frames(file_path, content):
    data_type = get_data_type(file_path)
    if data_type == BacktestingDataFormats.REGULAR_COLLECTOR_DATA:
        return content.keys()


def get_ohlcv_per_timeframe(file_path, content):
    data_type = get_data_type(file_path)
    if data_type == BacktestingDataFormats.REGULAR_COLLECTOR_DATA:
        return content


def get_candles_count(file_path, tf_content):
    data_type = get_data_type(file_path)
    if data_type == BacktestingDataFormats.REGULAR_COLLECTOR_DATA:
        return len(tf_content[0])


def get_number_of_candles(file_path):
    try:
        content = read_data_file(file_path)
        if content:
            candles_info = []
            time_frames = get_time_frames(file_path, content)
            min_time_frame = TimeFrameManager.find_min_time_frame(time_frames)
            additional_time_frames = [min_time_frame.value]
            for tf in TIME_FRAMES_TO_DISPLAY:
                if tf not in additional_time_frames:
                    additional_time_frames.append(tf)

            ohlcv_per_tf = get_ohlcv_per_timeframe(file_path, content)
            for time_frame in additional_time_frames:
                if time_frame in ohlcv_per_tf:
                    tf_content = ohlcv_per_tf[time_frame]
                    candles_count = get_candles_count(file_path, tf_content) if tf_content else 0
                    candles_info.append(f"{time_frame}: {candles_count}")

            return ", ".join(candles_info)
        return 0
    except Exception as e:
        return f"Impossible to read datafile: {e}"


def get_date(time_info):
    time_object = time.strptime(time_info, DATA_FILE_TIME_READ_FORMAT)
    return time.strftime(DATA_FILE_TIME_DISPLAY_FORMAT, time_object)


def get_file_description(file_name):
    SYMBOL = "symbol"
    EXCHANGE = "exchange"
    DATE = "date"
    CANDLES = "candles"
    TYPE = "type"
    exchange_name, symbol, time_info, data_type = interpret_file_name(file_name)
    return {
        SYMBOL: symbol,
        EXCHANGE: exchange_name,
        DATE: get_date(time_info),
        CANDLES: get_number_of_candles(join(CONFIG_DATA_COLLECTOR_PATH, file_name)),
        TYPE: data_type.name
    }


def is_valid_ending(ending):
    return ending in [DATA_FILE_EXT]


def get_all_available_data_files():
    path = CONFIG_DATA_COLLECTOR_PATH
    try:
        files = [file
                 for file in listdir(path)
                 if isfile(join(path, file)) and is_valid_ending(splitext(file)[1])]
    except FileNotFoundError:
        files = []
    return files


def delete_data_file(file_name):
    try:
        file_path = join(CONFIG_DATA_COLLECTOR_PATH, file_name)
        if isfile(file_path):
            remove(file_path)
            return True, ""
        else:
            return False, f"file can't be found"
    except Exception as e:
        return False, e
