from enum import Enum

MINUTE_TO_SECONDS = 60


class PriceStrings(Enum):
    STR_PRICE_CLOSE = "<CLOSE>"
    STR_PRICE_OPEN = "<OPEN>"
    STR_PRICE_HIGH = "<HIGH>"
    STR_PRICE_LOW = "<LOW>"
    STR_PRICE_VOL = "<VOL>"


class TimeFrames(Enum):
    ONE_MINUTE = 1
    FIVE_MINUTES = 5
    THIRTY_MINUTES = 30
    ONE_HOUR = 60
    TWO_HOURS = 120
    FOUR_HOURS = 240
    ONE_DAY = 1440
    THREE_DAYS = 4320
    ONE_WEEK = 10080
    ONE_MONTH = 43200
