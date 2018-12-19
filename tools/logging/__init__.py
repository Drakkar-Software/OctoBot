from logging import ERROR, getLevelName

from config import LOG_DATABASE, LOG_NEW_ERRORS_COUNT
from tools.timestamp_util import get_now_time


logs_database = {
    LOG_DATABASE: [],
    LOG_NEW_ERRORS_COUNT: 0
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


def reset_errors_count():
    logs_database[LOG_NEW_ERRORS_COUNT] = 0
