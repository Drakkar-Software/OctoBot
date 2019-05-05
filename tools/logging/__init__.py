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

from logging import ERROR, getLevelName

from config import LOG_DATABASE, LOG_NEW_ERRORS_COUNT, BACKTESTING_NEW_ERRORS_COUNT
from tools.timestamp_util import get_now_time


logs_database = {
    LOG_DATABASE: [],
    LOG_NEW_ERRORS_COUNT: 0,
    BACKTESTING_NEW_ERRORS_COUNT: 0
}

LOGS_MAX_COUNT = 1000


def add_log(level, source, message):
    logs_database[LOG_DATABASE].append({
        "Time": get_now_time(),
        "Level": getLevelName(level),
        "Source": str(source),
        "Message": message
    })
    if len(logs_database[LOG_DATABASE]) > LOGS_MAX_COUNT:
        logs_database[LOG_DATABASE].pop(0)
    if level >= ERROR:
        logs_database[LOG_NEW_ERRORS_COUNT] += 1
        logs_database[BACKTESTING_NEW_ERRORS_COUNT] += 1


def get_errors_count(counter=LOG_NEW_ERRORS_COUNT):
    return logs_database[counter]


def reset_errors_count(counter=LOG_NEW_ERRORS_COUNT):
    logs_database[counter] = 0
