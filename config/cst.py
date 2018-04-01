from enum import Enum

MINUTE_TO_SECONDS = 60
START_EVAL_NOTE = 0.5
START_EVAL_PERTINENCE = 1


class EvaluatorRisk(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class EvaluatorStates(Enum):
    SHORT = 1
    VERY_SHORT = 2
    LONG = 3
    VERY_LONG = 4
    NEUTRAL = 5


class EvaluatorsPertinence(Enum):
    SocialEvaluator = 1
    TAEvaluator = 1


class PriceStrings(Enum):
    STR_PRICE_CLOSE = "close"
    STR_PRICE_OPEN = "open"
    STR_PRICE_HIGH = "high"
    STR_PRICE_LOW = "low"
    STR_PRICE_VOL = "vol"


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


# TODO : review
class TimeFramePertinence(Enum):
    ONE_MINUTE = 1, TimeFrames.ONE_MINUTE
    FIVE_MINUTES = 1, TimeFrames.FIVE_MINUTES
    THIRTY_MINUTES = 1, TimeFrames.THIRTY_MINUTES
    ONE_HOUR = 1, TimeFrames.ONE_HOUR
    TWO_HOURS = 1, TimeFrames.TWO_HOURS
    FOUR_HOURS = 1, TimeFrames.FOUR_HOURS
    ONE_DAY = 1, TimeFrames.ONE_DAY
    THREE_DAYS = 1, TimeFrames.THREE_DAYS
    ONE_WEEK = 1, TimeFrames.ONE_WEEK
    ONE_MONTH = 1, TimeFrames.ONE_MONTH
